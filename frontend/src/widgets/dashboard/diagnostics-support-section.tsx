import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

import { runtimeApi } from '@shared/api/runtime-api'
import { Button } from '@shared/ui/button'
import { JsonPreview } from '@shared/ui/json-preview'

type DiagnosticsSupportSectionProps = {
  organizationId: string
  firstApiKeyId?: string
}

export function DiagnosticsSupportSection({
  organizationId,
  firstApiKeyId,
}: DiagnosticsSupportSectionProps) {
  const [jobId, setJobId] = useState('')
  const [auditEntityType, setAuditEntityType] = useState('job')
  const [auditEntityId, setAuditEntityId] = useState('')
  const [userId, setUserId] = useState('')
  const [apiKeyId, setApiKeyId] = useState(firstApiKeyId ?? '')
  const [result, setResult] = useState<unknown>(null)

  const failedJobsQuery = useQuery({
    queryKey: ['failed-jobs', organizationId],
    queryFn: () => runtimeApi.listFailedJobs(organizationId, 25),
    enabled: Boolean(organizationId),
  })

  const auditHistoryQuery = useQuery({
    queryKey: ['audit-history', organizationId, auditEntityType, auditEntityId],
    queryFn: () => runtimeApi.getAuditHistory(organizationId, auditEntityType, auditEntityId, 50),
    enabled: Boolean(organizationId && auditEntityId),
  })

  const replayMutation = useMutation({
    mutationFn: () => runtimeApi.replayJob(jobId, organizationId),
    onSuccess: setResult,
  })

  const invalidateMutation = useMutation({
    mutationFn: () => runtimeApi.invalidateJobCache(jobId, organizationId),
    onSuccess: setResult,
  })

  const disableUserMutation = useMutation({
    mutationFn: () => runtimeApi.disableUser(userId, organizationId),
    onSuccess: setResult,
  })

  const disableApiKeyMutation = useMutation({
    mutationFn: () => runtimeApi.disableIncidentApiKey(apiKeyId, organizationId),
    onSuccess: setResult,
  })

  const cleanupMutation = useMutation({
    mutationFn: () => runtimeApi.runMaintenanceCleanup(organizationId),
    onSuccess: setResult,
  })

  return (
    <section className="ops-section" id="diagnostics-support">
      <div className="data-card">
        <div className="data-card__header">
          <div>
            <p className="micro-label">Failed jobs, replay, cache invalidation, incident actions</p>
            <h2 className="newsreader">Diagnostics & Support</h2>
          </div>
        </div>

        <div className="ops-grid">
          <div className="ops-panel">
            {failedJobsQuery.data ? <JsonPreview title="Failed jobs" payload={failedJobsQuery.data} /> : null}

            <label className="field-label">
              Job ID
              <input value={jobId} onChange={(event) => setJobId(event.target.value)} />
            </label>

            <div className="ops-button-row">
              <Button type="button" onClick={() => replayMutation.mutate()} disabled={!jobId}>
                Replay job
              </Button>
              <Button type="button" variant="secondary" onClick={() => invalidateMutation.mutate()} disabled={!jobId}>
                Invalidate cache
              </Button>
            </div>
          </div>

          <div className="ops-panel">
            <label className="field-label">
              Audit entity type
              <input value={auditEntityType} onChange={(event) => setAuditEntityType(event.target.value)} />
            </label>
            <label className="field-label">
              Audit entity ID
              <input value={auditEntityId} onChange={(event) => setAuditEntityId(event.target.value)} />
            </label>

            {auditHistoryQuery.data ? <JsonPreview title="Audit history" payload={auditHistoryQuery.data} /> : null}
          </div>
        </div>

        <div className="ops-grid">
          <div className="ops-panel">
            <label className="field-label">
              User ID
              <input value={userId} onChange={(event) => setUserId(event.target.value)} />
            </label>
            <Button type="button" variant="secondary" onClick={() => disableUserMutation.mutate()} disabled={!userId}>
              Disable user
            </Button>
          </div>

          <div className="ops-panel">
            <label className="field-label">
              API key ID
              <input value={apiKeyId} onChange={(event) => setApiKeyId(event.target.value)} />
            </label>
            <div className="ops-button-row">
              <Button type="button" variant="secondary" onClick={() => disableApiKeyMutation.mutate()} disabled={!apiKeyId}>
                Disable API key
              </Button>
              <Button type="button" variant="secondary" onClick={() => cleanupMutation.mutate()}>
                Run maintenance cleanup
              </Button>
            </div>
          </div>
        </div>

        {result ? <JsonPreview title="Last support operation" payload={result} /> : null}
      </div>
    </section>
  )
}
