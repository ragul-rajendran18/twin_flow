export type UserRole = 'admin' | 'manager' | 'operator'

export interface User {
  id: number
  full_name: string
  email: string
  role: UserRole
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface MessageResponse {
  message: string
}

export interface Paginated<T> {
  total: number
  page: number
  page_size: number
  items: T[]
}

export interface Aisle {
  id: number
  aisle_code: string
  aisle_name: string
  capacity: number
  zone: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AisleStatus {
  id: number
  aisle_code: string
  aisle_name: string
  capacity: number
  zone: string
  is_active: boolean
  latest_event_timestamp: string | null
  occupancy: number | null
  agv_count: number | null
  queue_length: number | null
  order_volume: number | null
  conveyor_load: number | null
  congestion_level: string | null
}

export interface AislePayload {
  aisle_code: string
  aisle_name: string
  capacity: number
  zone: string
  is_active: boolean
}

export interface AisleUpdatePayload {
  aisle_name?: string
  capacity?: number
  zone?: string
  is_active?: boolean
}

export interface WarehouseEvent {
  id: number
  event_id: string
  aisle_id: number
  occupancy: number
  agv_count: number
  queue_length: number
  order_volume: number
  conveyor_load: number
  event_timestamp: string
  received_at: string
  source: string
  created_at: string
}

export interface WarehouseOverview {
  total_aisles: number
  active_aisles: number
  normal_aisles: number
  moderate_aisles: number
  high_congestion_aisles: number
  active_alerts: number
  average_occupancy: number
  total_agvs: number
  total_queue_length: number
  last_updated: string | null
}

export interface Prediction {
  id: number
  prediction_id: string
  aisle_id: number
  event_id: string | null
  congestion_probability: number
  congestion_level: string
  bottleneck_detected: boolean
  predicted_queue_length: number
  predicted_delay_minutes: number
  recommendation: string
  model_version: string
  created_at: string
}

export interface PredictionDetail extends Prediction {
  aisle_code?: string | null
  event?: WarehouseEvent | null
}

export interface PredictionRunResponse {
  model_version: string
  predictions_created: number
  alerts_created: number
  alerts_updated: number
  predictions: Prediction[]
}

export interface Alert {
  id: number
  aisle_id: number
  alert_type: string
  severity: string
  message: string
  status: string
  created_at: string
}

export interface AlertResolveResponse {
  message: string
  alert_id: number
  status: string
}

export interface SimulationStatus {
  seeded_aisles: number
  active_aisles: number
  total_events: number
  latest_event_timestamp: string | null
  supported_scenarios: string[]
  max_simulation_events: number
  message: string
}

export interface SeedResponse {
  aisles_created: number
  aisles_skipped: number
  events_created: number
  events_skipped: number
  message: string
}

export interface GenerateResponse {
  requested: number
  generated: number
  inserted: number
  duplicates: number
  rejected: number
  scenario: string
  message: string
}

export interface HealthResponse {
  message: string
  detail: string
}
