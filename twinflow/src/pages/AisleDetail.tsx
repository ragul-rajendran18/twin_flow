import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { aislesApi } from '../api/endpoints'
import type { AisleStatus, WarehouseEvent } from '../api/types'
import { extractErrorMessage } from '../api/client'
import Badge from '../components/Badge'
import ErrorBanner from '../components/ErrorBanner'
import PageHeader from '../components/PageHeader'
import Pagination from '../components/Pagination'
import Spinner from '../components/Spinner'
import StatCard from '../components/StatCard'
import { formatDateTime, formatNumber, formatPercent } from '../utils/format'

const PAGE_SIZE = 25

export default function AisleDetail() {
  const { aisleId } = useParams()
  const navigate = useNavigate()
  const id = Number(aisleId)
  const [aisle, setAisle] = useState<AisleStatus | null>(null)
  const [events, setEvents] = useState<WarehouseEvent[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setError('')
    try {
      const [status, history] = await Promise.all([
        aislesApi.get(id),
        aislesApi.history(id, { page, page_size: PAGE_SIZE }),
      ])
      setAisle(status)
      setEvents(history.items)
      setTotal(history.total)
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [id, page])

  useEffect(() => {
    void load()
  }, [load])

  if (loading) return <Spinner label="Loading aisle…" />
  if (!aisle) {
    return (
      <>
        <ErrorBanner message={error || 'Aisle not found.'} />
        <button type="button" className="btn" onClick={() => navigate('/aisles')}>
          ← Back to aisles
        </button>
      </>
    )
  }

  return (
    <>
      <PageHeader
        title={`${aisle.aisle_code} · ${aisle.aisle_name}`}
        subtitle={`Zone ${aisle.zone} · capacity ${aisle.capacity} · ${aisle.is_active ? 'active' : 'inactive'}`}
        actions={
          <button type="button" className="btn btn-ghost" onClick={() => navigate('/aisles')}>
            ← All aisles
          </button>
        }
      />
      <ErrorBanner message={error} onDismiss={() => setError('')} />

      <div className="grid grid-stats">
        <StatCard
          label="Occupancy"
          value={formatPercent(aisle.occupancy)}
          tone={aisle.congestion_level === 'HIGH' ? 'danger' : 'info'}
        />
        <StatCard label="AGV count" value={formatNumber(aisle.agv_count)} />
        <StatCard label="Queue length" value={formatNumber(aisle.queue_length)} tone={aisle.queue_length ? 'warning' : 'default'} />
        <StatCard label="Order volume" value={formatNumber(aisle.order_volume)} />
        <StatCard label="Conveyor load" value={formatPercent(aisle.conveyor_load)} />
        <StatCard
          label="Congestion"
          value={aisle.congestion_level ?? '—'}
          tone={aisle.congestion_level === 'HIGH' ? 'danger' : aisle.congestion_level === 'MODERATE' ? 'warning' : 'success'}
          hint={`updated ${formatDateTime(aisle.latest_event_timestamp)}`}
        />
      </div>

      <div className="card">
        <div className="card-title">
          <h2>Event history</h2>
          <span className="muted">most recent first</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Occupancy</th>
                <th>AGVs</th>
                <th>Queue</th>
                <th>Orders</th>
                <th>Conveyor</th>
                <th>Source</th>
                <th>Event ID</th>
              </tr>
            </thead>
            <tbody>
              {events.length === 0 && (
                <tr>
                  <td colSpan={8}>
                    <div className="empty-state">No events recorded for this aisle.</div>
                  </td>
                </tr>
              )}
              {events.map((event) => (
                <tr key={event.id}>
                  <td className="mono">{formatDateTime(event.event_timestamp)}</td>
                  <td>{formatPercent(event.occupancy)}</td>
                  <td>{event.agv_count}</td>
                  <td>{event.queue_length}</td>
                  <td>{event.order_volume}</td>
                  <td>{formatPercent(event.conveyor_load)}</td>
                  <td>
                    <Badge tone="info">{event.source}</Badge>
                  </td>
                  <td className="mono">{event.event_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPage={setPage} />
      </div>
    </>
  )
}
