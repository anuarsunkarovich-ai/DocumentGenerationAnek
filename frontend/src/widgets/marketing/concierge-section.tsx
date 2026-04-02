export function ConciergeSection() {
  return (
    <section className="section concierge" id="concierge">
      <div className="page-shell concierge-grid">
        <div>
          <p className="section-label">The white-glove engine</p>
          <h2 className="section-title newsreader">The Concierge Model.</h2>
          <p className="section-copy">
            Protocol is a document infrastructure partner, not another DIY SaaS panel. We audit
            your templates, map the variables, configure the workflow, and maintain the engine as
            requirements evolve.
          </p>

          <div className="process-grid">
            <article className="process-card">
              <h3>1. Template audit</h3>
              <p>We ingest the legacy document library and identify repeatable logic.</p>
            </article>
            <article className="process-card">
              <h3>2. Field mapping</h3>
              <p>Binding rules are normalized across lease, legal, and onboarding files.</p>
            </article>
            <article className="process-card">
              <h3>3. Workflow config</h3>
              <p>Approvals, conditions, and output formats are tuned to your operations.</p>
            </article>
            <article className="process-card">
              <h3>4. Maintenance</h3>
              <p>New clauses, revised forms, and policy changes are folded into the engine.</p>
            </article>
          </div>
        </div>

        <div className="concierge-visual">
          <div className="concierge-visual__grid" />
          <div className="concierge-visual__card concierge-visual__card--a">
            <h4>Template audit</h4>
            <p>Upload pack inventory, identify variable zones, and classify regulated clauses.</p>
          </div>
          <div className="concierge-visual__card concierge-visual__card--b">
            <h4>Workflow mapping</h4>
            <p>Translate handoffs between legal, sales, compliance, and operations.</p>
          </div>
          <div className="concierge-visual__card concierge-visual__card--c">
            <h4>Ongoing maintenance</h4>
            <p>Roll forward wording, fix drift, and keep output ready for clients and auditors.</p>
          </div>

          <div className="quote-card">
            <p className="newsreader">
              “Protocol transformed our legal desk from a manual bottleneck into a high-speed
              engine.”
            </p>
            <span>Chief legal officer</span>
          </div>
        </div>
      </div>
    </section>
  )
}
