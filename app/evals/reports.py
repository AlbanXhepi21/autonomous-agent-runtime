"""Terminal and JSON-friendly aggregation for evaluation suites."""

from app.evals.models import SuiteReport


def format_report(report: SuiteReport) -> str:
    lines = [f"Suite: {report.suite}", "", f"{report.total} cases", f"{report.passed} passed",
             f"{report.total - report.passed} failed", "", f"Pass rate: {report.pass_rate:.0%}"]
    averages = {"iterations": report.average("iterations"), "LLM calls": report.average("llm_calls"),
                "tokens": report.average("total_tokens"), "cost": report.average("estimated_cost"),
                "latency ms": report.average("total_duration_ms")}
    lines.extend(f"Average {name}: {value:.2f}" if value is not None else f"Average {name}: n/a"
                 for name, value in averages.items())
    for result in report.results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"[{status}] {result.case_id} run={result.run_id or '-'} trace={result.trace_run_id or '-'}")
        lines.extend(f"  - {reason}" for reason in result.failure_reasons)
        if result.trajectory_score is not None:
            lines.append(f"  trajectory score: {result.trajectory_score:.0%}")
        if result.metrics:
            lines.append(f"  metrics: llm={result.metrics.llm_calls} tokens={result.metrics.total_tokens} cost={result.metrics.estimated_cost} latency_ms={result.metrics.total_duration_ms}")
        lines.extend(f"  trajectory: {diagnostic}" for diagnostic in result.trajectory_diagnostics)
    return "\n".join(lines)
