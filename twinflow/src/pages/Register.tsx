import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { extractErrorMessage } from '../api/client'
import ErrorBanner from '../components/ErrorBanner'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!role) {
      setError('Please select a role.')
      return
    }
    if (password.length < 12) {
      setError('Password must be at least 12 characters.')
      return
    }
    setError('')
    setBusy(true)
    try {
      await register(fullName, email, password)
      navigate('/')
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={onSubmit}>
        <div className="auth-brand">
          <span className="brand-mark">TF</span>
          <div>
            <h1>Create account</h1>
            <p className="muted">New accounts start with the operator role</p>
          </div>
        </div>
        <ErrorBanner message={error} onDismiss={() => setError('')} />
        <div className="field">
          <label htmlFor="fullName">Full name</label>
          <input
            id="fullName"
            required
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Jane Operator"
          />
        </div>
        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
        </div>
        <div className="field">
          <label htmlFor="role">Role</label>
          <select id="role" required value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="" disabled>
              Select role…
            </option>
            <option value="operator">Operator — floor operations</option>
            <option value="manager" disabled>
              Manager — assigned by an administrator
            </option>
            <option value="admin" disabled>
              Admin — assigned by an administrator
            </option>
          </select>
          <span className="muted">Self-registration always creates an Operator account.</span>
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Min. 12 characters"
          />
        </div>
        <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
          {busy ? 'Creating…' : 'Create account'}
        </button>
        <div className="auth-switch">
          Already registered? <Link to="/login">Sign in</Link>
        </div>
      </form>
    </div>
  )
}
