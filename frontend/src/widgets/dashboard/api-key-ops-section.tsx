import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

import type { ApiKeyMetadata } from '@shared/api/contracts'
import { runtimeApi } from '@shared/api/runtime-api'
import { Button } from '@shared/ui/button'
import { JsonPreview } from '@shared/ui/json-preview'

type ApiKeyOpsSectionProps = {
  organizationId: string
  apiKeys: ApiKeyMetadata[]
}

export function ApiKeyOpsSection({
  organizationId,
  apiKeys,
}: ApiKeyOpsSectionProps) {
  const [name, setName] = useState('Client Production Key')
  const [scopes, setScopes] = useState('templates:read,documents:generate,documents:read')
  const [activeApiKeyId, setActiveApiKeyId] = useState(apiKeys[0]?.id ?? '')
  const [result, setResult] = useState<unknown>(null)

  const usageQuery = useQuery({
    queryKey: ['api-key-usage', organizationId],
    queryFn: () => runtimeApi.listApiKeyUsage(organizationId, 25),
    enabled: Boolean(organizationId),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      runtimeApi.createApiKey({
        organization_id: organizationId,
        name,
        scopes: scopes.split(',').map((item) => item.trim()).filter(Boolean),
      }),
    onSuccess: setResult,
  })

  const rotateMutation = useMutation({
    mutationFn: () => runtimeApi.rotateApiKey(activeApiKeyId, organizationId),
    onSuccess: setResult,
  })

  const revokeMutation = useMutation({
    mutationFn: () => runtimeApi.revokeApiKey(activeApiKeyId, organizationId),
    onSuccess: setResult,
  })

  return (
    <section className="ops-section" id="api-key-control">
      <div className="data-card">
        <div className="data-card__header">
          <div>
            <p className="micro-label">Create, rotate, revoke, usage logs</p>
            <h2 className="newsreader">API Key Control</h2>
          </div>
        </div>

        <div className="ops-grid">
          <div className="ops-panel">
            <label className="field-label">
              Key name
              <input value={name} onChange={(event) => setName(event.target.value)} />
            </label>

            <label className="field-label">
              Scopes
              <input value={scopes} onChange={(event) => setScopes(event.target.value)} />
            </label>

            <Button type="button" onClick={() => createMutation.mutate()}>
              Create API key
            </Button>

            <label className="field-label">
              Target key
              <select value={activeApiKeyId} onChange={(event) => setActiveApiKeyId(event.target.value)}>
                {apiKeys.map((apiKey) => (
                  <option key={apiKey.id} value={apiKey.id}>
                    {apiKey.name}
                  </option>
                ))}
              </select>
            </label>

            <div className="ops-button-row">
              <Button type="button" variant="secondary" onClick={() => rotateMutation.mutate()}>
                Rotate key
              </Button>
              <Button type="button" variant="secondary" onClick={() => revokeMutation.mutate()}>
                Revoke key
              </Button>
            </div>
          </div>

          <div className="ops-panel">
            {usageQuery.data ? <JsonPreview title="API key usage" payload={usageQuery.data} /> : null}
          </div>
        </div>

        {result ? <JsonPreview title="Last API key operation" payload={result} /> : null}
      </div>
    </section>
  )
}
