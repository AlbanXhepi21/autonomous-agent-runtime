"use client";

import { useEffect, useState } from "react";
import { configApi } from "@/lib/api/config";
import type { WorkbenchConfig } from "@/types/api";

/** Nothing developer-only is offered until the server says it is enabled. */
const CLOSED: WorkbenchConfig = { developer_mode: false };

/**
 * What this server has enabled.
 *
 * The server is the single source for these switches, and the endpoints behind
 * them enforce their own access, so a stale or failed read can only hide a
 * control, never expose one.
 */
export function useWorkbenchConfig(): WorkbenchConfig {
  const [config, setConfig] = useState<WorkbenchConfig>(CLOSED);

  useEffect(() => {
    let active = true;
    void configApi
      .get()
      .then((result) => {
        if (active) setConfig(result);
      })
      .catch(() => {
        if (active) setConfig(CLOSED);
      });
    return () => {
      active = false;
    };
  }, []);

  return config;
}
