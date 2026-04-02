import type { AuditEvent } from '@shared/api/contracts'

type AuditFeedProps = {
  events: AuditEvent[]
}

export function AuditFeed({ events }: AuditFeedProps) {
  return (
    <div className="audit-stack">
      {events.map((event) => (
        <article className="audit-card" key={event.id}>
          <p className="micro-label">{event.action}</p>
          <h3>{event.entity_type.replaceAll('_', ' ')}</h3>
          <p>{Object.entries(event.payload).map(([key, value]) => `${key}: ${String(value)}`).join(' • ')}</p>
          <p className="micro-label" style={{ marginTop: 12 }}>
            {new Date(event.created_at).toLocaleString()}
          </p>
        </article>
      ))}
    </div>
  )
}
