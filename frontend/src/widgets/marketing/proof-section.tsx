import { FileLock2, History, Share2, Workflow } from 'lucide-react'

import { MetricCard } from '@shared/ui/metric-card'

const metrics = [
  {
    value: '90%',
    label: 'Efficiency gain',
    copy: 'Fewer manual edits required across generated document flows through logic-driven templating.',
  },
  {
    value: '99%',
    label: 'Error reduction',
    copy: 'Formatting drift, redundant clauses, and human logic mistakes are removed before final issuance.',
  },
  {
    value: '01',
    label: 'Day turnaround',
    copy: 'Multi-stakeholder document packs move from request to signature inside the same business cycle.',
  },
] as const

const features = [
  {
    icon: History,
    title: 'Version control',
    copy: 'Immutable logs for every generation and revision.',
  },
  {
    icon: FileLock2,
    title: 'Auditability',
    copy: 'Clear chain of custody for edits and approvals.',
  },
  {
    icon: Share2,
    title: 'Secure sharing',
    copy: 'Presigned artifact delivery for client-ready output.',
  },
  {
    icon: Workflow,
    title: 'Approval tracking',
    copy: 'Real-time workflow state across legal, sales, and ops.',
  },
] as const

export function ProofSection() {
  return (
    <section className="section section-tight" id="solutions">
      <div className="page-shell">
        <div className="section-heading">
          <p className="section-label">Enterprise precision</p>
          <h2 className="section-title newsreader">Engineered for absolute accuracy.</h2>
        </div>

        <div className="metrics-grid">
          {metrics.map((metric) => (
            <MetricCard key={metric.label} {...metric} />
          ))}
        </div>

        <div className="feature-grid">
          {features.map((feature) => {
            const Icon = feature.icon

            return (
              <article className="feature-card" key={feature.title}>
                <Icon size={18} />
                <div>
                  <h3>{feature.title}</h3>
                  <p>{feature.copy}</p>
                </div>
              </article>
            )
          })}
        </div>
      </div>
    </section>
  )
}
