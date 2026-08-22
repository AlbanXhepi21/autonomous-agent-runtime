"""What a finished run exposes to the packages that consume its outcome.

Post-run consumers read a handful of fields, not the runtime's whole working
state. Declaring that subset structurally lets those packages depend on the
shape they need, so ``AgentState`` satisfies these protocols without naming
them and without either side importing the other.
"""

from collections.abc import Sequence
from typing import Protocol


class RunSummary(Protocol):
    """The part of a task summary that outlives the run that produced it."""

    @property
    def important_decisions(self) -> Sequence[str]: ...


class CompletedRun(Protocol):
    """The outcome of a run, as seen from outside the runtime."""

    @property
    def run_id(self) -> str: ...

    @property
    def completed(self) -> bool: ...

    @property
    def final_answer(self) -> str | None: ...

    @property
    def task_summary(self) -> RunSummary | None: ...
