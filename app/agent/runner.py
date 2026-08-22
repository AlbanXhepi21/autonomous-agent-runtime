"""Controlled, provider-neutral autonomous agent loop."""

import asyncio
import logging
from time import perf_counter

from app.agent.context import ContextBuilder
from app.agent.delegation import (
    DelegationContext,
    DelegationExecutor,
    DelegationObservation,
    DelegationRequest,
    ParallelDelegationResult,
    ParallelSubagentExecutor,
    SubagentResult,
)
from app.contracts.actions import AgentAction
from app.agent.registry import AgentRegistry
from app.agent.policy import delegation_fingerprint, tool_action_fingerprint
from app.agent.prompt import SYSTEM_PROMPT
from app.agent.state import AgentState, Observation, RunStatus, StopReason, TaskSummary
from app.agent.summarization import (
    DeterministicTaskSummarizer,
    SummaryPolicy,
    TaskSummarizer,
)
from app.core.exceptions import UnknownAgentError, UnknownSkillError
from app.core.limits import RuntimeLimits
from app.core.logging import log_event, safe_error_message, safe_log_value
from pydantic import ValidationError
from app.llm.base import LLMClient
from app.llm.pricing import PricingRegistry, estimate_cost
from app.reliability import RetryPolicy, classify_llm_failure
from app.reliability.retry import Sleep, default_sleep
from app.memory.manager import MemoryManager
from app.memory.models import Memory, MemoryType
from app.memory.retrieval import MemoryRetrievalRequest, MemoryRetriever
from app.memory.writing import MemoryWritingPipeline
from app.security import Capability, PolicyDecision, PolicyResult, SecurityAction, SecurityPolicy, SecurityResource, SecuritySubject
from app.security.approvals import ApprovalCheckpoint, ApprovalRequest, ApprovalStore, action_fingerprint, safe_argument_summary
from app.security import injection_indicators
from app.skills.registry import SkillRegistry
from app.tools.execution import ToolExecutor
from app.tools.models import ToolResult
from app.tools.registry import ToolRegistry
from app.artifacts.models import Artifact
from app.observability import InMemoryTraceStore, TraceEventType, TraceRecorder, TraceStatus


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
        self._summary_policy = summary_policy or SummaryPolicy()
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
        self._memory_manager = memory_manager
        self._memory_retriever = memory_retriever
        self._memory_writer = memory_writer
        self._task_summarizer = task_summarizer or DeterministicTaskSummarizer()

    async def run(
        self,
        goal: str,
        *,
        session_id: str | None = None,
        state: AgentState | None = None,
    ) -> AgentState:
        """Execute bounded, model-selected actions for a single goal."""

        state = state or AgentState(goal=goal)
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
        relevant_memories = await self._retrieve_relevant_memories(
            goal, run_id=state.run_id, session_id=session_id
        )

        try:
            if self._memory_manager is not None:
                await self._memory_manager.add_working_memory(
                    goal,
                    run_id=state.run_id,
                    metadata={"kind": "task_goal"},
                )
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
                    working_memories=await self._working_memories(state.run_id),
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
                await self._maybe_update_summary(state)

                if state.status is RunStatus.WAITING_FOR_APPROVAL:
                    return await self._finish_run(state, started_at, session_id=session_id)
                if state.completed or state.stop_reason is not None:
                    return await self._finish_run(state, started_at, session_id=session_id)

            return await self._finish_run(
                self._stop(
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
            await self._clear_run_working_memory(state.run_id)

    async def _retrieve_relevant_memories(
        self, goal: str, *, run_id: str, session_id: str | None
    ) -> list[Memory]:
        """Retrieve once per run; a failure leaves the run usable with no history."""

        if self._memory_retriever is None:
            return []
        log_event(self._logger, logging.INFO, "memory_retrieval_started", run_id=run_id)
        memory_span = self._trace_recorder.start_span(run_id, TraceEventType.MEMORY_RETRIEVAL_STARTED, name="memory_retrieval")
        started_at = perf_counter()
        try:
            result = await self._memory_retriever.retrieve(
                MemoryRetrievalRequest(query=goal, session_id=session_id)
            )
        except Exception as error:
            self._trace_recorder.finish_span(run_id, memory_span, TraceEventType.MEMORY_RETRIEVAL_FINISHED,
                success=False, metadata={"returned_count": 0, "error_type": type(error).__name__})
            log_event(
                self._logger, logging.WARNING, "memory_retrieval_failed", run_id=run_id,
                candidate_count=None, returned_count=0,
                duration_ms=round((perf_counter() - started_at) * 1000),
                error_type=type(error).__name__, error=safe_error_message(error),
            )
            return []
        log_event(
            self._logger, logging.INFO, "memory_retrieval_finished", run_id=run_id,
            candidate_count=result.candidate_count, returned_count=len(result.memories),
            duration_ms=round((perf_counter() - started_at) * 1000),
        )
        self._trace_recorder.finish_span(run_id, memory_span, TraceEventType.MEMORY_RETRIEVAL_FINISHED,
            success=True, metadata={"candidate_count": result.candidate_count, "returned_count": len(result.memories)})
        for memory in result.memories:
            log_event(self._logger, logging.INFO, "untrusted_content_ingested", run_id=run_id,
                      source_type="memory", source_identifier=str(memory.id))
            for indicator in injection_indicators(memory.content):
                log_event(self._logger, logging.WARNING, "prompt_injection_indicator_detected", run_id=run_id,
                          source_type="memory", source_identifier=str(memory.id), matched_heuristic=indicator)
        return result.memories

    async def _working_memories(self, run_id: str) -> list[Memory]:
        """Read explicit working memory without exposing store details to context."""

        if self._memory_manager is None:
            return []
        return await self._memory_manager.get_memories(MemoryType.WORKING, run_id=run_id)

    async def _maybe_update_summary(self, state: AgentState) -> None:
        """Summarize only history moving out of the recent-observation window."""

        observations = self._summary_policy.observations_to_summarize(
            state.task_summary, state.observations
        )
        if not observations:
            return
        log_event(
            self._logger, logging.INFO, "task_summary_started", run_id=state.run_id,
            iteration=state.iteration_count, observations_summarized=len(observations),
        )
        summary_span = self._trace_recorder.start_span(state.run_id, TraceEventType.TASK_SUMMARY_STARTED,
            name="task_summary", iteration=state.iteration_count,
            metadata={"observations_summarized": len(observations)})
        started_at = perf_counter()
        current_summary = state.task_summary or TaskSummary(goal=state.goal)
        try:
            summary = await self._task_summarizer.summarize(current_summary, observations)
        except Exception as error:
            self._trace_recorder.finish_span(state.run_id, summary_span, TraceEventType.TASK_SUMMARY_FINISHED,
                iteration=state.iteration_count, success=False, metadata={"error_type": type(error).__name__})
            log_event(
                self._logger, logging.WARNING, "task_summary_failed", run_id=state.run_id,
                iteration=state.iteration_count, observations_summarized=len(observations),
                duration_ms=round((perf_counter() - started_at) * 1000),
                error_type=type(error).__name__, error=safe_error_message(error),
            )
            return
        state.task_summary = summary.model_copy(
            update={
                "goal": state.goal,
                "last_updated_iteration": state.iteration_count,
                "summarized_observation_count": len(state.observations)
                - self._summary_policy.recent_observations,
            }
        )
        log_event(
            self._logger, logging.INFO, "task_summary_updated", run_id=state.run_id,
            iteration=state.iteration_count, observations_summarized=len(observations),
            duration_ms=round((perf_counter() - started_at) * 1000),
            summary_size=len(state.task_summary.model_dump_json()),
        )
        self._trace_recorder.finish_span(state.run_id, summary_span, TraceEventType.TASK_SUMMARY_FINISHED,
            iteration=state.iteration_count, success=True, metadata={"observations_summarized": len(observations)})
        log_event(
            self._logger, logging.DEBUG, "task_summary_content", run_id=state.run_id,
            iteration=state.iteration_count,
            summary=safe_log_value(state.task_summary.model_dump()),
        )

    async def _clear_run_working_memory(self, run_id: str) -> None:
        """Best-effort cleanup that must not change the agent run result."""

        if self._memory_manager is None:
            return
        try:
            await self._memory_manager.clear_working_memory(run_id)
        except Exception as error:
            log_event(
                self._logger,
                logging.WARNING,
                "working_memory_cleanup_failed",
                run_id=run_id,
                error_type=type(error).__name__,
                error=safe_error_message(error),
            )
            self._trace_recorder.record(state.run_id, TraceEventType.SKILL_LOADED, iteration=state.iteration_count,
                success=True, metadata={"skill": skill_name})

    async def _apply_action(self, state: AgentState, action: AgentAction) -> None:
        """Apply one model-selected action to the current runtime state."""

        if action.action_type == "use_tool":
            tool_name = action.tool_name or ""
            if state.total_tool_calls >= self._limits.max_tool_calls:
                self._stop(
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
            subject = self._security_subject(state)
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
                iteration=state.iteration_count,
                subject=subject,
            )
            if result.success and tool_name == "register_artifact" and isinstance(result.output, dict):
                try:
                    state.artifacts.append(Artifact.model_validate(result.output["artifact"]))
                except (KeyError, ValidationError):
                    log_event(self._logger, logging.WARNING, "artifact_registration_failed", run_id=state.run_id, iteration=state.iteration_count)
            self._record_observation(state, source=tool_name, result=result)
            if not result.success:
                state.recoverable_error_count += 1
                if state.recoverable_error_count >= self._limits.max_recoverable_errors:
                    self._stop(
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
                    self._stop(
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
            await self._handle_delegation(state, action)
            return

        if action.action_type == "delegate_parallel":
            await self._handle_parallel_delegation(state, action)
            return

        state.final_answer = action.final_answer
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
        subject = self._security_subject(state)
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

    def _security_subject(self, state: AgentState) -> SecuritySubject:
        """Construct identity solely from runner and state owned by the runtime."""

        return SecuritySubject(
            agent_name=self._security_agent_name,
            agent_type=self._security_agent_type,
            run_id=state.run_id,
            parent_run_id=self._parent_run_id,
            delegation_depth=self._agent_depth,
        )

    def _delegation_allowed(self, state: AgentState, target_agent: str) -> bool:
        """Apply the same centralized gate to delegation actions."""

        result = self._security_policy.evaluate(
            self._security_subject(state),
            SecurityAction(
                capability=Capability.AGENT_DELEGATE,
                resource=SecurityResource(resource_type="specialist_agent", identifier=target_agent or "unknown"),
            ),
        )
        fields = {
            "run_id": state.run_id, "agent": self._security_agent_name,
            "capability": Capability.AGENT_DELEGATE.value, "decision": result.decision.value,
            "policy_id": result.policy_id,
        }
        log_event(self._logger, logging.INFO, "risk_assessment_created", **fields,
                  risk_level=result.metadata.get("risk_level"), risk_rule=result.metadata.get("risk_rule"))
        log_event(self._logger, logging.INFO, "security_policy_evaluated", **fields)
        self._trace_recorder.record(state.run_id, TraceEventType.SECURITY_POLICY_EVALUATED,
            iteration=state.iteration_count, success=result.decision == PolicyDecision.ALLOW,
            metadata={"capability": Capability.AGENT_DELEGATE.value, "decision": result.decision.value,
            "policy_id": result.policy_id, "risk_level": result.metadata.get("risk_level")})
        if result.decision == PolicyDecision.ALLOW:
            log_event(self._logger, logging.INFO, "security_action_allowed", **fields)
            return True
        event = "security_approval_required" if result.decision == PolicyDecision.REQUIRE_APPROVAL else "security_action_denied"
        log_event(self._logger, logging.WARNING, event, **fields)
        return False

    async def _handle_delegation(self, state: AgentState, action: AgentAction) -> None:
        """Validate and execute a model-selected delegation through its boundary."""

        target_agent = action.agent_name if isinstance(action.agent_name, str) else ""
        objective = action.objective if isinstance(action.objective, str) else ""
        if self._agent_depth >= self._limits.max_agent_depth:
            self._record_delegation_limit(
                state,
                limit_type="max_agent_depth",
                current_value=self._agent_depth,
                configured_limit=self._limits.max_agent_depth,
            )
            return
        if not self._delegation_allowed(state, target_agent):
            self._record_delegation_observation(
                state, status="invalid", target_agent=target_agent,
                error="Delegation is not permitted by runtime security policy.",
            )
            self._record_recoverable_error(state)
            return
        if len(state.delegation_requests) >= self._limits.max_delegations_per_run:
            self._record_delegation_limit(
                state,
                limit_type="max_delegations_per_run",
                current_value=len(state.delegation_requests),
                configured_limit=self._limits.max_delegations_per_run,
            )
            return
        fingerprint = delegation_fingerprint(target_agent, objective, action.context)
        if self._consecutive_delegation_count(state, fingerprint) >= self._limits.max_consecutive_duplicate_actions:
            log_event(
                self._logger,
                logging.INFO,
                "duplicate_delegation_detected",
                run_id=state.run_id,
                iteration=state.iteration_count,
                target_agent=safe_log_value(target_agent),
                duplicate_count=self._consecutive_delegation_count(state, fingerprint) + 1,
                configured_limit=self._limits.max_consecutive_duplicate_actions,
            )
            self._record_delegation_observation(
                state,
                status="invalid",
                target_agent=target_agent,
                error="This delegation was repeatedly requested. Use the existing result, change strategy, or finish.",
            )
            self._record_recoverable_error(state)
            return
        try:
            request = DelegationRequest(
                parent_run_id=state.run_id,
                parent_iteration=state.iteration_count,
                target_agent=target_agent,
                objective=objective,
                context=DelegationContext(
                    objective=objective,
                    background=action.context,
                    constraints=action.constraints,
                    expected_output=action.expected_output,
                ),
            )
            if self._agent_registry is None:
                raise UnknownAgentError("No specialist agent registry is configured.")
            if not self._delegation_enabled:
                raise UnknownAgentError("Delegation is disabled for this agent run.")
            self._agent_registry.get_metadata(request.target_agent)
        except (ValidationError, UnknownAgentError) as error:
            message = safe_error_message(error)
            log_event(
                self._logger,
                logging.WARNING,
                "delegation_invalid",
                run_id=state.run_id,
                iteration=state.iteration_count,
                target_agent=safe_log_value(target_agent),
                objective=safe_log_value(objective),
                error=message,
            )
            self._record_delegation_observation(
                state,
                status="invalid",
                target_agent=target_agent,
                error=f"Delegation request was rejected: {message}",
            )
            self._record_recoverable_error(state)
            return

        state.delegation_requests.append(request)
        state.recent_delegation_fingerprints.append(fingerprint)
        log_event(
            self._logger,
            logging.INFO,
            "delegation_requested",
            run_id=state.run_id,
            iteration=state.iteration_count,
            target_agent=request.target_agent,
            objective=safe_log_value(request.objective),
        )
        delegation_span = self._trace_recorder.start_span(state.run_id, TraceEventType.DELEGATION_STARTED,
            name="delegation", iteration=state.iteration_count,
            metadata={"target_agent": request.target_agent})
        if self._delegation_executor is None:
            self._record_delegation_observation(
                state,
                status="unavailable",
                target_agent=request.target_agent,
                error=(
                    "Delegation was accepted, but child-agent execution is not available "
                    "because no executor is configured. "
                    "Continue the task yourself or choose another action."
                ),
            )
            self._record_recoverable_error(state)
            return

        result = await self._delegation_executor.execute(request)
        self._trace_recorder.finish_span(state.run_id, delegation_span, TraceEventType.DELEGATION_FINISHED,
            iteration=state.iteration_count, success=result.success, metadata={"child_run_id": result.child_run_id,
            "target_agent": request.target_agent})
        self._record_subagent_observation(state, result)
        self._account_delegation_results(state, [result])
        if not result.success:
            self._record_recoverable_error(state)

    async def _handle_parallel_delegation(self, state: AgentState, action: AgentAction) -> None:
        """Validate an explicit model-selected batch before concurrent execution."""

        if self._agent_depth >= self._limits.max_agent_depth:
            self._record_delegation_limit(
                state,
                limit_type="max_agent_depth",
                current_value=self._agent_depth,
                configured_limit=self._limits.max_agent_depth,
            )
            return
        if not self._delegation_allowed(state, "parallel"):
            self._record_delegation_observation(
                state, status="invalid", target_agent="parallel",
                error="Delegation is not permitted by runtime security policy.",
            )
            self._record_recoverable_error(state)
            return
        if not self._delegation_enabled or self._agent_registry is None:
            self._record_delegation_observation(
                state, status="invalid", target_agent="parallel",
                error="Parallel delegation is not available for this agent run.",
            )
            self._record_recoverable_error(state)
            return
        if len(action.delegations) > self._limits.max_parallel_subagents:
            self._record_delegation_limit(
                state,
                limit_type="max_parallel_subagents",
                current_value=len(action.delegations),
                configured_limit=self._limits.max_parallel_subagents,
            )
            return
        if len(state.delegation_requests) + len(action.delegations) > self._limits.max_delegations_per_run:
            self._record_delegation_limit(
                state,
                limit_type="max_delegations_per_run",
                current_value=len(state.delegation_requests) + len(action.delegations),
                configured_limit=self._limits.max_delegations_per_run,
            )
            return
        try:
            requests = [
                DelegationRequest(
                    parent_run_id=state.run_id,
                    parent_iteration=state.iteration_count,
                    target_agent=item.agent_name,
                    objective=item.objective,
                    context=DelegationContext(
                        objective=item.objective,
                        background=item.context,
                        constraints=item.constraints,
                        expected_output=item.expected_output,
                    ),
                )
                for item in action.delegations
            ]
            for request in requests:
                self._agent_registry.get_metadata(request.target_agent)
        except (AttributeError, ValidationError, UnknownAgentError) as error:
            message = safe_error_message(error)
            log_event(
                self._logger,
                logging.WARNING,
                "delegation_invalid",
                run_id=state.run_id,
                iteration=state.iteration_count,
                target_agent="parallel",
                objective="",
                error=message,
            )
            self._record_delegation_observation(
                state, status="invalid", target_agent="parallel",
                error=f"Delegation request was rejected: {message}",
            )
            self._record_recoverable_error(state)
            return
        state.delegation_requests.extend(requests)
        state.parallel_delegation_batch_count += 1
        parallel_span = self._trace_recorder.start_span(state.run_id, TraceEventType.PARALLEL_DELEGATION_STARTED,
            name="parallel_delegation", iteration=state.iteration_count,
            metadata={"delegation_count": len(requests), "target_agents": [request.target_agent for request in requests]})
        if self._parallel_delegation_executor is None:
            self._record_delegation_observation(
                state,
                status="unavailable",
                target_agent="parallel",
                error="Parallel delegation was accepted, but no parallel executor is configured.",
            )
            self._record_recoverable_error(state)
            return
        result = await self._parallel_delegation_executor.execute(requests)
        self._trace_recorder.finish_span(state.run_id, parallel_span, TraceEventType.PARALLEL_DELEGATION_FINISHED,
            iteration=state.iteration_count, success=result.success,
            metadata={"child_run_ids": [item.child_run_id for item in result.results]})
        self._record_parallel_subagent_observation(state, result)
        self._account_delegation_results(state, result.results)
        if not result.success:
            self._record_recoverable_error(state)

    def _record_recoverable_error(self, state: AgentState) -> None:
        state.recoverable_error_count += 1
        if state.recoverable_error_count >= self._limits.max_recoverable_errors:
            self._stop(
                state,
                StopReason.TOO_MANY_ERRORS,
                "Agent stopped after reaching the maximum recoverable error limit.",
            )

    def _record_delegation_limit(
        self, state: AgentState, *, limit_type: str, current_value: int, configured_limit: int
    ) -> None:
        """Expose a hard delegation boundary to the parent without launching work."""

        log_event(
            self._logger,
            logging.INFO,
            "delegation_limit_reached",
            run_id=state.run_id,
            iteration=state.iteration_count,
            limit_type=limit_type,
            current_value=current_value,
            configured_limit=configured_limit,
        )
        self._record_delegation_observation(
            state,
            status="invalid",
            target_agent="parallel" if limit_type == "max_parallel_subagents" else "delegation",
            error=f"Delegation limit reached: {limit_type} ({current_value}/{configured_limit}).",
        )
        self._record_recoverable_error(state)

    @staticmethod
    def _consecutive_delegation_count(state: AgentState, fingerprint: str) -> int:
        count = 0
        for previous in reversed(state.recent_delegation_fingerprints):
            if previous != fingerprint:
                break
            count += 1
        return count

    @staticmethod
    def _account_delegation_results(state: AgentState, results: list[SubagentResult]) -> None:
        state.successful_delegation_count += sum(result.success for result in results)
        state.failed_delegation_count += sum(not result.success for result in results)
        state.child_run_ids.extend(
            result.child_run_id for result in results if result.child_run_id is not None
        )

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

    @staticmethod
    def _record_delegation_observation(
        state: AgentState, *, status: str, target_agent: str, error: str
    ) -> None:
        """Record a delegation boundary outcome without masquerading as a tool result."""

        state.observations.append(
            Observation(
                source=f"delegation:{target_agent or 'unknown'}",
                content=DelegationObservation(
                    status=status,  # type: ignore[arg-type]
                    target_agent=target_agent,
                    error=error,
                ),
                iteration=state.iteration_count,
                sequence=len(state.observations) + 1,
            )
        )

    @staticmethod
    def _record_subagent_observation(state: AgentState, result: SubagentResult) -> None:
        """Append a child result as a delegation observation, never a tool result."""

        state.observations.append(
            Observation(
                source="subagent",
                content=result,
                iteration=state.iteration_count,
                sequence=len(state.observations) + 1,
            )
        )

    @staticmethod
    def _record_parallel_subagent_observation(
        state: AgentState, result: ParallelDelegationResult
    ) -> None:
        """Append one ordered parallel-result observation for the parent LLM."""

        state.observations.append(
            Observation(
                source="parallel_subagents",
                content=result,
                iteration=state.iteration_count,
                sequence=len(state.observations) + 1,
            )
        )

    def _stop(self, state: AgentState, reason: StopReason, answer: str) -> AgentState:
        """Record a runtime-enforced terminal state."""

        state.completed = False
        state.status = RunStatus.FAILED
        state.stop_reason = reason
        state.final_answer = answer
        limit = self._limit_details(state, reason)
        if limit is not None:
            log_event(
                self._logger,
                logging.INFO,
                "runtime_limit_reached",
                run_id=state.run_id,
                resulting_stop_reason=reason,
                **limit,
            )
        return state

    async def _finish_run(
        self, state: AgentState, started_at: float, *, session_id: str | None
    ) -> AgentState:
        """Log the terminal summary for a normal or runtime-limited run."""

        if self._memory_writer is not None:
            await self._memory_writer.capture_completed_run(state, session_id=session_id)
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

    def _limit_details(
        self, state: AgentState, reason: StopReason
    ) -> dict[str, int | str] | None:
        """Return the current and configured value for a runtime limit stop."""

        if reason is StopReason.MAX_ITERATIONS:
            return {
                "limit_type": "max_iterations",
                "current_value": state.iteration_count,
                "configured_limit": self._limits.max_iterations,
            }
        if reason is StopReason.MAX_TOOL_CALLS:
            return {
                "limit_type": "max_tool_calls",
                "current_value": state.total_tool_calls,
                "configured_limit": self._limits.max_tool_calls,
            }
        if reason is StopReason.TOO_MANY_ERRORS:
            return {
                "limit_type": "max_recoverable_errors",
                "current_value": state.recoverable_error_count,
                "configured_limit": self._limits.max_recoverable_errors,
            }
        return None
