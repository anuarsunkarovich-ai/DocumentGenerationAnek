import {
  apiKeyListResponseSchema,
  auditEventListResponseSchema,
  authTokenResponseSchema,
  billingSnapshotSchema,
  cacheStatsSchema,
  jobQueueItemSchema,
  quickGenerationPayloadSchema,
  systemPulseSchema,
  templateListResponseSchema,
  workerStatusSchema,
  type ApprovalItem,
  type AuditEvent,
  type AuthTokenResponse,
  type BillingSnapshot,
  type CacheStats,
  type JobQueueItem,
  type QuickGenerationPayload,
  type SystemPulse,
  type TemplateListResponse,
} from '@shared/api/contracts'
import {
  apiKeyDisableResponseSchema,
  apiKeySecretResponseSchema,
  apiKeyUsageListResponseSchema,
  billingCycleRunResponseSchema,
  billingInvoiceListResponseSchema,
  billingPlanListResponseSchema,
  cacheInvalidationResponseSchema,
  constructorSchemaResponseSchema,
  documentArtifactAccessResponseSchema,
  documentJobResponseSchema,
  documentJobStatusResponseSchema,
  documentVerificationResponseSchema,
  failedJobsListResponseSchema,
  maintenanceCleanupResponseSchema,
  replayJobResponseSchema,
  templateDetailSchema,
  templateImportAnalysisResponseSchema,
  templateImportConfirmationResponseSchema,
  templateImportInspectionResponseSchema,
  templateIngestionResponseSchema,
  templateSchemaExtractionResponseSchema,
  templateTemplateizationConfirmationResponseSchema,
  userDisableResponseSchema,
} from '@shared/api/extended-contracts'

const organizationId = 'd05af282-af5c-4df8-807f-c71110f90294'
const userId = 'b5ce8874-4bdb-4660-a673-fb254c9704f5'

const demoSession = authTokenResponseSchema.parse({
  access_token: 'demo-access-token',
  refresh_token: 'demo-refresh-token',
  token_type: 'bearer',
  access_token_expires_in: 900,
  refresh_token_expires_in: 2_592_000,
  user: {
    id: userId,
    organization_id: organizationId,
    email: 'operator@protocol.kz',
    full_name: 'Heinrich Schmidt',
    role: 'admin',
    is_active: true,
    organization: {
      id: organizationId,
      name: 'Astana Realty Group Ltd.',
      code: 'astana-realty-group',
    },
    memberships: [
      {
        id: '744c8e23-a625-408a-9cfb-edf6cbb36145',
        organization_id: organizationId,
        role: 'admin',
        is_active: true,
        is_default: true,
        organization: {
          id: organizationId,
          name: 'Astana Realty Group Ltd.',
          code: 'astana-realty-group',
        },
      },
      {
        id: '8532990f-1e38-4498-a2db-5b8175e554c0',
        organization_id: 'f82ab95e-4811-4ad1-b917-b7170aafef8b',
        role: 'admin',
        is_active: true,
        is_default: false,
        organization: {
          id: 'f82ab95e-4811-4ad1-b917-b7170aafef8b',
          name: 'Capital Legal Desk',
          code: 'capital-legal-desk',
        },
      },
    ],
  },
})

const templateList = templateListResponseSchema.parse({
  items: [
    {
      id: '2f5fd5ef-cf40-4101-bacf-30a0b507f0c4',
      organization_id: organizationId,
      name: 'Mutual Sales Agreement',
      code: 'mutual-sales-agreement',
      status: 'active',
      description: 'Operational property sale agreement for agency transactions.',
      current_version: {
        id: '6efb8a73-2b74-4126-b958-74a48d71f430',
        version: '4.22',
        is_current: true,
        is_published: true,
      },
    },
    {
      id: '0ea5674f-0719-4b7e-8125-0d8e70b96a91',
      organization_id: organizationId,
      name: 'Executive Employment Contract',
      code: 'executive-employment-contract',
      status: 'active',
      description: 'Onboarding and compliance contract for senior hires.',
      current_version: {
        id: '1f29d296-b37c-4f15-bacd-e852750d6b7f',
        version: '1.0',
        is_current: true,
        is_published: true,
      },
    },
    {
      id: '7e0f7292-7ecb-422f-a82b-2af365af70aa',
      organization_id: organizationId,
      name: 'Commercial Leasing Addendum',
      code: 'commercial-leasing-addendum',
      status: 'active',
      description: 'Regional leasing clauses for premium commercial property.',
      current_version: {
        id: 'feddb88c-6c7b-43e4-8c85-17f578c4eb17',
        version: '2023.10',
        is_current: true,
        is_published: true,
      },
    },
  ],
})

const billingSnapshot = billingSnapshotSchema.parse({
  subscription: {
    organization_id: organizationId,
    status: 'active',
    current_period_start: '2026-03-01',
    current_period_end: '2026-04-01',
    plan: {
      id: 'fef53fd2-1ef4-4901-b1fd-0e52d6a42adb',
      code: 'growth',
      name: 'Growth',
      billable_unit: 'per_organization',
      monthly_generation_cap: 1000,
      max_templates: 50,
      max_users: 15,
      storage_quota_bytes: 5_368_709_120,
      monthly_price_cents: 19900,
      currency_code: 'USD',
      audit_retention_days: 180,
      signature_support: true,
      is_active: true,
    },
    pending_plan: {
      id: '6b48cf59-c7d4-4bcc-aa0d-d664c444b30c',
      code: 'scale',
      name: 'Scale',
      billable_unit: 'per_organization',
      monthly_generation_cap: 5000,
      max_templates: 120,
      max_users: 40,
      storage_quota_bytes: 21_474_836_480,
      monthly_price_cents: 49900,
      currency_code: 'USD',
      audit_retention_days: 365,
      signature_support: true,
      is_active: true,
    },
  },
  usage_meter: {
    period_start: '2026-03-01',
    period_end: '2026-04-01',
    generation_count: 312,
    storage_bytes: 429_496_729,
    template_count: 18,
    user_count: 7,
    premium_feature_usage: {
      signature_requests: 42,
    },
  },
})

const apiKeys = apiKeyListResponseSchema.parse({
  items: [
    {
      id: 'bb3d2ab1-c779-4e9c-9739-abd4b29f2504',
      organization_id: organizationId,
      name: 'Agency Production',
      key_prefix: 'lgk_astana_prod',
      scopes: ['templates:read', 'documents:generate', 'documents:read'],
      status: 'active',
      rotated_at: null,
      last_used_at: '2026-04-02T05:58:00Z',
      revoked_at: null,
      created_at: '2026-02-10T08:30:00Z',
    },
    {
      id: 'fcf50899-d194-42f4-9c2f-c6b6bb8d5416',
      organization_id: organizationId,
      name: 'Notary Partner Sandbox',
      key_prefix: 'lgk_notary_sbx',
      scopes: ['templates:read', 'audit:read'],
      status: 'active',
      rotated_at: '2026-03-14T10:15:00Z',
      last_used_at: '2026-04-01T14:21:00Z',
      revoked_at: null,
      created_at: '2026-01-19T09:12:00Z',
    },
  ],
})

const apiKeyUsage = apiKeyUsageListResponseSchema.parse({
  items: [
    {
      id: crypto.randomUUID(),
      api_key_id: apiKeys.items[0].id,
      organization_id: organizationId,
      scope: 'documents:generate',
      method: 'POST',
      path: '/api/v1/public/documents/generate',
      status_code: 202,
      request_id: 'req_001',
      correlation_id: 'corr_001',
      rate_limited: false,
      created_at: nowIso(-10),
    },
    {
      id: crypto.randomUUID(),
      api_key_id: apiKeys.items[1].id,
      organization_id: organizationId,
      scope: 'audit:read',
      method: 'GET',
      path: '/api/v1/public/audit/events',
      status_code: 200,
      request_id: 'req_002',
      correlation_id: 'corr_002',
      rate_limited: false,
      created_at: nowIso(-120),
    },
  ],
})

const billingPlans = billingPlanListResponseSchema.parse({
  items: [
    billingSnapshot.subscription.plan,
    billingSnapshot.subscription.pending_plan!,
  ],
})

const billingInvoices = billingInvoiceListResponseSchema.parse({
  items: [
    {
      id: crypto.randomUUID(),
      organization_id: organizationId,
      organization_plan_id: crypto.randomUUID(),
      plan_definition_id: billingSnapshot.subscription.plan.id,
      plan_code: billingSnapshot.subscription.plan.code,
      currency_code: 'USD',
      status: 'finalized',
      period_start: '2026-02-01',
      period_end: '2026-03-01',
      subtotal_cents: 19900,
      generation_count: 288,
      template_count: 16,
      user_count: 7,
      storage_bytes: 400_000_000,
      premium_feature_usage: { signature_requests: 31 },
      line_items: [{ label: 'Growth Plan', subtotal_cents: 19900 }],
      issued_at: nowIso(-14_400),
      due_at: nowIso(-10_080),
      paid_at: null,
      created_at: nowIso(-14_400),
    },
  ],
})

const constructorSchema = constructorSchemaResponseSchema.parse({
  descriptor: {
    schema_version: '1.0',
    default_formatting: {
      page: {
        profile: 'gost_r_7_0_97_2016',
        paper_size: 'A4',
        orientation: 'portrait',
        margin_left_mm: 30,
        margin_right_mm: 10,
        margin_top_mm: 20,
        margin_bottom_mm: 20,
        header_distance_mm: 12.5,
        footer_distance_mm: 12.5,
      },
      typography: {
        font_family: 'Times New Roman',
        font_size_pt: 14,
        line_spacing: 1.5,
        first_line_indent_mm: 12.5,
        paragraph_spacing_before_pt: 0,
        paragraph_spacing_after_pt: 0,
        alignment: 'justify',
      },
      allow_orphan_headings: false,
      repeat_table_header_on_each_page: true,
      force_table_borders: true,
      signatures_align_right: true,
    },
    supported_blocks: ['text', 'table', 'image', 'header', 'signature', 'page_break', 'spacer'],
  },
})

const templateDetail = templateDetailSchema.parse({
  ...templateList.items[0],
  versions: [
    templateList.items[0].current_version,
    {
      id: crypto.randomUUID(),
      version: '4.10',
      is_current: false,
      is_published: true,
    },
  ],
  current_version_details: {
    id: templateList.items[0].current_version!.id,
    version: templateList.items[0].current_version!.version,
    is_current: true,
    is_published: true,
    original_filename: 'mutual-sales-agreement.docx',
    storage_key: 'templates/astana-realty-group/mutual-sales-agreement/4.22/template.docx',
    checksum: '7dfb8d04f2f3948931fef8b3b020e80b',
    notes: 'Primary sales template for high-volume property deals.',
    render_strategy: 'constructor',
    imported_binding_count: 0,
    schema: {
      variable_count: 3,
      variables: [
        {
          key: 'buyer_name',
          label: 'Buyer Name',
          placeholder: '{{buyer_name}}',
          value_type: 'string',
          component_type: 'text',
          required: true,
        },
        {
          key: 'seller_name',
          label: 'Seller Name',
          placeholder: '{{seller_name}}',
          value_type: 'string',
          component_type: 'text',
          required: true,
        },
        {
          key: 'property_address',
          label: 'Property Address',
          placeholder: '{{property_address}}',
          value_type: 'string',
          component_type: 'text',
          required: true,
        },
      ],
      components: [
        {
          id: 'buyer_name',
          component: 'text',
          binding: 'buyer_name',
          label: 'Buyer Name',
          value_type: 'string',
          required: true,
        },
      ],
    },
  },
})

const templateCurrentVersion = templateDetail.current_version_details!

const auditEvents = auditEventListResponseSchema.parse({
  items: [
    {
      id: '51b5e1e3-98d1-4cad-b4a0-42e53d0901b9',
      organization_id: organizationId,
      user_id: userId,
      action: 'template.promoted',
      entity_type: 'template_version',
      entity_id: '6efb8a73-2b74-4126-b958-74a48d71f430',
      payload: {
        template_name: 'Mutual Sales Agreement',
        environment: 'production',
      },
      created_at: '2026-04-02T05:22:00Z',
    },
    {
      id: '2f596d8a-c15d-42c8-a52b-6cd33c7c9a58',
      organization_id: organizationId,
      user_id: userId,
      action: 'document.generated',
      entity_type: 'job',
      entity_id: '6af40f39-4dc9-4480-aad4-46b531ef57b0',
      payload: {
        task_id: 'PRT-992-AK_V4',
        artifact_kind: 'pdf',
      },
      created_at: '2026-04-02T04:48:00Z',
    },
    {
      id: '497fc33c-78d3-46f8-8ed1-b0ccde3f53c4',
      organization_id: organizationId,
      user_id: userId,
      action: 'access.logged',
      entity_type: 'security',
      entity_id: null,
      payload: {
        ip_address: '92.44.11.2',
      },
      created_at: '2026-04-02T04:11:00Z',
    },
  ],
})

const workerStatus = workerStatusSchema.parse({
  organization_id: organizationId,
  queue_depth: 6,
  workers: [
    { name: 'worker-eu-central-1', is_online: true },
    { name: 'worker-astana-hotpath', is_online: true },
    { name: 'worker-batch-cold', is_online: true },
  ],
})

const cacheStats = cacheStatsSchema.parse({
  organization_id: organizationId,
  completed_jobs: 1284,
  cached_jobs: 318,
  cached_artifacts: 711,
  cache_hit_ratio: 0.248,
})

const prototypeApprovals: ApprovalItem[] = [
  {
    id: 'lease-addendum-12d',
    title: 'Lease Addendum #12-D',
    reference: 'Ref 242-99-C-2023',
    kind: 'Legal review required',
    status: 'signature',
    action_label: 'Execute Signature',
    secondary_action_label: 'Defer to Compliance',
  },
  {
    id: 'vendor-onboarding-v2',
    title: 'Vendor Onboarding v2',
    reference: 'Requested by M. Ivanova',
    kind: 'Peer approval queue',
    status: 'review',
    action_label: 'Review Packet',
    secondary_action_label: 'Assign Reviewer',
  },
]

let prototypeJobs: JobQueueItem[] = [
  {
    id: 'PRT-992-AK_V4',
    recipient: 'Alisher Kenesbayev',
    recipient_meta: 'Retail sector',
    status: 'generated',
    document_name: 'Sales agreement package',
  },
  {
    id: 'PRT-981-ZM_CORE',
    recipient: 'Zukhra Mussina',
    recipient_meta: 'Executive board',
    status: 'downloaded',
    document_name: 'Executive employment file',
  },
  {
    id: 'PRT-977-RL_EX',
    recipient: 'Astana Central Real Estate',
    recipient_meta: 'B2B holding',
    status: 'pending_audit',
    document_name: 'Commercial leasing addendum',
  },
  {
    id: 'PRT-940-EX_ERR',
    recipient: 'External Audit Office',
    recipient_meta: 'Compliance department',
    status: 'validation_failed',
    document_name: 'External validation memo',
  },
]

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

function nowIso(offsetMinutes = 0) {
  return new Date(Date.now() + offsetMinutes * 60_000).toISOString()
}

export const demoApi = {
  async getSystemPulse(): Promise<SystemPulse> {
    await wait(120)
    return systemPulseSchema.parse({
      status: 'operational',
      mode: 'mock',
      label: 'Prototype data with live-ready adapters',
    })
  },

  async getDemoSession(): Promise<AuthTokenResponse> {
    await wait(80)
    return demoSession
  },

  async login() {
    await wait(320)
    return demoSession
  },

  async getCurrentUser() {
    await wait(100)
    return demoSession.user
  },

  async listTemplates(): Promise<TemplateListResponse> {
    await wait(180)
    return templateList
  },

  async getTemplateDetail() {
    await wait(180)
    return templateDetail
  },

  async uploadTemplate() {
    await wait(250)
    return templateIngestionResponseSchema.parse({
      template: templateList.items[2],
      version: templateCurrentVersion,
    })
  },

  async registerTemplate() {
    await wait(220)
    return templateIngestionResponseSchema.parse({
      template: templateList.items[1],
      version: {
        ...templateCurrentVersion,
        id: crypto.randomUUID(),
        version: '1.1',
        original_filename: 'registered-contract.docx',
      },
    })
  },

  async extractSchema() {
    await wait(160)
    return templateCurrentVersion.schema
  },

  async analyzeImportUpload() {
    await wait(170)
    return templateImportAnalysisResponseSchema.parse({
      analysis_checksum: 'a'.repeat(64),
      candidate_count: 2,
      candidates: [
        {
          id: 'candidate-1',
          label: 'Tenant name',
          suggested_binding: 'tenant_name',
          raw_fragment: 'Tenant Name',
          paragraph_path: 'body/p/12',
          source_type: 'paragraph',
          detection_kind: 'placeholder',
          confidence: 0.92,
          preview_text: 'Tenant Name: ______',
          value_type: 'string',
          component_type: 'text',
          required: true,
          fragment_start: 0,
          fragment_end: 11,
        },
      ],
      schema: templateCurrentVersion.schema,
    })
  },

  async inspectImportUpload() {
    await wait(160)
    return templateImportInspectionResponseSchema.parse({
      inspection_checksum: 'b'.repeat(64),
      paragraph_count: 3,
      paragraphs: [
        {
          path: 'body/p/12',
          source_type: 'paragraph',
          text: 'Tenant Name: ______',
          char_count: 19,
          table_header_label: null,
        },
      ],
    })
  },

  async analyzeStoredTemplate() {
    return this.analyzeImportUpload()
  },

  async inspectStoredTemplate() {
    return this.inspectImportUpload()
  },

  async confirmStoredTemplate() {
    const analysis = await this.analyzeImportUpload()
    await wait(180)
    return templateImportConfirmationResponseSchema.parse({
      organization_id: organizationId,
      template_id: templateDetail.id,
      template_version_id: templateCurrentVersion.id,
      render_strategy: 'docx_import',
      analysis,
      schema: templateCurrentVersion.schema,
      confirmed_binding_count: 1,
      bindings: [
        {
          id: 'binding-1',
          candidate_id: 'candidate-1',
          binding_key: 'tenant_name',
          label: 'Tenant Name',
          raw_fragment: 'Tenant Name',
          paragraph_path: 'body/p/12',
          source_type: 'paragraph',
          detection_kind: 'placeholder',
          confidence: 0.92,
          preview_text: 'Tenant Name: ______',
          value_type: 'string',
          component_type: 'text',
          required: true,
          sample_value: 'Aisha K.',
          fragment_start: 0,
          fragment_end: 11,
        },
      ],
    })
  },

  async templateizeStoredTemplate() {
    const inspection = await this.inspectImportUpload()
    await wait(180)
    return templateTemplateizationConfirmationResponseSchema.parse({
      organization_id: organizationId,
      template_id: templateDetail.id,
      template_version_id: templateCurrentVersion.id,
      render_strategy: 'docx_import',
      inspection,
      schema: templateCurrentVersion.schema,
      confirmed_binding_count: 1,
      bindings: [
        {
          id: 'binding-1',
          candidate_id: 'manual-1',
          binding_key: 'tenant_name',
          label: 'Tenant Name',
          raw_fragment: 'Tenant Name',
          paragraph_path: 'body/p/12',
          source_type: 'paragraph',
          detection_kind: 'manual',
          confidence: 1,
          preview_text: 'Tenant Name: ______',
          value_type: 'string',
          component_type: 'text',
          required: true,
          sample_value: 'Aisha K.',
          fragment_start: 0,
          fragment_end: 11,
        },
      ],
    })
  },

  async extractStoredTemplateSchema() {
    await wait(140)
    return templateSchemaExtractionResponseSchema.parse({
      organization_id: organizationId,
      template_id: templateDetail.id,
      template_version_id: templateCurrentVersion.id,
      schema: templateCurrentVersion.schema,
    })
  },

  async getConstructorSchema() {
    await wait(100)
    return constructorSchema
  },

  async getBillingSnapshot(): Promise<BillingSnapshot> {
    await wait(150)
    return billingSnapshot
  },

  async listBillingPlans() {
    await wait(120)
    return billingPlans
  },

  async listBillingInvoices() {
    await wait(120)
    return billingInvoices
  },

  async changeSubscription(payload: { target_plan_code?: string }) {
    await wait(140)
    return billingSnapshotSchema.parse({
      ...billingSnapshot,
      subscription: {
        ...billingSnapshot.subscription,
        pending_plan:
          billingPlans.items.find((plan) => plan.code === payload.target_plan_code) ??
          billingSnapshot.subscription.pending_plan,
      },
    })
  },

  async runBillingCycle() {
    await wait(140)
    return billingCycleRunResponseSchema.parse({
      finalized_invoice_count: 1,
      renewed_subscription_count: 1,
      billed_organization_ids: [organizationId],
    })
  },

  async listApiKeys() {
    await wait(140)
    return apiKeys
  },

  async createApiKey(payload: { name?: string; scopes?: string[] }) {
    await wait(150)
    return apiKeySecretResponseSchema.parse({
      api_key: 'lgk_demo_plaintext_key_only_once',
      metadata: {
        id: crypto.randomUUID(),
        organization_id: organizationId,
        name: payload.name ?? 'New integration',
        key_prefix: 'lgk_new_demo',
        scopes: payload.scopes ?? ['templates:read'],
        status: 'active',
        rotated_at: null,
        last_used_at: null,
        revoked_at: null,
        created_at: nowIso(),
      },
    })
  },

  async rotateApiKey(apiKeyId: string) {
    const existing = apiKeys.items.find((item) => item.id === apiKeyId) ?? apiKeys.items[0]
    await wait(140)
    return apiKeySecretResponseSchema.parse({
      api_key: 'lgk_rotated_plaintext_key_only_once',
      metadata: {
        ...existing,
        rotated_at: nowIso(),
      },
    })
  },

  async revokeApiKey(apiKeyId: string) {
    const existing = apiKeys.items.find((item) => item.id === apiKeyId) ?? apiKeys.items[0]
    await wait(120)
    return {
      ...existing,
      status: 'revoked',
      revoked_at: nowIso(),
    }
  },

  async listApiKeyUsage() {
    await wait(120)
    return apiKeyUsage
  },

  async listAuditEvents(): Promise<{ items: AuditEvent[] }> {
    await wait(120)
    return auditEvents
  },

  async getWorkerStatus() {
    await wait(110)
    return workerStatus
  },

  async getCacheStats(): Promise<CacheStats> {
    await wait(110)
    return cacheStats
  },

  async listFailedJobs() {
    await wait(110)
    return failedJobsListResponseSchema.parse({
      items: [
        {
          task_id: crypto.randomUUID(),
          organization_id: organizationId,
          template_id: templateDetail.id,
          template_version_id: templateCurrentVersion.id,
          requested_by_user_id: userId,
          status: 'failed',
          error_message: 'Validation failed for property_address',
          created_at: nowIso(-240),
          completed_at: nowIso(-236),
        },
      ],
    })
  },

  async getAuditHistory(_organizationId: string, entityType: string, entityId: string) {
    await wait(120)
    return auditEventListResponseSchema.parse({
      items: auditEvents.items.map((event) => ({
        ...event,
        entity_type: entityType,
        entity_id: entityId,
      })),
    })
  },

  async generateDocument(_payload?: Record<string, unknown>) {
    void _payload
    await wait(150)
    return documentJobResponseSchema.parse({
      task_id: crypto.randomUUID(),
      organization_id: organizationId,
      status: 'queued',
      template_id: templateDetail.id,
      template_version_id: templateCurrentVersion.id,
      requested_by_user_id: userId,
      from_cache: false,
    })
  },

  async generateImportedDocument(_payload?: Record<string, unknown>) {
    void _payload
    return this.generateDocument()
  },

  async getJobStatus(taskId: string) {
    await wait(140)
    return documentJobStatusResponseSchema.parse({
      task_id: taskId,
      organization_id: organizationId,
      status: 'completed',
      template_id: templateDetail.id,
      template_version_id: templateCurrentVersion.id,
      requested_by_user_id: userId,
      from_cache: false,
      error_message: null,
      created_at: nowIso(-8),
      started_at: nowIso(-7),
      completed_at: nowIso(-4),
      artifacts: [
        {
          id: crypto.randomUUID(),
          kind: 'pdf',
          file_name: 'mutual-sales-agreement.pdf',
          content_type: 'application/pdf',
          size_bytes: 12034,
          download_url: 'https://example.com/demo.pdf',
        },
      ],
    })
  },

  async getJobDownload(taskId: string) {
    const status = await this.getJobStatus(taskId)
    return documentArtifactAccessResponseSchema.parse({
      organization_id: organizationId,
      task_id: status.task_id,
      artifact: status.artifacts[0],
    })
  },

  async getJobPreview(taskId: string) {
    return this.getJobDownload(taskId)
  },

  async verifyDocument(_organizationId: string, _file?: File, authenticityHash?: string) {
    await wait(140)
    return documentVerificationResponseSchema.parse({
      organization_id: organizationId,
      matched: true,
      provided_hash: authenticityHash ?? 'demo-sha256',
      authenticity_algorithm: 'sha256',
      matched_artifact_count: 1,
      artifact: {
        artifact_id: crypto.randomUUID(),
        task_id: crypto.randomUUID(),
        kind: 'pdf',
        file_name: 'verified-artifact.pdf',
        content_type: 'application/pdf',
        size_bytes: 12034,
        issued_at: nowIso(-200),
        authenticity_hash: authenticityHash ?? 'demo-sha256',
        authenticity_algorithm: 'sha256',
        verification_code: 'VER-ABCDEF12-1234ABCD5678',
      },
    })
  },

  async replayJob(taskId: string) {
    const job = await this.generateDocument()
    await wait(100)
    return replayJobResponseSchema.parse({
      replayed_from_task_id: taskId,
      job,
    })
  },

  async invalidateJobCache(taskId: string) {
    await wait(120)
    return cacheInvalidationResponseSchema.parse({
      organization_id: organizationId,
      task_id: taskId,
      cache_key: 'cache:demo:123',
      invalidated_artifact_count: 2,
      invalidated_at: nowIso(),
    })
  },

  async disableUser(userIdToDisable: string) {
    await wait(120)
    return userDisableResponseSchema.parse({
      id: userIdToDisable,
      organization_id: organizationId,
      email: 'disabled-user@protocol.kz',
      full_name: 'Disabled User',
      is_active: false,
      revoked_session_count: 3,
    })
  },

  async disableIncidentApiKey(apiKeyId: string) {
    const existing = apiKeys.items.find((item) => item.id === apiKeyId) ?? apiKeys.items[0]
    await wait(120)
    return apiKeyDisableResponseSchema.parse({
      id: existing.id,
      organization_id: organizationId,
      name: existing.name,
      status: 'disabled',
      disabled_at: nowIso(),
    })
  },

  async runMaintenanceCleanup() {
    await wait(130)
    return maintenanceCleanupResponseSchema.parse({
      expired_artifacts_deleted: 12,
      failed_jobs_deleted: 4,
      audit_logs_deleted: 0,
      temp_files_deleted: 31,
      storage_bytes_reclaimed: 4567890,
    })
  },

  async listPublicTemplates() {
    await wait(110)
    return templateList
  },

  async getPublicTemplate() {
    await wait(110)
    return templateDetail
  },

  async getPublicConstructorSchema() {
    return this.getConstructorSchema()
  },

  async generatePublicDocument(_apiKey: string, payload: Record<string, unknown>) {
    await wait(150)
    return this.generateDocument(payload)
  },

  async getPublicJobStatus(_apiKey: string, taskId: string) {
    return this.getJobStatus(taskId)
  },

  async getPublicJobDownload(_apiKey: string, taskId: string) {
    return this.getJobDownload(taskId)
  },

  async getPublicJobPreview(_apiKey: string, taskId: string) {
    return this.getJobPreview(taskId)
  },

  async verifyPublicDocument(_apiKey: string, file?: File, authenticityHash?: string) {
    return this.verifyDocument(organizationId, file, authenticityHash)
  },

  async listPublicAuditEvents() {
    await wait(110)
    return auditEvents
  },

  async listJobQueue(): Promise<{ items: JobQueueItem[] }> {
    await wait(120)
    return {
      items: prototypeJobs.map((job) => jobQueueItemSchema.parse(job)),
    }
  },

  async listApprovals(): Promise<{ items: ApprovalItem[] }> {
    await wait(90)
    return { items: prototypeApprovals }
  },

  async createQuickGeneration(payload: QuickGenerationPayload) {
    const parsed = quickGenerationPayloadSchema.parse(payload)

    await wait(260)

    const nextJob = jobQueueItemSchema.parse({
      id: `PRT-${Math.floor(Math.random() * 900 + 100)}-${parsed.documentType.slice(0, 2).toUpperCase()}_${Date.now().toString().slice(-2)}`,
      recipient: parsed.recipient,
      recipient_meta: parsed.recipientRole,
      status: 'generated',
      document_name: parsed.documentType,
    })

    prototypeJobs = [nextJob, ...prototypeJobs].slice(0, 5)
    auditEvents.items = [
      {
        id: crypto.randomUUID(),
        organization_id: organizationId,
        user_id: userId,
        action: 'document.generated',
        entity_type: 'job',
        entity_id: crypto.randomUUID(),
        payload: {
          recipient: parsed.recipient,
          template_id: parsed.templateId,
        },
        created_at: nowIso(),
      },
      ...auditEvents.items,
    ].slice(0, 5)

    return nextJob
  },
}
