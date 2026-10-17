import { useCallback, useEffect, useState } from 'react'
import { alertsApi } from '../api/endpoints'
import type { Alert } from '../api/types'
import { extractErrorMessage } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import Badge from '../components/Badge'
import ErrorBanner from '../components/ErrorBanner'
import PageHeader from '../components/PageHeader'
import Pagination from '../components/Pagination'
import Spinner from '../components/Spinner'
import { formatDateTime } from '../utils/format'

const PAGE_SIZE = 25

function severityTone(severity: string): 'high' | 'moderate' | 'warning' {
  if (severity === 'HIGH') return 'high'
  if (severity === 'MEDIUM') return 'moderate'
  return 'warning'
}

export default function Alerts() {
  const { canOperate } = useAuth()
  const [tab, setTab] = useState<'active' | 'all'>('active')
  const [active, setActive] = useState<Alert[]>([])
  const [all, setAll] = useState<Alert[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [severityFilter, setSeverityFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(true)
  const [resolvingId, setResolvingId] = useState<number | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      if (tab === 'active') {
        setActive(await alertsApi.active())
      } else {
        const data = await alertsApi.list({
          page,
          page_size: PAGE_SIZE,
          status: statusFilter || undefined,
          severity: severityFilter || undefined,
          alert_type: typeFilter || undefined,
        })
        setAll(data.items)
        setTotal(data.total)
      }
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [tab, page, statusFilter, severityFilter, typeFilter])

  useEffect(() => {
    void load()
  }, [load])

  const resolve = async (alert: Alert) => {
    setResolvingId(alert.id)
    setError('')
    setSuccess('')
    try {
      const result = await alertsApi.resolve(alert.id)
      setSuccess(result.message)
      await load()
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setResolvingId(null)
    }
  }

  const rows = tab === 'active' ? active : all

  return (
    <>
      <PageHeader
        title="Alerts"
        subtitle="Congestion and bottleneck alerts raised by the prediction engine"
        actions={
          <button type="button" className="btn" onClick={() => void load()}>
            Refresh
          </button>
        }
      />
      <ErrorBanner message={error} onDismiss={() => setError('')} />
      {success && <div className="success-banner">{success}</div>}

      <div className="card">
        <div className="tabs">
          <button type="button" className={`tab${tab === 'active' ? ' active' : ''}`} onClick={() => setTab('active')}>
            Active ({active.length})
          </button>
          <button type="button" className={`tab${tab === 'all' ? ' active' : ''}`} onClick={() => { setTab('all'); setPage(1) }}>
            All
          </button>
        </div>

        {tab === 'all' && (
          <div className="filters" style={{ margin: '12px 0 14px' }}>
            <div className="field">
              <label htmlFor="status">Status</label>
              <select id="status" value={statusFilter} onChange={(e) => { setPage(1); setStatusFilter(e.target.value) }}>
                <option value="">All</option>
                <option value="ACTIVE">Active</option>
                <option value="RESOLVED">Resolved</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="severity">Severity</label>
              <select id="severity" value={severityFilter} onChange={(e) => { setPage(1); setSeverityFilter(e.target.value) }}>
                <option value="">All</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="type">Type</label>
              <input id="type" value={typeFilter} onChange={(e) => { setPage(1); setTypeFilter(e.target.value) }} placeholder="CONGESTION" />
            </div>
          </div>
        )}

        {loading ? (
          <Spinner />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Type</th>
                  <th>Message</th>
                  <th>Aisle</th>
                  <th>Status</th>
                  <th>Created</th>
                  {canOperate && <th></th>}
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={canOperate ? 7 : 6}>
                      <div className="empty-state">
                        {tab === 'active' ? 'No active alerts.' : 'No alerts match the current filters.'}
                      </div>
                    </td>
                  </tr>
                )}
                {rows.map((alert) => (
                  <tr key={alert.id}>
                    <td>
                      <Badge tone={severityTone(alert.severity)}>{alert.severity}</Badge>
                    </td>
                    <td>{alert.alert_type}</td>
                    <td>{alert.message}</td>
                    <td className="mono">#{alert.aisle_id}</td>
                    <td>
                      <Badge tone={alert.status === 'ACTIVE' ? 'danger' : 'success'}>{alert.status}</Badge>
                    </td>
                    <td className="mono">{formatDateTime(alert.created_at)}</td>
                    {canOperate && (
                      <td>
                        {alert.status === 'ACTIVE' && (
                          <button
                            type="button"
                            className="btn btn-sm"
                            disabled={resolvingId === alert.id}
                            onClick={() => void resolve(alert)}
                          >
                            {resolvingId === alert.id ? 'Resolving…' : 'Resolve'}
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {tab === 'all' && <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPage={setPage} />}
      </div>
    </>
  )
}
