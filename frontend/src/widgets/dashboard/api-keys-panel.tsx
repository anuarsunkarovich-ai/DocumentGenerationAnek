import { KeyRound } from 'lucide-react'

import type { ApiKeyMetadata } from '@shared/api/contracts'
import { StatusBadge } from '@shared/ui/status-badge'

type ApiKeysPanelProps = {
  items: ApiKeyMetadata[]
}

export function ApiKeysPanel({ items }: ApiKeysPanelProps) {
  return (
    <div className="key-stack">
      {items.map((item) => (
        <article className="key-card" key={item.id}>
          <div className="row-between">
            <div>
              <p className="micro-label">API key</p>
              <h3>{item.name}</h3>
            </div>
            <KeyRound size={16} />
          </div>
          <p>{item.key_prefix}</p>
          <div className="inline-meta" style={{ marginTop: 14 }}>
            <StatusBadge label={item.status} variant="live" />
            <StatusBadge label={`${item.scopes.length} scopes`} variant="info" />
          </div>
        </article>
      ))}
    </div>
  )
}
