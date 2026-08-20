"""Offline evaluator CLI for recorded Data Analyst runs.

The analyst run must be completed first. This command receives only its
sanitized trace and final answer; it reads private ground truth afterwards.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.agent.state import AgentState
from app.evals.analytics import (AnalyticsBenchmarkSummary, DeterministicAnalyticsEvaluator,
                                 GroundTruthLoader, load_analytics_dataset)
from app.observability import RunTrace


def evaluate_recordings(*, dataset_path: Path, ground_truth_path: Path, recordings: list[dict[str, object]]) -> AnalyticsBenchmarkSummary:
    cases = {case.id: case for case in load_analytics_dataset(dataset_path).cases}
    evaluator = DeterministicAnalyticsEvaluator(GroundTruthLoader.load(ground_truth_path))
    results = []
    for recording in recordings:
        case_id = recording.get("case_id")
        if not isinstance(case_id, str) or case_id not in cases:
            raise ValueError(f"Recording references unknown case: {case_id!r}")
        state = AgentState.model_validate(recording["state"])
        trace_payload = recording.get("trace")
        trace = RunTrace.model_validate(trace_payload) if isinstance(trace_payload, dict) else None
        results.append(evaluator.evaluate(cases[case_id], state, trace))
    return AnalyticsBenchmarkSummary.from_results(results)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate recorded Data Analyst benchmark runs.")
    parser.add_argument("--ground-truth", type=Path, required=True, help="Private data-generator scenarios JSON.")
    parser.add_argument("--recordings", type=Path, required=True, help="JSON list of sanitized completed runs.")
    parser.add_argument("--dataset", type=Path, default=Path(__file__).with_name("datasets") / "analytics_cases.json")
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    parser.add_argument("--previous", type=Path, help="Optional prior JSON summary for comparison.")
    args = parser.parse_args()
    recordings = json.loads(args.recordings.read_text(encoding="utf-8"))
    if not isinstance(recordings, list):
        raise ValueError("Recordings must be a JSON list.")
    summary = evaluate_recordings(dataset_path=args.dataset, ground_truth_path=args.ground_truth, recordings=recordings)
    previous = AnalyticsBenchmarkSummary.model_validate_json(args.previous.read_text(encoding="utf-8")) if args.previous else None
    args.json_output.write_text(summary.model_dump_json(indent=2) + "\n", encoding="utf-8")
    args.markdown_output.write_text(summary.markdown(previous) + "\n", encoding="utf-8")
    print(summary.markdown(previous))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
