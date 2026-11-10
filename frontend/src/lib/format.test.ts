import { describe, expect, it } from 'vitest'
import { duration, miles, nextQuarterHour, toLocalInput } from './format'

describe('miles', () => {
  it.each([
    [0, '0 mi'],
    [12.34, '12.3 mi'],
    [99.96, '100 mi'],
    [1003.4, '1,003 mi'],
  ])('%s -> %s', (n, out) => expect(miles(n)).toBe(out))
})

describe('duration', () => {
  it.each([
    [0, '0 min'],
    [45 * 60, '45 min'],
    [3600, '1 h'],
    [55800, '15 h 30 min'],
    [3599, '1 h'],
  ])('%s s -> %s', (s, out) => expect(duration(s)).toBe(out))
})

describe('nextQuarterHour', () => {
  it.each([
    ['2026-11-12T14:00:00', '2026-11-12T14:15'],
    ['2026-11-12T14:01:30', '2026-11-12T14:15'],
    ['2026-11-12T14:14:59', '2026-11-12T14:15'],
    ['2026-11-12T14:15:00', '2026-11-12T14:30'],
    ['2026-11-12T23:50:00', '2026-11-13T00:00'],
  ])('%s -> %s', (now, out) => expect(toLocalInput(nextQuarterHour(new Date(now)))).toBe(out))
})
