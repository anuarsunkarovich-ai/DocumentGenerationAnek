import { cn } from '@shared/lib/cn'

type StatusVariant =
  | 'ready'
  | 'downloaded'
  | 'pending'
  | 'failed'
  | 'live'
  | 'info'

const statusClassMap: Record<StatusVariant, string> = {
  ready: 'status-ready',
  downloaded: 'status-downloaded',
  pending: 'status-pending',
  failed: 'status-failed',
  live: 'status-live',
  info: 'status-info',
}

type StatusBadgeProps = {
  label: string
  variant: StatusVariant
  className?: string
}

export function StatusBadge({ label, variant, className }: StatusBadgeProps) {
  return <span className={cn('status-badge', statusClassMap[variant], className)}>{label}</span>
}
