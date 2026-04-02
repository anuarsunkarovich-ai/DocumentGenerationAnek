import { backendApi } from '@shared/api/backend-api'
import { demoApi } from '@shared/api/demo-api'
import { env } from '@shared/config/env'

export const runtimeApi = {
  getSystemPulse: () =>
    env.apiMode === 'live'
      ? Promise.resolve({
          status: 'operational' as const,
          mode: 'live' as const,
          label: `Connected to ${env.apiBaseUrl}`,
        })
      : demoApi.getSystemPulse(),

  getDemoSession: demoApi.getDemoSession,
  login: (payload: unknown) =>
    env.apiMode === 'live' ? backendApi.login(payload) : demoApi.login(),
  getCurrentUser: () =>
    env.apiMode === 'live' ? backendApi.getCurrentUser() : demoApi.getCurrentUser(),
  listTemplates: (organizationId: string) =>
    env.apiMode === 'live'
      ? backendApi.listTemplates(organizationId)
      : demoApi.listTemplates(),
  getTemplateDetail: (organizationId: string, templateId: string) =>
    env.apiMode === 'live'
      ? backendApi.getTemplateDetail(organizationId, templateId)
      : demoApi.getTemplateDetail(),
  uploadTemplate: (formData: FormData) =>
    env.apiMode === 'live' ? backendApi.uploadTemplate(formData) : demoApi.uploadTemplate(),
  registerTemplate: (payload: Record<string, unknown>) =>
    env.apiMode === 'live'
      ? backendApi.registerTemplate(payload)
      : demoApi.registerTemplate(),
  extractSchema: (file: File) =>
    env.apiMode === 'live' ? backendApi.extractSchema(file) : demoApi.extractSchema(),
  analyzeImportUpload: (file: File) =>
    env.apiMode === 'live'
      ? backendApi.analyzeImportUpload(file)
      : demoApi.analyzeImportUpload(),
  inspectImportUpload: (file: File) =>
    env.apiMode === 'live'
      ? backendApi.inspectImportUpload(file)
      : demoApi.inspectImportUpload(),
  analyzeStoredTemplate: (templateId: string, organizationId: string) =>
    env.apiMode === 'live'
      ? backendApi.analyzeStoredTemplate(templateId, organizationId)
      : demoApi.analyzeStoredTemplate(),
  inspectStoredTemplate: (templateId: string, organizationId: string) =>
    env.apiMode === 'live'
      ? backendApi.inspectStoredTemplate(templateId, organizationId)
      : demoApi.inspectStoredTemplate(),
  confirmStoredTemplate: (templateId: string, payload: Record<string, unknown>) =>
    env.apiMode === 'live'
      ? backendApi.confirmStoredTemplate(templateId, payload)
      : demoApi.confirmStoredTemplate(),
  templateizeStoredTemplate: (templateId: string, payload: Record<string, unknown>) =>
    env.apiMode === 'live'
      ? backendApi.templateizeStoredTemplate(templateId, payload)
      : demoApi.templateizeStoredTemplate(),
  extractStoredTemplateSchema: (templateId: string, organizationId: string) =>
    env.apiMode === 'live'
      ? backendApi.extractStoredTemplateSchema(templateId, organizationId)
      : demoApi.extractStoredTemplateSchema(),
  getConstructorSchema: () =>
    env.apiMode === 'live'
      ? backendApi.getConstructorSchema()
      : demoApi.getConstructorSchema(),
  generateDocument: (payload: Record<string, unknown>) =>
    env.apiMode === 'live'
      ? backendApi.generateDocument(payload)
      : demoApi.generateDocument(),
  generateImportedDocument: (payload: Record<string, unknown>) =>
    env.apiMode === 'live'
      ? backendApi.generateImportedDocument(payload)
      : demoApi.generateImportedDocument(),
  getJobStatus: (taskId: string, organizationId: string) =>
    env.apiMode === 'live'
      ? backendApi.getJobStatus(taskId, organizationId)
      : demoApi.getJobStatus(taskId),
  getJobDownload: (taskId: string, organizationId: string) =>
    env.apiMode === 'live'
      ? backendApi.getJobDownload(taskId, organizationId)
      : demoApi.getJobDownload(taskId),
  getJobPreview: (taskId: string, organizationId: string) =>
    env.apiMode === 'live'
      ? backendApi.getJobPreview(taskId, organizationId)
      : demoApi.getJobPreview(taskId),
  verifyDocument: (organizationId: string, file?: File, authenticityHash?: string) =>
    env.apiMode === 'live'
      ? backendApi.verifyDocument(organizationId, file, authenticityHash)
      : demoApi.verifyDocument(organizationId, file, authenticityHash),
  listBillingPlans: (organizationId: string) =>
    env.apiMode === 'live'
      ? backendApi.listBillingPlans(organizationId)
      : demoApi.listBillingPlans(),
  getBillingSnapshot: (organizationId: string) =>
    env.apiMode === 'live'
      ? backendApi.getBillingSnapshot(organizationId)
      : demoApi.getBillingSnapshot(),
  listBillingInvoices: (organizationId: string, limit?: number) =>
    env.apiMode === 'live'
      ? backendApi.listBillingInvoices(organizationId, limit)
      : demoApi.listBillingInvoices(),
  changeSubscription: (payload: Record<string, unknown>) =>
    env.apiMode === 'live'
      ? backendApi.changeSubscription(payload)
      : demoApi.changeSubscription(payload),
  runBillingCycle: (payload: Record<string, unknown>) =>
    env.apiMode === 'live'
      ? backendApi.runBillingCycle(payload)
      : demoApi.runBillingCycle(),
  listApiKeys: (organizationId: string) =>
    env.apiMode === 'live'
      ? backendApi.listApiKeys(organizationId)
      : demoApi.listApiKeys(),
  createApiKey: (payload: Record<string, unknown>) =>
    env.apiMode === 'live'
      ? backendApi.createApiKey(payload)
      : demoApi.createApiKey(payload),
  rotateApiKey: (apiKeyId: string, organizationId: string) =>
    env.apiMode === 'live'
      ? backendApi.rotateApiKey(apiKeyId, organizationId)
      : demoApi.rotateApiKey(apiKeyId),
  revokeApiKey: (apiKeyId: string, organizationId: string) =>
    env.apiMode === 'live'
      ? backendApi.revokeApiKey(apiKeyId, organizationId)
      : demoApi.revokeApiKey(apiKeyId),
  listApiKeyUsage: (organizationId: string, limit?: number) =>
    env.apiMode === 'live'
      ? backendApi.listApiKeyUsage(organizationId, limit)
      : demoApi.listApiKeyUsage(),
  listAuditEvents: (organizationId: string) =>
    env.apiMode === 'live'
      ? backendApi.listAuditEvents(organizationId)
      : demoApi.listAuditEvents(),
  getWorkerStatus: (organizationId: string) =>
    env.apiMode === 'live'
      ? backendApi.getWorkerStatus(organizationId)
      : demoApi.getWorkerStatus(),
  getCacheStats: (organizationId: string) =>
    env.apiMode === 'live'
      ? backendApi.getCacheStats(organizationId)
      : demoApi.getCacheStats(),
  listFailedJobs: (organizationId: string, limit?: number) =>
    env.apiMode === 'live'
      ? backendApi.listFailedJobs(organizationId, limit)
      : demoApi.listFailedJobs(),
  getAuditHistory: (
    organizationId: string,
    entityType: string,
    entityId: string,
    limit?: number,
  ) =>
    env.apiMode === 'live'
      ? backendApi.getAuditHistory(organizationId, entityType, entityId, limit)
      : demoApi.getAuditHistory(organizationId, entityType, entityId),
  replayJob: (jobId: string, organizationId: string) =>
    env.apiMode === 'live'
      ? backendApi.replayJob(jobId, organizationId)
      : demoApi.replayJob(jobId),
  invalidateJobCache: (jobId: string, organizationId: string) =>
    env.apiMode === 'live'
      ? backendApi.invalidateJobCache(jobId, organizationId)
      : demoApi.invalidateJobCache(jobId),
  disableUser: (userId: string, organizationId: string) =>
    env.apiMode === 'live'
      ? backendApi.disableUser(userId, organizationId)
      : demoApi.disableUser(userId),
  disableIncidentApiKey: (apiKeyId: string, organizationId: string) =>
    env.apiMode === 'live'
      ? backendApi.disableIncidentApiKey(apiKeyId, organizationId)
      : demoApi.disableIncidentApiKey(apiKeyId),
  runMaintenanceCleanup: (organizationId: string) =>
    env.apiMode === 'live'
      ? backendApi.runMaintenanceCleanup(organizationId)
      : demoApi.runMaintenanceCleanup(),
  listPublicTemplates: (apiKey: string) =>
    env.apiMode === 'live'
      ? backendApi.listPublicTemplates(apiKey)
      : demoApi.listPublicTemplates(),
  getPublicTemplate: (apiKey: string, templateId: string) =>
    env.apiMode === 'live'
      ? backendApi.getPublicTemplate(apiKey, templateId)
      : demoApi.getPublicTemplate(),
  getPublicConstructorSchema: (apiKey: string) =>
    env.apiMode === 'live'
      ? backendApi.getPublicConstructorSchema(apiKey)
      : demoApi.getPublicConstructorSchema(),
  generatePublicDocument: (apiKey: string, payload: Record<string, unknown>) =>
    env.apiMode === 'live'
      ? backendApi.generatePublicDocument(apiKey, payload)
      : demoApi.generatePublicDocument(apiKey, payload),
  getPublicJobStatus: (apiKey: string, taskId: string) =>
    env.apiMode === 'live'
      ? backendApi.getPublicJobStatus(apiKey, taskId)
      : demoApi.getPublicJobStatus(apiKey, taskId),
  getPublicJobDownload: (apiKey: string, taskId: string) =>
    env.apiMode === 'live'
      ? backendApi.getPublicJobDownload(apiKey, taskId)
      : demoApi.getPublicJobDownload(apiKey, taskId),
  getPublicJobPreview: (apiKey: string, taskId: string) =>
    env.apiMode === 'live'
      ? backendApi.getPublicJobPreview(apiKey, taskId)
      : demoApi.getPublicJobPreview(apiKey, taskId),
  verifyPublicDocument: (apiKey: string, file?: File, authenticityHash?: string) =>
    env.apiMode === 'live'
      ? backendApi.verifyPublicDocument(apiKey, file, authenticityHash)
      : demoApi.verifyPublicDocument(apiKey, file, authenticityHash),
  listPublicAuditEvents: (apiKey: string) =>
    env.apiMode === 'live'
      ? backendApi.listPublicAuditEvents(apiKey)
      : demoApi.listPublicAuditEvents(),
  listJobQueue: demoApi.listJobQueue,
  listApprovals: demoApi.listApprovals,
  createQuickGeneration: demoApi.createQuickGeneration,
}
