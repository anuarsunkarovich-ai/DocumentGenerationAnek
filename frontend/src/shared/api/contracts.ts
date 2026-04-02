import { z } from 'zod'

const uuid = () => z.string().uuid()

export const organizationSummarySchema = z.object({
  id: uuid(),
  name: z.string(),
  code: z.string(),
})

export const membershipSchema = z.object({
  id: uuid(),
  organization_id: uuid(),
  role: z.string(),
  is_active: z.boolean(),
  is_default: z.boolean(),
  organization: organizationSummarySchema,
})

export const userSchema = z.object({
  id: uuid(),
  organization_id: uuid(),
  email: z.string().email(),
  full_name: z.string(),
  role: z.string(),
  is_active: z.boolean(),
  organization: organizationSummarySchema,
  memberships: z.array(membershipSchema),
})

export const loginPayloadSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
})

export const authTokenResponseSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  token_type: z.string(),
  access_token_expires_in: z.number(),
  refresh_token_expires_in: z.number(),
  user: userSchema,
})

export const templateVersionSummarySchema = z.object({
  id: uuid(),
  version: z.string(),
  is_current: z.boolean(),
  is_published: z.boolean(),
})

export const templateSchemaResponseSchema = z.object({
  variable_count: z.number(),
  variables: z.array(
    z.object({
      key: z.string(),
      label: z.string(),
      placeholder: z.string(),
      value_type: z.string(),
      component_type: z.string(),
      required: z.boolean(),
    }),
  ),
  components: z.array(
    z.object({
      id: z.string(),
      component: z.string(),
      binding: z.string(),
      label: z.string(),
      value_type: z.string(),
      required: z.boolean(),
    }),
  ),
})

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

export const templateSchema = z.object({
  id: uuid(),
  organization_id: uuid(),
  name: z.string(),
  code: z.string(),
  status: z.string(),
  description: z.string().nullable().optional(),
  current_version: templateVersionSummarySchema.nullable().optional(),
})

export const templateListResponseSchema = z.object({
  items: z.array(templateSchema),
})

export const billingPlanSchema = z.object({
  id: uuid(),
  code: z.string(),
  name: z.string(),
  billable_unit: z.string(),
  monthly_generation_cap: z.number(),
  max_templates: z.number(),
  max_users: z.number(),
  storage_quota_bytes: z.number(),
  monthly_price_cents: z.number(),
  currency_code: z.string(),
  audit_retention_days: z.number(),
  signature_support: z.boolean(),
  is_active: z.boolean(),
})

export const billingSnapshotSchema = z.object({
  subscription: z.object({
    organization_id: uuid(),
    status: z.string(),
    current_period_start: z.string(),
    current_period_end: z.string(),
    plan: billingPlanSchema,
    pending_plan: billingPlanSchema.nullable().optional(),
  }),
  usage_meter: z.object({
    period_start: z.string(),
    period_end: z.string(),
    generation_count: z.number(),
    storage_bytes: z.number(),
    template_count: z.number(),
    user_count: z.number(),
    premium_feature_usage: z.record(z.string(), z.number()).default({}),
  }),
})

export const apiKeyMetadataSchema = z.object({
  id: uuid(),
  organization_id: uuid(),
  name: z.string(),
  key_prefix: z.string(),
  scopes: z.array(z.string()),
  status: z.string(),
  rotated_at: z.string().datetime().nullable(),
  last_used_at: z.string().datetime().nullable(),
  revoked_at: z.string().datetime().nullable(),
  created_at: z.string().datetime(),
})

export const apiKeyListResponseSchema = z.object({
  items: z.array(apiKeyMetadataSchema),
})

export const auditEventSchema = z.object({
  id: uuid(),
  organization_id: uuid(),
  user_id: uuid().nullable().optional(),
  action: z.string(),
  entity_type: z.string(),
  entity_id: uuid().nullable().optional(),
  payload: z.record(z.string(), z.unknown()).default({}),
  created_at: z.string().datetime(),
})

export const auditEventListResponseSchema = z.object({
  items: z.array(auditEventSchema),
})

export const workerStatusSchema = z.object({
  organization_id: uuid(),
  queue_depth: z.number(),
  workers: z.array(
    z.object({
      name: z.string(),
      is_online: z.boolean(),
    }),
  ),
})

export const cacheStatsSchema = z.object({
  organization_id: uuid(),
  completed_jobs: z.number(),
  cached_jobs: z.number(),
  cached_artifacts: z.number(),
  cache_hit_ratio: z.number(),
})

export const jobQueueItemSchema = z.object({
  id: z.string(),
  recipient: z.string(),
  recipient_meta: z.string(),
  status: z.enum(['generated', 'downloaded', 'pending_audit', 'validation_failed']),
  document_name: z.string(),
})

export const approvalItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  reference: z.string(),
  kind: z.string(),
  status: z.string(),
  action_label: z.string(),
  secondary_action_label: z.string().optional(),
})

export const quickGenerationPayloadSchema = z.object({
  templateId: z.string().min(1),
  recipient: z.string().min(2),
  recipientRole: z.string().min(2),
  documentType: z.string().min(2),
})

export const systemPulseSchema = z.object({
  status: z.enum(['operational', 'degraded']),
  mode: z.enum(['mock', 'live']),
  label: z.string(),
})

export type OrganizationSummary = z.infer<typeof organizationSummarySchema>
export type Membership = z.infer<typeof membershipSchema>
export type User = z.infer<typeof userSchema>
export type AuthTokenResponse = z.infer<typeof authTokenResponseSchema>
export type LoginPayload = z.infer<typeof loginPayloadSchema>
export type Template = z.infer<typeof templateSchema>
export type TemplateListResponse = z.infer<typeof templateListResponseSchema>
export type BillingSnapshot = z.infer<typeof billingSnapshotSchema>
export type ApiKeyMetadata = z.infer<typeof apiKeyMetadataSchema>
export type AuditEvent = z.infer<typeof auditEventSchema>
export type WorkerStatus = z.infer<typeof workerStatusSchema>
export type CacheStats = z.infer<typeof cacheStatsSchema>
export type JobQueueItem = z.infer<typeof jobQueueItemSchema>
export type ApprovalItem = z.infer<typeof approvalItemSchema>
export type QuickGenerationPayload = z.infer<typeof quickGenerationPayloadSchema>
export type SystemPulse = z.infer<typeof systemPulseSchema>
