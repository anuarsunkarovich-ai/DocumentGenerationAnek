import { useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

import type { Template } from '@shared/api/contracts'
import { runtimeApi } from '@shared/api/runtime-api'
import { Button } from '@shared/ui/button'
import { JsonPreview } from '@shared/ui/json-preview'
import { LoadingState } from '@shared/ui/loading-state'

type TemplateOpsSectionProps = {
  organizationId: string
  templates: Template[]
}

export function TemplateOpsSection({
  organizationId,
  templates,
}: TemplateOpsSectionProps) {
  const [selectedTemplateId, setSelectedTemplateId] = useState(templates[0]?.id ?? '')
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [result, setResult] = useState<unknown>(null)

  const selectedTemplate = useMemo(
    () => templates.find((template) => template.id === selectedTemplateId) ?? templates[0],
    [selectedTemplateId, templates],
  )

  const templateDetailQuery = useQuery({
    queryKey: ['template-detail', organizationId, selectedTemplateId],
    queryFn: () => runtimeApi.getTemplateDetail(organizationId, selectedTemplateId),
    enabled: Boolean(selectedTemplateId),
  })

  const uploadMutation = useMutation({
    mutationFn: async () => {
      const formData = new FormData()
      formData.append('organization_id', organizationId)
      formData.append('name', 'Uploaded Template')
      formData.append('code', 'uploaded-template')
      formData.append('version', '1.0.0')
      formData.append('publish', 'true')
      if (uploadFile) {
        formData.append('file', uploadFile)
      } else {
        formData.append('file', new Blob(['demo'], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }), 'demo.docx')
      }
      return runtimeApi.uploadTemplate(formData)
    },
    onSuccess: setResult,
  })

  const registerMutation = useMutation({
    mutationFn: () =>
      runtimeApi.registerTemplate({
        organization_id: organizationId,
        name: 'Registered Template',
        code: 'registered-template',
        version: '1.0.1',
        storage_key: 'templates/demo/registered-template.docx',
        original_filename: 'registered-template.docx',
        publish: true,
      }),
    onSuccess: setResult,
  })

  const fileActionMutation = useMutation({
    mutationFn: async (action: 'extract' | 'analyze' | 'inspect') => {
      const file =
        uploadFile ??
        new File(['demo'], 'demo.docx', {
          type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        })

      if (action === 'extract') return runtimeApi.extractSchema(file)
      if (action === 'analyze') return runtimeApi.analyzeImportUpload(file)
      return runtimeApi.inspectImportUpload(file)
    },
    onSuccess: setResult,
  })

  const storedActionMutation = useMutation({
    mutationFn: async (
      action:
        | 'analyzeStored'
        | 'inspectStored'
        | 'confirmStored'
        | 'templateizeStored'
        | 'extractStored',
    ) => {
      if (!selectedTemplateId) return null
      if (action === 'analyzeStored')
        return runtimeApi.analyzeStoredTemplate(selectedTemplateId, organizationId)
      if (action === 'inspectStored')
        return runtimeApi.inspectStoredTemplate(selectedTemplateId, organizationId)
      if (action === 'confirmStored')
        return runtimeApi.confirmStoredTemplate(selectedTemplateId, {
          organization_id: organizationId,
          analysis_checksum: 'a'.repeat(64),
          bindings: [
            {
              candidate_id: 'candidate-1',
              binding_key: 'tenant_name',
              label: 'Tenant Name',
            },
          ],
        })
      if (action === 'templateizeStored')
        return runtimeApi.templateizeStoredTemplate(selectedTemplateId, {
          organization_id: organizationId,
          inspection_checksum: 'b'.repeat(64),
          selections: [
            {
              paragraph_path: 'body/p/12',
              fragment_start: 0,
              fragment_end: 11,
              binding_key: 'tenant_name',
              label: 'Tenant Name',
            },
          ],
        })
      return runtimeApi.extractStoredTemplateSchema(selectedTemplateId, organizationId)
    },
    onSuccess: setResult,
  })

  return (
    <section className="ops-section" id="templates-workbench">
      <div className="data-card">
        <div className="data-card__header">
          <div>
            <p className="micro-label">Template ingestion and schema flows</p>
            <h2 className="newsreader">Template Workbench</h2>
          </div>
        </div>

        <div className="ops-grid">
          <div className="ops-panel">
            <label className="field-label">
              Active template
              <select value={selectedTemplateId} onChange={(event) => setSelectedTemplateId(event.target.value)}>
                {templates.map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name}
                  </option>
                ))}
              </select>
            </label>

            {templateDetailQuery.isLoading ? (
              <LoadingState />
            ) : templateDetailQuery.data ? (
              <JsonPreview title="Template detail" payload={templateDetailQuery.data} />
            ) : null}
          </div>

          <div className="ops-panel">
            <p className="micro-label">Upload / register / import</p>
            <div className="field-grid">
              <label className="field-label">
                DOCX file
                <input
                  type="file"
                  accept=".docx"
                  onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
                />
              </label>

              <div className="ops-button-row">
                <Button type="button" onClick={() => uploadMutation.mutate()} disabled={uploadMutation.isPending}>
                  Upload template
                </Button>
                <Button type="button" variant="secondary" onClick={() => registerMutation.mutate()} disabled={registerMutation.isPending}>
                  Register storage template
                </Button>
              </div>

              <div className="ops-button-row">
                <Button type="button" variant="secondary" onClick={() => fileActionMutation.mutate('extract')}>
                  Extract schema
                </Button>
                <Button type="button" variant="secondary" onClick={() => fileActionMutation.mutate('analyze')}>
                  Analyze upload
                </Button>
                <Button type="button" variant="secondary" onClick={() => fileActionMutation.mutate('inspect')}>
                  Inspect upload
                </Button>
              </div>

              <div className="ops-button-row">
                <Button type="button" variant="secondary" onClick={() => storedActionMutation.mutate('analyzeStored')}>
                  Analyze stored
                </Button>
                <Button type="button" variant="secondary" onClick={() => storedActionMutation.mutate('inspectStored')}>
                  Inspect stored
                </Button>
                <Button type="button" variant="secondary" onClick={() => storedActionMutation.mutate('extractStored')}>
                  Extract stored schema
                </Button>
              </div>

              <div className="ops-button-row">
                <Button type="button" variant="secondary" onClick={() => storedActionMutation.mutate('confirmStored')}>
                  Confirm import bindings
                </Button>
                <Button type="button" variant="secondary" onClick={() => storedActionMutation.mutate('templateizeStored')}>
                  Templateize spans
                </Button>
              </div>
            </div>
          </div>
        </div>

        {selectedTemplate ? (
          <div className="ops-summary">
            <strong>{selectedTemplate.name}</strong>
            <span>{selectedTemplate.description}</span>
          </div>
        ) : null}

        {result ? <JsonPreview title="Last template operation" payload={result} /> : null}
      </div>
    </section>
  )
}
