import { useCallback, useEffect, useState } from 'react'
import { warehouseApi } from '../api/endpoints'
import type { WarehouseEvent } from '../api/types'
import { extractErrorMessage } from '../api/client'
import Badge from '../components/Badge'
import ErrorBanner from '../components/ErrorBanner'
import PageHeader from '../components/PageHeader'
import Pagination from '../components/Pagination'
import Spinner from '../components/Spinner'
import { formatDateTime, formatPercent } from '../utils/format'

const PAGE_SIZE = 25

export default function Events() {
  const [events, setEvents] = useState<WarehouseEvent[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [aisleCode, setAisleCode] = useState('')
  const [source, setSource] = useState('')
  const [startTime, setStartTime] = useState('')
  const [endTime, setEndTime] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await warehouseApi.events({
        page,
        page_size: PAGE_SIZE,
        aisle_code: aisleCode || undefined,
        source: source || undefined,
        start_time: startTime ? new Date(startTime).toISOString() : undefined,
        end_time: endTime ? new Date(endTime).toISOString() : undefined,
      })
      setEvents(data.items)
      setTotal(data.total)
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [page, aisleCode, source, startTime, endTime])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <>
      <PageHeader
        title="Warehouse events"
        subtitle="Raw telemetry ingested from AGVs, conveyors and scanners"
        actions={
          <button type="button" className="btn" onClick={() => void load()}>
            Refresh
          </button>
        }
      />
      <ErrorBanner message={error} onDismiss={() => setError('')} />

      <div className="card">
        <div className="filters" style={{ marginBottom: 14 }}>
          <div className="field">
            <label htmlFor="aisleCode">Aisle code</label>
            <input
              id="aisleCode"
              value={aisleCode}
              onChange={(e) => { setPage(1); setAisleCode(e.target.value) }}
              placeholder="A-01"
            />
          </div>
          <div className="field">
            <label htmlFor="source">Source</label>
            <input
              id="source"
              value={source}
              onChange={(e) => { setPage(1); setSource(e.target.value) }}
              placeholder="simulation"
            />
          </div>
          <div className="field">
            <label htmlFor="start">From</label>
            <input id="start" type="datetime-local" value={startTime} onChange={(e) => { setPage(1); setStartTime(e.target.value) }} />
          </div>
          <div className="field">
            <label htmlFor="end">To</label>
            <input id="end" type="datetime-local" value={endTime} onChange={(e) => { setPage(1); setEndTime(e.target.value) }} />
          </div>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => {
              setPage(1)
              setAisleCode('')
              setSource('')
              setStartTime('')
              setEndTime('')
            }}
          >
            Clear
          </button>
        </div>

        {loading ? (
          <Spinner />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Aisle</th>
                  <th>Occupancy</th>
                  <th>AGVs</th>
                  <th>Queue</th>
                  <th>Orders</th>
                  <th>Conveyor</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {events.length === 0 && (
                  <tr>
                    <td colSpan={8}>
                      <div className="empty-state">No events match the current filters.</div>
                    </td>
                  </tr>
                )}
                {events.map((event) => (
                  <tr key={event.id}>
                    <td className="mono">{formatDateTime(event.event_timestamp)}</td>
                    <td className="mono">aisle #{event.aisle_id}</td>
                    <td>{formatPercent(event.occupancy)}</td>
                    <td>{event.agv_count}</td>
                    <td>{event.queue_length}</td>
                    <td>{event.order_volume}</td>
                    <td>{formatPercent(event.conveyor_load)}</td>
                    <td>
                      <Badge tone="info">{event.source}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPage={setPage} />
      </div>
    </>
  )
}
