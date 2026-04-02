import type { ApprovalItem } from '@shared/api/contracts'
import { Button } from '@shared/ui/button'

type ApprovalsPanelProps = {
  items: ApprovalItem[]
}

export function ApprovalsPanel({ items }: ApprovalsPanelProps) {
  return (
    <div className="approval-stack">
      {items.map((item) => (
        <article className="approval-card" key={item.id}>
          <p className="micro-label">{item.kind}</p>
          <h3>{item.title}</h3>
          <p>{item.reference}</p>
          <div className="field-grid" style={{ marginTop: 16 }}>
            <Button type="button">{item.action_label}</Button>
            {item.secondary_action_label ? (
              <Button type="button" variant="secondary">
                {item.secondary_action_label}
              </Button>
            ) : null}
          </div>
        </article>
      ))}
    </div>
  )
}
