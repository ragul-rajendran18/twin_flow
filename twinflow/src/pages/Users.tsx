import { useCallback, useEffect, useState } from 'react'
import { usersApi } from '../api/endpoints'
import type { User, UserRole } from '../api/types'
import { extractErrorMessage } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import Badge from '../components/Badge'
import ErrorBanner from '../components/ErrorBanner'
import PageHeader from '../components/PageHeader'
import Pagination from '../components/Pagination'
import Spinner from '../components/Spinner'
import { formatDateTime } from '../utils/format'

const PAGE_SIZE = 20
const ROLES: UserRole[] = ['admin', 'manager', 'operator']

export default function Users() {
  const { user: me } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [editId, setEditId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [editEmail, setEditEmail] = useState('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await usersApi.list({ page, page_size: PAGE_SIZE })
      setUsers(data.items)
      setTotal(data.total)
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => {
    void load()
  }, [load])

  const changeRole = async (user: User, role: UserRole) => {
    setBusyId(user.id)
    setError('')
    setSuccess('')
    try {
      await usersApi.setRole(user.id, role)
      setSuccess(`${user.full_name} is now ${role}.`)
      await load()
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setBusyId(null)
    }
  }

  const toggleStatus = async (user: User) => {
    setBusyId(user.id)
    setError('')
    setSuccess('')
    try {
      await usersApi.setStatus(user.id, !user.is_active)
      setSuccess(`${user.full_name} ${user.is_active ? 'deactivated' : 'activated'}.`)
      await load()
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setBusyId(null)
    }
  }

  const saveProfile = async (event: { preventDefault: () => void }) => {
    event.preventDefault()
    if (editId === null) return
    setSaving(true)
    setError('')
    setSuccess('')
    try {
      await usersApi.update(editId, { full_name: editName, email: editEmail })
      setSuccess('User updated.')
      setEditId(null)
      await load()
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <PageHeader title="Users" subtitle="Administrator-only account management" />
      <ErrorBanner message={error} onDismiss={() => setError('')} />
      {success && <div className="success-banner">{success}</div>}

      <div className="card">
        {loading ? (
          <Spinner />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td className="mono">{user.id}</td>
                    <td>
                      {editId === user.id ? (
                        <input value={editName} onChange={(e) => setEditName(e.target.value)} />
                      ) : (
                        user.full_name
                      )}
                      {me?.id === user.id && <span className="muted"> (you)</span>}
                    </td>
                    <td>
                      {editId === user.id ? (
                        <input type="email" value={editEmail} onChange={(e) => setEditEmail(e.target.value)} />
                      ) : (
                        <span className="mono">{user.email}</span>
                      )}
                    </td>
                    <td>
                      <select
                        value={user.role}
                        disabled={busyId === user.id}
                        onChange={(e) => void changeRole(user, e.target.value as UserRole)}
                      >
                        {ROLES.map((role) => (
                          <option key={role} value={role}>{role}</option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <Badge tone={user.is_active ? 'success' : 'danger'}>{user.is_active ? 'Active' : 'Disabled'}</Badge>
                    </td>
                    <td className="mono">{formatDateTime(user.created_at)}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 6 }}>
                        {editId === user.id ? (
                          <>
                            <button type="button" className="btn btn-sm btn-primary" disabled={saving} onClick={(e) => void saveProfile(e)}>
                              {saving ? 'Saving…' : 'Save'}
                            </button>
                            <button type="button" className="btn btn-sm btn-ghost" onClick={() => setEditId(null)}>
                              Cancel
                            </button>
                          </>
                        ) : (
                          <>
                            <button
                              type="button"
                              className="btn btn-sm"
                              onClick={() => {
                                setEditId(user.id)
                                setEditName(user.full_name)
                                setEditEmail(user.email)
                              }}
                            >
                              Edit
                            </button>
                            <button
                              type="button"
                              className="btn btn-sm btn-danger"
                              disabled={busyId === user.id || me?.id === user.id}
                              onClick={() => void toggleStatus(user)}
                            >
                              {user.is_active ? 'Disable' : 'Enable'}
                            </button>
                          </>
                        )}
                      </div>
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
