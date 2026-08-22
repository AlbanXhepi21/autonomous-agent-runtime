"""Deterministic V7.2 runtime evaluation framework."""

from app.evals.contracts import EvalCase, EvalDataset, EvalResult, EvaluatorResult, SuiteReport
from app.evals.analytics import AnalyticsBenchmarkSummary, AnalyticsEvalCase, AnalyticsEvalDataset, GroundTruthLoader

__all__ = ["EvalCase", "EvalDataset", "EvalResult", "EvalRunner", "EvaluatorResult", "SuiteReport", "load_dataset", "load_datasets",
           "AnalyticsBenchmarkSummary", "AnalyticsEvalCase", "AnalyticsEvalDataset", "GroundTruthLoader"]


def __getattr__(name: str):
    """Avoid importing the CLI module while it is executed with ``-m``."""

    if name in {"EvalRunner", "load_dataset", "load_datasets"}:
        from app.evals.runner import EvalRunner, load_dataset, load_datasets
        return {"EvalRunner": EvalRunner, "load_dataset": load_dataset, "load_datasets": load_datasets}[name]
    raise AttributeError(name)
