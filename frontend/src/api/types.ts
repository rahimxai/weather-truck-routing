export type Level = 'LOW' | 'MODERATE' | 'HIGH' | 'SEVERE' | 'NO_TRAVEL'

export type LonLat = [number, number]

export type Interval = 10 | 25 | 50

export type Scenario = 'winter_storm'

export interface Place {
  label: string
  lat: number
  lon: number
}

export interface Weather {
  wind_mph: number
  gust_mph: number
  rain_in_hr: number
  snow_in_hr: number
}

export interface Checkpoint {
  mile: number
  lat: number
  lon: number
  eta: string
  covered_mi: number
  weather: Weather
  level: Level
  reason: string
  levels: { wind: Level; rain: Level; snow: Level }
}

export interface Segment {
  level: Level
  path: LonLat[]
}

export interface RoutePlan {
  id: string
  rank: number
  distance_mi: number
  duration_s: number
  departure: string
  arrival: string
  geometry: LonLat[]
  segments: Segment[]
  checkpoints: Checkpoint[]
  summary: { miles_by_level: Record<Level, number>; avg_risk: number }
}

export interface PlanResponse {
  routes: RoutePlan[]
  recommended_id: string
  explanation: string
  warnings: string[]
  scenario: Scenario | null
}

export interface PlanRequest {
  origin: Place
  destination: Place
  departure: string
  load_lb: number
  interval_mi: Interval
  scenario: Scenario | null
}

export type Metric = 'risk' | 'wind' | 'rain' | 'snow'

export interface HeatmapRequest {
  routes: LonLat[][]
  departure: string
  load_lb: number
  scenario: Scenario | null
}

export interface HeatmapResponse {
  points: LonLat[]
  cell_deg: number
  hours: number
  start: string
  frames: Record<Metric, string>
  scenario: Scenario | null
}
