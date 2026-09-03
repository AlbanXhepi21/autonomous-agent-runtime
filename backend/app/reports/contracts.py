"""A saved report definition: a reusable recipe, never a generated document.

A definition names a template, the metric requests and default period a
reader wants recomputed, and a narrative policy -- nothing here is a figure,
a chart or a rendered page. Executing a definition produces those separately,
through the same deterministic compiler and rerun machinery an ad-hoc report
publish already uses. Nothing in this module calls a model or executes SQL;
it only describes what a later execution should do.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.analytics.semantics.parameters import Grain, MetricFilter

#: What a saved report's rerun does with the narrative prose a report can carry.
#:
#:   exclude                  - never include prose; every execution is facts only.
#:   include_original         - reuse the narrative captured when the definition
#:                              was saved, under the same pinned-period warning
#:                              a manual metric rerun already prints.
#:   require_new_investigation - the deterministic pipeline refuses to run;
#:                              only a fresh, explicitly requested agent run may
#:                              produce a new narrative.
NarrativePolicy = Literal["exclude", "include_original", "require_new_investigation"]

SavedReportStatus = Literal["active", "archived"]

#: Every relative period this system can resolve without a caller-supplied
#: date range. Deliberately closed -- see app.reports.periods for the exact
#: resolution rule and timezone behind each one.
RelativePeriodKind = Literal[
    "current_month", "previous_month",
    "current_quarter", "previous_quarter",
    "current_year", "previous_year",
    "last_n_days", "fixed",
]

#: An executed report may not reach back further than this from "today",
#: matching the five-year span ReportPeriod itself already enforces.
MAX_RELATIVE_DAYS = 366 * 5


class RelativePeriod(BaseModel):
    """A deterministic period description, resolved at execution time.

    Never "recently" or another ambiguous phrase: every kind here names an
    exact, reproducible rule in ``app.reports.periods.resolve_relative_period``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: RelativePeriodKind
    #: Only for kind="last_n_days": how many complete days immediately before
    #: today to cover. Today itself is never included -- see the resolver.
    days: int | None = Field(default=None, ge=1, le=MAX_RELATIVE_DAYS)
    #: Only for kind="fixed": a literal, non-relative period.
    start: date | None = None
    end: date | None = None

    @model_validator(mode="after")
    def _shape_matches_kind(self) -> RelativePeriod:
        if self.kind == "last_n_days":
            if self.days is None:
                raise ValueError("last_n_days requires 'days'.")
        elif self.days is not None:
            raise ValueError(f"'days' is only meaningful for last_n_days, not {self.kind!r}.")

        if self.kind == "fixed":
            if self.start is None or self.end is None:
                raise ValueError("fixed requires both 'start' and 'end'.")
            if self.end <= self.start:
                raise ValueError("A fixed period must end after it starts.")
        elif self.start is not None or self.end is not None:
            raise ValueError(f"'start'/'end' are only meaningful for fixed, not {self.kind!r}.")
        return self


class SavedMetricRequest(BaseModel):
    """One metric a saved report reruns -- ``MetricParameters`` without a period.

    The period is never stored per metric: a saved report resolves one period
    for the whole document from its own ``default_period``, so every metric in
    it describes the same window a reader would expect from one report.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    metric: str = Field(min_length=1, max_length=64)
    dimensions: list[str] = Field(default_factory=list, max_length=3)
    filters: list[MetricFilter] = Field(default_factory=list, max_length=8)
    grain: Grain = "month"

    @model_validator(mode="after")
    def _dimensions_are_unique(self) -> SavedMetricRequest:
        if len(set(self.dimensions)) != len(self.dimensions):
            raise ValueError("A dimension may be requested only once.")
        return self


class SavedReportDefinition(BaseModel):
    """The durable recipe: what a saved report should execute, and how.

    This is the domain-facing view; ``app.db.records.SavedReportRecord`` is
    its SQLAlchemy row. Every JSONB column on that row round-trips through a
    typed field here rather than being read or written as a raw dict.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    workspace_id: UUID
    owner: str | None = Field(default=None, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2_000)
    template_id: str = Field(min_length=1, max_length=64)
    #: The template version pinned when this was last saved. Compared against
    #: the registry's current version at execution time; a divergence is
    #: surfaced as a caveat, never a silent re-render under a different shape.
    template_version: str = Field(min_length=1, max_length=32)
    metric_requests: list[SavedMetricRequest] = Field(min_length=1, max_length=24)
    default_period: RelativePeriod
    narrative_policy: NarrativePolicy
    #: Captured once, at the run this definition was created or last re-seeded
    #: from. Never written by anything except an explicit "seed from this run"
    #: action -- an execution reruns metrics, it never writes prose.
    seed_run_id: str | None = Field(default=None, max_length=255)
    seed_narrative: str | None = Field(default=None, max_length=20_000)
    seed_narrative_period: str | None = Field(default=None, max_length=160)
    version: int = Field(ge=1)
    status: SavedReportStatus
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def _include_original_needs_a_seed(self) -> SavedReportDefinition:
        if self.narrative_policy == "include_original" and not self.seed_narrative:
            raise ValueError(
                "narrative_policy 'include_original' requires a seed_narrative captured "
                "from an existing run; there is nothing to reuse otherwise."
            )
        return self


ExecutionMode = Literal["preview", "publish"]
ExecutionStatus = Literal["running", "completed", "failed"]


class SavedReportExecution(BaseModel):
    """One attempt to run a saved report definition -- the audit trail entry.

    Distinct from an ``Artifact``: this exists even for a "preview" execution
    that never wrote a file, and even for one that failed. ``artifact_ids``
    is denormalised alongside ``run_id`` -- ``ArtifactStore.list(run_id=...)``
    already answers "what did this execution produce," but persisting it here
    keeps the record self-describing even if artifact rows are later pruned.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    saved_report_id: UUID
    #: Null for an execution triggered manually through the API; set when a
    #: SchedulerWorker minted this run on the saved report's own schedule.
    scheduled_report_id: UUID | None = None
    run_id: str = Field(min_length=1, max_length=255)
    mode: ExecutionMode
    status: ExecutionStatus
    resolved_period_start: date | None = None
    resolved_period_end: date | None = None
    formats: list[str] | None = None
    error: str | None = Field(default=None, max_length=2_000)
    #: A closed vocabulary matching app.reliability.contracts.FailureCategory,
    #: so a scheduled failure is groupable the same way a runtime one is.
    error_category: str | None = Field(default=None, max_length=32)
    retry_count: int = Field(default=0, ge=0)
    usage_metadata: dict[str, Any] = Field(default_factory=dict)
    artifact_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    completed_at: datetime | None = None
