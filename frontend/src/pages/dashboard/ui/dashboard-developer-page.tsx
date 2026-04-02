import { useSessionStore } from '@entities/session/model/session.store'
import { useApiKeysQuery } from '@pages/dashboard/model/queries'
import { DashboardScaffold } from '@pages/dashboard/ui/dashboard-scaffold'
import { LoadingState } from '@shared/ui/loading-state'
import { ApiKeyOpsSection } from '@widgets/dashboard/api-key-ops-section'
import { ApiKeysPanel } from '@widgets/dashboard/api-keys-panel'
import { DiagnosticsSupportSection } from '@widgets/dashboard/diagnostics-support-section'
import { PublicApiPlaygroundSection } from '@widgets/dashboard/public-api-playground-section'

export function DashboardDeveloperPage() {
  const activeOrganizationId = useSessionStore((state) => state.activeOrganizationId)
  const apiKeysQuery = useApiKeysQuery(activeOrganizationId)

  return (
    <DashboardScaffold
      eyebrow="Developer hub"
      title="Machine access, public API testing, and incident controls."
      description="This page exposes the key-management surface, usage logs, public machine-auth routes, and support actions so the frontend actually covers the backend’s API-key and admin capabilities."
    >
      {apiKeysQuery.isLoading ? (
        <LoadingState />
      ) : (
        <>
          <section className="notes-grid">
            <article className="data-card">
              <div className="data-card__header">
                <div>
                  <p className="micro-label">Machine access</p>
                  <h2 className="newsreader">Issued Keys</h2>
                </div>
              </div>
              <ApiKeysPanel items={apiKeysQuery.data?.items ?? []} />
            </article>

            <article className="data-card">
              <div className="data-card__header">
                <div>
                  <p className="micro-label">Public routes</p>
                  <h2 className="newsreader">API Playground</h2>
                </div>
              </div>
              <p className="support-copy">
                Test the published `/public/*` endpoints with a real API key. This is useful for
                demos, partner onboarding, and validating machine-auth before you hand access to a
                client.
              </p>
            </article>
          </section>

          {activeOrganizationId ? (
            <ApiKeyOpsSection
              organizationId={activeOrganizationId}
              apiKeys={apiKeysQuery.data?.items ?? []}
            />
          ) : null}

          <PublicApiPlaygroundSection />

          {activeOrganizationId ? (
            <DiagnosticsSupportSection
              organizationId={activeOrganizationId}
              firstApiKeyId={apiKeysQuery.data?.items[0]?.id}
            />
          ) : null}
        </>
      )}
    </DashboardScaffold>
  )
}
