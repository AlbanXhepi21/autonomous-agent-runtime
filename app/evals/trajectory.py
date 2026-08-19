"""Derived, sanitized action views over V7.1 run traces."""

from collections import Counter
from typing import Callable

from pydantic import BaseModel, ConfigDict, Field

from app.observability import RunTrace, TraceEventType


class TrajectoryAction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    sequence: int = Field(ge=1)
    kind: str
    name: str | None = None
    iteration: int | None = Field(default=None, ge=0)
    success: bool | None = None

    @property
    def label(self) -> str:
        return f"{self.kind}({self.name})" if self.name else self.kind


class Trajectory(BaseModel):
    """Evaluation-only projection of one parent trace and its child traces."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    parent_run_id: str | None = None
    actions: list[TrajectoryAction] = Field(default_factory=list)
    llm_decisions: list[str] = Field(default_factory=list)
    security_decisions: list[str] = Field(default_factory=list)
    errors: int = Field(default=0, ge=0)
    iterations: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    delegations: int = Field(default=0, ge=0)
    stop_reason: str | None = None
    children: list["Trajectory"] = Field(default_factory=list)

    @property
    def total_iterations(self) -> int:
        return self.iterations + sum(child.total_iterations for child in self.children)

    @property
    def total_tool_calls(self) -> int:
        return self.tool_calls + sum(child.total_tool_calls for child in self.children)

    @property
    def total_delegations(self) -> int:
        return self.delegations + sum(child.total_delegations for child in self.children)

    def duplicate_actions(self) -> dict[str, int]:
        """Count extra same-run actions, leaving parallel child siblings independent."""

        counts = Counter(action.label for action in self.actions if action.kind in {"tool", "skill", "delegation"})
        return {label: count - 1 for label, count in counts.items() if count > 1}

    @classmethod
    def from_trace(cls, trace: RunTrace, lookup: Callable[[str], RunTrace | None] | None = None) -> "Trajectory":
        actions: list[TrajectoryAction] = []
        child_ids: set[str] = set()
        for event in trace.events:
            name: str | None = None
            kind: str | None = None
            if event.event_type is TraceEventType.TOOL_STARTED:
                kind, name = "tool", str(event.metadata.get("tool_name", "unknown"))
            elif event.event_type is TraceEventType.SKILL_LOADED:
                kind, name = "skill", str(event.metadata.get("skill", "unknown"))
            elif event.event_type in {TraceEventType.DELEGATION_STARTED, TraceEventType.PARALLEL_DELEGATION_STARTED}:
                kind = "parallel_delegation" if event.event_type is TraceEventType.PARALLEL_DELEGATION_STARTED else "delegation"
                name = str(event.metadata.get("target_agent", "parallel" if kind.startswith("parallel") else "unknown"))
            elif event.event_type is TraceEventType.LLM_REQUEST_FINISHED and event.metadata.get("action_type") == "finish":
                kind = "finish"
            elif event.event_type in {TraceEventType.TOOL_FINISHED, TraceEventType.TOOL_FAILED}:
                tool_name = str(event.metadata.get("tool_name", "unknown"))
                for index in range(len(actions) - 1, -1, -1):
                    action = actions[index]
                    if action.kind == "tool" and action.name == tool_name and action.success is None:
                        actions[index] = action.model_copy(update={"success": event.event_type is TraceEventType.TOOL_FINISHED})
                        break
            if kind:
                actions.append(TrajectoryAction(run_id=trace.run_id, sequence=len(actions) + 1, kind=kind,
                    name=name, iteration=event.iteration, success=event.success))
            if event.child_run_id:
                child_ids.add(event.child_run_id)
            raw_child_ids = event.metadata.get("child_run_ids", [])
            if isinstance(raw_child_ids, list):
                child_ids.update(child_id for child_id in raw_child_ids if isinstance(child_id, str))

        children = [cls.from_trace(child, lookup) for child_id in sorted(child_ids)
                    if lookup is not None and (child := lookup(child_id)) is not None]
        return cls(run_id=trace.run_id, parent_run_id=trace.parent_run_id, actions=actions,
            llm_decisions=[str(event.metadata.get("action_type")) for event in trace.events
                           if event.event_type is TraceEventType.LLM_REQUEST_FINISHED
                           and isinstance(event.metadata.get("action_type"), str)],
            security_decisions=[str(event.metadata.get("decision")) for event in trace.events
                                if event.event_type is TraceEventType.SECURITY_POLICY_EVALUATED],
            errors=sum(event.event_type in {TraceEventType.TOOL_FAILED, TraceEventType.LLM_REQUEST_FAILED} for event in trace.events),
            iterations=trace.metrics.iterations, tool_calls=trace.metrics.tool_calls,
            delegations=trace.metrics.delegations, stop_reason=trace.stop_reason, children=children)
