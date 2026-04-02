import { ButtonLink } from '@shared/ui/button'

export function SiteHeader() {
  return (
    <header className="site-header">
      <div className="page-shell site-header__inner">
        <a className="brand newsreader" href="#top">
          Protocol
        </a>

        <nav className="nav-links" aria-label="Primary">
          <a href="#solutions">Solutions</a>
          <a href="#concierge">The Concierge</a>
          <a href="#pricing">Pricing</a>
          <a href="#security">Security</a>
        </nav>

        <div className="header-actions">
          <ButtonLink to="/dashboard" variant="ghost">
            Dashboard
          </ButtonLink>
          <a className="button button-primary" href="#pricing">
            Book a Demo
          </a>
        </div>
      </div>
    </header>
  )
}
