import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { alertsApi, predictionsApi, warehouseApi } from '../api/endpoints'
import type { AisleStatus, Alert, PredictionDetail, WarehouseOverview } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import Badge, { toneForLevel } from '../components/Badge'
import ErrorBanner from '../components/ErrorBanner'
import PageHeader from '../components/PageHeader'
import Spinner from '../components/Spinner'
import StatCard from '../components/StatCard'
import { extractErrorMessage } from '../api/client'
import { formatDateTime, formatNumber, formatPercent } from '../utils/format'

export default function Dashboard() {
  const { canOperate } = useAuth()
  const navigate = useNavigate()
  const [overview, setOverview] = useState<WarehouseOverview | null>(null)
  const [aisles, setAisles] = useState<AisleStatus[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [predictions, setPredictions] = useState<PredictionDetail[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date())

  const load = useCallback(async () => {
    setError('')
    try {
      const [ov, al, ac, pr] = await Promise.all([
        warehouseApi.overview(),
        warehouseApi.aisles(),
        alertsApi.active(),
        predictionsApi.latest(),
      ])
      setOverview(ov)
      setAisles(al)
      setAlerts(ac)
      setPredictions(pr)
      setLastRefresh(new Date())
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
    const timer = window.setInterval(() => void load(), 30000)
    return () => window.clearInterval(timer)
  }, [load])

  if (loading) return <Spinner label="Loading warehouse overview…" />

  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle={`Live congestion overview · refreshed ${lastRefresh.toLocaleTimeString()}`}
        actions={
          <>
            <button type="button" className="btn" onClick={() => void load()}>
              Refresh
            </button>
            {canOperate && (
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => void predictionsApi.run().then(load).catch((e) => setError(extractErrorMessage(e)))}
              >
                Run predictions
              </button>
            )}
          </>
        }
      />
      <ErrorBanner message={error} onDismiss={() => setError('')} />

      <div className="grid grid-stats">
        <StatCard label="Total aisles" value={overview?.total_aisles ?? 0} hint={`${overview?.active_aisles ?? 0} active`} />
        <StatCard label="Normal" value={overview?.normal_aisles ?? 0} tone="success" />
        <StatCard label="Moderate" value={overview?.moderate_aisles ?? 0} tone="warning" />
        <StatCard label="High congestion" value={overview?.high_congestion_aisles ?? 0} tone="danger" />
        <StatCard label="Active alerts" value={overview?.active_alerts ?? 0} tone="danger" />
        <StatCard label="Avg occupancy" value={formatPercent(overview?.average_occupancy)} tone="info" />
        <StatCard label="AGVs in motion" value={overview?.total_agvs ?? 0} tone="info" />
        <StatCard label="Total queue" value={overview?.total_queue_length ?? 0} tone="info" />
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-title">
            <h2>Aisle status</h2>
            <span className="muted">latest event per aisle</span>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Aisle</th>
                  <th>Zone</th>
                  <th>Occupancy</th>
                  <th>AGVs</th>
                  <th>Queue</th>
                  <th>Congestion</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {aisles.length === 0 && (
                  <tr>
                    <td colSpan={7}>
                      <div className="empty-state">No aisles yet — seed the simulation to get started.</div>
                    </td>
                  </tr>
                )}
                {aisles.map((aisle) => (
                  <tr key={aisle.id} onClick={() => navigate(`/aisles/${aisle.id}`)}>
                    <td className="row-link">
                      {aisle.aisle_code}
                      <div className="muted">{aisle.aisle_name}</div>
                    </td>
                    <td>{aisle.zone}</td>
                    <td>
                      {formatPercent(aisle.occupancy)}
                      <div className="progress-bar">
                        <span
                          className={`meter-${toneForLevel(aisle.congestion_level)}`}
                          style={{ width: `${Math.min(100, aisle.occupancy ?? 0)}%` }}
                        />
                      </div>
                    </td>
                    <td>{formatNumber(aisle.agv_count)}</td>
                    <td>{formatNumber(aisle.queue_length)}</td>
                    <td>
                      {aisle.congestion_level ? (
                        <Badge tone={toneForLevel(aisle.congestion_level)}>{aisle.congestion_level}</Badge>
                      ) : (
                        <span className="muted">no prediction</span>
                      )}
                    </td>
                    <td className="mono">{formatDateTime(aisle.latest_event_timestamp)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="card-title">
            <h2>Active alerts</h2>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => navigate('/alerts')}>
              View all
            </button>
          </div>
          {alerts.length === 0 && <div className="empty-state">No active alerts. All clear.</div>}
          <div className="grid" style={{ gap: 10 }}>
            {alerts.slice(0, 8).map((alert) => (
              <div key={alert.id} className="card" style={{ padding: '10px 12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
                  <div>
                    <Badge tone={alert.severity === 'HIGH' ? 'high' : alert.severity === 'MEDIUM' ? 'moderate' : 'warning'}>
                      {alert.severity}
                    </Badge>{' '}
                    <strong>{alert.alert_type}</strong>
                    <div className="muted">{alert.message}</div>
                  </div>
                  <span className="mono">{formatDateTime(alert.created_at)}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="card-title" style={{ marginTop: 18 }}>
            <h2>Latest predictions</h2>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => navigate('/predictions')}>
              View all
            </button>
          </div>
          {predictions.length === 0 && <div className="empty-state">No predictions yet.</div>}
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Aisle</th>
                  <th>Congestion</th>
                  <th>Probability</th>
                  <th>Delay</th>
                  <th>Bottleneck</th>
                </tr>
              </thead>
              <tbody>
                {predictions.slice(0, 8).map((p) => (
                  <tr key={p.prediction_id}>
                    <td>{p.aisle_code ?? p.aisle_id}</td>
                    <td>
                      <Badge tone={toneForLevel(p.congestion_level)}>{p.congestion_level}</Badge>
                    </td>
                    <td>{formatPercent(p.congestion_probability * 100)}</td>
                    <td>{formatNumber(p.predicted_delay_minutes, 1)} min</td>
                    <td>
                      {p.bottleneck_detected ? <Badge tone="danger">Yes</Badge> : <span className="muted">No</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  )
}
