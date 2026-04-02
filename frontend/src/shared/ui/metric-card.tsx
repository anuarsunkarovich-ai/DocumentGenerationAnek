type MetricCardProps = {
  value: string
  label: string
  copy: string
}

export function MetricCard({ value, label, copy }: MetricCardProps) {
  return (
    <article className="metric-card">
      <p className="metric-card__value newsreader">{value}</p>
      <p className="metric-card__label">{label}</p>
      <p className="metric-card__copy">{copy}</p>
    </article>
  )
}
