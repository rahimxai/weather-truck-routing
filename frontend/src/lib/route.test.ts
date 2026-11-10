import { describe, expect, it } from 'vitest'
import type { Checkpoint, Level, RoutePlan } from '../api/types'
import { bounds, levelTotals, riskSpans } from './route'

const cp = (level: Level, covered_mi: number) => ({ level, covered_mi }) as Checkpoint

describe('riskSpans', () => {
  it('merges neighbours with the same level', () => {
    const spans = riskSpans([cp('LOW', 12.5), cp('LOW', 25), cp('HIGH', 25), cp('LOW', 5)])
    expect(spans).toEqual([
      { level: 'LOW', start: 0, end: 37.5 },
      { level: 'HIGH', start: 37.5, end: 62.5 },
      { level: 'LOW', start: 62.5, end: 67.5 },
    ])
  })

  it('skips zero-length checkpoints', () => {
    expect(riskSpans([cp('SEVERE', 0)])).toEqual([])
  })
})

describe('levelTotals', () => {
  it('lists worst first and drops empty levels', () => {
    const route = {
      summary: {
        miles_by_level: { LOW: 900, MODERATE: 0, HIGH: 25, SEVERE: 0, NO_TRAVEL: 12.5 },
        avg_risk: 0.2,
      },
    } as RoutePlan
    expect(levelTotals(route).map((t) => t.level)).toEqual(['NO_TRAVEL', 'HIGH', 'LOW'])
  })
})

describe('bounds', () => {
  it('covers every route', () => {
    const r = (geometry: [number, number][]) => ({ geometry }) as RoutePlan
    expect(
      bounds([
        r([
          [-87, 41],
          [-104, 39],
        ]),
        r([[-95, 44]]),
      ]),
    ).toEqual([
      [-104, 39],
      [-87, 44],
    ])
  })
})
