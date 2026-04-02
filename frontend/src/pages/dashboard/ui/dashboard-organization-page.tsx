import { useSessionStore } from '@entities/session/model/session.store'
import {
  useBillingQuery,
  useCacheQuery,
  useWorkerQuery,
} from '@pages/dashboard/model/queries'
import { DashboardScaffold } from '@pages/dashboard/ui/dashboard-scaffold'
import { LoadingState } from '@shared/ui/loading-state'
import { TelemetryPanel } from '@widgets/dashboard/telemetry-panel'
import { BillingOpsSection } from '@widgets/dashboard/billing-ops-section'

export function DashboardOrganizationPage() {
  const activeOrganizationId = useSessionStore((state) => state.activeOrganizationId)

  const billingQuery = useBillingQuery(activeOrganizationId)
  const workerQuery = useWorkerQuery(activeOrganizationId)
  const cacheQuery = useCacheQuery(activeOrganizationId)

  const isLoading =
    billingQuery.isLoading || workerQuery.isLoading || cacheQuery.isLoading

  return (
    <DashboardScaffold
      eyebrow="Organization settings"
      title="Billing, telemetry, and tenant-level operations."
      description="This page maps to the operational backbone of the backend: subscription state, usage meters, invoice controls, worker health, and cache metrics for the active organization."
    >
      {isLoading ? (
        <LoadingState />
      ) : (
        <>
          <section className="notes-grid">
            <article className="data-card">
              <div className="data-card__header">
                <div>
                  <p className="micro-label">Plan snapshot</p>
                  <h2 className="newsreader">Subscription State</h2>
                </div>
              </div>

              {billingQuery.data ? (
                <div className="approval-stack">
                  <article className="approval-card">
                    <p className="micro-label">Active plan</p>
                    <h3>{billingQuery.data.subscription.plan.name}</h3>
                    <p>
                      {billingQuery.data.usage_meter.generation_count}/
                      {billingQuery.data.subscription.plan.monthly_generation_cap} generations,
                      {` ${billingQuery.data.usage_meter.template_count}`} templates, and{' '}
                      {billingQuery.data.usage_meter.user_count} users in the current period.
                    </p>
                  </article>

                  <article className="approval-card">
                    <p className="micro-label">Storage + retention</p>
                    <h3>{billingQuery.data.subscription.plan.audit_retention_days} day audit window</h3>
                    <p>
                      Storage used: {billingQuery.data.usage_meter.storage_bytes} bytes. Signature
                      support:{' '}
                      {billingQuery.data.subscription.plan.signature_support ? 'enabled' : 'disabled'}.
                    </p>
                  </article>
                </div>
              ) : null}
            </article>

            <article className="data-card">
              <div className="data-card__header">
                <div>
                  <p className="micro-label">Infrastructure telemetry</p>
                  <h2 className="newsreader">System Health</h2>
                </div>
              </div>

              {workerQuery.data && cacheQuery.data ? (
                <TelemetryPanel cacheStats={cacheQuery.data} workerStatus={workerQuery.data} />
              ) : null}
            </article>
          </section>

          {activeOrganizationId ? <BillingOpsSection organizationId={activeOrganizationId} /> : null}
        </>
      )}
    </DashboardScaffold>
  )
}
