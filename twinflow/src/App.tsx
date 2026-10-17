import type { ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import Layout from './components/Layout'
import Spinner from './components/Spinner'
import Alerts from './pages/Alerts'
import AisleDetail from './pages/AisleDetail'
import Aisles from './pages/Aisles'
import Dashboard from './pages/Dashboard'
import Events from './pages/Events'
import Login from './pages/Login'
import Predictions from './pages/Predictions'
import Profile from './pages/Profile'
import Register from './pages/Register'
import Simulation from './pages/Simulation'
import Users from './pages/Users'

function Protected({ children }: { children: ReactNode }) {
  const { isAuthenticated, loading } = useAuth()
  if (loading) return <Spinner label="Checking session…" />
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AdminOnly({ children }: { children: ReactNode }) {
  const { isAdmin } = useAuth()
  if (!isAdmin) return <Navigate to="/" replace />
  return <>{children}</>
}

function GuestOnly({ children }: { children: ReactNode }) {
  const { isAuthenticated, loading } = useAuth()
  if (loading) return <Spinner label="Checking session…" />
  if (isAuthenticated) return <Navigate to="/" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route
          path="/login"
          element={
            <GuestOnly>
              <Login />
            </GuestOnly>
          }
        />
        <Route
          path="/register"
          element={
            <GuestOnly>
              <Register />
            </GuestOnly>
          }
        />
        <Route
          element={
            <Protected>
              <Layout />
            </Protected>
          }
        >
          <Route path="/" element={<Dashboard />} />
          <Route path="/aisles" element={<Aisles />} />
          <Route path="/aisles/:aisleId" element={<AisleDetail />} />
          <Route path="/events" element={<Events />} />
          <Route path="/predictions" element={<Predictions />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/simulation" element={<Simulation />} />
          <Route
            path="/users"
            element={
              <AdminOnly>
                <Users />
              </AdminOnly>
            }
          />
          <Route path="/profile" element={<Profile />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}
