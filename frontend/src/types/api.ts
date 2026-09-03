/**
 * Readable aliases over the generated OpenAPI types.
 *
 * types/api.generated.ts is produced by `npm run gen:api` and must not be
 * edited. Addressing its schemas through components["schemas"][...] at every
 * call site is unreadable, so the names the Workbench uses live here.
 */
import type { components } from "@/types/api.generated";
import type { PublicRunEventType } from "@/lib/api/events";

type Schemas = components["schemas"];

/**
 * Mark every property of a response present.
 *
 * A pydantic field with a default is not *required* in JSON Schema, so the
 * generator marks it optional. FastAPI still serialises it on every response,
 * so the field is always on the wire — `error?: string | null` really means
 * `error: string | null`. Applied to responses only; request bodies have
 * genuinely optional fields.
 */
type Always<T> = T extends (infer U)[]
  ? Always<U>[]
  : T extends object
    ? { [K in keyof T]-?: Always<T[K]> }
    : T;

export type RunStatus = Schemas["RunStatus"];
export type ChartType = Schemas["ChartSpec"]["type"];
export type ChartSpec = Always<Schemas["ChartSpec"]>;
export type AnswerSource = Always<Schemas["AnswerSource"]>;
export type ReportTemplate = Always<Schemas["ReportTemplateResponse"]>;
export type PublishReportRequest = Schemas["PublishReportRequest"];
export type PublishedDocument = Always<Schemas["PublishedDocumentResponse"]>;
export type PublishReportResponse = Always<Schemas["PublishReportResponse"]>;
export type DocumentFormat = PublishReportRequest["formats"][number];
export type RerunMetric = Always<Schemas["MetricSummaryResponse"]>;
export type MetricParameters = Schemas["MetricParameters"];
export type MetricFilter = Schemas["MetricFilter"];
export type ReportPeriod = Schemas["ReportPeriod"];
export type NarrativeStatus = NonNullable<PublishReportRequest["narrative"]>;
export type RunMetrics = Always<Schemas["RunMetricsResponse"]>;
export type CreateRunRequest = Schemas["CreateRunRequest"];
export type CreateRunResponse = Always<Schemas["CreateRunResponse"]>;
export type AnalystRun = Always<Schemas["RunResponse"]>;
export type RunHistory = Always<Schemas["RunHistoryResponse"]>;

export type Conversation = Always<Schemas["ConversationResponse"]>;
export type ConversationMessage = Always<Schemas["app__api__schemas__analytics__MessageResponse"]>;
export type ConversationList = Always<Schemas["ConversationListResponse"]>;
export type ConversationDetail = Always<Schemas["ConversationDetailResponse"]>;

export type Approval = Always<Schemas["ApprovalResponse"]>;
export type WorkbenchConfig = Always<Schemas["WorkbenchConfigResponse"]>;

/** The runtime's artifact record, as embedded in an agent run response. */
export type Artifact = Always<Schemas["Artifact"]>;
/** What GET /artifacts lists, which renames and narrows the record above. */
export type ArtifactMetadata = Always<Schemas["ArtifactMetadata"]>;

export type DatabaseTable = Always<Schemas["DatabaseTable"]>;
export type DatabaseColumn = Always<Schemas["DatabaseColumn"]>;
export type TableDescription = Always<Schemas["TableDescription"]>;
export type DatabaseSchemaSummary = Always<Schemas["DatabaseSchemaSummary"]>;
export type ForeignKeyRelationship = Always<Schemas["ForeignKeyRelationship"]>;

/**
 * The server types this field as a plain string; the Workbench narrows it to
 * the projected vocabulary so an unhandled event name is a compile error.
 */
export type PublicRunEvent = Omit<Always<Schemas["PublicRunEvent"]>, "type"> & {
  type: PublicRunEventType;
};
export type PublicRunEventListResponse = Always<Schemas["PublicRunEventListResponse"]>;

export type ReportPreviewRequest = Schemas["ReportPreviewRequest"];
export type ReportPreview = Always<Schemas["ReportPreview"]>;
export type CompiledReport = Always<Schemas["CompiledReport"]>;
/** One block of a compiled report, discriminated by `kind`. */
export type ReportBlock = CompiledReport["blocks"][number];
export type CompiledMetric = Always<Schemas["CompiledMetric"]>;
export type CompiledRows = Always<Schemas["CompiledRows"]>;
export type EvidenceEntry = Always<Schemas["EvidenceEntry"]>;
export type TemplateAssignment = Always<Schemas["TemplateAssignment"]>;
export type SlotAssignment = Always<Schemas["SlotAssignment"]>;
export type TemplateSuitability = Always<Schemas["TemplateSuitability"]>;
export type TemplateSuitabilityOverview = Always<Schemas["TemplateSuitabilityOverview"]>;

export type SavedReportMetricRequest = Always<Schemas["MetricRequestPayload"]>;
export type SavedReportRelativePeriod = Always<Schemas["RelativePeriodPayload"]>;
export type RelativePeriodKind = SavedReportRelativePeriod["kind"];
export type SavedReportCreateRequest = Schemas["SavedReportCreateRequest"];
export type SavedReportUpdateRequest = Schemas["SavedReportUpdateRequest"];
export type SavedReportArchiveRequest = Schemas["SavedReportArchiveRequest"];
export type NarrativePolicy = NonNullable<SavedReportCreateRequest["narrative_policy"]>;
export type SavedReportSummary = Always<Schemas["SavedReportSummaryResponse"]>;
export type SavedReport = Always<Schemas["SavedReportResponse"]>;
export type SavedReportList = Always<Schemas["SavedReportListResponse"]>;
export type SavedReportResolvedParameters = Always<Schemas["ResolvedParametersResponse"]>;
export type SavedReportExecuteRequest = Schemas["SavedReportExecuteRequest"];
export type SavedReportDocument = Always<Schemas["PublishedDocumentSummary"]>;
export type SavedReportExecuteResponse = Always<Schemas["SavedReportExecuteResponse"]>;
export type SavedReportExecution = Always<Schemas["SavedReportExecutionResponse"]>;
export type SavedReportExecutionList = Always<Schemas["SavedReportExecutionListResponse"]>;

// -- authentication -----------------------------------------------------------

export type RegisterRequest = Schemas["RegisterRequest"];
export type LoginRequest = Schemas["LoginRequest"];
export type ForgotPasswordRequest = Schemas["ForgotPasswordRequest"];
export type ResetPasswordRequest = Schemas["ResetPasswordRequest"];
export type AuthUser = Always<Schemas["UserResponse"]>;
export type AuthMessage = Always<Schemas["app__api__schemas__auth__MessageResponse"]>;

// -- tenancy --------------------------------------------------------------------

export type Role = Schemas["Role"];
export type MembershipStatus = Schemas["MembershipStatus"];
export type Workspace = Always<Schemas["WorkspaceResponse"]>;
export type WorkspaceList = Always<Schemas["WorkspaceListResponse"]>;
export type WorkspaceCreateRequest = Schemas["WorkspaceCreateRequest"];
export type WorkspaceUpdateRequest = Schemas["WorkspaceUpdateRequest"];
export type Membership = Always<Schemas["MembershipResponse"]>;
export type MembershipList = Always<Schemas["MembershipListResponse"]>;
export type Invitation = Always<Schemas["InvitationResponse"]>;
export type InviteMemberRequest = Schemas["InviteMemberRequest"];
export type AcceptInvitationRequest = Schemas["AcceptInvitationRequest"];
export type ChangeRoleRequest = Schemas["ChangeRoleRequest"];
export type TransferOwnershipRequest = Schemas["TransferOwnershipRequest"];
export type ChangePasswordRequest = Schemas["ChangePasswordRequest"];

export type ReportPreferences = Always<Schemas["ReportPreferencesResponse"]>;
export type ReportPreferencesUpdateRequest = Schemas["ReportPreferencesUpdateRequest"];
/** Mirrors `app.reports.contracts.NarrativePolicy` -- the same three values used by saved reports. */
export type NarrativePolicyDefault = NonNullable<ReportPreferences["default_narrative_policy"]>;

export type AuditLogEntry = Always<Schemas["AuditLogEntryResponse"]>;
export type AuditLogList = Always<Schemas["AuditLogListResponse"]>;

// -- user settings --------------------------------------------------------------

export type UserSettings = Always<Schemas["UserSettingsResponse"]>;
export type UserSettingsUpdateRequest = Schemas["UserSettingsUpdateRequest"];
export type RequestEmailChangeRequest = Schemas["RequestEmailChangeRequest"];
export type ConfirmEmailChangeRequest = Schemas["ConfirmEmailChangeRequest"];
export type VerifyEmailConfirmRequest = Schemas["VerifyEmailConfirmRequest"];
