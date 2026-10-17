import api, { API_BASE_URL } from './client'
import type {
  Aisle,
  AislePayload,
  AisleStatus,
  AisleUpdatePayload,
  Alert,
  AlertResolveResponse,
  GenerateResponse,
  HealthResponse,
  MessageResponse,
  Paginated,
  Prediction,
  PredictionDetail,
  PredictionRunResponse,
  SeedResponse,
  SimulationStatus,
  TokenResponse,
  User,
  WarehouseEvent,
  WarehouseOverview,
} from './types'

export interface ListParams {
  page?: number
  page_size?: number
  [key: string]: string | number | boolean | undefined
}

function params(input: Record<string, unknown> | undefined): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(input ?? {})) {
    if (value !== undefined && value !== null && value !== '') out[key] = value
  }
  return out
}

export const healthApi = {
  check: async (): Promise<HealthResponse> => {
    const { data } = await api.get<HealthResponse>('/health', { baseURL: API_BASE_URL })
    return data
  },
}

export const authApi = {
  login: async (email: string, password: string): Promise<TokenResponse> => {
    const { data } = await api.post<TokenResponse>('/auth/login', { email, password })
    return data
  },
  register: async (payload: { full_name: string; email: string; password: string }): Promise<User> => {
    const { data } = await api.post<User>('/auth/register', payload)
    return data
  },
  me: async (): Promise<User> => {
    const { data } = await api.get<User>('/auth/me')
    return data
  },
  changePassword: async (current_password: string, new_password: string): Promise<MessageResponse> => {
    const { data } = await api.post<MessageResponse>('/auth/change-password', {
      current_password,
      new_password,
    })
    return data
  },
}

export const usersApi = {
  list: async (query: ListParams = {}): Promise<Paginated<User>> => {
    const { data } = await api.get<Paginated<User>>('/users/', { params: params(query) })
    return data
  },
  update: async (id: number, payload: { full_name?: string; email?: string }): Promise<User> => {
    const { data } = await api.patch<User>(`/users/${id}`, params(payload))
    return data
  },
  setStatus: async (id: number, is_active: boolean): Promise<User> => {
    const { data } = await api.patch<User>(`/users/${id}/status`, { is_active })
    return data
  },
  setRole: async (id: number, role: string): Promise<User> => {
    const { data } = await api.patch<User>(`/users/${id}/role`, { role })
    return data
  },
}

export const aislesApi = {
  list: async (query: ListParams = {}): Promise<Paginated<Aisle>> => {
    const { data } = await api.get<Paginated<Aisle>>('/aisles', { params: params(query) })
    return data
  },
  get: async (id: number): Promise<AisleStatus> => {
    const { data } = await api.get<AisleStatus>(`/aisles/${id}`)
    return data
  },
  create: async (payload: AislePayload): Promise<Aisle> => {
    const { data } = await api.post<Aisle>('/aisles', payload)
    return data
  },
  update: async (id: number, payload: AisleUpdatePayload): Promise<Aisle> => {
    const { data } = await api.patch<Aisle>(`/aisles/${id}`, payload)
    return data
  },
  history: async (id: number, query: ListParams = {}): Promise<Paginated<WarehouseEvent>> => {
    const { data } = await api.get<Paginated<WarehouseEvent>>(`/aisles/${id}/history`, {
      params: params(query),
    })
    return data
  },
}

export const warehouseApi = {
  overview: async (): Promise<WarehouseOverview> => {
    const { data } = await api.get<WarehouseOverview>('/warehouse/overview')
    return data
  },
  aisles: async (): Promise<AisleStatus[]> => {
    const { data } = await api.get<AisleStatus[]>('/warehouse/aisles')
    return data
  },
  events: async (query: ListParams = {}): Promise<Paginated<WarehouseEvent>> => {
    const { data } = await api.get<Paginated<WarehouseEvent>>('/warehouse/events', {
      params: params(query),
    })
    return data
  },
}

export const predictionsApi = {
  run: async (aisle_code?: string): Promise<PredictionRunResponse> => {
    const { data } = await api.post<PredictionRunResponse>('/predictions/run', aisle_code ? { aisle_code } : {})
    return data
  },
  latest: async (query: ListParams = {}): Promise<PredictionDetail[]> => {
    const { data } = await api.get<PredictionDetail[]>('/predictions/latest', { params: params(query) })
    return data
  },
  history: async (query: ListParams = {}): Promise<Paginated<Prediction>> => {
    const { data } = await api.get<Paginated<Prediction>>('/predictions/history', { params: params(query) })
    return data
  },
  get: async (predictionId: string): Promise<PredictionDetail> => {
    const { data } = await api.get<PredictionDetail>(`/predictions/${predictionId}`)
    return data
  },
}

export const alertsApi = {
  list: async (query: ListParams = {}): Promise<Paginated<Alert>> => {
    const { data } = await api.get<Paginated<Alert>>('/alerts', { params: params(query) })
    return data
  },
  active: async (): Promise<Alert[]> => {
    const { data } = await api.get<Alert[]>('/alerts/active')
    return data
  },
  resolve: async (id: number): Promise<AlertResolveResponse> => {
    const { data } = await api.patch<AlertResolveResponse>(`/alerts/${id}/resolve`)
    return data
  },
}

export const simulationApi = {
  status: async (): Promise<SimulationStatus> => {
    const { data } = await api.get<SimulationStatus>('/simulation/status')
    return data
  },
  seed: async (payload: {
    include_historical_events?: boolean
    historical_events?: number
    scenario?: string
    seed?: number | null
  }): Promise<SeedResponse> => {
    const { data } = await api.post<SeedResponse>('/simulation/seed', payload)
    return data
  },
  generate: async (payload: {
    number_of_events: number
    scenario: string
    seed?: number | null
  }): Promise<GenerateResponse> => {
    const { data } = await api.post<GenerateResponse>('/simulation/generate', payload)
    return data
  },
  step: async (payload: { aisle_codes?: string[]; scenario: string; seed?: number | null }): Promise<GenerateResponse> => {
    const { data } = await api.post<GenerateResponse>('/simulation/step', payload)
    return data
  },
}
