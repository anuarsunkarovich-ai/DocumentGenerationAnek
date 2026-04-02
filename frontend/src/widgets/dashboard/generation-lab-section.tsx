import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

import type { Template } from '@shared/api/contracts'
import { useLiveJobStore } from '@pages/dashboard/model/live-job.store'
import { runtimeApi } from '@shared/api/runtime-api'
import { Button } from '@shared/ui/button'
import { JsonPreview } from '@shared/ui/json-preview'
import { LoadingState } from '@shared/ui/loading-state'

type GenerationLabSectionProps = {
  organizationId: string
  templates: Template[]
}

export function GenerationLabSection({
  organizationId,
  templates,
}: GenerationLabSectionProps) {
  const [templateId, setTemplateId] = useState(templates[0]?.id ?? '')
  const [taskId, setTaskId] = useState('')
  const [verificationHash, setVerificationHash] = useState('demo-sha256')
  const [result, setResult] = useState<unknown>(null)
  const upsertJob = useLiveJobStore((state) => state.upsertJob)

  const selectedTemplate = useMemo(
    () => templates.find((template) => template.id === templateId) ?? templates[0],
    [templateId, templates],
  )

  const constructorSchemaQuery = useQuery({
    queryKey: ['constructor-schema'],
    queryFn: () => runtimeApi.getConstructorSchema(),
  })

  const jobStatusQuery = useQuery({
    queryKey: ['job-status', organizationId, taskId],
    queryFn: () => runtimeApi.getJobStatus(taskId, organizationId),
    enabled: Boolean(taskId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'queued' || status === 'processing' ? 1500 : false
    },
  })

  const generateMutation = useMutation({
    mutationFn: (mode: 'constructor' | 'imported') =>
      mode === 'constructor'
        ? runtimeApi.generateDocument({
            organization_id: organizationId,
            template_id: templateId,
            template_version_id: null,
            data: {
              buyer_name: 'Anek M.',
              seller_name: 'Aisha K.',
            },
            constructor: {
              locale: 'ru-RU',
              metadata: { document_type: 'sales_agreement' },
              blocks: [
                {
                  type: 'header',
                  id: 'header-1',
                  text: 'Mutual Sales Agreement',
                },
                {
                  type: 'text',
                  id: 'text-1',
                  binding: { key: 'buyer_name' },
                },
              ],
            },
          })
        : runtimeApi.generateImportedDocument({
            organization_id: organizationId,
            template_id: templateId,
            template_version_id: null,
            data: {
              tenant_name: 'Anek M.',
            },
          }),
    onSuccess: (job) => {
      setTaskId(job.task_id)
      setResult(job)
      upsertJob({
        id: job.task_id,
        recipient: 'Interactive operator',
        recipient_meta: 'Queued live run',
        status: job.status,
        document_name: selectedTemplate?.name ?? 'Generated document',
        created_at: new Date().toISOString(),
      })
    },
  })

  const artifactMutation = useMutation({
    mutationFn: (mode: 'download' | 'preview') =>
      mode === 'download'
        ? runtimeApi.getJobDownload(taskId, organizationId)
        : runtimeApi.getJobPreview(taskId, organizationId),
    onSuccess: setResult,
  })

  const verifyMutation = useMutation({
    mutationFn: () => runtimeApi.verifyDocument(organizationId, undefined, verificationHash),
    onSuccess: setResult,
  })

  useEffect(() => {
    if (!jobStatusQuery.data) {
      return
    }

    upsertJob({
      id: jobStatusQuery.data.task_id,
      recipient: 'Interactive operator',
      recipient_meta: 'Live status poll',
      status: jobStatusQuery.data.status,
      document_name: selectedTemplate?.name ?? 'Generated document',
      created_at: jobStatusQuery.data.created_at,
    })
  }, [jobStatusQuery.data, selectedTemplate?.name, upsertJob])

  return (
    <section className="ops-section" id="generation-lab">
      <div className="data-card">
        <div className="data-card__header">
          <div>
            <p className="micro-label">Constructor, imported generation, polling, verification</p>
            <h2 className="newsreader">Generation Lab</h2>
          </div>
        </div>

        <div className="ops-grid">
          <div className="ops-panel">
            <label className="field-label">
              Template
              <select value={templateId} onChange={(event) => setTemplateId(event.target.value)}>
                {templates.map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name}
                  </option>
                ))}
              </select>
            </label>

            <div className="ops-button-row">
              <Button type="button" onClick={() => generateMutation.mutate('constructor')}>
                Generate constructor job
              </Button>
              <Button type="button" variant="secondary" onClick={() => generateMutation.mutate('imported')}>
                Generate imported job
              </Button>
            </div>

            <label className="field-label">
              Task ID
              <input value={taskId} onChange={(event) => setTaskId(event.target.value)} />
            </label>

            <div className="ops-button-row">
              <Button type="button" variant="secondary" onClick={() => artifactMutation.mutate('download')} disabled={!taskId}>
                Download artifact
              </Button>
              <Button type="button" variant="secondary" onClick={() => artifactMutation.mutate('preview')} disabled={!taskId}>
                Preview artifact
              </Button>
            </div>

            <label className="field-label">
              Verification hash
              <input value={verificationHash} onChange={(event) => setVerificationHash(event.target.value)} />
            </label>
            <Button type="button" variant="secondary" onClick={() => verifyMutation.mutate()}>
              Verify artifact
            </Button>
          </div>

          <div className="ops-panel">
            {constructorSchemaQuery.isLoading ? (
              <LoadingState />
            ) : constructorSchemaQuery.data ? (
              <JsonPreview title="Constructor schema" payload={constructorSchemaQuery.data} />
            ) : null}

            {jobStatusQuery.data ? <JsonPreview title="Job status" payload={jobStatusQuery.data} /> : null}
          </div>
        </div>

        {result ? <JsonPreview title="Last generation operation" payload={result} /> : null}
      </div>
    </section>
  )
}
