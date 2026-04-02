export function SiteFooter() {
  return (
    <footer className="site-footer" id="security">
      <div className="page-shell site-footer__inner">
        <div>
          <div className="brand newsreader">Protocol</div>
          <p className="support-copy" style={{ color: 'rgba(215, 221, 234, 0.58)', maxWidth: 420 }}>
            The document automation engine for regulated, operations-heavy teams that need speed
            without chaos.
          </p>
          <div className="footer-links">
            <a href="#security">Secure access</a>
            <a href="#security">Audit logs</a>
            <a href="#security">Private deployment</a>
            <a href="/dashboard">API-ready prototype</a>
          </div>
        </div>

        <div className="footer-meta">
          <p className="newsreader" style={{ fontSize: '1.25rem' }}>
            © Protocol Document Engine
          </p>
          <p
            style={{
              color: 'rgba(215, 221, 234, 0.52)',
              fontSize: '12px',
              letterSpacing: '0.2em',
              textTransform: 'uppercase',
            }}
          >
            Astana, Kazakhstan
          </p>
        </div>
      </div>
    </footer>
  )
}
