"""What a finished answer cites, and what those citations resolve to.

An answer references evidence by identifier; the runtime resolves each
identifier against what the run actually executed and writes the resulting
registry beside the answer. The model never authors a source record, so a
citation cannot describe evidence that does not exist.

The registry is denormalised on purpose. Query identifiers are minted against
a process-local trace that is evicted on restart, so a stored citation holding
only ``query_003`` would resolve to nothing the next time the conversation is
opened.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ``database_query`` is SQL the agent wrote during a run. ``metric_rerun`` is a
# statement the runtime compiled from a metric definition when a reader changed
# a report's parameters — a different provenance story, so a different kind
# rather than a flag on the same one.
AnswerSourceKind = Literal["database_query", "metric_rerun"]


class AnswerSource(BaseModel):
    """One piece of evidence an answer may cite, captured so it outlives its trace."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=80)
    kind: AnswerSourceKind = "database_query"
    run_id: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1, max_length=200)
    referenced_tables: list[str] = Field(default_factory=list, max_length=16)
    #: The result's column names, recorded by the runtime from what the executor
    #: returned. Empty on evidence stored before this was captured.
    columns: list[str] = Field(default_factory=list, max_length=32)
    row_count: int | None = Field(default=None, ge=0)
    truncated: bool = False
    executed_at: datetime | None = None
    #: Set only on a ``metric_rerun``: which definition was compiled, and with
    #: what. These say how the statement was arrived at, which for a rerun is
    #: the whole provenance story — nobody wrote the SQL by hand.
    metric: str | None = Field(default=None, max_length=64)
    dimensions: list[str] = Field(default_factory=list, max_length=4)
    #: Applied filters, each already rendered for a reader.
    filters: list[str] = Field(default_factory=list, max_length=8)
    #: Digest of the compiled statement, so the same question asked twice is
    #: recognisable as the same question.
    sql_fingerprint: str | None = Field(default=None, max_length=64)
