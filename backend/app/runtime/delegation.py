"""Typed contracts and sequential execution for specialist-agent delegation."""

import asyncio
import logging
from dataclasses import replace
from time import perf_counter
from typing import Callable, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.contracts.specialists import AgentDefinition
from app.core.limits import RuntimeLimits
from app.core.logging import log_event, safe_error_message
from app.llm.contracts import LLMClient
from app.llm.pricing import PricingRegistry
from app.observability import TraceRecorder
from app.runtime.registry import AgentRegistry
from app.security import ContentTrust, SecurityPolicy
from app.security.approvals import ApprovalStore
from app.skills.registry import SkillRegistry
from app.tools.execution import ToolExecutor
from app.tools.registry import ToolRegistry

MAX_DELEGATION_OBJECTIVE_LENGTH = 2_000
MAX_DELEGATION_BACKGROUND_LENGTH = 2_000
MAX_DELEGATION_CONSTRAINTS_LENGTH = 1_000
MAX_DELEGATION_EXPECTED_OUTPUT_LENGTH = 1_000
MAX_DELEGATION_MEMORIES = 3
MAX_DELEGATION_MEMORY_CONTENT_LENGTH = 1_000
MAX_SUBAGENT_RESULT_LENGTH = 2_000


class DelegationMemory(BaseModel):
    """One explicitly approved memory excerpt for a child context."""

    model_config = ConfigDict(extra="forbid")

    reference: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1, max_length=MAX_DELEGATION_MEMORY_CONTENT_LENGTH)
    trust: ContentTrust = ContentTrust.RETRIEVED_MEMORY
    source_type: str = "memory"


class DelegationContext(BaseModel):
    """Bounded, intentionally selected information for one child run."""

    model_config = ConfigDict(extra="forbid")

    objective: str = Field(min_length=1, max_length=MAX_DELEGATION_OBJECTIVE_LENGTH)
    background: str | None = Field(default=None, max_length=MAX_DELEGATION_BACKGROUND_LENGTH)
    constraints: str | None = Field(default=None, max_length=MAX_DELEGATION_CONSTRAINTS_LENGTH)
    expected_output: str | None = Field(default=None, max_length=MAX_DELEGATION_EXPECTED_OUTPUT_LENGTH)
    selected_memories: list[DelegationMemory] = Field(
        default_factory=list, max_length=MAX_DELEGATION_MEMORIES
    )

    @field_validator("objective")
    @classmethod
    def require_objective(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class DelegationRequest(BaseModel):
    """A deliberately narrow request from a parent run to a specialist."""

    model_config = ConfigDict(extra="forbid")

    parent_run_id: str = Field(min_length=1)
    parent_iteration: int = Field(ge=1)
    target_agent: str = Field(min_length=1)
    objective: str = Field(min_length=1, max_length=MAX_DELEGATION_OBJECTIVE_LENGTH)
    context: DelegationContext
    #: Inherited unchanged from the parent run -- a subagent never crosses tenants.
    workspace_id: str | None = None

    @field_validator("target_agent", "objective")
    @classmethod
    def require_non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="before")
    @classmethod
    def accept_v43_context_shape(cls, value: object) -> object:
        """Accept the former supplied_context field while retaining one typed payload."""

        if not isinstance(value, dict) or "context" in value:
            return value
        raw = dict(value)
        raw["context"] = {
            "objective": raw.get("objective", ""),
            "background": raw.pop("supplied_context", None),
        }
        return raw

    @property
    def supplied_context(self) -> str | None:
        """Compatibility accessor for the V4.3 background field."""

        return self.context.background


class SubagentResult(BaseModel):
    """Safe, compact outcome of one isolated specialist run."""

    model_config = ConfigDict(extra="forbid")

    parent_run_id: str = Field(min_length=1)
    child_run_id: str | None = None
    agent_name: str = Field(min_length=1)
    objective: str = Field(min_length=1, max_length=MAX_DELEGATION_OBJECTIVE_LENGTH)
    success: bool
    answer: str | None = Field(default=None, max_length=MAX_SUBAGENT_RESULT_LENGTH)
    outcome: str | None = Field(default=None, max_length=MAX_SUBAGENT_RESULT_LENGTH)
    iterations: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    duration_ms: int = Field(default=0, ge=0)
    stop_reason: str | None = None
    error: str | None = Field(default=None, max_length=MAX_SUBAGENT_RESULT_LENGTH)

    @property
    def output(self) -> str | None:
        """Expose a common observation view without serializing child state."""

        return self.answer or self.outcome


class ParallelDelegationResult(BaseModel):
    """Ordered, bounded outcomes from one explicit parallel delegation action."""

    model_config = ConfigDict(extra="forbid")

    parent_run_id: str = Field(min_length=1)
    results: list[SubagentResult] = Field(min_length=1)

    @property
    def success(self) -> bool:
        return all(result.success for result in self.results)

    @property
    def output(self) -> None:
        """Parallel observations use their structured result view instead."""

        return None

    @property
    def error(self) -> None:
        return None


class DelegationObservation(BaseModel):
    """A runtime boundary outcome, distinct from a tool or subagent result."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["invalid", "unavailable"]
    target_agent: str
    success: Literal[False] = False
    output: None = None
    error: str


class DelegationExecutor(Protocol):
    """Boundary for executing one validated specialist request."""

    async def execute(self, request: DelegationRequest) -> SubagentResult:
        """Execute one request and return only a compact specialist outcome."""


class SequentialSubagentExecutor:
    """Construct and run one capability-scoped child agent at a time."""

    def __init__(
        self,
        *,
        agent_registry: AgentRegistry,
        tool_registry: ToolRegistry,
        skill_registry: SkillRegistry,
        llm_client_factory: Callable[[AgentDefinition], LLMClient],
        parent_limits: RuntimeLimits,
        security_policy: SecurityPolicy | None = None,
        approval_store: ApprovalStore | None = None,
        trace_recorder: TraceRecorder | None = None,
        pricing_registry: PricingRegistry | None = None,
    ) -> None:
        self._agent_registry = agent_registry
        self._tool_registry = tool_registry
        self._skill_registry = skill_registry
        self._llm_client_factory = llm_client_factory
        self._parent_limits = parent_limits
        self._security_policy = security_policy or SecurityPolicy.primary()
        self._approval_store = approval_store
        self._trace_recorder = trace_recorder
        self._pricing_registry = pricing_registry or PricingRegistry()
        self._logger = logging.getLogger(__name__)

    async def execute(self, request: DelegationRequest) -> SubagentResult:
        """Run a specialist sequentially, converting ordinary failures to results."""

        child_state: "AgentState | None" = None
        started_at = perf_counter()
        definition: AgentDefinition | None = None
        try:
            definition = self._agent_registry.load_agent(request.target_agent)
            from app.runtime.state import AgentState

            child_state = AgentState(goal=request.objective, agent_depth=1, workspace_id=request.workspace_id)
            log_event(
                self._logger,
                logging.INFO,
                "subagent_execution_started",
                parent_run_id=request.parent_run_id,
                child_run_id=child_state.run_id,
                agent=definition.name,
            )
            child_runner = self._build_child_runner(definition, request)
            log_event(
                self._logger,
                logging.DEBUG,
                "delegation_context_created",
                parent_run_id=request.parent_run_id,
                child_run_id=child_state.run_id,
                agent=definition.name,
                background_length=len(request.context.background or ""),
                constraints_length=len(request.context.constraints or ""),
                memory_count=len(request.context.selected_memories),
                available_tool_count=len(definition.allowed_tools),
                available_skill_count=len(definition.allowed_skills),
            )
            state = await child_runner.run(child_state.goal, state=child_state)
        except Exception as error:
            result = SubagentResult(
                parent_run_id=request.parent_run_id,
                child_run_id=child_state.run_id if child_state else None,
                agent_name=request.target_agent,
                objective=request.objective,
                success=False,
                iterations=child_state.iteration_count if child_state else 0,
                tool_calls=child_state.total_tool_calls if child_state else 0,
                duration_ms=round((perf_counter() - started_at) * 1000),
                stop_reason=child_state.stop_reason if child_state else None,
                error="Subagent execution failed.",
            )
            log_event(
                self._logger,
                logging.WARNING,
                "subagent_execution_failed",
                parent_run_id=request.parent_run_id,
                child_run_id=result.child_run_id,
                agent=request.target_agent,
                duration_ms=round((perf_counter() - started_at) * 1000),
                iterations=result.iterations,
                tool_calls=result.tool_calls,
                stop_reason=result.stop_reason,
                error=safe_error_message(error),
            )
            return result

        success = state.completed and state.stop_reason == "completed"
        result = SubagentResult(
            parent_run_id=request.parent_run_id,
            child_run_id=state.run_id,
            agent_name=definition.name,
            objective=request.objective,
            success=success,
            answer=_bounded_text(state.final_answer) if success else None,
            outcome="Specialist completed the delegated objective." if success else None,
            iterations=state.iteration_count,
            tool_calls=state.total_tool_calls,
            duration_ms=round((perf_counter() - started_at) * 1000),
            stop_reason=state.stop_reason,
            error=None if success else _bounded_text(
                state.final_answer or "Specialist did not complete the objective."
            ),
        )
        event = "subagent_execution_finished" if success else "subagent_execution_failed"
        log_event(
            self._logger,
            logging.INFO if success else logging.WARNING,
            event,
            parent_run_id=request.parent_run_id,
            child_run_id=result.child_run_id,
            agent=definition.name,
            duration_ms=round((perf_counter() - started_at) * 1000),
            iterations=result.iterations,
            tool_calls=result.tool_calls,
            stop_reason=result.stop_reason,
        )
        return result

    def _build_child_runner(
        self, definition: AgentDefinition, request: DelegationRequest
    ) -> "AgentRunner":
        """Build a new autonomous runtime with only specialist-granted capabilities."""

        from app.runtime.runner import AgentRunner

        limits = replace(
            self._parent_limits,
            max_iterations=(
                min(
                    definition.runtime_overrides.max_iterations
                    or self._parent_limits.max_iterations,
                    self._parent_limits.max_subagent_iterations,
                )
            ),
        )
        return AgentRunner(
            llm_client=self._llm_client_factory(definition),
            tool_registry=self._tool_registry.restricted_to(set(definition.allowed_tools)),
            skill_registry=self._skill_registry.restricted_to(set(definition.allowed_skills)),
            limits=limits,
            system_prompt=self._child_system_prompt(definition, request),
            delegation_enabled=False,
            delegation_context=request.context,
            agent_depth=1,
            security_policy=self._security_policy.with_specialist(definition),
            security_agent_name=definition.name,
            security_agent_type="specialist",
            parent_run_id=request.parent_run_id,
            tool_executor=ToolExecutor(
                self._tool_registry.restricted_to(set(definition.allowed_tools)),
                security_policy=self._security_policy.with_specialist(definition),
                trace_recorder=self._trace_recorder,
            ),
            approval_store=self._approval_store,
            trace_recorder=self._trace_recorder,
            pricing_registry=self._pricing_registry,
        )

    @staticmethod
    def _child_system_prompt(definition: AgentDefinition, request: DelegationRequest) -> str:
        """Compose base runtime guidance with just one specialist's instructions."""

        from app.runtime.prompt import SYSTEM_PROMPT

        context = request.context.background or "None supplied."
        constraints = request.context.constraints or "None supplied."
        expected_output = request.context.expected_output or "None specified."
        return (
            f"{SYSTEM_PROMPT}\n\nYou are the {definition.name} specialist.\n"
            f"Specialist instructions:\n{definition.instructions}\n\n"
            f"Delegated objective:\n{request.objective}\n\n"
            f"Relevant background:\n{context}\n\n"
            f"Constraints:\n{constraints}\n\n"
            f"Expected output:\n{expected_output}\n\n"
            "Complete only this delegated objective and return a concise final answer."
        )


def _bounded_text(value: str | None) -> str | None:
    """Keep child results useful without forwarding an unbounded final answer."""

    if value is None or len(value) <= MAX_SUBAGENT_RESULT_LENGTH:
        return value
    return f"{value[:MAX_SUBAGENT_RESULT_LENGTH - 3]}..."


class ParallelSubagentExecutor:
    """Run explicitly requested child delegations concurrently and collect every outcome."""

    def __init__(self, executor: DelegationExecutor, *, max_parallel_subagents: int) -> None:
        self._executor = executor
        self._max_parallel_subagents = max_parallel_subagents
        self._logger = logging.getLogger(__name__)

    async def execute(self, requests: list[DelegationRequest]) -> ParallelDelegationResult:
        """Execute a validated bounded batch without discarding sibling outcomes."""

        if not requests:
            raise ValueError("Parallel delegation requires at least one request.")
        if len(requests) > self._max_parallel_subagents:
            raise ValueError(
                f"Parallel delegation limit is {self._max_parallel_subagents}; "
                f"received {len(requests)} requests."
            )
        parent_run_id = requests[0].parent_run_id
        started_at = perf_counter()
        log_event(
            self._logger,
            logging.INFO,
            "parallel_delegation_started",
            parent_run_id=parent_run_id,
            delegation_count=len(requests),
            configured_limit=self._max_parallel_subagents,
        )
        outcomes = await asyncio.gather(
            *(self._executor.execute(request) for request in requests),
            return_exceptions=True,
        )
        results = [
            outcome
            if isinstance(outcome, SubagentResult)
            else _unexpected_parallel_failure(request, outcome)
            for request, outcome in zip(requests, outcomes, strict=True)
        ]
        event = "parallel_delegation_finished" if all(result.success for result in results) else "parallel_delegation_partial_failure"
        log_event(
            self._logger,
            logging.INFO if event.endswith("finished") else logging.WARNING,
            event,
            parent_run_id=parent_run_id,
            delegation_count=len(results),
            successful_count=sum(result.success for result in results),
            failed_count=sum(not result.success for result in results),
            duration_ms=round((perf_counter() - started_at) * 1000),
        )
        return ParallelDelegationResult(parent_run_id=parent_run_id, results=results)


def _unexpected_parallel_failure(
    request: DelegationRequest, outcome: BaseException,
) -> SubagentResult:
    """Convert an unexpected sibling exception without hiding successful siblings."""

    return SubagentResult(
        parent_run_id=request.parent_run_id,
        agent_name=request.target_agent,
        objective=request.objective,
        success=False,
        duration_ms=0,
        error="Subagent execution failed.",
    )
