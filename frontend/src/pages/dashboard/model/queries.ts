import { useQuery } from '@tanstack/react-query'

import { runtimeApi } from '@shared/api/runtime-api'

export const dashboardQueryKeys = {
  templates: (organizationId: string | null) => ['dashboard', 'templates', organizationId] as const,
  billing: (organizationId: string | null) => ['dashboard', 'billing', organizationId] as const,
  apiKeys: (organizationId: string | null) => ['dashboard', 'api-keys', organizationId] as const,
  audit: (organizationId: string | null) => ['dashboard', 'audit', organizationId] as const,
  worker: (organizationId: string | null) => ['dashboard', 'worker-status', organizationId] as const,
  cache: (organizationId: string | null) => ['dashboard', 'cache-stats', organizationId] as const,
  jobQueue: (organizationId: string | null) => ['dashboard', 'job-queue', organizationId] as const,
  approvals: (organizationId: string | null) => ['dashboard', 'approvals', organizationId] as const,
} as const

export function useTemplatesQuery(organizationId: string | null) {
  return useQuery({
    queryKey: dashboardQueryKeys.templates(organizationId),
    queryFn: () => runtimeApi.listTemplates(organizationId ?? ''),
    enabled: Boolean(organizationId),
  })
}

export function useBillingQuery(organizationId: string | null) {
  return useQuery({
    queryKey: dashboardQueryKeys.billing(organizationId),
    queryFn: () => runtimeApi.getBillingSnapshot(organizationId ?? ''),
    enabled: Boolean(organizationId),
  })
}

export function useApiKeysQuery(organizationId: string | null) {
  return useQuery({
    queryKey: dashboardQueryKeys.apiKeys(organizationId),
    queryFn: () => runtimeApi.listApiKeys(organizationId ?? ''),
    enabled: Boolean(organizationId),
  })
}

export function useAuditQuery(organizationId: string | null) {
  return useQuery({
    queryKey: dashboardQueryKeys.audit(organizationId),
    queryFn: () => runtimeApi.listAuditEvents(organizationId ?? ''),
    enabled: Boolean(organizationId),
  })
}

export function useWorkerQuery(organizationId: string | null) {
  return useQuery({
    queryKey: dashboardQueryKeys.worker(organizationId),
    queryFn: () => runtimeApi.getWorkerStatus(organizationId ?? ''),
    enabled: Boolean(organizationId),
  })
}

export function useCacheQuery(organizationId: string | null) {
  return useQuery({
    queryKey: dashboardQueryKeys.cache(organizationId),
    queryFn: () => runtimeApi.getCacheStats(organizationId ?? ''),
    enabled: Boolean(organizationId),
  })
}

export function useJobQueueQuery(organizationId: string | null) {
  return useQuery({
    queryKey: dashboardQueryKeys.jobQueue(organizationId),
    queryFn: () => runtimeApi.listJobQueue(),
    enabled: Boolean(organizationId),
  })
}

export function useApprovalsQuery(organizationId: string | null) {
  return useQuery({
    queryKey: dashboardQueryKeys.approvals(organizationId),
    queryFn: () => runtimeApi.listApprovals(),
    enabled: Boolean(organizationId),
  })
}
