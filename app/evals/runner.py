"""CLI and in-process runner for deterministic evaluation datasets."""

import argparse
import asyncio
import json
from pathlib import Path
from time import perf_counter
from typing import Callable

from app.agent.models import AgentAction
from app.agent.runner import AgentRunner
from app.core.limits import RuntimeLimits
from app.evals.evaluators import DEFAULT_EVALUATORS, Evaluator
from app.evals.models import EvalCase, EvalDataset, EvalResult, SuiteReport
from app.evals.reports import format_report
from app.evals.trajectory import Trajectory
from app.llm.base import LLMClient
from app.observability import InMemoryTraceStore, TraceRecorder, aggregate_run_metrics
from app.skills.registry import SkillRegistry
from app.tools.calculator import CalculatorTool
from app.tools.registry import ToolRegistry

DATASET_DIRECTORY = Path(__file__).with_name("datasets")
RunnerFactory = Callable[[EvalCase, TraceRecorder], AgentRunner]


class ScriptedEvalLLM(LLMClient):
    """A deterministic action source used only by local datasets and CI tests."""

    def __init__(self, actions: list[object]) -> None:
        self._actions = actions
        self._index = 0

    async def choose_action(self, *, system_prompt: str, context: dict[str, object]) -> AgentAction:
        if not self._actions:
            return AgentAction(action_type="finish", reasoning_summary="", final_answer="Evaluation complete.")
        action = self._actions[min(self._index, len(self._actions) - 1)]
        self._index += 1
        if isinstance(action, BaseException):
            raise action
        return action


def load_dataset(path: Path) -> EvalDataset:
    """Parse one strict, readable JSON suite."""

    return EvalDataset.model_validate_json(path.read_text(encoding="utf-8"))


def load_datasets(directory: Path = DATASET_DIRECTORY) -> dict[str, EvalDataset]:
    """Load all suite files, rejecting duplicate suite names or case IDs."""

    paths = [path for path in sorted(directory.glob("*.json")) if path.name != "analytics_cases.json"]
    datasets = {dataset.suite: dataset for dataset in (load_dataset(path) for path in paths)}
    if len(datasets) != len(paths):
        raise ValueError("Dataset suite names must be unique.")
    case_ids = [case.id for dataset in datasets.values() for case in dataset.cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Eval case IDs must be unique across datasets.")
    return datasets


def deterministic_runner_factory(case: EvalCase, recorder: TraceRecorder) -> AgentRunner:
    """Build the small no-network runtime used by bundled example datasets."""

    actions: list[object] = []
    for raw in case.setup.get("actions", []):
        if isinstance(raw, dict) and raw.get("failure") == "timeout":
            actions.append(TimeoutError("Synthetic transient timeout."))
        elif isinstance(raw, dict) and raw.get("failure") == "rate_limit":
            actions.append(RuntimeError("Synthetic rate limit."))
        elif isinstance(raw, dict) and raw.get("failure") == "invalid_output":
            actions.append(object())
        else:
            actions.append(AgentAction.model_validate(raw))
    tools = ToolRegistry()
    tools.register(CalculatorTool())
    return AgentRunner(ScriptedEvalLLM(actions), tools, SkillRegistry(), limits=RuntimeLimits(max_iterations=8),
                       trace_recorder=recorder)


class EvalRunner:
    def __init__(self, runner_factory: RunnerFactory = deterministic_runner_factory,
                 evaluators: tuple[Evaluator, ...] = DEFAULT_EVALUATORS,
                 trace_recorder: TraceRecorder | None = None) -> None:
        self._runner_factory = runner_factory
        self._evaluators = evaluators
        self._trace_recorder = trace_recorder or TraceRecorder(InMemoryTraceStore())

    async def run_case(self, case: EvalCase, *, suite: str = "adhoc") -> EvalResult:
        started = perf_counter()
        state = await self._runner_factory(case, self._trace_recorder).run(case.goal)
        trace = self._trace_recorder.get_trace(state.run_id)
        trajectory = Trajectory.from_trace(trace, self._trace_recorder.get_trace) if trace else None
        evaluator_results = [evaluator.evaluate(case, state, trace, trajectory) for evaluator in self._evaluators]
        failures = [result.reason for result in evaluator_results if not result.passed and result.reason]
        passed = not failures
        trajectory_results = [result for result in evaluator_results if result.evaluator.endswith("Evaluator")
                              and result.evaluator not in {"RunCompletedEvaluator", "ExpectedStopReasonEvaluator", "RequiredToolUsedEvaluator", "ForbiddenToolUsedEvaluator", "SkillUsedEvaluator", "DelegationUsedEvaluator", "ArtifactCreatedEvaluator", "SecurityDecisionEvaluator"}]
        trajectory_score = (sum(item.passed for item in trajectory_results) / len(trajectory_results)
                            if trajectory_results else None)
        return EvalResult(case_id=case.id, suite=suite, passed=passed,
            score=sum(result.passed for result in evaluator_results) / len(evaluator_results),
            failure_reasons=failures, run_id=state.run_id,
            duration_ms=round((perf_counter() - started) * 1000),
            stop_reason=state.stop_reason.value if state.stop_reason else None,
            trace_run_id=trace.run_id if trace else None, evaluator_results=evaluator_results,
            trajectory_score=trajectory_score,
            trajectory_diagnostics=[result.reason for result in trajectory_results if not result.passed and result.reason],
            metrics=trace.metrics if trace else None,
            system_metrics=aggregate_run_metrics(trace, self._trace_recorder.get_trace) if trace else None)

    async def run_suite(self, dataset: EvalDataset) -> SuiteReport:
        return SuiteReport(suite=dataset.suite,
            results=[await self.run_case(case, suite=dataset.suite) for case in dataset.cases])

    async def run_all(self, datasets: dict[str, EvalDataset]) -> list[SuiteReport]:
        return [await self.run_suite(dataset) for dataset in datasets.values()]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run deterministic autonomous-agent evaluations.")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--suite")
    selection.add_argument("--case")
    selection.add_argument("--all", action="store_true")
    parser.add_argument("--json-output", type=Path)
    return parser


async def _main(args: argparse.Namespace) -> int:
    datasets = load_datasets()
    runner = EvalRunner()
    if args.case:
        matches = [(suite, case) for suite, dataset in datasets.items() for case in dataset.cases if case.id == args.case]
        if not matches:
            raise ValueError(f"Unknown eval case: {args.case}")
        suite, case = matches[0]
        reports = [SuiteReport(suite=suite, results=[await runner.run_case(case, suite=suite)])]
    elif args.suite:
        if args.suite not in datasets:
            raise ValueError(f"Unknown suite: {args.suite}")
        reports = [await runner.run_suite(datasets[args.suite])]
    else:
        reports = await runner.run_all(datasets)
    print("\n\n".join(format_report(report) for report in reports))
    if args.json_output:
        args.json_output.write_text(json.dumps([report.model_dump() for report in reports], indent=2) + "\n", encoding="utf-8")
    return 0 if all(result.passed for report in reports for result in report.results) else 1


def main() -> int:
    return asyncio.run(_main(_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
