"""Typed, evidence-linked analytical report contracts and Markdown rendering."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReportType(StrEnum):
    EXECUTIVE = "executive"
    SALES = "sales"
    MARKETING = "marketing"
    CUSTOMER = "customer"
    OPERATIONS = "operations"
    INVENTORY = "inventory"


class ReportMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=128)
    value: str | int | float
    unit: str | None = Field(default=None, max_length=64)
    comparison: str | None = Field(default=None, max_length=512)
    metric_definition_id: str | None = Field(default=None, max_length=128)
    evidence_query_ids: list[str] = Field(min_length=1)


class ReportFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    statement: str = Field(min_length=1, max_length=2_000)
    evidence_query_ids: list[str] = Field(min_length=1)
    caveat: str | None = Field(default=None, max_length=1_000)


class ReportRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(min_length=1, max_length=1_000)
    rationale: str = Field(min_length=1, max_length=1_000)
    evidence_query_ids: list[str] = Field(min_length=1)


class ReportSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=128)
    metrics: list[ReportMetric] = Field(default_factory=list)
    findings: list[ReportFinding] = Field(default_factory=list)


class ReportArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    artifact_type: str


class AnalyticalReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    report_type: ReportType
    title: str = Field(min_length=1, max_length=256)
    time_period: str = Field(min_length=1, max_length=256)
    executive_summary: str = Field(min_length=1, max_length=4_000)
    sections: list[ReportSection] = Field(default_factory=list)
    recommendations: list[ReportRecommendation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    source_query_ids: list[str] = Field(min_length=1)
    dataset_ids_for_csv: list[str] = Field(default_factory=list)
    chart_artifact_ids: list[str] = Field(default_factory=list)

    @field_validator("source_query_ids")
    @classmethod
    def query_ids_must_be_stable(cls, values: list[str]) -> list[str]:
        if any(not value.startswith("query_") for value in values):
            raise ValueError("Report evidence must use stable query references.")
        return values


def render_markdown(report: AnalyticalReport) -> str:
    lines = [f"# {report.title}", "", f"**Period:** {report.time_period}", "", "## Executive Summary", "", report.executive_summary]
    for section in report.sections:
        lines.extend(["", f"## {section.title}"])
        for metric in section.metrics:
            suffix = f" {metric.unit}" if metric.unit else ""
            comparison = f" ({metric.comparison})" if metric.comparison else ""
            definition = f" ({metric.metric_definition_id})" if metric.metric_definition_id else ""
            lines.append(f"- **{metric.name}:** {metric.value}{suffix}{comparison}{definition} [{', '.join(metric.evidence_query_ids)}]")
        for finding in section.findings:
            lines.append(f"- {finding.statement} [{', '.join(finding.evidence_query_ids)}]")
            if finding.caveat:
                lines.append(f"  - Caveat: {finding.caveat}")
    if report.recommendations:
        lines.extend(["", "## Recommended Actions"])
        for item in report.recommendations:
            lines.append(f"- **{item.action}:** {item.rationale} [{', '.join(item.evidence_query_ids)}]")
    if report.limitations:
        lines.extend(["", "## Limitations"])
        lines.extend(f"- {item}" for item in report.limitations)
    return "\n".join(lines) + "\n"
