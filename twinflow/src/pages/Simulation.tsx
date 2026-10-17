import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { simulationApi } from '../api/endpoints'
import type { GenerateResponse, SeedResponse, SimulationStatus } from '../api/types'
import { extractErrorMessage } from '../api/client'
import ErrorBanner from '../components/ErrorBanner'
import PageHeader from '../components/PageHeader'
import Spinner from '../components/Spinner'
import StatCard from '../components/StatCard'
import { formatDateTime } from '../utils/format'

export default function Simulation() {
  const [status, setStatus] = useState<SimulationStatus | null>(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  const [seedScenario, setSeedScenario] = useState('mixed')
  const [includeHistory, setIncludeHistory] = useState(false)
  const [historicalEvents, setHistoricalEvents] = useState(50)
  const [genCount, setGenCount] = useState(20)
  const [genScenario, setGenScenario] = useState('mixed')
  const [stepScenario, setStepScenario] = useState('mixed')

  const load = useCallback(async () => {
    setError('')
    try {
      setStatus(await simulationApi.status())
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const run = async (fn: () => Promise<SeedResponse | GenerateResponse>) => {
    setBusy(true)
    setError('')
    setSuccess('')
    try {
      const result = await fn()
      setSuccess(result.message)
      await load()
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const onSeed = (event: FormEvent) => {
    event.preventDefault()
    void run(() =>
      simulationApi.seed({
        include_historical_events: includeHistory,
        historical_events: includeHistory ? historicalEvents : 0,
        scenario: seedScenario,
      }),
    )
  }

  const onGenerate = (event: FormEvent) => {
    event.preventDefault()
    void run(() => simulationApi.generate({ number_of_events: genCount, scenario: genScenario }))
  }

  const onStep = () => {
    void run(() => simulationApi.step({ scenario: stepScenario }))
  }

  const scenarios = status?.supported_scenarios ?? ['mixed', 'normal', 'congestion', 'bottleneck']

  if (loading) return <Spinner label="Loading simulation status…" />

  return (
    <>
      <PageHeader
        title="Simulation"
        subtitle="Seed aisles and generate synthetic warehouse telemetry"
        actions={
          <button type="button" className="btn" onClick={() => void load()}>
            Refresh
          </button>
        }
      />
      <ErrorBanner message={error} onDismiss={() => setError('')} />
      {success && <div className="success-banner">{success}</div>}

      <div className="grid grid-stats">
        <StatCard label="Seeded aisles" value={status?.seeded_aisles ?? 0} />
        <StatCard label="Active aisles" value={status?.active_aisles ?? 0} tone="info" />
        <StatCard label="Total events" value={status?.total_events ?? 0} tone="success" />
        <StatCard label="Latest event" value={formatDateTime(status?.latest_event_timestamp)} hint={status?.message} />
      </div>

      <div className="grid grid-2">
        <form className="card" onSubmit={onSeed}>
          <div className="card-title">
            <h2>1 · Seed aisles</h2>
          </div>
          <p className="muted" style={{ marginBottom: 12 }}>
            Creates the standard aisle layout. Safe to re-run — existing aisles are skipped.
          </p>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="seedScenario">Scenario</label>
              <select id="seedScenario" value={seedScenario} onChange={(e) => setSeedScenario(e.target.value)}>
                {scenarios.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="histCount">Historical events</label>
              <input
                id="histCount"
                type="number"
                min={0}
                max={1000}
                value={historicalEvents}
                disabled={!includeHistory}
                onChange={(e) => setHistoricalEvents(Number(e.target.value))}
              />
            </div>
            <div className="field">
              <label>Options</label>
              <label className="checkbox-row">
                <input type="checkbox" checked={includeHistory} onChange={(e) => setIncludeHistory(e.target.checked)} />
                Include historical events
              </label>
            </div>
          </div>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={busy}>
              {busy ? 'Working…' : 'Seed simulation'}
            </button>
          </div>
        </form>

        <form className="card" onSubmit={onGenerate}>
          <div className="card-title">
            <h2>2 · Generate events</h2>
          </div>
          <p className="muted" style={{ marginBottom: 12 }}>
            Pushes a batch of synthetic events through the ingestion pipeline (max {status?.max_simulation_events ?? 500}).
          </p>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="genCount">Events</label>
              <input
                id="genCount"
                type="number"
                min={1}
                max={status?.max_simulation_events ?? 500}
                value={genCount}
                onChange={(e) => setGenCount(Number(e.target.value))}
              />
            </div>
            <div className="field">
              <label htmlFor="genScenario">Scenario</label>
              <select id="genScenario" value={genScenario} onChange={(e) => setGenScenario(e.target.value)}>
                {scenarios.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={busy}>
              {busy ? 'Working…' : 'Generate events'}
            </button>
          </div>
        </form>

        <div className="card">
          <div className="card-title">
            <h2>3 · Advance one step</h2>
          </div>
          <p className="muted" style={{ marginBottom: 12 }}>
            Generates one event per active aisle, simulating the next interval of operations.
          </p>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="stepScenario">Scenario</label>
              <select id="stepScenario" value={stepScenario} onChange={(e) => setStepScenario(e.target.value)}>
                {scenarios.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="form-actions">
            <button type="button" className="btn btn-primary" disabled={busy} onClick={onStep}>
              {busy ? 'Working…' : 'Step simulation'}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
