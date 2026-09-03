"""Controlled, provider-neutral autonomous agent loop."""

import asyncio
import logging
from time import perf_counter

from pydantic import ValidationError

from app.artifacts.contracts import Artifact
from app.contracts.actions import AgentAction, normalize_caveats
from app.contracts.answers import AnswerSource
from app.contracts.investigation import InvestigationPlan
from app.core.exceptions import UnknownSkillError
from app.core.limits import RuntimeLimits
from app.core.logging import log_event, safe_error_message, safe_log_value
from app.llm.contracts import LLMClient
from app.llm.pricing import PricingRegistry, estimate_cost
from app.memory.manager import MemoryManager
from app.memory.retrieval import MemoryRetriever
from app.memory.writing import MemoryWritingPipeline
from app.observability import (
    InMemoryTraceStore,
    TraceEventType,
    TraceRecorder,
    TraceStatus,
    resolve_citations,
)
from app.reliability import RetryPolicy, classify_llm_failure
from app.reliability.retry import Sleep, default_sleep
from app.runtime.context import ContextBuilder
from app.runtime.control import RunControl
from app.runtime.delegation import (
    DelegationContext,
    DelegationExecutor,
    ParallelSubagentExecutor,
)
from app.runtime.fingerprints import tool_action_fingerprint
from app.runtime.planning import evaluate_finish, plan_progress, reconcile_plan
from app.runtime.prompt import SYSTEM_PROMPT
from app.runtime.registry import AgentRegistry
from app.runtime.state import AgentState, Observation, RunStatus, StopReason
from app.runtime.steps.delegation_step import DelegationStep
from app.runtime.steps.memory_step import MemoryStep
from app.runtime.steps.summarization_step import SummarizationStep
from app.runtime.summarization import (
    DeterministicTaskSummarizer,
    SummaryPolicy,
    TaskSummarizer,
)
from app.security import (
    PolicyDecision,
    PolicyResult,
    SecurityAction,
    SecurityPolicy,
    SecuritySubject,
)
from app.security.approvals import (
    ApprovalCheckpoint,
    ApprovalRequest,
    ApprovalStore,
    action_fingerprint,
    safe_argument_summary,
)
from app.skills.registry import SkillRegistry
from app.tools.contracts import ToolResult
from app.tools.execution import ToolExecutor
from app.tools.registry import ToolRegistry


class AgentRunner:
    """Run dynamic agent actions inside deterministic runtime boundaries."""

    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        skill_registry: SkillRegistry,
        tool_executor: ToolExecutor | None = None,
        limits: RuntimeLimits | None = None,
        memory_manager: MemoryManager | None = None,
        memory_retriever: MemoryRetriever | None = None,
        memory_writer: MemoryWritingPipeline | None = None,
        task_summarizer: TaskSummarizer | None = None,
        summary_policy: SummaryPolicy | None = None,
        agent_registry: AgentRegistry | None = None,
        delegation_executor: DelegationExecutor | None = None,
        parallel_delegation_executor: ParallelSubagentExecutor | None = None,
        system_prompt: str = SYSTEM_PROMPT,
        delegation_enabled: bool = True,
        delegation_context: DelegationContext | None = None,
        agent_depth: int = 0,
        security_policy: SecurityPolicy | None = None,
        security_agent_name: str = "primary",
        security_agent_type: str = "primary",
        parent_run_id: str | None = None,
        approval_store: ApprovalStore | None = None,
        trace_recorder: TraceRecorder | None = None,
        pricing_registry: PricingRegistry | None = None,
        retry_policy: RetryPolicy | None = None,
        retry_sleep: Sleep = default_sleep,
    ) -> None:
        self._llm_client = llm_client
        self._tool_registry = tool_registry
        self._security_policy = security_policy or SecurityPolicy.primary()
        self._trace_recorder = trace_recorder or TraceRecorder(InMemoryTraceStore())
        self._pricing_registry = pricing_registry or PricingRegistry()
        self._retry_policy = retry_policy or RetryPolicy()
        self._retry_sleep = retry_sleep
        self._tool_executor = tool_executor or ToolExecutor(
            tool_registry, security_policy=self._security_policy, trace_recorder=self._trace_recorder
        )
        self._skill_registry = skill_registry
        self._logger = logging.getLogger(__name__)
        self._limits = limits or RuntimeLimits()
        self._control = RunControl(
            limits=self._limits, agent_name=security_agent_name, agent_type=security_agent_type,
            agent_depth=agent_depth, parent_run_id=parent_run_id,
        )
        self._delegation = DelegationStep(
            control=self._control, agent_registry=agent_registry,
            executor=delegation_executor, parallel_executor=parallel_delegation_executor,
            security_policy=self._security_policy, enabled=delegation_enabled,
            trace_recorder=self._trace_recorder,
        )
        self._summary_policy = summary_policy or SummaryPolicy()
        self._summarization = SummarizationStep(
            summarizer=task_summarizer or DeterministicTaskSummarizer(),
            policy=self._summary_policy, trace_recorder=self._trace_recorder,
        )
        self._context_builder = ContextBuilder(
            tool_registry, skill_registry, self._limits,
            recent_observations=self._summary_policy.recent_observations,
            agent_registry=agent_registry,
            delegation_context=delegation_context,
        )
        self._agent_registry = agent_registry
        self._delegation_executor = delegation_executor
        self._parallel_delegation_executor = parallel_delegation_executor
        if (delegation_executor is not None and hasattr(delegation_executor, "_trace_recorder")
                and getattr(delegation_executor, "_trace_recorder", None) is None):
            # The concrete executor owns child-run construction; share the parent recorder.
            setattr(delegation_executor, "_trace_recorder", self._trace_recorder)
        if delegation_executor is not None and hasattr(delegation_executor, "_pricing_registry"):
            setattr(delegation_executor, "_pricing_registry", self._pricing_registry)
        self._system_prompt = system_prompt
        self._delegation_enabled = delegation_enabled
        self._agent_depth = agent_depth
        self._security_agent_name = security_agent_name
        self._security_agent_type = security_agent_type
        self._parent_run_id = parent_run_id
        self._approval_store = approval_store
        self._memory = MemoryStep(
            manager=memory_manager, retriever=memory_retriever, writer=memory_writer,
            trace_recorder=self._trace_recorder,
        )

    async def run(
        self,
        goal: str,
        *,
        session_id: str | None = None,
        workspace_id: str | None = None,
        state: AgentState | None = None,
    ) -> AgentState:
        """Execute bounded, model-selected actions for a single goal.

        ``workspace_id`` is only used to seed a *new* state -- when ``state``
        is already provided (a resumed or child run), its own
        ``state.workspace_id`` is authoritative.
        """

        state = state or AgentState(goal=goal, workspace_id=workspace_id)
        if state.goal != goal:
            raise ValueError("Provided agent state goal must match the run goal.")
        if state.agent_depth != self._agent_depth:
            raise ValueError("Provided agent state depth must match the runner depth.")
        if state.status is RunStatus.WAITING_FOR_APPROVAL:
            return state
        started_at = perf_counter()
        self._trace_recorder.start_run(
            run_id=state.run_id, parent_run_id=self._parent_run_id,
            agent_name=self._security_agent_name, agent_type=self._security_agent_type, goal=goal,
        )
        log_event(
            self._logger,
            logging.INFO,
            "agent_run_started",
            run_id=state.run_id,
            goal=safe_log_value(goal),
            max_iterations=self._limits.max_iterations,
            max_tool_calls=self._limits.max_tool_calls,
            max_recoverable_errors=self._limits.max_recoverable_errors,
            max_consecutive_duplicate_actions=self._limits.max_consecutive_duplicate_actions,
            max_parallel_subagents=self._limits.max_parallel_subagents,
            max_delegations_per_run=self._limits.max_delegations_per_run,
            max_subagent_iterations=self._limits.max_subagent_iterations,
            max_agent_depth=self._limits.max_agent_depth,
            agent_depth=self._agent_depth,
        )
        relevant_memories = await self._memory.retrieve(
            goal, run_id=state.run_id, workspace_id=state.workspace_id, session_id=session_id
        )

        try:
            await self._memory.record_goal(goal, run_id=state.run_id, workspace_id=state.workspace_id)
            while state.iteration_count < self._limits.max_iterations:
                iteration = state.iteration_count + 1
                log_event(
                    self._logger,
                    logging.DEBUG,
                    "iteration_started",
                    run_id=state.run_id,
                    iteration=iteration,
                    tool_calls=state.total_tool_calls,
                    errors=state.recoverable_error_count,
                )
                context = self._context_builder.build(
                    state,
                    working_memories=await self._memory.working(state.run_id, workspace_id=state.workspace_id),
                    relevant_memories=relevant_memories,
                )
                log_event(
                    self._logger,
                    logging.DEBUG,
                    "llm_context_stats",
                    run_id=state.run_id,
                    iteration=iteration,
                    observation_count=len(state.observations),
                    loaded_skill_count=len(state.loaded_skills),
                    available_tool_count=len(context["available_tools"]),
                    available_skill_count=len(context["available_skills"]),
                )
                log_event(
                    self._logger,
                    logging.DEBUG,
                    "llm_request_started",
                    run_id=state.run_id,
                    iteration=iteration,
                )
                llm_started_at = perf_counter()
                attempt = 1
                while True:
                    llm_span = self._trace_recorder.start_span(
                        state.run_id, TraceEventType.LLM_REQUEST_STARTED, name="llm_request", iteration=iteration,
                        metadata={"provider": type(self._llm_client).__name__, "model": self._llm_client.model, "attempt": attempt},
                    )
                    try:
                        # LLMDecision validates action as an AgentAction, so a provider
                        # returning anything else fails here as invalid model output.
                        decision = await self._llm_client.choose_decision(
                            system_prompt=self._system_prompt, context=context
                        )
                    except Exception as error:
                        failure = classify_llm_failure(error, run_id=state.run_id, iteration=iteration, attempt=attempt)
                        self._trace_recorder.finish_span(state.run_id, llm_span, TraceEventType.LLM_REQUEST_FAILED,
                            iteration=iteration, success=False, metadata={"failure_category": failure.category.value, "attempt": attempt})
                        self._trace_recorder.record(state.run_id, TraceEventType.OPERATION_FAILED, iteration=iteration,
                            metadata={"failure_category": failure.category.value, "source": failure.source, "attempt": attempt})
                        delay = self._retry_policy.retry_delay(failure)
                        if delay is None:
                            self._trace_recorder.record(state.run_id, TraceEventType.RETRY_EXHAUSTED, iteration=iteration,
                                metadata={"failure_category": failure.category.value, "source": failure.source, "attempt": attempt})
                            raise
                        self._trace_recorder.record(state.run_id, TraceEventType.RETRY_SCHEDULED, iteration=iteration,
                            metadata={"failure_category": failure.category.value, "source": failure.source, "attempt": attempt, "delay_ms": round(delay * 1000)})
                        if failure.category.value == "invalid_model_output":
                            context = {**context, "runtime_correction": "Return one valid action matching the available schema."}
                        await self._retry_sleep(delay)
                        attempt += 1
                        self._trace_recorder.record(state.run_id, TraceEventType.RETRY_STARTED, iteration=iteration,
                            metadata={"failure_category": failure.category.value, "source": failure.source, "attempt": attempt})
                        continue
                    break
                action = decision.action
                usage = decision.usage
                self._trace_recorder.finish_span(state.run_id, llm_span, TraceEventType.LLM_REQUEST_FINISHED,
                    iteration=iteration, success=True, metadata={
                        "action_type": action.action_type, "provider": decision.provider,
                        "model": decision.model, "input_tokens": usage.input_tokens if usage else None,
                        "output_tokens": usage.output_tokens if usage else None,
                        "cached_input_tokens": usage.cached_input_tokens if usage else None,
                        "cache_write_tokens": usage.cache_write_tokens if usage else None,
                        "reasoning_tokens": usage.reasoning_tokens if usage else None,
                        "estimated_cost": estimate_cost(usage, self._pricing_registry.get(decision.model), model=decision.model),
                    })
                if attempt > 1:
                    self._trace_recorder.record(state.run_id, TraceEventType.RETRY_SUCCEEDED, iteration=iteration,
                        metadata={"source": "llm", "attempt": attempt})
                log_event(
                    self._logger,
                    logging.INFO,
                    "llm_action_selected",
                    run_id=state.run_id,
                    iteration=iteration,
                    action=action.action_type,
                    tool=action.tool_name,
                    skill=action.skill_name,
                    specialist=action.agent_name,
                    duration_ms=round((perf_counter() - llm_started_at) * 1000),
                )
                log_event(
                    self._logger,
                    logging.DEBUG,
                    "llm_action_reasoning_summary",
                    run_id=state.run_id,
                    iteration=iteration,
                    reasoning_summary=safe_log_value(action.reasoning_summary),
                )
                state.iteration_count += 1
                await self._apply_action(state, action)
                await self._summarization.update(state)

                if state.status is RunStatus.WAITING_FOR_APPROVAL:
                    return await self._finish_run(state, started_at, session_id=session_id)
                if state.completed or state.stop_reason is not None:
                    return await self._finish_run(state, started_at, session_id=session_id)

            return await self._finish_run(
                self._control.stop(
                    state,
                    StopReason.MAX_ITERATIONS,
                    "Agent stopped after reaching the maximum iteration limit.",
                ),
                started_at, session_id=session_id,
            )
        except Exception as error:
            log_event(
                self._logger,
                logging.ERROR,
                "agent_run_failed",
                run_id=state.run_id,
                iteration=state.iteration_count,
                error_type=type(error).__name__,
                error=safe_error_message(error),
                duration_ms=round((perf_counter() - started_at) * 1000),
            )
            self._trace_recorder.finish_run(state.run_id, status=TraceStatus.FAILED,
                stop_reason=StopReason.FATAL_ERROR.value,
                metrics={"iterations": state.iteration_count, "tool_calls": state.total_tool_calls,
                         "recoverable_errors": state.recoverable_error_count,
                         "delegations": len(state.delegation_requests)})
            raise
        finally:
            await self._memory.clear(state.run_id, workspace_id=state.workspace_id)

    async def _apply_action(self, state: AgentState, action: AgentAction) -> None:
        """Apply one model-selected action to the current runtime state."""

        if action.action_type == "use_tool":
            tool_name = action.tool_name or ""
            if state.total_tool_calls >= self._limits.max_tool_calls:
                self._control.stop(
                    state,
                    StopReason.MAX_TOOL_CALLS,
                    "Agent stopped after reaching the maximum tool call limit.",
                )
                return

            fingerprint = tool_action_fingerprint(tool_name, action.tool_arguments)
            duplicate_count = self._consecutive_duplicate_count(state, fingerprint)
            if duplicate_count >= self._limits.max_consecutive_duplicate_actions:
                log_event(
                    self._logger,
                    logging.INFO,
                    "duplicate_action_detected",
                    run_id=state.run_id,
                    iteration=state.iteration_count,
                    action="use_tool",
                    tool=tool_name,
                    duplicate_count=duplicate_count + 1,
                    configured_limit=self._limits.max_consecutive_duplicate_actions,
                )
                self._record_observation(
                    state,
                    source=tool_name,
                    result=ToolResult(
                        success=False,
                        error=(
                            "This tool action has already been attempted repeatedly. "
                            "Use the existing result, change approach, use another tool, "
                            "or finish."
                        ),
                        metadata={"tool_name": tool_name, "duplicate_action": True},
                    ),
                )
                return

            state.recent_action_fingerprints.append(fingerprint)
            state.total_tool_calls += 1
            subject = self._control.subject(state)
            preflight = self._tool_executor.evaluate_policy(
                tool_name, action.tool_arguments, subject
            )
            if preflight is not None and preflight[0].decision is PolicyDecision.REQUIRE_APPROVAL:
                policy_result = preflight[0]
                log_event(self._logger, logging.INFO, "risk_assessment_created", run_id=state.run_id,
                          agent=subject.agent_name,
                          capability=policy_result.capability.value if policy_result.capability else "unknown",
                          risk_level=policy_result.metadata.get("risk_level"),
                          risk_rule=policy_result.metadata.get("risk_rule"))
                await self._pause_for_approval(
                    state, tool_name, action.tool_arguments, subject, *preflight
                )
                return
            result = await self._tool_executor.execute(
                tool_name,
                action.tool_arguments,
                run_id=state.run_id,
                workspace_id=state.workspace_id,
                iteration=state.iteration_count,
                subject=subject,
            )
            if result.success and tool_name == "register_artifact" and isinstance(result.output, dict):
                try:
                    state.artifacts.append(Artifact.model_validate(result.output["artifact"]))
                except (KeyError, ValidationError):
                    log_event(self._logger, logging.WARNING, "artifact_registration_failed", run_id=state.run_id, iteration=state.iteration_count)
            if result.success and tool_name == "update_investigation_plan" and isinstance(result.output, dict):
                self._update_investigation_plan(state, result.output)
            self._record_observation(state, source=tool_name, result=result)
            if not result.success:
                state.recoverable_error_count += 1
                if state.recoverable_error_count >= self._limits.max_recoverable_errors:
                    self._control.stop(
                        state,
                        StopReason.TOO_MANY_ERRORS,
                        "Agent stopped after reaching the maximum recoverable error limit.",
                    )
            return

        if action.action_type == "load_skill":
            skill_name = action.skill_name or ""
            log_event(
                self._logger,
                logging.DEBUG,
                "skill_load_requested",
                run_id=state.run_id,
                iteration=state.iteration_count,
                skill=skill_name,
            )
            try:
                if skill_name not in state.loaded_skills:
                    state.loaded_skills[skill_name] = await asyncio.to_thread(
                        self._skill_registry.load_skill, skill_name
                    )
            except UnknownSkillError:
                self._record_observation(
                    state,
                    source=f"skill:{skill_name}",
                    result=ToolResult(
                        success=False,
                        error=safe_error_message(f"Unknown skill: {skill_name}."),
                        metadata={"skill_name": skill_name},
                    ),
                )
                state.recoverable_error_count += 1
                if state.recoverable_error_count >= self._limits.max_recoverable_errors:
                    self._control.stop(
                        state,
                        StopReason.TOO_MANY_ERRORS,
                        "Agent stopped after reaching the maximum recoverable error limit.",
                    )
                return
            except Exception as error:
                log_event(
                    self._logger,
                    logging.WARNING,
                    "skill_load_failed",
                    run_id=state.run_id,
                    iteration=state.iteration_count,
                    skill=skill_name,
                    error_type=type(error).__name__,
                    error=safe_error_message(error),
                )
                raise
            log_event(
                self._logger,
                logging.INFO,
                "skill_loaded",
                run_id=state.run_id,
                iteration=state.iteration_count,
                skill=skill_name,
            )
            state.recent_action_fingerprints.clear()
            return

        if action.action_type == "delegate":
            await self._delegation.handle(state, action)
            return

        if action.action_type == "delegate_parallel":
            await self._delegation.handle_parallel(state, action)
            return

        evaluation = evaluate_finish(state, self._limits)
        if not evaluation.accept:
            state.finish_redirect_count += 1
            self._record_observation(
                state,
                source="investigation_plan",
                result=ToolResult(
                    success=False,
                    error=(
                        "Finish was not accepted: " + " ".join(evaluation.missing) + " "
                        "Continue the investigation, or call update_investigation_plan to mark "
                        "an item blocked with why, then finish again."
                    ),
                    metadata={"redirected_finish": True, "missing_count": len(evaluation.missing)},
                ),
            )
            log_event(
                self._logger, logging.INFO, "finish_redirected", run_id=state.run_id,
                iteration=state.iteration_count, missing_count=len(evaluation.missing),
                redirect_count=state.finish_redirect_count,
            )
            return

        state.final_answer = action.final_answer
        state.answer_sources = self._resolved_sources(state, action)
        caveats = self._accepted_caveats(state, action)
        if evaluation.missing:
            caveats = normalize_caveats(caveats + [f"Incomplete: {item}" for item in evaluation.missing])
            log_event(
                self._logger, logging.INFO, "finish_accepted_with_gaps", run_id=state.run_id,
                iteration=state.iteration_count, missing_count=len(evaluation.missing),
            )
        state.answer_caveats = caveats
        state.completed = True
        state.status = RunStatus.COMPLETED
        state.stop_reason = StopReason.COMPLETED

    async def _pause_for_approval(self, state: AgentState, tool_name: str, arguments: dict,
                                  subject: SecuritySubject, policy_result: PolicyResult,
                                  security_action: SecurityAction) -> None:
        """Persist a safe request and private exact-action checkpoint, then pause."""

        if self._approval_store is None or security_action.capability is None:
            self._record_observation(state, source=tool_name, result=ToolResult(
                success=False, error="This action requires human approval, which is not available in this runtime.",
                metadata={"tool_name": tool_name, "security_decision": "require_approval"},
            ))
            return
        fingerprint = action_fingerprint(subject, security_action, arguments)
        request = ApprovalRequest(
            run_id=state.run_id, parent_run_id=subject.parent_run_id, agent_name=subject.agent_name,
            capability=security_action.capability, tool_name=tool_name,
            resource=security_action.resource.identifier if security_action.resource else None,
            argument_summary=safe_argument_summary(arguments), reason=policy_result.reason,
            policy_id=policy_result.policy_id, action_fingerprint=fingerprint,
        )
        await self._approval_store.create(request, ApprovalCheckpoint(
            state=state.model_dump(mode="json"), tool_name=tool_name, tool_arguments=arguments,
            action_fingerprint=fingerprint,
        ))
        state.status = RunStatus.WAITING_FOR_APPROVAL
        log_event(self._logger, logging.INFO, "approval_requested", run_id=state.run_id,
                  approval_id=request.id, agent=subject.agent_name, capability=request.capability.value)
        self._trace_recorder.record(state.run_id, TraceEventType.APPROVAL_REQUESTED,
            iteration=state.iteration_count, metadata={"approval_id": request.id, "capability": request.capability.value,
            "policy_id": policy_result.policy_id})
        log_event(self._logger, logging.INFO, "agent_paused_for_approval", run_id=state.run_id,
                  approval_id=request.id, agent=subject.agent_name, capability=request.capability.value)

    async def resume_approval(self, approval_id: str) -> AgentState | None:
        """Execute one human-approved checkpoint exactly once, then continue the loop."""

        if self._approval_store is None:
            return None
        claimed = await self._approval_store.claim_approved(approval_id)
        if claimed is None:
            checkpoint = await self._approval_store.checkpoint(approval_id)
            return AgentState.model_validate(checkpoint.state) if checkpoint else None
        request, checkpoint = claimed
        state = AgentState.model_validate(checkpoint.state)
        subject = self._control.subject(state)
        preflight = self._tool_executor.evaluate_policy(checkpoint.tool_name, checkpoint.tool_arguments, subject)
        if (
            preflight is None
            or request.action_fingerprint != checkpoint.action_fingerprint
            or action_fingerprint(subject, preflight[1], checkpoint.tool_arguments)
            != checkpoint.action_fingerprint
        ):
            self._record_observation(state, source=checkpoint.tool_name, result=ToolResult(
                success=False, error="Approved action could not be validated for execution.",
                metadata={"tool_name": checkpoint.tool_name, "approval_id": approval_id},
            ))
        else:
            result = await self._tool_executor.execute_approved(
                checkpoint.tool_name, checkpoint.tool_arguments, run_id=state.run_id,
                workspace_id=state.workspace_id,
                iteration=state.iteration_count, subject=subject,
                approval_token=self._tool_executor._approved_execution_token,
            )
            self._record_observation(state, source=checkpoint.tool_name, result=result)
        state.status = RunStatus.RUNNING
        log_event(self._logger, logging.INFO, "agent_resumed_after_approval", run_id=state.run_id,
                  approval_id=approval_id, agent=subject.agent_name, capability=request.capability.value)
        self._trace_recorder.record(state.run_id, TraceEventType.APPROVAL_RESOLVED,
            iteration=state.iteration_count, success=True, metadata={"approval_id": approval_id})
        resumed = await self.run(state.goal, state=state)
        await self._approval_store.complete_execution(approval_id, resumed.model_dump(mode="json"))
        return resumed

    async def resume_rejection(self, approval_id: str) -> AgentState | None:
        """Record a human rejection as an observation and let the agent choose again."""

        if self._approval_store is None:
            return None
        claimed = await self._approval_store.claim_rejected(approval_id)
        if claimed is None:
            checkpoint = await self._approval_store.checkpoint(approval_id)
            return AgentState.model_validate(checkpoint.state) if checkpoint else None
        request, checkpoint = claimed
        state = AgentState.model_validate(checkpoint.state)
        self._record_observation(state, source=checkpoint.tool_name, result=ToolResult(
            success=False, error="The requested action was rejected by a human reviewer.",
            metadata={"tool_name": checkpoint.tool_name, "approval_id": approval_id,
                      "security_decision": "rejected"},
        ))
        state.recoverable_error_count += 1
        state.status = RunStatus.RUNNING
        log_event(self._logger, logging.INFO, "agent_resumed_after_approval", run_id=state.run_id,
                  approval_id=approval_id, agent=request.agent_name, capability=request.capability.value)
        self._trace_recorder.record(state.run_id, TraceEventType.APPROVAL_RESOLVED,
            iteration=state.iteration_count, success=False, metadata={"approval_id": approval_id})
        resumed = await self.run(state.goal, state=state)
        await self._approval_store.complete_execution(approval_id, resumed.model_dump(mode="json"))
        return resumed

    @staticmethod
    def _consecutive_duplicate_count(state: AgentState, fingerprint: str) -> int:
        """Count immediately preceding identical tool actions."""

        count = 0
        for previous in reversed(state.recent_action_fingerprints):
            if previous != fingerprint:
                break
            count += 1
        return count

    @staticmethod
    def _record_observation(
        state: AgentState, *, source: str, result: ToolResult
    ) -> None:
        """Append a consistently sequenced execution observation."""

        state.observations.append(
            Observation(
                source=source,
                content=result,
                iteration=state.iteration_count,
                sequence=len(state.observations) + 1,
            )
        )

    def _update_investigation_plan(self, state: AgentState, output: dict) -> None:
        """Store the model's proposed plan only after reconciling its claims.

        A question or output the model marks resolved is trusted only once
        `reconcile_plan` confirms this run actually produced the evidence or
        display behind it; anything it cannot confirm reverts to "pending"
        here, before the plan is ever shown back to the model or a reader.
        """

        try:
            proposed = InvestigationPlan.model_validate(output["plan"])
        except (KeyError, ValidationError):
            log_event(self._logger, logging.WARNING, "investigation_plan_update_failed", run_id=state.run_id, iteration=state.iteration_count)
            return
        state.investigation_plan = reconcile_plan(proposed, state.observations)
        self._trace_recorder.record(
            state.run_id, TraceEventType.PLAN_UPDATED, iteration=state.iteration_count,
            metadata={
                "plan": state.investigation_plan.model_dump(mode="json"),
                "progress": plan_progress(state.investigation_plan),
            },
        )
        log_event(
            self._logger, logging.INFO, "investigation_plan_updated", run_id=state.run_id,
            iteration=state.iteration_count, **plan_progress(state.investigation_plan),
        )

    def _resolved_sources(self, state: AgentState, action: AgentAction) -> list[AnswerSource]:
        """Keep only the cited evidence this run actually produced.

        A citation the run cannot account for is dropped rather than shown. The
        answer text still stands on its own, and a dropped reference is logged
        so the gap is visible in operations rather than in the Workbench.
        """

        resolved, unresolved = resolve_citations(
            self._trace_recorder.get_trace(state.run_id), action.citations
        )
        if unresolved:
            log_event(
                self._logger,
                logging.WARNING,
                "answer_citation_unresolved",
                run_id=state.run_id,
                iteration=state.iteration_count,
                unresolved_citations=safe_log_value(unresolved),
                resolved_count=len(resolved),
            )
        return resolved

    def _accepted_caveats(self, state: AgentState, action: AgentAction) -> list[str]:
        """Record the limitations the model stated, as the contract bounded them.

        The model writes these; nothing here rewrites them, and publishing later
        prints them verbatim rather than asking for them again.
        """

        caveats = list(action.caveats)
        if caveats:
            log_event(
                self._logger,
                logging.INFO,
                "answer_caveats_recorded",
                run_id=state.run_id,
                iteration=state.iteration_count,
                caveat_count=len(caveats),
            )
        return caveats

    async def _finish_run(
        self, state: AgentState, started_at: float, *, session_id: str | None
    ) -> AgentState:
        """Log the terminal summary for a normal or runtime-limited run."""

        await self._memory.capture(state, workspace_id=state.workspace_id, session_id=session_id)
        log_event(
            self._logger,
            logging.INFO,
            "agent_finished",
            run_id=state.run_id,
            iterations=state.iteration_count,
            tool_calls=state.total_tool_calls,
            errors=state.recoverable_error_count,
            skills_used=sorted(state.loaded_skills),
            delegations=len(state.delegation_requests),
            successful_delegations=state.successful_delegation_count,
            failed_delegations=state.failed_delegation_count,
            parallel_delegation_batches=state.parallel_delegation_batch_count,
            stop_reason=state.stop_reason,
            duration_ms=round((perf_counter() - started_at) * 1000),
        )
        if state.status is not RunStatus.WAITING_FOR_APPROVAL:
            self._trace_recorder.finish_run(state.run_id,
                status=TraceStatus.COMPLETED if state.completed else TraceStatus.FAILED,
                stop_reason=state.stop_reason.value if state.stop_reason else None,
                metrics={"iterations": state.iteration_count, "tool_calls": state.total_tool_calls,
                         "recoverable_errors": state.recoverable_error_count,
                         "delegations": len(state.delegation_requests)})
        return state

