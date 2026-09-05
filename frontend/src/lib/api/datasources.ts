import { request } from "@/lib/api/client";
import type {
  ConnectionTestResult,
  DataSource,
  DataSourceCreateRequest,
  DataSourceList,
  DataSourceReplaceCredentialsRequest,
  DataSourceUpdateRequest,
  ReadOnlyVerification,
} from "@/types/api";

export const dataSourcesApi = {
  list: (workspaceId: string) =>
    request<DataSourceList>(`/api/v1/workspaces/${workspaceId}/datasources`),
  get: (workspaceId: string, dataSourceId: string) =>
    request<DataSource>(`/api/v1/workspaces/${workspaceId}/datasources/${dataSourceId}`),
  create: (workspaceId: string, body: DataSourceCreateRequest) =>
    request<DataSource>(`/api/v1/workspaces/${workspaceId}/datasources`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  update: (workspaceId: string, dataSourceId: string, body: DataSourceUpdateRequest) =>
    request<DataSource>(`/api/v1/workspaces/${workspaceId}/datasources/${dataSourceId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  replaceCredentials: (
    workspaceId: string,
    dataSourceId: string,
    body: DataSourceReplaceCredentialsRequest,
  ) =>
    request<DataSource>(
      `/api/v1/workspaces/${workspaceId}/datasources/${dataSourceId}/replace-credentials`,
      { method: "POST", body: JSON.stringify(body) },
    ),
  testConnection: (workspaceId: string, dataSourceId: string) =>
    request<ConnectionTestResult>(
      `/api/v1/workspaces/${workspaceId}/datasources/${dataSourceId}/test-connection`,
      { method: "POST" },
    ),
  verifyReadOnly: (workspaceId: string, dataSourceId: string) =>
    request<ReadOnlyVerification>(
      `/api/v1/workspaces/${workspaceId}/datasources/${dataSourceId}/verify-read-only`,
      { method: "POST" },
    ),
  enable: (workspaceId: string, dataSourceId: string) =>
    request<DataSource>(`/api/v1/workspaces/${workspaceId}/datasources/${dataSourceId}/enable`, {
      method: "POST",
    }),
  disable: (workspaceId: string, dataSourceId: string) =>
    request<DataSource>(`/api/v1/workspaces/${workspaceId}/datasources/${dataSourceId}/disable`, {
      method: "POST",
    }),
  remove: (workspaceId: string, dataSourceId: string) =>
    request<DataSource>(`/api/v1/workspaces/${workspaceId}/datasources/${dataSourceId}`, {
      method: "DELETE",
    }),
};
