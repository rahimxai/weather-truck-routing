// @vitest-environment jsdom
import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, fetchHeatmap } from '../api/client'
import type { HeatmapResponse, PlanResponse } from '../api/types'
import { useHeatmap } from './useHeatmap'

vi.mock('../api/client', async (real) => ({
  ...(await real<typeof import('../api/client')>()),
  fetchHeatmap: vi.fn(),
}))
const fetchMock = vi.mocked(fetchHeatmap)

const plan = {
  routes: [
    {
      geometry: [
        [-87.6, 41.9],
        [-105, 39.7],
      ],
      departure: '2026-11-10T12:00:00Z',
    },
  ],
  scenario: null,
} as unknown as PlanResponse

const frame = btoa('\0'.repeat(49))
const resp: HeatmapResponse = {
  points: [[-90, 40]],
  cell_deg: 0.2,
  hours: 49,
  start: '2026-11-10T12:00:00Z',
  frames: { risk: frame, wind: frame, rain: frame, snow: frame },
  scenario: null,
}
const busy = () => new ApiError('Open-Meteo is busy right now.', 'UPSTREAM_ERROR', 503)

describe('useHeatmap', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    fetchMock.mockReset()
  })
  afterEach(() => vi.useRealTimers())

  it('retries once when the upstream is busy', async () => {
    fetchMock.mockRejectedValueOnce(busy()).mockResolvedValueOnce(resp)
    const { result } = renderHook(() => useHeatmap(plan, 42000))
    await act(() => vi.advanceTimersByTimeAsync(0))
    expect(result.current.status).toBe('loading')

    await act(() => vi.advanceTimersByTimeAsync(4000))
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(result.current.status).toBe('ready')
  })

  it('shows the error after the retry fails', async () => {
    fetchMock.mockRejectedValue(busy())
    const { result } = renderHook(() => useHeatmap(plan, 42000))
    await act(() => vi.advanceTimersByTimeAsync(10_000))
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(result.current).toEqual({ status: 'error', message: 'Open-Meteo is busy right now.' })
  })

  it('does not retry a bad request', async () => {
    fetchMock.mockRejectedValue(new ApiError('Bad input.', 'INVALID', 400))
    const { result } = renderHook(() => useHeatmap(plan, 42000))
    await act(() => vi.advanceTimersByTimeAsync(10_000))
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(result.current.status).toBe('error')
  })
})
