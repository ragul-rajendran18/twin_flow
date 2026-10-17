import axios, { AxiosError } from 'axios'

export const API_BASE_URL = (
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? ''
).replace(/\/$/, '')

export const TOKEN_STORAGE_KEY = 'twinflow.token'

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && localStorage.getItem(TOKEN_STORAGE_KEY)) {
      localStorage.removeItem(TOKEN_STORAGE_KEY)
      localStorage.removeItem('twinflow.user')
      window.dispatchEvent(new Event('twinflow:unauthorized'))
    }
    return Promise.reject(error)
  },
)

export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail
        .map((d) => (typeof d === 'object' && d !== null ? String(d.msg ?? JSON.stringify(d)) : String(d)))
        .join('; ')
    }
    if (detail && typeof detail === 'object') {
      const obj = detail as { message?: string; code?: string }
      return obj.message ?? obj.code ?? JSON.stringify(detail)
    }
    if (!error.response) return 'Cannot reach the API server. Is the backend running?'
    return error.message
  }
  if (error instanceof Error) return error.message
  return 'Unexpected error'
}

export default api
