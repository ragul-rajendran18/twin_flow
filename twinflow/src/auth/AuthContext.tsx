import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { authApi } from '../api/endpoints'
import { TOKEN_STORAGE_KEY } from '../api/client'
import type { User, UserRole } from '../api/types'

interface AuthContextValue {
  user: User | null
  token: string | null
  loading: boolean
  isAuthenticated: boolean
  isAdmin: boolean
  canOperate: boolean
  login: (email: string, password: string) => Promise<void>
  register: (fullName: string, email: string, password: string) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_STORAGE_KEY))
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState<boolean>(Boolean(localStorage.getItem(TOKEN_STORAGE_KEY)))

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    localStorage.removeItem('twinflow.user')
    setToken(null)
    setUser(null)
  }, [])

  const refreshUser = useCallback(async () => {
    if (!localStorage.getItem(TOKEN_STORAGE_KEY)) return
    try {
      const me = await authApi.me()
      setUser(me)
      localStorage.setItem('twinflow.user', JSON.stringify(me))
    } catch {
      logout()
    }
  }, [logout])

  useEffect(() => {
    if (!token) {
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    authApi
      .me()
      .then((me) => {
        if (!cancelled) {
          setUser(me)
          localStorage.setItem('twinflow.user', JSON.stringify(me))
        }
      })
      .catch(() => {
        if (!cancelled) logout()
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [token, logout])

  useEffect(() => {
    const onUnauthorized = () => {
      setToken(null)
      setUser(null)
    }
    window.addEventListener('twinflow:unauthorized', onUnauthorized)
    return () => window.removeEventListener('twinflow:unauthorized', onUnauthorized)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const response = await authApi.login(email, password)
    localStorage.setItem(TOKEN_STORAGE_KEY, response.access_token)
    setToken(response.access_token)
  }, [])

  const register = useCallback(async (fullName: string, email: string, password: string) => {
    await authApi.register({ full_name: fullName, email, password })
    await authApi.login(email, password).then((response) => {
      localStorage.setItem(TOKEN_STORAGE_KEY, response.access_token)
      setToken(response.access_token)
    })
  }, [])

  const value = useMemo<AuthContextValue>(() => {
    const role: UserRole | undefined = user?.role
    return {
      user,
      token,
      loading,
      isAuthenticated: Boolean(user),
      isAdmin: role === 'admin',
      canOperate: role === 'admin' || role === 'manager',
      login,
      register,
      logout,
      refreshUser,
    }
  }, [user, token, loading, login, register, logout, refreshUser])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
