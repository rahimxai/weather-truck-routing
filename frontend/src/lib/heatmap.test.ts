import { describe, expect, it } from 'vitest'
import type { Checkpoint, RoutePlan } from '../api/types'
import { cellColor, decodeFrames, NO_DATA, toHeatmap } from './heatmap'
import { arrived, drawTimestamps, positionAt, track } from './route'
import { timeline, type Timeline } from './timeline'

const b64 = (bytes: number[]) => btoa(String.fromCharCode(...bytes))

describe('decodeFrames', () => {
  it('turns base64 into bytes', () => {
    expect([...decodeFrames(b64([0, 1, 2, 3, 4, 255]))]).toEqual([0, 1, 2, 3, 4, 255])
  })

  it('handles an empty frame set', () => {
    expect(decodeFrames('').length).toBe(0)
  })
})

describe('toHeatmap', () => {
  it('builds a square per cell and decodes every metric', () => {
    const frames = b64([0, 4])
    const heat = toHeatmap({
      points: [[-90, 40]],
      cell_deg: 0.2,
      hours: 2,
      start: '2026-11-12T14:00:00Z',
      frames: { risk: frames, wind: frames, rain: frames, snow: frames },
      scenario: null,
    })
    expect(heat.cells[0]).toEqual([
      [-90.1, 39.9],
      [-89.9, 39.9],
      [-89.9, 40.1],
      [-90.1, 40.1],
    ])
    expect(heat.start).toBe(Date.UTC(2026, 10, 12, 14))
    expect([...heat.frames.snow]).toEqual([0, 4])
  })
})

describe('cellColor', () => {
  it('keeps Low faint and hides missing data', () => {
    expect(cellColor(0)[3]).toBeLessThan(cellColor(4)[3])
    expect(cellColor(NO_DATA)[3]).toBe(0)
  })
})

describe('timeline', () => {
  const at = (hour: number, playing = false): Timeline => ({ hour, playing, last: 48 })

  it('ticks forward and stops at the end', () => {
    expect(timeline(at(5, true), { type: 'tick' })).toEqual(at(6, true))
    expect(timeline(at(48, true), { type: 'tick' })).toEqual(at(48, false))
  })

  it('restarts when played from the end', () => {
    expect(timeline(at(48), { type: 'play' })).toEqual(at(0, true))
    expect(timeline(at(10), { type: 'play' })).toEqual(at(10, true))
  })

  it('clamps seeking', () => {
    expect(timeline(at(0), { type: 'seek', hour: 99 }).hour).toBe(48)
    expect(timeline(at(0), { type: 'seek', hour: -3 }).hour).toBe(0)
  })
})

describe('truck position', () => {
  const t0 = Date.UTC(2026, 10, 12, 14)
  const cp = (mile: number, hours: number) =>
    ({ mile, eta: new Date(t0 + hours * 3_600_000).toISOString() }) as Checkpoint
  // Two straight legs north: 0 -> 1 degree, then 1 -> 2 degrees, about 69 mi each.
  const route = {
    distance_mi: 138.19,
    geometry: [
      [0, 0],
      [0, 1],
      [0, 2],
    ],
    checkpoints: [cp(0, 0), cp(69.09, 1), cp(138.19, 3)],
  } as RoutePlan
  const tr = track(route)

  it('starts at the origin and ends at the destination', () => {
    expect(positionAt(tr, t0)).toEqual([0, 0])
    expect(positionAt(tr, t0 + 10 * 3_600_000)).toEqual([0, 2])
  })

  it('knows when the truck has arrived', () => {
    expect(arrived(tr, t0 + 2.9 * 3_600_000)).toBe(false)
    expect(arrived(tr, t0 + 3 * 3_600_000)).toBe(true)
  })

  it('follows each leg at its own speed', () => {
    expect(positionAt(tr, t0 + 0.5 * 3_600_000)[1]).toBeCloseTo(0.5, 2)
    expect(positionAt(tr, t0 + 2 * 3_600_000)[1]).toBeCloseTo(1.5, 2) // slower second leg
  })
})

describe('drawTimestamps', () => {
  it('runs 0 to 1 across all segments in order', () => {
    const ts = drawTimestamps([
      {
        level: 'LOW',
        path: [
          [0, 0],
          [0, 1],
        ],
      },
      {
        level: 'HIGH',
        path: [
          [0, 1],
          [0, 2],
          [0, 3],
        ],
      },
    ])
    expect(ts[0][0]).toBe(0)
    expect(ts[0][1]).toBeCloseTo(1 / 3, 3)
    expect(ts[1][0]).toBeCloseTo(1 / 3, 3)
    expect(ts[1][2]).toBeCloseTo(1, 6)
  })

  it('copes with a zero-length route', () => {
    expect(
      drawTimestamps([
        {
          level: 'LOW',
          path: [
            [1, 1],
            [1, 1],
          ],
        },
      ]),
    ).toEqual([[0, 0]])
  })
})
