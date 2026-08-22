"""Run-scoped, bounded query-result references for analytics Python work."""

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DatasetReference:
    id: str
    row_count: int
    byte_count: int
    query_id: str


class AnalyticsDatasetStore:
    """Keep only small, runtime-owned query results; never database credentials."""

    def __init__(self, *, max_rows: int, max_bytes: int) -> None:
        self._max_rows, self._max_bytes = max_rows, max_bytes
        self._datasets: dict[tuple[str, str], dict[str, object]] = {}

    def register(self, *, run_id: str, query_id: str, columns: list[dict[str, Any]], rows: list[list[Any]]) -> DatasetReference | None:
        if len(rows) > self._max_rows:
            return None
        data: dict[str, object] = {"columns": [column.get("name", "") for column in columns], "rows": rows}
        byte_count = len(json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8"))
        if byte_count > self._max_bytes:
            return None
        dataset_id = f"dataset_{query_id}"
        self._datasets[(run_id, dataset_id)] = data
        return DatasetReference(id=dataset_id, row_count=len(rows), byte_count=byte_count, query_id=query_id)

    def get(self, *, run_id: str, dataset_id: str) -> dict[str, object] | None:
        return self._datasets.get((run_id, dataset_id))

    def clear_run(self, run_id: str) -> None:
        for key in [key for key in self._datasets if key[0] == run_id]:
            del self._datasets[key]
