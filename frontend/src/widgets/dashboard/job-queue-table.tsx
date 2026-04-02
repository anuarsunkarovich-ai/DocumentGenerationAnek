import { Download, Eye, RefreshCw } from 'lucide-react'

import { StatusBadge } from '@shared/ui/status-badge'

type JobQueueTableItem = {
  id: string
  recipient: string
  recipient_meta: string
  status: string
  document_name: string
}

type JobQueueTableProps = {
  items: JobQueueTableItem[]
}

function statusMeta(status: string) {
  switch (status) {
    case 'generated':
    case 'completed':
      return { label: 'Generated', variant: 'ready' as const, icon: <Download size={14} /> }
    case 'downloaded':
      return {
        label: 'Downloaded',
        variant: 'downloaded' as const,
        icon: <Eye size={14} />,
      }
    case 'queued':
      return {
        label: 'Queued',
        variant: 'pending' as const,
        icon: <RefreshCw size={14} />,
      }
    case 'processing':
      return {
        label: 'Processing',
        variant: 'pending' as const,
        icon: <RefreshCw size={14} />,
      }
    case 'pending_audit':
      return {
        label: 'Pending audit',
        variant: 'pending' as const,
        icon: <RefreshCw size={14} />,
      }
    case 'validation_failed':
    case 'failed':
      return {
        label: 'Validation failed',
        variant: 'failed' as const,
        icon: <RefreshCw size={14} />,
      }
    default:
      return {
        label: status.replaceAll('_', ' '),
        variant: 'info' as const,
        icon: <Eye size={14} />,
      }
  }
}

export function JobQueueTable({ items }: JobQueueTableProps) {
  return (
    <div className="table-shell">
      <table>
        <thead>
          <tr>
            <th>Asset reference</th>
            <th>Principal recipient</th>
            <th>Engine status</th>
            <th>Utility</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const meta = statusMeta(item.status)

            return (
              <tr key={item.id}>
                <td>
                  <strong>{item.id}</strong>
                </td>
                <td>
                  <p className="recipient-name">{item.recipient}</p>
                  <p className="recipient-meta">{item.recipient_meta}</p>
                </td>
                <td>
                  <StatusBadge label={meta.label} variant={meta.variant} />
                </td>
                <td>{meta.icon}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
