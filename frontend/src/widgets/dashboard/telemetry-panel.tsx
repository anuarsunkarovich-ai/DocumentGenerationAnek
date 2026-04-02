import type { CacheStats, WorkerStatus } from '@shared/api/contracts'

type TelemetryPanelProps = {
  workerStatus: WorkerStatus
  cacheStats: CacheStats
}

export function TelemetryPanel({ workerStatus, cacheStats }: TelemetryPanelProps) {
  const cacheHitRatio = `${Math.round(cacheStats.cache_hit_ratio * 100)}%`

  return (
    <article className="telemetry-card">
      <p className="micro-label" style={{ color: 'rgba(255,255,255,0.54)' }}>
        Primary API engine
      </p>
      <h3 className="newsreader">Fully operational</h3>
      <p>
        Queue depth {workerStatus.queue_depth},{' '}
        {workerStatus.workers.filter((worker) => worker.is_online).length} worker nodes online,
        and cached artifact reuse holding at {cacheHitRatio}.
      </p>

      <div className="telemetry-bars" aria-hidden="true">
        <span style={{ height: '42%' }} />
        <span style={{ height: '58%' }} />
        <span style={{ height: '50%' }} />
        <span style={{ height: '72%' }} />
        <span style={{ height: '86%' }} />
        <span style={{ height: '100%' }} />
      </div>

      <div className="telemetry-stats">
        <div className="telemetry-stat">
          <p className="micro-label" style={{ color: 'rgba(255,255,255,0.54)', margin: 0 }}>
            Worker nodes
          </p>
          <strong>{workerStatus.workers.length}</strong>
        </div>
        <div className="telemetry-stat">
          <p className="micro-label" style={{ color: 'rgba(255,255,255,0.54)', margin: 0 }}>
            Cached artifacts
          </p>
          <strong>{cacheStats.cached_artifacts}</strong>
        </div>
      </div>
    </article>
  )
}
