import {
  apiKeyMetadataSchema,
  apiKeyListResponseSchema,
  auditEventListResponseSchema,
  authTokenResponseSchema,
  billingSnapshotSchema,
  cacheStatsSchema,
  loginPayloadSchema,
  templateSchemaResponseSchema,
  templateListResponseSchema,
  userSchema,
  workerStatusSchema,
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
import { httpClient } from '@shared/api/http-client'

export const backendApi = {
  login(credentials: unknown) {
    const payload = loginPayloadSchema.parse(credentials)
    return httpClient.post('/auth/login', payload, authTokenResponseSchema)
  },

  getCurrentUser() {
    return httpClient.get('/auth/me', userSchema)
  },

  listTemplates(organizationId: string) {
    return httpClient.get(
      `/templates?organization_id=${encodeURIComponent(organizationId)}`,
      templateListResponseSchema,
    )
  },

  getTemplateDetail(organizationId: string, templateId: string) {
    return httpClient.get(
      `/templates/${templateId}?organization_id=${encodeURIComponent(organizationId)}`,
      templateDetailSchema,
    )
  },

  uploadTemplate(formData: FormData) {
    return httpClient.post('/templates/upload', formData, templateIngestionResponseSchema)
  },

  registerTemplate(payload: Record<string, unknown>) {
    return httpClient.post('/templates/register', payload, templateIngestionResponseSchema)
  },

  extractSchema(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return httpClient.post('/templates/extract-schema', formData, templateSchemaResponseSchema)
  },

  analyzeImportUpload(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return httpClient.post('/templates/import/analyze', formData, templateImportAnalysisResponseSchema)
  },

  inspectImportUpload(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return httpClient.post('/templates/import/inspect', formData, templateImportInspectionResponseSchema)
  },

  analyzeStoredTemplate(templateId: string, organizationId: string) {
    return httpClient.post(
      `/templates/${templateId}/import/analyze`,
      { organization_id: organizationId },
      templateImportAnalysisResponseSchema,
    )
  },

  inspectStoredTemplate(templateId: string, organizationId: string) {
    return httpClient.post(
      `/templates/${templateId}/import/inspect`,
      { organization_id: organizationId },
      templateImportInspectionResponseSchema,
    )
  },

  confirmStoredTemplate(templateId: string, payload: Record<string, unknown>) {
    return httpClient.post(
      `/templates/${templateId}/import/confirm`,
      payload,
      templateImportConfirmationResponseSchema,
    )
  },

  templateizeStoredTemplate(templateId: string, payload: Record<string, unknown>) {
    return httpClient.post(
      `/templates/${templateId}/import/templateize`,
      payload,
      templateTemplateizationConfirmationResponseSchema,
    )
  },

  extractStoredTemplateSchema(templateId: string, organizationId: string) {
    return httpClient.post(
      `/templates/${templateId}/extract-schema?organization_id=${encodeURIComponent(organizationId)}`,
      undefined,
      templateSchemaExtractionResponseSchema,
    )
  },

  getConstructorSchema() {
    return httpClient.get('/documents/constructor-schema', constructorSchemaResponseSchema)
  },

  generateDocument(payload: Record<string, unknown>) {
    return httpClient.post('/documents/generate', payload, documentJobResponseSchema)
  },

  generateImportedDocument(payload: Record<string, unknown>) {
    return httpClient.post('/documents/generate-imported', payload, documentJobResponseSchema)
  },

  getJobStatus(taskId: string, organizationId: string) {
    return httpClient.get(
      `/documents/jobs/${taskId}?organization_id=${encodeURIComponent(organizationId)}`,
      documentJobStatusResponseSchema,
    )
  },

  getJobDownload(taskId: string, organizationId: string) {
    return httpClient.get(
      `/documents/jobs/${taskId}/download?organization_id=${encodeURIComponent(organizationId)}`,
      documentArtifactAccessResponseSchema,
    )
  },

  getJobPreview(taskId: string, organizationId: string) {
    return httpClient.get(
      `/documents/jobs/${taskId}/preview?organization_id=${encodeURIComponent(organizationId)}`,
      documentArtifactAccessResponseSchema,
    )
  },

  verifyDocument(organizationId: string, file?: File, authenticityHash?: string) {
    const formData = new FormData()
    formData.append('organization_id', organizationId)
    if (file) {
      formData.append('file', file)
    }
    if (authenticityHash) {
      formData.append('authenticity_hash', authenticityHash)
    }
    return httpClient.post('/documents/verify', formData, documentVerificationResponseSchema)
  },

  listBillingPlans(organizationId: string) {
    return httpClient.get(
      `/admin/billing/plans?organization_id=${encodeURIComponent(organizationId)}`,
      billingPlanListResponseSchema,
    )
  },

  getBillingSnapshot(organizationId: string) {
    return httpClient.get(
      `/admin/billing/snapshot?organization_id=${encodeURIComponent(organizationId)}`,
      billingSnapshotSchema,
    )
  },

  listBillingInvoices(organizationId: string, limit = 10) {
    return httpClient.get(
      `/admin/billing/invoices?organization_id=${encodeURIComponent(organizationId)}&limit=${limit}`,
      billingInvoiceListResponseSchema,
    )
  },

  changeSubscription(payload: Record<string, unknown>) {
    return httpClient.post('/admin/billing/subscription/change', payload, billingSnapshotSchema)
  },

  runBillingCycle(payload: Record<string, unknown>) {
    return httpClient.post('/admin/billing/cycle/run', payload, billingCycleRunResponseSchema)
  },

  listApiKeys(organizationId: string) {
    return httpClient.get(
      `/admin/api-keys?organization_id=${encodeURIComponent(organizationId)}`,
      apiKeyListResponseSchema,
    )
  },

  createApiKey(payload: Record<string, unknown>) {
    return httpClient.post('/admin/api-keys', payload, apiKeySecretResponseSchema)
  },

  rotateApiKey(apiKeyId: string, organizationId: string) {
    return httpClient.post(
      `/admin/api-keys/${apiKeyId}/rotate?organization_id=${encodeURIComponent(organizationId)}`,
      undefined,
      apiKeySecretResponseSchema,
    )
  },

  revokeApiKey(apiKeyId: string, organizationId: string) {
    return httpClient.post(
      `/admin/api-keys/${apiKeyId}/revoke?organization_id=${encodeURIComponent(organizationId)}`,
      undefined,
      apiKeyMetadataSchema,
    )
  },

  listApiKeyUsage(organizationId: string, limit = 25) {
    return httpClient.get(
      `/admin/api-keys/usage?organization_id=${encodeURIComponent(organizationId)}&limit=${limit}`,
      apiKeyUsageListResponseSchema,
    )
  },

  listAuditEvents(organizationId: string) {
    return httpClient.get(
      `/admin/diagnostics/audit-events?organization_id=${encodeURIComponent(organizationId)}&limit=5`,
      auditEventListResponseSchema,
    )
  },

  getWorkerStatus(organizationId: string) {
    return httpClient.get(
      `/admin/diagnostics/worker-status?organization_id=${encodeURIComponent(organizationId)}`,
      workerStatusSchema,
    )
  },

  getCacheStats(organizationId: string) {
    return httpClient.get(
      `/admin/diagnostics/cache-stats?organization_id=${encodeURIComponent(organizationId)}`,
      cacheStatsSchema,
    )
  },

  listFailedJobs(organizationId: string, limit = 25) {
    return httpClient.get(
      `/admin/diagnostics/failed-jobs?organization_id=${encodeURIComponent(organizationId)}&limit=${limit}`,
      failedJobsListResponseSchema,
    )
  },

  getAuditHistory(organizationId: string, entityType: string, entityId: string, limit = 50) {
    return httpClient.get(
      `/admin/support/audit-history?organization_id=${encodeURIComponent(organizationId)}&entity_type=${encodeURIComponent(entityType)}&entity_id=${encodeURIComponent(entityId)}&limit=${limit}`,
      auditEventListResponseSchema,
    )
  },

  replayJob(jobId: string, organizationId: string) {
    return httpClient.post(
      `/admin/support/jobs/${jobId}/replay?organization_id=${encodeURIComponent(organizationId)}`,
      undefined,
      replayJobResponseSchema,
    )
  },

  invalidateJobCache(jobId: string, organizationId: string) {
    return httpClient.post(
      `/admin/support/jobs/${jobId}/invalidate-cache?organization_id=${encodeURIComponent(organizationId)}`,
      undefined,
      cacheInvalidationResponseSchema,
    )
  },

  disableUser(userId: string, organizationId: string) {
    return httpClient.post(
      `/admin/support/users/${userId}/disable?organization_id=${encodeURIComponent(organizationId)}`,
      undefined,
      userDisableResponseSchema,
    )
  },

  disableIncidentApiKey(apiKeyId: string, organizationId: string) {
    return httpClient.post(
      `/admin/support/api-keys/${apiKeyId}/disable?organization_id=${encodeURIComponent(organizationId)}`,
      undefined,
      apiKeyDisableResponseSchema,
    )
  },

  runMaintenanceCleanup(organizationId: string) {
    return httpClient.post(
      `/admin/support/maintenance/cleanup?organization_id=${encodeURIComponent(organizationId)}`,
      undefined,
      maintenanceCleanupResponseSchema,
    )
  },

  listPublicTemplates(apiKey: string) {
    return httpClient.request(
      '/public/templates',
      {
        method: 'GET',
        auth: false,
        headers: {
          'X-API-Key': apiKey,
        },
      },
      templateListResponseSchema,
    )
  },

  getPublicTemplate(apiKey: string, templateId: string) {
    return httpClient.request(
      `/public/templates/${templateId}`,
      {
        method: 'GET',
        auth: false,
        headers: {
          'X-API-Key': apiKey,
        },
      },
      templateDetailSchema,
    )
  },

  getPublicConstructorSchema(apiKey: string) {
    return httpClient.request(
      '/public/documents/constructor-schema',
      {
        method: 'GET',
        auth: false,
        headers: {
          'X-API-Key': apiKey,
        },
      },
      constructorSchemaResponseSchema,
    )
  },

  generatePublicDocument(apiKey: string, payload: Record<string, unknown>) {
    return httpClient.request(
      '/public/documents/generate',
      {
        method: 'POST',
        auth: false,
        headers: {
          'X-API-Key': apiKey,
        },
        body: payload,
      },
      documentJobResponseSchema,
    )
  },

  getPublicJobStatus(apiKey: string, taskId: string) {
    return httpClient.request(
      `/public/documents/jobs/${taskId}`,
      {
        method: 'GET',
        auth: false,
        headers: {
          'X-API-Key': apiKey,
        },
      },
      documentJobStatusResponseSchema,
    )
  },

  getPublicJobDownload(apiKey: string, taskId: string) {
    return httpClient.request(
      `/public/documents/jobs/${taskId}/download`,
      {
        method: 'GET',
        auth: false,
        headers: {
          'X-API-Key': apiKey,
        },
      },
      documentArtifactAccessResponseSchema,
    )
  },

  getPublicJobPreview(apiKey: string, taskId: string) {
    return httpClient.request(
      `/public/documents/jobs/${taskId}/preview`,
      {
        method: 'GET',
        auth: false,
        headers: {
          'X-API-Key': apiKey,
        },
      },
      documentArtifactAccessResponseSchema,
    )
  },

  verifyPublicDocument(apiKey: string, file?: File, authenticityHash?: string) {
    const formData = new FormData()

    if (file) {
      formData.append('file', file)
    }
    if (authenticityHash) {
      formData.append('authenticity_hash', authenticityHash)
    }

    return httpClient.request(
      '/public/documents/verify',
      {
        method: 'POST',
        auth: false,
        headers: {
          'X-API-Key': apiKey,
        },
        body: formData,
      },
      documentVerificationResponseSchema,
    )
  },

  listPublicAuditEvents(apiKey: string) {
    return httpClient.request(
      '/public/audit/events',
      {
        method: 'GET',
        auth: false,
        headers: {
          'X-API-Key': apiKey,
        },
      },
      auditEventListResponseSchema,
    )
  },
}
