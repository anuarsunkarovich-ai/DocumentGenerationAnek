import { ArrowRight } from 'lucide-react'

import type { Template } from '@shared/api/contracts'
import { StatusBadge } from '@shared/ui/status-badge'

type TemplateLibraryCardProps = {
  template: Template
}

export function TemplateLibraryCard({ template }: TemplateLibraryCardProps) {
  return (
    <article className="template-card">
      <div className="template-card__visual" />
      <div className="row-between">
        <StatusBadge label={template.current_version?.version ?? 'Draft'} variant="info" />
        <ArrowRight size={16} />
      </div>
      <div>
        <h3 className="newsreader" style={{ margin: '0 0 10px', fontSize: '1.5rem' }}>
          {template.name}
        </h3>
        <p className="support-copy">{template.description ?? 'No description available yet.'}</p>
      </div>
    </article>
  )
}
