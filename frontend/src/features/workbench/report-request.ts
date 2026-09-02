import type { MetricParameters, NarrativeStatus } from "@/types/analytics";

/**
 * The request body shared by a report preview and a report publish.
 *
 * Built once so the two can never quietly drift apart — whatever a reader
 * last previewed is exactly what publishing that same selection will compile.
 */
export function reportRequestPayload({
  template,
  period,
  metrics,
  narrative,
}: {
  template: string;
  period: string;
  metrics: MetricParameters[];
  narrative: NarrativeStatus;
}) {
  return {
    template,
    ...(period.trim() ? { period: period.trim() } : {}),
    ...(metrics.length ? { metrics, narrative } : {}),
  };
}
