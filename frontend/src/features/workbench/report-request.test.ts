import { describe, expect, it } from "vitest";
import { reportRequestPayload } from "@/features/workbench/report-request";

describe("reportRequestPayload", () => {
  it("sends only the template when nothing else was chosen", () => {
    expect(
      reportRequestPayload({ template: "monthly_business_review", period: "", metrics: [], narrative: "current" }),
    ).toEqual({ template: "monthly_business_review" });
  });

  it("trims and includes a typed period", () => {
    expect(
      reportRequestPayload({
        template: "monthly_business_review", period: "  August 2026  ", metrics: [], narrative: "current",
      }),
    ).toEqual({ template: "monthly_business_review", period: "August 2026" });
  });

  it("includes metrics and narrative only when a rerun was requested", () => {
    const metrics = [{ metric: "revenue", period: { start: "2026-01-01", end: "2026-01-31" }, grain: "day" as const }];

    const payload = reportRequestPayload({
      template: "monthly_business_review", period: "", metrics, narrative: "pinned_to_original_period",
    });

    expect(payload).toEqual({
      template: "monthly_business_review", metrics, narrative: "pinned_to_original_period",
    });
  });
});
