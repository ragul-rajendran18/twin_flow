import { useState, type FormEvent } from 'react'
import { authApi } from '../api/endpoints'
import { extractErrorMessage } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import Badge from '../components/Badge'
import ErrorBanner from '../components/ErrorBanner'
import PageHeader from '../components/PageHeader'
import { formatDateTime } from '../utils/format'

export default function Profile() {
  const { user, refreshUser } = useAuth()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setSuccess('')
    if (newPassword.length < 12) {
      setError('New password must be at least 12 characters.')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match.')
      return
    }
    setBusy(true)
    try {
      const result = await authApi.changePassword(currentPassword, newPassword)
      setSuccess(result.message)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      await refreshUser()
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader title="Profile" subtitle="Your account details and password" />
      <ErrorBanner message={error} onDismiss={() => setError('')} />
      {success && <div className="success-banner">{success}</div>}

      <div className="grid grid-2">
        <div className="card">
          <h2 style={{ marginBottom: 12 }}>Account</h2>
          <div className="form-grid">
            <div className="field">
              <label>Full name</label>
              <div>{user?.full_name}</div>
            </div>
            <div className="field">
              <label>Email</label>
              <div className="mono">{user?.email}</div>
            </div>
            <div className="field">
              <label>Role</label>
              <div>
                <Badge tone="info">{user?.role}</Badge>
              </div>
            </div>
            <div className="field">
              <label>Status</label>
              <div>
                <Badge tone={user?.is_active ? 'success' : 'danger'}>{user?.is_active ? 'Active' : 'Disabled'}</Badge>
              </div>
            </div>
            <div className="field">
              <label>Member since</label>
              <div className="mono">{formatDateTime(user?.created_at)}</div>
            </div>
          </div>
        </div>

        <form className="card" onSubmit={submit}>
          <h2 style={{ marginBottom: 12 }}>Change password</h2>
          <div className="grid" style={{ gap: 12 }}>
            <div className="field">
              <label htmlFor="current">Current password</label>
              <input
                id="current"
                type="password"
                autoComplete="current-password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="new">New password</label>
              <input
                id="new"
                type="password"
                autoComplete="new-password"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Min. 12 characters"
              />
            </div>
            <div className="field">
              <label htmlFor="confirm">Confirm new password</label>
              <input
                id="confirm"
                type="password"
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
              />
            </div>
          </div>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={busy}>
              {busy ? 'Updating…' : 'Update password'}
            </button>
          </div>
        </form>
      </div>
    </>
  )
}
