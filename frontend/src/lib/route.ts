import type { Checkpoint, Level, LonLat, RoutePlan, Segment } from '../api/types'
import { LEVELS } from './riskColors'

export interface Span {
  level: Level
  start: number
  end: number
}

/** Stretches of road in order, merging neighbouring checkpoints with the same level. */
export function riskSpans(cps: Checkpoint[]): Span[] {
  const spans: Span[] = []
  let start = 0
  for (const cp of cps) {
    const end = start + cp.covered_mi
    const last = spans[spans.length - 1]
    if (end > start) {
      if (last?.level === cp.level) last.end = end
      else spans.push({ level: cp.level, start, end })
    }
    start = end
  }
  return spans
}

/** Miles per level, worst first, skipping levels the route never hits. */
export function levelTotals(route: RoutePlan) {
  return [...LEVELS]
    .reverse()
    .map((level) => ({ level, miles: route.summary.miles_by_level[level] }))
    .filter((t) => t.miles > 0)
}

export function bounds(routes: RoutePlan[]): [LonLat, LonLat] {
  let [w, s, e, n] = [180, 90, -180, -90]
  for (const r of routes) {
    for (const [lon, lat] of r.geometry) {
      w = Math.min(w, lon)
      e = Math.max(e, lon)
      s = Math.min(s, lat)
      n = Math.max(n, lat)
    }
  }
  return [
    [w, s],
    [e, n],
  ]
}

const EARTH_RADIUS_MI = 3958.8

function haversine([lon1, lat1]: LonLat, [lon2, lat2]: LonLat) {
  const rad = Math.PI / 180
  const h =
    Math.sin(((lat2 - lat1) * rad) / 2) ** 2 +
    Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(((lon2 - lon1) * rad) / 2) ** 2
  return 2 * EARTH_RADIUS_MI * Math.asin(Math.sqrt(h))
}

/** Piecewise-linear lookup, clamped at both ends; xs must be sorted. */
function interp(xs: number[], ys: number[], x: number) {
  if (x <= xs[0]) return ys[0]
  if (x >= xs[xs.length - 1]) return ys[ys.length - 1]
  let j = 1
  while (xs[j] < x) j++
  const i = j - 1
  return xs[j] === xs[i] ? ys[j] : ys[i] + ((ys[j] - ys[i]) * (x - xs[i])) / (xs[j] - xs[i])
}

export interface Track {
  pts: LonLat[]
  cum: number[]
  etas: number[]
  miles: number[]
}

/** Everything needed to place a route's truck at any moment, worked out once per plan. */
export function track(route: RoutePlan): Track {
  const pts = route.geometry
  const cum = [0]
  for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + haversine(pts[i - 1], pts[i]))
  // The drawn line is simplified, so its length differs a little from the route's miles.
  const scale = route.distance_mi ? cum[cum.length - 1] / route.distance_mi : 0
  return {
    pts,
    cum,
    etas: route.checkpoints.map((c) => Date.parse(c.eta)),
    miles: route.checkpoints.map((c) => c.mile * scale),
  }
}

export function arrived(t: Track, when: number) {
  return when >= t.etas[t.etas.length - 1]
}

/** The truck's position at a time: checkpoint ETAs give the mile, the line gives the place. */
export function positionAt(t: Track, when: number): LonLat {
  const mile = interp(t.etas, t.miles, when)
  const { pts, cum } = t
  if (mile <= 0) return pts[0]
  if (mile >= cum[cum.length - 1]) return pts[pts.length - 1]
  let j = 1
  while (cum[j] < mile) j++
  const f = (mile - cum[j - 1]) / (cum[j] - cum[j - 1])
  const [x0, y0] = pts[j - 1]
  const [x1, y1] = pts[j]
  return [x0 + (x1 - x0) * f, y0 + (y1 - y0) * f]
}

/** For drawing a route on: each vertex's share of the way along the whole route, 0 to 1. */
export function drawTimestamps(segments: Segment[]): number[][] {
  const cums = segments.map((s) => {
    const cum = [0]
    for (let i = 1; i < s.path.length; i++)
      cum.push(cum[i - 1] + haversine(s.path[i - 1], s.path[i]))
    return cum
  })
  const total = cums.reduce((sum, c) => sum + c[c.length - 1], 0) || 1
  let offset = 0
  return cums.map((cum) => {
    const out = cum.map((d) => (offset + d) / total)
    offset += cum[cum.length - 1]
    return out
  })
}
