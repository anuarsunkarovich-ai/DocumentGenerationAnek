import { ArrowRight, FileCheck2, ScrollText } from 'lucide-react'

import type { SystemPulse } from '@shared/api/contracts'
import { ButtonLink } from '@shared/ui/button'
import { StatusBadge } from '@shared/ui/status-badge'

type HeroSectionProps = {
  pulse: SystemPulse
}

export function HeroSection({ pulse }: HeroSectionProps) {
  return (
    <section className="hero" id="top">
      <div className="page-shell hero-grid">
        <div className="hero-copy">
          <span className="eyebrow">System status: {pulse.status}</span>
          <h1 className="newsreader">
            Documents generated in <em>minutes</em>, not hours.
          </h1>
          <p>
            A concierge document automation engine for contracts, forms, acts, lease
            documents, onboarding packs, and approval workflows. Built to serve high-trust real
            estate and legal operations teams in Astana.
          </p>

          <div className="hero-actions">
            <ButtonLink to="/dashboard">
              Open live prototype <ArrowRight size={16} />
            </ButtonLink>
            <a className="button button-secondary" href="#solutions">
              Explore solutions
            </a>
          </div>
        </div>

        <div className="hero-aside">
          <div className="hero-glow" />
          <div className="product-frame">
            <div className="product-window">
              <div className="window-dots">
                <span />
                <span />
                <span />
              </div>
              <span className="micro-label">protocol-engine-v4.0.12</span>
            </div>

            <div className="product-body">
              <aside className="product-sidebar">
                <div className="product-sidebar__block">
                  <p className="product-sidebar__label">Library</p>
                  <div className="skeleton-stack">
                    <span className="skeleton-line" />
                    <span className="skeleton-line" />
                    <span className="skeleton-line" />
                  </div>
                </div>

                <div className="product-sidebar__block">
                  <p className="product-sidebar__label">Recent jobs</p>
                  <div className="skeleton-stack">
                    <span className="skeleton-line" />
                    <span className="skeleton-line" />
                    <span className="skeleton-line" />
                  </div>
                </div>
              </aside>

              <div className="product-main">
                <div className="product-main__top">
                  <div>
                    <h2 className="product-main__title newsreader">Active Templates</h2>
                    <p className="product-main__meta">
                      operational workspace / legal_alpha / {pulse.label}
                    </p>
                  </div>
                  <StatusBadge label="Live" variant="live" />
                </div>

                <div className="template-grid">
                  <article className="template-mini-card">
                    <div className="template-mini-card__top">
                      <ScrollText size={18} />
                      <StatusBadge label="Ready" variant="ready" />
                    </div>
                    <h3 className="template-mini-card__title">Sales Agreement</h3>
                    <p className="template-mini-card__meta">
                      Multi-step approval workflow with pricing, escrow, and sign-off logic.
                    </p>
                  </article>

                  <article className="template-mini-card">
                    <div className="template-mini-card__top">
                      <FileCheck2 size={18} />
                      <StatusBadge label="Ready" variant="ready" />
                    </div>
                    <h3 className="template-mini-card__title">Lease Addendum</h3>
                    <p className="template-mini-card__meta">
                      Region-specific clauses, renewal dates, and audit-safe document history.
                    </p>
                  </article>
                </div>

                <div className="activity-list">
                  <div className="activity-row">
                    <div className="activity-row__left">
                      <span className="activity-icon">
                        <FileCheck2 size={16} />
                      </span>
                      <span>V2.4 approved by legal counsel</span>
                    </div>
                    <span className="micro-label">2m ago</span>
                  </div>
                  <div className="activity-row">
                    <div className="activity-row__left">
                      <span className="activity-icon">
                        <ScrollText size={16} />
                      </span>
                      <span>Field mapping updated for clause 14b</span>
                    </div>
                    <span className="micro-label">14m ago</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
