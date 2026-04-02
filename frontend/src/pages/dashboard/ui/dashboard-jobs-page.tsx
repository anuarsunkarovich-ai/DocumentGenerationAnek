import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'

import { useSessionStore } from '@entities/session/model/session.store'
import { useTemplatesQuery } from '@pages/dashboard/model/queries'
import { useDashboardUiStore } from '@pages/dashboard/model/dashboard-ui.store'
import { useLiveJobStore } from '@pages/dashboard/model/live-job.store'
import { DashboardScaffold } from '@pages/dashboard/ui/dashboard-scaffold'
import { runtimeApi } from '@shared/api/runtime-api'
import { env } from '@shared/config/env'
import { JsonPreview } from '@shared/ui/json-preview'
import { LoadingState } from '@shared/ui/loading-state'
import { StatusBadge } from '@shared/ui/status-badge'
import { QuickGenerationForm } from '@features/quick-generation/ui/quick-generation-form'
import { GenerationLabSection } from '@widgets/dashboard/generation-lab-section'
import { JobQueueTable } from '@widgets/dashboard/job-queue-table'

export function DashboardJobsPage() {
  const activeOrganizationId = useSessionStore((state) => state.activeOrganizationId)
  const search = useDashboardUiStore((state) => state.search)
  const trackedJobs = useLiveJobStore((state) => state.items)

  const templatesQuery = useTemplatesQuery(activeOrganizationId)
  const failedJobsQuery = useQuery({
    queryKey: ['failed-jobs', activeOrganizationId],
    queryFn: () => runtimeApi.listFailedJobs(activeOrganizationId ?? '', 25),
    enabled: Boolean(activeOrganizationId),
  })

  const jobRows = useMemo(() => {
    const failedItems =
      failedJobsQuery.data?.items.map((job) => ({
        id: job.task_id,
        recipient: 'Backend diagnostic',
        recipient_meta: 'Failed generation',
        status: 'failed',
        document_name: job.error_message ?? 'Generation failure',
      })) ?? []

    const items = [...trackedJobs, ...failedItems]
    const query = search.trim().toLowerCase()

    if (!query) {
      return items
    }

    return items.filter((job) => {
      const haystack =
        `${job.id} ${job.recipient} ${job.recipient_meta} ${job.document_name}`.toLowerCase()
      return haystack.includes(query)
    })
  }, [failedJobsQuery.data?.items, search, trackedJobs])

  return (
    <DashboardScaffold
      eyebrow="Generation control"
      title="Generate, poll, verify, and track live jobs."
      description="This surface is where we actually drive the backend. Launch generation jobs, poll task status, inspect artifacts, verify authenticity hashes, and keep a browser-side queue of recent runs."
    >
      {templatesQuery.isLoading ? (
        <LoadingState />
      ) : (
        <>
          <section className="dashboard-grid">
            <article className="data-card">
              <div className="data-card__header">
                <div>
                  <p className="micro-label">Recent tracked runs</p>
                  <h2 className="newsreader">Job Queue</h2>
                </div>
                <StatusBadge label={`${jobRows.length} tracked`} variant="live" />
              </div>

              {jobRows.length ? (
                <JobQueueTable items={jobRows} />
              ) : (
                <p className="support-copy">
                  No browser-tracked jobs yet. Generate a document below and it will appear here.
                  Failed job diagnostics from the backend will also surface on this page.
                </p>
              )}
            </article>

            <article className="data-card">
              <div className="data-card__header">
                <div>
                  <p className="micro-label">Launch flow</p>
                  <h2 className="newsreader">
                    {env.apiMode === 'live' ? 'Generation Lab' : 'Quick Prototype'}
                  </h2>
                </div>
              </div>

              {env.apiMode === 'mock' && activeOrganizationId && templatesQuery.data ? (
                <QuickGenerationForm
                  organizationId={activeOrganizationId}
                  templates={templatesQuery.data.items}
                />
              ) : (
                <p className="support-copy">
                  Live mode uses the full generation lab below instead of the old prototype-only
                  quick form so you can work directly against the deployed API contract.
                </p>
              )}

              {failedJobsQuery.data ? (
                <JsonPreview title="Failed-job diagnostics" payload={failedJobsQuery.data} />
              ) : null}
            </article>
          </section>

          {activeOrganizationId && templatesQuery.data ? (
            <GenerationLabSection
              organizationId={activeOrganizationId}
              templates={templatesQuery.data.items}
            />
          ) : null}
        </>
      )}
    </DashboardScaffold>
  )
}
