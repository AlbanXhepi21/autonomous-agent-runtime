"use client";

import { useCallback, useState } from "react";
import { savedReportsApi } from "@/lib/api/saved-reports";
import { ApiError } from "@/lib/api/client";
import type {
  SavedReport,
  SavedReportCreateRequest,
  SavedReportExecuteResponse,
  SavedReportExecution,
  SavedReportResolvedParameters,
  SavedReportSummary,
  SavedReportUpdateRequest,
} from "@/types/saved-reports";

export const SAVED_REPORT_PAGE_SIZE = 10;

/**
 * The saved-reports sidebar: listing, opening one, editing, archiving and
 * running it again.
 *
 * Selecting a report fetches its full definition, its resolved parameters
 * (what running it right now would use) and its execution history together,
 * since a reader opening one wants all three at once.
 */
export function useSavedReports(workspaceId: string) {
  const [items, setItems] = useState<SavedReportSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState<"active" | "archived">("active");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<SavedReport | null>(null);
  const [resolvedParameters, setResolvedParameters] = useState<SavedReportResolvedParameters | null>(
    null,
  );
  const [executions, setExecutions] = useState<SavedReportExecution[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [lastResult, setLastResult] = useState<SavedReportExecuteResponse | null>(null);

  const load = useCallback(
    async (status: "active" | "archived" = statusFilter) => {
      try {
        const page = await savedReportsApi.list(workspaceId, status, SAVED_REPORT_PAGE_SIZE, 0);
        setStatusFilter(status);
        setItems(page.items);
        setTotal(page.total);
        setError(null);
      } catch {
        setError("Saved reports could not be loaded.");
      }
    },
    [statusFilter, workspaceId],
  );

  const select = useCallback(
    async (id: string) => {
      setSelectedId(id);
      setBusy(true);
      setError(null);
      setLastResult(null);
      try {
        const [report, resolved, executionPage] = await Promise.all([
          savedReportsApi.get(workspaceId, id),
          savedReportsApi.resolvedParameters(workspaceId, id),
          savedReportsApi.executions(workspaceId, id),
        ]);
        setDetail(report);
        setResolvedParameters(resolved);
        setExecutions(executionPage.items);
      } catch {
        setError("This saved report could not be opened.");
      } finally {
        setBusy(false);
      }
    },
    [workspaceId],
  );

  const close = useCallback(() => {
    setSelectedId(null);
    setDetail(null);
    setResolvedParameters(null);
    setExecutions([]);
    setLastResult(null);
  }, []);

  const create = useCallback(
    async (payload: SavedReportCreateRequest) => {
      setBusy(true);
      setError(null);
      try {
        const report = await savedReportsApi.create(workspaceId, payload);
        setItems((current) => [report, ...current]);
        setTotal((current) => current + 1);
        return report;
      } catch (cause) {
        setError(cause instanceof ApiError ? cause.message : "The saved report could not be created.");
        return null;
      } finally {
        setBusy(false);
      }
    },
    [workspaceId],
  );

  const update = useCallback(
    async (changes: Omit<SavedReportUpdateRequest, "expected_version">) => {
      if (!detail) return null;
      setBusy(true);
      setError(null);
      try {
        const updated = await savedReportsApi.update(workspaceId, detail.id, {
          expected_version: detail.version,
          ...changes,
        });
        setDetail(updated);
        setItems((current) => current.map((item) => (item.id === updated.id ? updated : item)));
        return updated;
      } catch (cause) {
        setError(
          cause instanceof ApiError && cause.status === 409
            ? "This saved report changed elsewhere. Reopen it to see the latest version."
            : "The saved report could not be updated.",
        );
        return null;
      } finally {
        setBusy(false);
      }
    },
    [detail, workspaceId],
  );

  const archive = useCallback(async () => {
    if (!detail) return;
    setBusy(true);
    setError(null);
    try {
      const archived = await savedReportsApi.archive(workspaceId, detail.id, { expected_version: detail.version });
      setDetail(archived);
      setItems((current) => current.filter((item) => item.id !== archived.id));
      setTotal((current) => Math.max(0, current - 1));
    } catch {
      setError("The saved report could not be archived.");
    } finally {
      setBusy(false);
    }
  }, [detail, workspaceId]);

  const execute = useCallback(
    async (mode: "preview" | "publish", formats: ("pdf" | "docx")[] = ["pdf"]) => {
      if (!detail) return null;
      setBusy(true);
      setError(null);
      try {
        const result = await savedReportsApi.execute(workspaceId, detail.id, { mode, formats });
        setLastResult(result);
        const executionPage = await savedReportsApi.executions(workspaceId, detail.id);
        setExecutions(executionPage.items);
        return result;
      } catch (cause) {
        setError(cause instanceof ApiError ? cause.message : "This saved report could not be run.");
        return null;
      } finally {
        setBusy(false);
      }
    },
    [detail, workspaceId],
  );

  return {
    items,
    total,
    statusFilter,
    selectedId,
    detail,
    resolvedParameters,
    executions,
    error,
    setError,
    busy,
    lastResult,
    load,
    select,
    close,
    create,
    update,
    archive,
    execute,
  };
}
