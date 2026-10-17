import { useCallback, useEffect, useState } from 'react'
import { predictionsApi } from '../api/endpoints'
import type { Prediction, PredictionDetail } from '../api/types'
import { extractErrorMessage } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import Badge, { toneForLevel } from '../components/Badge'
import ErrorBanner from '../components/ErrorBanner'
import PageHeader from '../components/PageHeader'
import Pagination from '../components/Pagination'
import Spinner from '../components/Spinner'
import { formatDateTime, formatNumber, formatPercent } from '../utils/format'

const PAGE_SIZE = 25

export default function Predictions() {
  const { canOperate } = useAuth()
  const [tab, setTab] = useState<'latest' | 'history'>('latest')
  const [latest, setLatest] = useState<PredictionDetail[]>([])
  const [history, setHistory] = useState<Prediction[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [levelFilter, setLevelFilter] = useState('')
  const [aisleFilter, setAisleFilter] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      if (tab === 'latest') {
        const data = await predictionsApi.latest({
          congestion_level: levelFilter || undefined,
          aisle_code: aisleFilter || undefined,
        })
        setLatest(data)
      } else {
        const data = await predictionsApi.history({
          page,
          page_size: PAGE_SIZE,
          congestion_level: levelFilter || undefined,
          aisle_code: aisleFilter || undefined,
        })
        setHistory(data.items)
        setTotal(data.total)
      }
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [tab, page, levelFilter, aisleFilter])

  useEffect(() => {
    void load()
  }, [load])

  const runPredictions = async () => {
    setRunning(true)
    setError('')
    setSuccess('')
    try {
      const result = await predictionsApi.run(aisleFilter || undefined)
      setSuccess(
        `Model ${result.model_version}: ${result.predictions_created} prediction(s), ${result.alerts_created} alert(s) created, ${result.alerts_updated} updated.`,
      )
      await load()
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setRunning(false)
    }
  }

  return (
    <>
      <PageHeader
        title="Predictions"
        subtitle="ML congestion forecasts and bottleneck recommendations"
        actions={
          canOperate && (
            <button type="button" className="btn btn-primary" disabled={running} onClick={() => void runPredictions()}>
              {running ? 'Running…' : 'Run predictions'}
            </button>
          )
        }
      />
      <ErrorBanner message={error} onDismiss={() => setError('')} />
      {success && <div className="success-banner">{success}</div>}

      <div className="card">
        <div className="tabs">
          <button type="button" className={`tab${tab === 'latest' ? ' active' : ''}`} onClick={() => { setTab('latest'); setPage(1) }}>
            Latest per aisle
          </button>
          <button type="button" className={`tab${tab === 'history' ? ' active' : ''}`} onClick={() => { setTab('history'); setPage(1) }}>
            History
          </button>
        </div>

        <div className="filters" style={{ margin: '12px 0 14px' }}>
          <div className="field">
            <label htmlFor="level">Congestion level</label>
            <select id="level" value={levelFilter} onChange={(e) => { setPage(1); setLevelFilter(e.target.value) }}>
              <option value="">All</option>
              <option value="NORMAL">Normal</option>
              <option value="MODERATE">Moderate</option>
              <option value="HIGH">High</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="aisle">Aisle code</label>
            <input id="aisle" value={aisleFilter} onChange={(e) => { setPage(1); setAisleFilter(e.target.value) }} placeholder="A-01" />
          </div>
          <button type="button" className="btn" onClick={() => void load()}>
            Apply
          </button>
        </div>

        {loading ? (
          <Spinner />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Aisle</th>
                  <th>Congestion</th>
                  <th>Probability</th>
                  <th>Predicted queue</th>
                  <th>Delay</th>
                  <th>Bottleneck</th>
                  <th>Recommendation</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {tab === 'latest' && latest.length === 0 && (
                  <tr><td colSpan={8}><div className="empty-state">No predictions. Run the prediction engine or seed the simulation first.</div></td></tr>
                )}
                {tab === 'history' && history.length === 0 && (
                  <tr><td colSpan={8}><div className="empty-state">No prediction history.</div></td></tr>
                )}
                {tab === 'latest' &&
                  latest.map((p) => (
                    <tr key={p.prediction_id}>
                      <td>{p.aisle_code ?? `#${p.aisle_id}`}</td>
                      <td><Badge tone={toneForLevel(p.congestion_level)}>{p.congestion_level}</Badge></td>
                      <td>{formatPercent(p.congestion_probability * 100)}</td>
                      <td>{formatNumber(p.predicted_queue_length, 1)}</td>
                      <td>{formatNumber(p.predicted_delay_minutes, 1)} min</td>
                      <td>{p.bottleneck_detected ? <Badge tone="danger">Yes</Badge> : <span className="muted">No</span>}</td>
                      <td className="recommendation">{p.recommendation}</td>
                      <td className="mono">{formatDateTime(p.created_at)}</td>
                    </tr>
                  ))}
                {tab === 'history' &&
                  history.map((p) => (
                    <tr key={p.prediction_id}>
                      <td>#{p.aisle_id}</td>
                      <td><Badge tone={toneForLevel(p.congestion_level)}>{p.congestion_level}</Badge></td>
                      <td>{formatPercent(p.congestion_probability * 100)}</td>
                      <td>{formatNumber(p.predicted_queue_length, 1)}</td>
                      <td>{formatNumber(p.predicted_delay_minutes, 1)} min</td>
                      <td>{p.bottleneck_detected ? <Badge tone="danger">Yes</Badge> : <span className="muted">No</span>}</td>
                      <td className="recommendation">{p.recommendation}</td>
                      <td className="mono">{formatDateTime(p.created_at)}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
        {tab === 'history' && <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPage={setPage} />}
      </div>
    </>
  )
}
