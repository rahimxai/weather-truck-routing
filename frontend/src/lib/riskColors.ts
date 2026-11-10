import type { Level } from '../api/types'

export const LEVELS: Level[] = ['LOW', 'MODERATE', 'HIGH', 'SEVERE', 'NO_TRAVEL']

type RGB = [number, number, number]

export const RISK: Record<Level, { label: string; hex: string; rgb: RGB }> = {
  LOW: { label: 'Low', hex: '#2E9E5B', rgb: [46, 158, 91] },
  MODERATE: { label: 'Moderate', hex: '#E8C547', rgb: [232, 197, 71] },
  HIGH: { label: 'High', hex: '#F08A24', rgb: [240, 138, 36] },
  SEVERE: { label: 'Severe', hex: '#D6332F', rgb: [214, 51, 47] },
  NO_TRAVEL: { label: 'No Travel', hex: '#5B1A6E', rgb: [91, 26, 110] },
}

// Dark text reads better on the two light swatches.
export function textOn(level: Level) {
  return level === 'MODERATE' || level === 'HIGH' ? '#1B2430' : '#FFFFFF'
}
