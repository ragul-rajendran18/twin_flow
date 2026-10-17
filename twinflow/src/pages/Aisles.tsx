import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { aislesApi } from '../api/endpoints'
import type { Aisle } from '../api/types'
import { extractErrorMessage } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import Badge, { toneForLevel } from '../components/Badge'
import ErrorBanner from '../components/ErrorBanner'
import PageHeader from '../components/PageHeader'
import Pagination from '../components/Pagination'
import Spinner from '../components/Spinner'
import { formatDateTime } from '../utils/format'

const PAGE_SIZE = 20

interface FormState {
  aisle_code: string
  aisle_name: string
  capacity: number
  zone: string
  is_active: boolean
}

const EMPTY_FORM: FormState = { aisle_code: '', aisle_name: '', capacity: 100, zone: '', is_active: true }

export default function Aisles() {
  const { isAdmin, canOperate } = useAuth()
  const navigate = useNavigate()
  const [aisles, setAisles] = useState<Aisle[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [zone, setZone] = useState('')
  const [activeFilter, setActiveFilter] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState<FormState | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await aislesApi.list({
        page,
        page_size: PAGE_SIZE,
        zone: zone || undefined,
        is_active: activeFilter === '' ? undefined : activeFilter === 'true',
      })
      setAisles(data.items)
      setTotal(data.total)
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [page, zone, activeFilter])

  useEffect(() => {
    void load()
  }, [load])

  const openCreate = () => {
    setEditingId(null)
    setForm({ ...EMPTY_FORM })
  }

  const openEdit = (aisle: Aisle) => {
    setEditingId(aisle.id)
    setForm({
      aisle_code: aisle.aisle_code,
      aisle_name: aisle.aisle_name,
      capacity: aisle.capacity,
      zone: aisle.zone,
      is_active: aisle.is_active,
    })
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!form) return
    setSaving(true)
    setError('')
    setSuccess('')
    try {
      if (editingId === null) {
        const created = await aislesApi.create(form)
        setSuccess(`Aisle ${created.aisle_code} created.`)
      } else {
        const { aisle_code: _code, ...update } = form
        const updated = await aislesApi.update(editingId, update)
        setSuccess(`Aisle ${updated.aisle_code} updated.`)
      }
      setForm(null)
      setEditingId(null)
      await load()
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <PageHeader
        title="Aisles"
        subtitle="Manage warehouse aisles and review operational capacity"
        actions={
          isAdmin ? (
            <button type="button" className="btn btn-primary" onClick={openCreate}>
              New aisle
            </button>
          ) : (
            <span className="muted">Administrator access required to create or edit aisles</span>
          )
        }
      />
      <ErrorBanner message={error} onDismiss={() => setError('')} />
      {success && <div className="success-banner">{success}</div>}

      {form && (
        <form className="card" onSubmit={submit}>
          <h2 style={{ marginBottom: 12 }}>{editingId === null ? 'Create aisle' : 'Edit aisle'}</h2>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="aisle_code">Code</label>
              <input
                id="aisle_code"
                required
                minLength={3}
                maxLength={50}
                disabled={editingId !== null}
                value={form.aisle_code}
                onChange={(e) => setForm({ ...form, aisle_code: e.target.value })}
                placeholder="A-01"
              />
            </div>
            <div className="field">
              <label htmlFor="aisle_name">Name</label>
              <input
                id="aisle_name"
                required
                minLength={3}
                maxLength={150}
                value={form.aisle_name}
                onChange={(e) => setForm({ ...form, aisle_name: e.target.value })}
                placeholder="Aisle A-01"
              />
            </div>
            <div className="field">
              <label htmlFor="capacity">Capacity</label>
              <input
                id="capacity"
                type="number"
                min={1}
                required
                value={form.capacity}
                onChange={(e) => setForm({ ...form, capacity: Number(e.target.value) })}
              />
            </div>
            <div className="field">
              <label htmlFor="zone">Zone</label>
              <input
                id="zone"
                required
                maxLength={50}
                value={form.zone}
                onChange={(e) => setForm({ ...form, zone: e.target.value })}
                placeholder="Inbound"
              />
            </div>
            <div className="field">
              <label>Status</label>
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                />
                Active
              </label>
            </div>
          </div>
          <div className="form-actions">
            <button type="button" className="btn btn-ghost" onClick={() => setForm(null)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving…' : 'Save aisle'}
            </button>
          </div>
        </form>
      )}

      <div className="card">
        <div className="filters" style={{ marginBottom: 14 }}>
          <div className="field">
            <label htmlFor="zoneFilter">Zone</label>
            <input id="zoneFilter" value={zone} onChange={(e) => { setPage(1); setZone(e.target.value) }} placeholder="All zones" />
          </div>
          <div className="field">
            <label htmlFor="activeFilter">Active</label>
            <select
              id="activeFilter"
              value={activeFilter}
              onChange={(e) => { setPage(1); setActiveFilter(e.target.value) }}
            >
              <option value="">All</option>
              <option value="true">Active only</option>
              <option value="false">Inactive only</option>
            </select>
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
                  <th>Code</th>
                  <th>Name</th>
                  <th>Zone</th>
                  <th>Capacity</th>
                  <th>Active</th>
                  <th>Created</th>
                  {isAdmin && <th></th>}
                </tr>
              </thead>
              <tbody>
                {aisles.length === 0 && (
                  <tr>
                    <td colSpan={isAdmin ? 7 : 6}>
                      <div className="empty-state">No aisles found.</div>
                    </td>
                  </tr>
                )}
                {aisles.map((aisle) => (
                  <tr key={aisle.id}>
                    <td className="row-link" onClick={() => navigate(`/aisles/${aisle.id}`)}>
                      {aisle.aisle_code}
                    </td>
                    <td>{aisle.aisle_name}</td>
                    <td>{aisle.zone}</td>
                    <td>{aisle.capacity}</td>
                    <td>
                      <Badge tone={aisle.is_active ? toneForLevel('normal') : 'muted'}>
                        {aisle.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </td>
                    <td className="mono">{formatDateTime(aisle.created_at)}</td>
                    {isAdmin && (
                      <td>
                        <button type="button" className="btn btn-sm" onClick={() => openEdit(aisle)}>
                          Edit
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPage={setPage} />
        {!canOperate && <p className="muted" style={{ marginTop: 8 }}>Read-only view for your role.</p>}
      </div>
    </>
  )
}
