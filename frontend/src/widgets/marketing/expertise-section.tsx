const domains = [
  {
    visualLabel: 'Property transactions',
    visualTitle: 'Real estate protocol layer',
    title: 'Real Estate Agencies',
    items: ['Sale & purchase agreements', 'Lease contracts', 'Property transfer acts'],
  },
  {
    visualLabel: 'Certified workflows',
    visualTitle: 'Notarial document desk',
    title: 'Notaries & Legal Admin',
    items: ['Power of attorney', 'Certified copies & deeds', 'Rigorous audit trails'],
  },
  {
    visualLabel: 'Back-office operations',
    visualTitle: 'HR onboarding engine',
    title: 'HR & Operations',
    items: ['Employment agreements', 'Onboarding packs', 'Internal compliance forms'],
  },
] as const

export function ExpertiseSection() {
  return (
    <section className="section">
      <div className="page-shell">
        <div className="section-heading" style={{ marginInline: 'auto', textAlign: 'center' }}>
          <p className="section-label">Industry-specific protocol layers</p>
          <h2 className="section-title newsreader">Vertical Domain Expertise</h2>
        </div>

        <div className="expertise-grid">
          {domains.map((domain) => (
            <article className="domain-card" key={domain.title}>
              <div className="domain-visual">
                <div className="domain-visual__content">
                  <span className="domain-visual__eyebrow">{domain.visualLabel}</span>
                  <h3 className="domain-visual__title newsreader">{domain.visualTitle}</h3>
                </div>
              </div>
              <h3 className="newsreader">{domain.title}</h3>
              <ul className="domain-list">
                {domain.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}
