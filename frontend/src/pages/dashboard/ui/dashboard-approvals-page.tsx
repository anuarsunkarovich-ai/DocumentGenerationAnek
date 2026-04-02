import { useQuery } from '@tanstack/react-query'

import { useSessionStore } from '@entities/session/model/session.store'
import { useAuditQuery } from '@pages/dashboard/model/queries'
import { DashboardScaffold } from '@pages/dashboard/ui/dashboard-scaffold'
import { runtimeApi } from '@shared/api/runtime-api'
import { env } from '@shared/config/env'
import { JsonPreview } from '@shared/ui/json-preview'
import { LoadingState } from '@shared/ui/loading-state'
import { ApprovalsPanel } from '@widgets/dashboard/approvals-panel'
import { AuditFeed } from '@widgets/dashboard/audit-feed'

export function DashboardApprovalsPage() {
  const activeOrganizationId = useSessionStore((state) => state.activeOrganizationId)

  const auditQuery = useAuditQuery(activeOrganizationId)
  const approvalsQuery = useQuery({
    queryKey: ['approval-workflow', activeOrganizationId, env.apiMode],
    queryFn: () => runtimeApi.listApprovals(),
    enabled: env.apiMode === 'mock' && Boolean(activeOrganizationId),
  })

  return (
    <DashboardScaffold
      eyebrow="Approval workflow"
      title="Review the audit trail and operator checkpoints."
      description="The deployed backend exposes auditability and support actions directly. In prototype mode we also keep the visual approval cards; in live mode this page leans on the real audit stream and support data instead of fake buttons."
    >
      {auditQuery.isLoading ? (
        <LoadingState />
      ) : (
        <section className="notes-grid">
          <article className="data-card">
            <div className="data-card__header">
              <div>
                <p className="micro-label">Recent activity</p>
                <h2 className="newsreader">Audit Trail</h2>
              </div>
            </div>
            <AuditFeed events={auditQuery.data?.items ?? []} />
          </article>

          <article className="data-card">
            <div className="data-card__header">
              <div>
                <p className="micro-label">Workflow state</p>
                <h2 className="newsreader">Approvals Surface</h2>
              </div>
            </div>

            {env.apiMode === 'mock' ? (
              <ApprovalsPanel items={approvalsQuery.data?.items ?? []} />
            ) : (
              <JsonPreview
                title="Live-mode note"
                payload={{
                  status: 'connected',
                  message:
                    'The backend does not publish a standalone approvals list endpoint. This page therefore uses the real audit stream and support controls rather than fake approval records.',
                }}
              />
            )}
          </article>
        </section>
      )}
    </DashboardScaffold>
  )
}
