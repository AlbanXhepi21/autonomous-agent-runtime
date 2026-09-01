import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ReportExport } from "./report-export";
import { analyticsApi } from "@/lib/api/analytics";
import { ApiError } from "@/lib/api/client";

vi.mock("@/lib/api/analytics", () => ({
  analyticsApi: { reportTemplates: vi.fn(), publishReport: vi.fn(), rerunMetrics: vi.fn() },
}));

const templates = {
  items: [
    {
      name: "monthly_business_review",
      title: "Monthly Business Review",
      description: "Headline metrics and the month's movements.",
      report_type: "executive",
      period_granularity: "month",
      sections: ["Executive summary", "Evidence"],
    },
  ],
};

describe("ReportExport", () => {
  beforeEach(() => {
    vi.mocked(analyticsApi.reportTemplates).mockResolvedValue(templates);
    // Recompute controls are built from the server's metric definitions; with
    // none offered the panel does not render and export behaves as before.
    vi.mocked(analyticsApi.rerunMetrics).mockResolvedValue({ items: [] });
    vi.mocked(analyticsApi.publishReport).mockResolvedValue({
      run_id: "run-1",
      template: "monthly_business_review",
      narrative: "current",
      rerun_query_ids: [],
      documents: [
        {
          artifact_id: "a1",
          name: "monthly_business_review.pdf",
          media_type: "application/pdf",
          size: 74000,
        },
      ],
    });
  });

  const openPanel = async () => {
    render(<ReportExport runId="run-1" />);
    fireEvent.click(screen.getByRole("button", { name: "Export report" }));
    await screen.findByText("Headline metrics and the month's movements.");
  };

  it("offers the available templates once opened", async () => {
    await openPanel();

    expect(screen.getByRole("combobox")).toHaveValue("monthly_business_review");
  });

  it("publishes the chosen template and offers the document", async () => {
    await openPanel();

    fireEvent.click(screen.getByRole("button", { name: "Generate" }));

    await waitFor(() =>
      expect(analyticsApi.publishReport).toHaveBeenCalledWith("run-1", {
        template: "monthly_business_review",
        formats: ["pdf"],
      }),
    );
    expect(
      await screen.findByText(/Download monthly_business_review.pdf \(72 KB\)/),
    ).toBeInTheDocument();
  });

  it("sends a period only when one was typed", async () => {
    await openPanel();

    fireEvent.change(screen.getByPlaceholderText("August 2026"), {
      target: { value: "  August 2026  " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Generate" }));

    await waitFor(() =>
      expect(analyticsApi.publishReport).toHaveBeenCalledWith(
        "run-1",
        expect.objectContaining({ period: "August 2026" }),
      ),
    );
  });

  it("can request both formats at once", async () => {
    await openPanel();

    fireEvent.click(screen.getByRole("button", { name: "Word" }));
    fireEvent.click(screen.getByRole("button", { name: "Generate" }));

    await waitFor(() =>
      expect(analyticsApi.publishReport).toHaveBeenCalledWith(
        "run-1",
        expect.objectContaining({ formats: ["pdf", "docx"] }),
      ),
    );
  });

  it("cannot generate with no format selected", async () => {
    await openPanel();

    fireEvent.click(screen.getByRole("button", { name: "PDF" }));

    expect(screen.getByRole("button", { name: "Generate" })).toBeDisabled();
  });

  it("reports a failure instead of a silent no-op", async () => {
    vi.mocked(analyticsApi.publishReport).mockRejectedValue(
      new ApiError("Only a completed run can be published."),
    );
    await openPanel();

    fireEvent.click(screen.getByRole("button", { name: "Generate" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Only a completed run can be published.",
    );
  });
});
