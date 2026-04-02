import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'

import { useSessionBootstrap } from '@entities/session/model/use-session-bootstrap'
import { useSessionStore } from '@entities/session/model/session.store'
import { SignInPanel } from '@features/auth/sign-in/ui/sign-in-panel'
import { runtimeApi } from '@shared/api/runtime-api'
import { env } from '@shared/config/env'
import { LoadingState } from '@shared/ui/loading-state'
import { StatusBadge } from '@shared/ui/status-badge'
import { DashboardSidebar } from '@widgets/dashboard/dashboard-sidebar'
import { DashboardTopbar } from '@widgets/dashboard/dashboard-topbar'

type DashboardScaffoldProps = {
  eyebrow: string
  title: string
  description: string
  children: ReactNode
}

export function DashboardScaffold({
  eyebrow,
  title,
  description,
  children,
}: DashboardScaffoldProps) {
  useSessionBootstrap()

  const hydrated = useSessionStore((state) => state.hydrated)
  const user = useSessionStore((state) => state.user)

  const systemPulseQuery = useQuery({
    queryKey: ['dashboard-pulse'],
    queryFn: () => runtimeApi.getSystemPulse(),
  })

  const requiresLiveSignIn = env.apiMode === 'live' && !user

  return (
    <div className="dashboard-layout">
      <DashboardSidebar />

      <div className="dashboard-main">
        <DashboardTopbar />

        <main className="dashboard-content">
          <section className="dashboard-hero-card">
            <div>
              <p className="section-label">{eyebrow}</p>
              <h1 className="newsreader">{title}</h1>
              <p>{description}</p>
            </div>
            {systemPulseQuery.data ? (
              <StatusBadge
                label={systemPulseQuery.data.mode === 'live' ? 'Live backend' : 'Prototype mode'}
                variant={systemPulseQuery.data.mode === 'live' ? 'live' : 'info'}
              />
            ) : null}
          </section>

          {!hydrated ? (
            <LoadingState />
          ) : requiresLiveSignIn ? (
            <section className="dashboard-grid">
              <article className="data-card">
                <div className="data-card__header">
                  <div>
                    <p className="micro-label">Live connection required</p>
                    <h2 className="newsreader">Sign in to hydrate the real organization.</h2>
                  </div>
                </div>
                <p className="support-copy" style={{ marginBottom: 18 }}>
                  The frontend is now routed against the live backend surface. Sign in with your
                  deployed admin credentials to unlock templates, generation, billing, API keys,
                  diagnostics, and public API testing.
                </p>
                <SignInPanel />
              </article>
            </section>
          ) : (
            children
          )}
        </main>
      </div>
    </div>
  )
}
