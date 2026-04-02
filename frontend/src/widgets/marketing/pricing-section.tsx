import { DemoRequestForm } from '@features/demo-request/ui/demo-request-form'
import { StatusBadge } from '@shared/ui/status-badge'

export function PricingSection() {
  return (
    <section className="section" id="pricing">
      <div className="page-shell">
        <div className="section-heading" style={{ marginInline: 'auto', textAlign: 'center' }}>
          <p className="section-label">Transparent service architecture</p>
          <h2 className="section-title newsreader">Bespoke Engagement Model</h2>
          <p className="section-copy">
            This is sold as concierge infrastructure: setup fee, monthly maintenance, and custom
            integrations when the workflow needs them.
          </p>
        </div>

        <div className="pricing-grid">
          <div className="pricing-main">
            <div className="pricing-list">
              <article className="pricing-item">
                <div>
                  <h3>Initial template audit</h3>
                  <p>One-time setup for digitizing core document packs and field logic.</p>
                </div>
                <StatusBadge className="pricing-tag" label="Setup fee" variant="info" />
              </article>

              <article className="pricing-item">
                <div>
                  <h3>Monthly engine maintenance</h3>
                  <p>Retainer for updates, template tuning, support, and operational fixes.</p>
                </div>
                <StatusBadge className="pricing-tag" label="Monthly" variant="info" />
              </article>

              <article className="pricing-item">
                <div>
                  <h3>Workflow integration</h3>
                  <p>CRM, signature, ERP, and partner-system connectivity scoped to the client.</p>
                </div>
                <StatusBadge className="pricing-tag" label="Custom" variant="info" />
              </article>
            </div>
          </div>

          <div className="pricing-side">
            <p className="section-label">Initiate protocol</p>
            <h3 className="section-title newsreader" style={{ color: '#fff', fontSize: '2.6rem' }}>
              Request a custom proposal for your firm.
            </h3>
            <p className="support-copy" style={{ margin: '14px 0 28px' }}>
              Use this form as the prototype contact flow. For production, wire it to the channel
              you will actually close deals in.
            </p>
            <DemoRequestForm />
          </div>
        </div>
      </div>
    </section>
  )
}
