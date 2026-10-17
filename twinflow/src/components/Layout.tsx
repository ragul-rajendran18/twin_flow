import { useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { healthApi } from '../api/endpoints'

const NAV = [
  { to: '/', label: 'Dashboard', icon: '▦', end: true },
  { to: '/aisles', label: 'Aisles', icon: '☰' },
  { to: '/events', label: 'Events', icon: '↯' },
  { to: '/predictions', label: 'Predictions', icon: '◈' },
  { to: '/alerts', label: 'Alerts', icon: '⚠' },
  { to: '/simulation', label: 'Simulation', icon: '⟳', roles: ['admin', 'manager'] },
  { to: '/users', label: 'Users', icon: '☰', roles: ['admin'] },
  { to: '/profile', label: 'Profile', icon: '●' },
]

export default function Layout() {
  const { user, logout, isAdmin, canOperate } = useAuth()
  const navigate = useNavigate()
  const [backend, setBackend] = useState<'checking' | 'online' | 'offline'>('checking')

  useEffect(() => {
    let cancelled = false
    healthApi
      .check()
      .then(() => !cancelled && setBackend('online'))
      .catch(() => !cancelled && setBackend('offline'))
    return () => {
      cancelled = true
    }
  }, [])

  const visibleNav = NAV.filter((item) => {
    if (!item.roles) return true
    if (item.roles.includes('admin')) return isAdmin
    if (item.roles.includes('manager')) return canOperate || isAdmin
    return true
  })

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">TF</span>
          <div>
            <div className="brand-name">TwinFlow</div>
            <div className="brand-sub">Warehouse Twin</div>
          </div>
        </div>
        <nav className="nav">
          {visibleNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className={`backend-dot backend-${backend}`} />
          <span className="muted">{backend === 'online' ? 'API online' : backend === 'offline' ? 'API offline' : 'Checking API…'}</span>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <div className="topbar-title">Smart Warehouse Congestion Control</div>
          <div className="topbar-user">
            <div className="user-meta">
              <div className="user-name">{user?.full_name}</div>
              <div className="user-role">{user?.role}</div>
            </div>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => {
                logout()
                navigate('/login')
              }}
            >
              Sign out
            </button>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
