import { useMemo } from 'react'

import { useSessionStore } from '@entities/session/model/session.store'
import { useTemplatesQuery } from '@pages/dashboard/model/queries'
import { useDashboardUiStore } from '@pages/dashboard/model/dashboard-ui.store'
import { DashboardScaffold } from '@pages/dashboard/ui/dashboard-scaffold'
import { LoadingState } from '@shared/ui/loading-state'
import { StatusBadge } from '@shared/ui/status-badge'
import { TemplateLibraryCard } from '@widgets/dashboard/template-library-card'
import { TemplateOpsSection } from '@widgets/dashboard/template-ops-section'

export function DashboardTemplatesPage() {
  const activeOrganizationId = useSessionStore((state) => state.activeOrganizationId)
  const user = useSessionStore((state) => state.user)
  const search = useDashboardUiStore((state) => state.search)
  const templatesQuery = useTemplatesQuery(activeOrganizationId)

  const filteredTemplates = useMemo(() => {
    const items = templatesQuery.data?.items ?? []
    const query = search.trim().toLowerCase()

    if (!query) {
      return items
    }

    return items.filter((template) => {
      const haystack = `${template.name} ${template.code} ${template.description ?? ''}`.toLowerCase()
      return haystack.includes(query)
    })
  }, [search, templatesQuery.data?.items])

  return (
    <DashboardScaffold
      eyebrow="Template operations"
      title="Template library, ingestion, and schema extraction."
      description="This module is live-backed: list templates, inspect current versions, upload DOCX sources, register storage assets, and run the import/schema flows against the deployed API."
    >
      {templatesQuery.isLoading ? (
        <LoadingState />
      ) : (
        <>
          <section className="dashboard-grid">
            <article className="data-card">
              <div className="data-card__header">
                <div>
                  <p className="micro-label">Enterprise repository</p>
                  <h2 className="newsreader">Template Library</h2>
                </div>
                <StatusBadge label={`${filteredTemplates.length} visible`} variant="info" />
              </div>

              {filteredTemplates.length ? (
                <div className="template-library-grid">
                  {filteredTemplates.map((template) => (
                    <TemplateLibraryCard key={template.id} template={template} />
                  ))}
                </div>
              ) : (
                <p className="support-copy">
                  No templates match the current search or this organization has not published any
                  templates yet.
                </p>
              )}
            </article>

            <article className="data-card">
              <div className="data-card__header">
                <div>
                  <p className="micro-label">Search state</p>
                  <h2 className="newsreader">Current Workspace</h2>
                </div>
              </div>
                <div className="approval-stack">
                  <article className="approval-card">
                    <p className="micro-label">Organization</p>
                    <h3>{user?.organization.name ?? 'Unassigned'}</h3>
                    <p>
                      Search in the top bar filters this page in real time. Open the workbench below
                      to inspect a template, extract schema, or run import assistance endpoints.
                  </p>
                </article>
              </div>
            </article>
          </section>

          {activeOrganizationId && templatesQuery.data ? (
            <TemplateOpsSection
              organizationId={activeOrganizationId}
              templates={templatesQuery.data.items}
            />
          ) : null}
        </>
      )}
    </DashboardScaffold>
  )
}
