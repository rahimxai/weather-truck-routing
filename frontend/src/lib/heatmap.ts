import type { HeatmapResponse, LonLat, Metric } from '../api/types'
import { LEVELS, RISK } from './riskColors'

export const NO_DATA = 255

export interface Heatmap {
  cells: LonLat[][] // one square per grid cell
  hours: number
  start: number // ms since epoch
  frames: Record<Metric, Uint8Array> // frames[m][hour * n + cell]
}

/** base64 to bytes, once per response; the slider then only indexes into these. */
export function decodeFrames(b64: string) {
  const bin = atob(b64)
  const out = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i)
  return out
}

export function toHeatmap(resp: HeatmapResponse): Heatmap {
  const h = resp.cell_deg / 2
  return {
    cells: resp.points.map(([x, y]) => [
      [x - h, y - h],
      [x + h, y - h],
      [x + h, y + h],
      [x - h, y + h],
    ]),
    hours: resp.hours,
    start: Date.parse(resp.start),
    frames: {
      risk: decodeFrames(resp.frames.risk),
      wind: decodeFrames(resp.frames.wind),
      rain: decodeFrames(resp.frames.rain),
      snow: decodeFrames(resp.frames.snow),
    },
  }
}

type RGBA = [number, number, number, number]

// Low stays faint so the corridor reads as a shape without drowning the routes.
const ALPHA = [40, 120, 150, 170, 190]
const CLEAR: RGBA = [0, 0, 0, 0]
const COLORS: RGBA[] = LEVELS.map((level, i) => [...RISK[level].rgb, ALPHA[i]])

export function cellColor(level: number): RGBA {
  return COLORS[level] ?? CLEAR
}
