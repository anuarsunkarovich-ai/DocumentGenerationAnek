import { z } from 'zod'

import {
  apiKeyMetadataSchema,
  billingPlanSchema,
  cacheStatsSchema,
  templateSchema,
  templateSchemaResponseSchema,
  templateVersionSummarySchema,
  workerStatusSchema,
} from '@shared/api/contracts'

const uuid = () => z.string().uuid()

export const templateVersionDetailSchema = z.object({
  id: uuid(),
  version: z.string(),
  is_current: z.boolean(),
  is_published: z.boolean(),
  original_filename: z.string(),
  storage_key: z.string(),
  checksum: z.string().nullable().optional(),
  notes: z.string().nullable().optional(),
  render_strategy: z.string(),
  imported_binding_count: z.number(),
  schema: templateSchemaResponseSchema,
})

export const templateDetailSchema = templateSchema.extend({
  versions: z.array(templateVersionSummarySchema),
  current_version_details: templateVersionDetailSchema.nullable().optional(),
})

export const templateIngestionResponseSchema = z.object({
  template: templateSchema,
  version: templateVersionDetailSchema,
})

export const templateSchemaExtractionResponseSchema = z.object({
  organization_id: uuid(),
  template_id: uuid(),
  template_version_id: uuid(),
  schema: templateSchemaResponseSchema,
})

export const templateImportFieldCandidateSchema = z.object({
  id: z.string(),
  label: z.string(),
  suggested_binding: z.string(),
  raw_fragment: z.string(),
  paragraph_path: z.string(),
  source_type: z.string(),
  detection_kind: z.string(),
  confidence: z.number(),
  preview_text: z.string(),
  value_type: z.string(),
  component_type: z.string(),
  required: z.boolean(),
  fragment_start: z.number(),
  fragment_end: z.number(),
})

export const templateImportAnalysisResponseSchema = z.object({
  analysis_checksum: z.string(),
  candidate_count: z.number(),
  candidates: z.array(templateImportFieldCandidateSchema),
  schema: templateSchemaResponseSchema,
})

export const templateImportParagraphItemSchema = z.object({
  path: z.string(),
  source_type: z.string(),
  text: z.string(),
  char_count: z.number(),
  table_header_label: z.string().nullable().optional(),
})

export const templateImportInspectionResponseSchema = z.object({
  inspection_checksum: z.string(),
  paragraph_count: z.number(),
  paragraphs: z.array(templateImportParagraphItemSchema),
})

export const templateImportBindingSchema = z.object({
  id: z.string(),
  candidate_id: z.string(),
  binding_key: z.string(),
  label: z.string(),
  raw_fragment: z.string(),
  paragraph_path: z.string(),
  source_type: z.string(),
  detection_kind: z.string(),
  confidence: z.number(),
  preview_text: z.string(),
  value_type: z.string(),
  component_type: z.string(),
  required: z.boolean(),
  sample_value: z.string().nullable().optional(),
  fragment_start: z.number(),
  fragment_end: z.number(),
})

export const templateImportConfirmationResponseSchema = z.object({
  organization_id: uuid(),
  template_id: uuid(),
  template_version_id: uuid(),
  render_strategy: z.string(),
  analysis: templateImportAnalysisResponseSchema,
  schema: templateSchemaResponseSchema,
  confirmed_binding_count: z.number(),
  bindings: z.array(templateImportBindingSchema),
})

export const templateTemplateizationConfirmationResponseSchema = z.object({
  organization_id: uuid(),
  template_id: uuid(),
  template_version_id: uuid(),
  render_strategy: z.string(),
  inspection: templateImportInspectionResponseSchema,
  schema: templateSchemaResponseSchema,
  confirmed_binding_count: z.number(),
  bindings: z.array(templateImportBindingSchema),
})

export const constructorSchemaResponseSchema = z.object({
  descriptor: z.object({
    schema_version: z.string(),
    default_formatting: z.object({
      page: z.record(z.string(), z.union([z.string(), z.number(), z.boolean()])),
      typography: z.record(z.string(), z.union([z.string(), z.number(), z.boolean()])),
      allow_orphan_headings: z.boolean(),
      repeat_table_header_on_each_page: z.boolean(),
      force_table_borders: z.boolean(),
      signatures_align_right: z.boolean(),
    }),
    supported_blocks: z.array(z.string()),
  }),
})

export const documentJobResponseSchema = z.object({
  task_id: uuid(),
  organization_id: uuid(),
  status: z.string(),
  template_id: uuid().nullable().optional(),
  template_version_id: uuid().nullable().optional(),
  requested_by_user_id: uuid().nullable().optional(),
  from_cache: z.boolean(),
})

export const documentArtifactSchema = z.object({
  id: uuid(),
  kind: z.string(),
  file_name: z.string(),
  content_type: z.string(),
  size_bytes: z.number().nullable().optional(),
  download_url: z.string().nullable().optional(),
})

export const documentJobStatusResponseSchema = z.object({
  task_id: uuid(),
  organization_id: uuid(),
  status: z.string(),
  template_id: uuid(),
  template_version_id: uuid(),
  requested_by_user_id: uuid().nullable().optional(),
  from_cache: z.boolean(),
  error_message: z.string().nullable().optional(),
  created_at: z.string(),
  started_at: z.string().nullable().optional(),
  completed_at: z.string().nullable().optional(),
  artifacts: z.array(documentArtifactSchema),
})

export const documentArtifactAccessResponseSchema = z.object({
  organization_id: uuid(),
  task_id: uuid(),
  artifact: documentArtifactSchema,
})

export const documentVerificationResponseSchema = z.object({
  organization_id: uuid(),
  matched: z.boolean(),
  provided_hash: z.string(),
  authenticity_algorithm: z.string(),
  matched_artifact_count: z.number(),
  artifact: z
    .object({
      artifact_id: uuid(),
      task_id: uuid().nullable().optional(),
      kind: z.string(),
      file_name: z.string(),
      content_type: z.string(),
      size_bytes: z.number().nullable().optional(),
      issued_at: z.string(),
      authenticity_hash: z.string(),
      authenticity_algorithm: z.string(),
      verification_code: z.string(),
    })
    .nullable()
    .optional(),
})

export const billingPlanListResponseSchema = z.object({
  items: z.array(billingPlanSchema),
})

export const billingInvoiceResponseSchema = z.object({
  id: uuid(),
  organization_id: uuid(),
  organization_plan_id: uuid(),
  plan_definition_id: uuid(),
  plan_code: z.string(),
  currency_code: z.string(),
  status: z.string(),
  period_start: z.string(),
  period_end: z.string(),
  subtotal_cents: z.number(),
  generation_count: z.number(),
  template_count: z.number(),
  user_count: z.number(),
  storage_bytes: z.number(),
  premium_feature_usage: z.record(z.string(), z.unknown()),
  line_items: z.array(z.record(z.string(), z.unknown())),
  issued_at: z.string(),
  due_at: z.string(),
  paid_at: z.string().nullable().optional(),
  created_at: z.string(),
})

export const billingInvoiceListResponseSchema = z.object({
  items: z.array(billingInvoiceResponseSchema),
})

export const billingCycleRunResponseSchema = z.object({
  finalized_invoice_count: z.number(),
  renewed_subscription_count: z.number(),
  billed_organization_ids: z.array(uuid()),
})

export const apiKeySecretResponseSchema = z.object({
  api_key: z.string(),
  metadata: apiKeyMetadataSchema,
})

export const apiKeyUsageResponseSchema = z.object({
  id: uuid(),
  api_key_id: uuid(),
  organization_id: uuid(),
  scope: z.string().nullable().optional(),
  method: z.string(),
  path: z.string(),
  status_code: z.number(),
  request_id: z.string().nullable().optional(),
  correlation_id: z.string().nullable().optional(),
  rate_limited: z.boolean(),
  created_at: z.string(),
})

export const apiKeyUsageListResponseSchema = z.object({
  items: z.array(apiKeyUsageResponseSchema),
})

export const failedJobDiagnosticSchema = z.object({
  task_id: uuid(),
  organization_id: uuid(),
  template_id: uuid(),
  template_version_id: uuid(),
  requested_by_user_id: uuid().nullable().optional(),
  status: z.string(),
  error_message: z.string().nullable().optional(),
  created_at: z.string(),
  completed_at: z.string().nullable().optional(),
})

export const failedJobsListResponseSchema = z.object({
  items: z.array(failedJobDiagnosticSchema),
})

export const replayJobResponseSchema = z.object({
  replayed_from_task_id: uuid(),
  job: documentJobResponseSchema,
})

export const cacheInvalidationResponseSchema = z.object({
  organization_id: uuid(),
  task_id: uuid(),
  cache_key: z.string().nullable().optional(),
  invalidated_artifact_count: z.number(),
  invalidated_at: z.string(),
})

export const userDisableResponseSchema = z.object({
  id: uuid(),
  organization_id: uuid(),
  email: z.string(),
  full_name: z.string().nullable().optional(),
  is_active: z.boolean(),
  revoked_session_count: z.number(),
})

export const apiKeyDisableResponseSchema = z.object({
  id: uuid(),
  organization_id: uuid(),
  name: z.string(),
  status: z.string(),
  disabled_at: z.string(),
})

export const maintenanceCleanupResponseSchema = z.object({
  expired_artifacts_deleted: z.number(),
  failed_jobs_deleted: z.number(),
  audit_logs_deleted: z.number(),
  temp_files_deleted: z.number(),
  storage_bytes_reclaimed: z.number(),
})

export type TemplateDetail = z.infer<typeof templateDetailSchema>
export type TemplateIngestionResponse = z.infer<typeof templateIngestionResponseSchema>
export type TemplateImportAnalysisResponse = z.infer<typeof templateImportAnalysisResponseSchema>
export type TemplateImportInspectionResponse = z.infer<typeof templateImportInspectionResponseSchema>
export type TemplateImportConfirmationResponse = z.infer<typeof templateImportConfirmationResponseSchema>
export type TemplateTemplateizationConfirmationResponse = z.infer<typeof templateTemplateizationConfirmationResponseSchema>
export type ConstructorSchemaResponse = z.infer<typeof constructorSchemaResponseSchema>
export type DocumentJobResponse = z.infer<typeof documentJobResponseSchema>
export type DocumentJobStatusResponse = z.infer<typeof documentJobStatusResponseSchema>
export type DocumentArtifactAccessResponse = z.infer<typeof documentArtifactAccessResponseSchema>
export type DocumentVerificationResponse = z.infer<typeof documentVerificationResponseSchema>
export type BillingPlanListResponse = z.infer<typeof billingPlanListResponseSchema>
export type BillingInvoiceListResponse = z.infer<typeof billingInvoiceListResponseSchema>
export type ApiKeySecretResponse = z.infer<typeof apiKeySecretResponseSchema>
export type ApiKeyUsageListResponse = z.infer<typeof apiKeyUsageListResponseSchema>
export type FailedJobsListResponse = z.infer<typeof failedJobsListResponseSchema>
export type ReplayJobResponse = z.infer<typeof replayJobResponseSchema>
export type CacheInvalidationResponse = z.infer<typeof cacheInvalidationResponseSchema>
export type UserDisableResponse = z.infer<typeof userDisableResponseSchema>
export type ApiKeyDisableResponse = z.infer<typeof apiKeyDisableResponseSchema>
export type MaintenanceCleanupResponse = z.infer<typeof maintenanceCleanupResponseSchema>
export type CacheStatsResponse = z.infer<typeof cacheStatsSchema>
export type WorkerStatusResponse = z.infer<typeof workerStatusSchema>
