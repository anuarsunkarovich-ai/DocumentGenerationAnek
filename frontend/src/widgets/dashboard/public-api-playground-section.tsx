import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'

import { ApiError } from '@shared/api/http-client'
import { runtimeApi } from '@shared/api/runtime-api'
import { Button } from '@shared/ui/button'
import { JsonPreview } from '@shared/ui/json-preview'

export function PublicApiPlaygroundSection() {
  const [apiKey, setApiKey] = useState('')
  const [templateId, setTemplateId] = useState('')
  const [taskId, setTaskId] = useState('')
  const [authenticityHash, setAuthenticityHash] = useState('demo-sha256')
  const [result, setResult] = useState<unknown>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const actionMutation = useMutation({
    mutationFn: async (
      action:
        | 'listTemplates'
        | 'getTemplate'
        | 'constructorSchema'
        | 'generate'
        | 'status'
        | 'download'
        | 'preview'
        | 'verify'
        | 'audit',
    ) => {
      const normalizedApiKey = apiKey.trim()
      if (!normalizedApiKey) {
        throw new Error('Enter an API key from the developer hub before calling the public routes.')
      }

      switch (action) {
        case 'listTemplates':
          return runtimeApi.listPublicTemplates(normalizedApiKey)
        case 'getTemplate':
          return runtimeApi.getPublicTemplate(normalizedApiKey, templateId)
        case 'constructorSchema':
          return runtimeApi.getPublicConstructorSchema(normalizedApiKey)
        case 'generate':
          return runtimeApi.generatePublicDocument(normalizedApiKey, {
            template_id: templateId,
            template_version_id: null,
            data: {
              client_name: 'Anek M.',
              counterparty_name: 'Astana Realty Group',
              effective_date: '2026-04-02',
            },
            constructor: {
              locale: 'en-US',
              metadata: {
                channel: 'public-playground',
                document_type: 'demo_contract',
              },
              blocks: [
                {
                  id: 'header-1',
                  type: 'header',
                  text: 'Generated via Public API',
                },
                {
                  id: 'text-1',
                  type: 'text',
                  text: 'Client: {{client_name}}',
                },
                {
                  id: 'text-2',
                  type: 'text',
                  text: 'Counterparty: {{counterparty_name}}',
                },
              ],
            },
          })
        case 'status':
          return runtimeApi.getPublicJobStatus(normalizedApiKey, taskId)
        case 'download':
          return runtimeApi.getPublicJobDownload(normalizedApiKey, taskId)
        case 'preview':
          return runtimeApi.getPublicJobPreview(normalizedApiKey, taskId)
        case 'verify':
          return runtimeApi.verifyPublicDocument(normalizedApiKey, undefined, authenticityHash)
        case 'audit':
          return runtimeApi.listPublicAuditEvents(normalizedApiKey)
      }
    },
    onSuccess: (payload, action) => {
      setErrorMessage(null)
      setResult(payload)

      if (action === 'listTemplates') {
        const firstTemplateId = (payload as { items?: Array<{ id: string }> }).items?.[0]?.id
        if (firstTemplateId) {
          setTemplateId(firstTemplateId)
        }
      }

      if (action === 'generate') {
        const generatedTaskId = (payload as { task_id?: string }).task_id
        if (generatedTaskId) {
          setTaskId(generatedTaskId)
        }
      }
    },
    onError: (error) => {
      if (error instanceof ApiError) {
        setErrorMessage(error.detail)
        return
      }

      setErrorMessage(error instanceof Error ? error.message : 'Public API call failed.')
    },
  })

  return (
    <section className="ops-section" id="public-api-playground">
      <div className="data-card">
        <div className="data-card__header">
          <div>
            <p className="micro-label">Published machine-auth routes</p>
            <h2 className="newsreader">Public API Playground</h2>
          </div>
        </div>

        <div className="ops-grid">
          <div className="ops-panel">
            <label className="field-label">
              API key
              <input
                placeholder="Paste an X-API-Key value"
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
              />
            </label>

            <label className="field-label">
              Published template ID
              <input
                placeholder="Fetched from public template list"
                value={templateId}
                onChange={(event) => setTemplateId(event.target.value)}
              />
            </label>

            <label className="field-label">
              Public task ID
              <input
                placeholder="Populated after generation"
                value={taskId}
                onChange={(event) => setTaskId(event.target.value)}
              />
            </label>

            <label className="field-label">
              Verification hash
              <input
                value={authenticityHash}
                onChange={(event) => setAuthenticityHash(event.target.value)}
              />
            </label>

            <div className="ops-button-row">
              <Button type="button" onClick={() => actionMutation.mutate('listTemplates')}>
                List public templates
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => actionMutation.mutate('getTemplate')}
                disabled={!templateId}
              >
                Get template detail
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => actionMutation.mutate('constructorSchema')}
              >
                Constructor schema
              </Button>
            </div>

            <div className="ops-button-row">
              <Button
                type="button"
                variant="secondary"
                onClick={() => actionMutation.mutate('generate')}
                disabled={!templateId}
              >
                Generate public job
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => actionMutation.mutate('status')}
                disabled={!taskId}
              >
                Poll status
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => actionMutation.mutate('audit')}
              >
                Read public audit
              </Button>
            </div>

            <div className="ops-button-row">
              <Button
                type="button"
                variant="secondary"
                onClick={() => actionMutation.mutate('download')}
                disabled={!taskId}
              >
                Download artifact
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => actionMutation.mutate('preview')}
                disabled={!taskId}
              >
                Preview artifact
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => actionMutation.mutate('verify')}
              >
                Verify artifact
              </Button>
            </div>

            {errorMessage ? (
              <div className="form-feedback form-feedback--error">{errorMessage}</div>
            ) : null}
          </div>

          <div className="ops-panel">
            {result ? (
              <JsonPreview title="Public API response" payload={result} />
            ) : (
              <p className="support-copy">
                Create an API key with the scopes you need, paste it here, then exercise the
                public template, document, and audit endpoints directly from the UI.
              </p>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
