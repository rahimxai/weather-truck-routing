// @vitest-environment jsdom
import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useIntro } from './useIntro'

function prefersReduced(reduce: boolean) {
  vi.stubGlobal('matchMedia', (q: string) => ({ matches: reduce && q.includes('reduce') }))
}

describe('useIntro', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('is done at once when motion is reduced', () => {
    prefersReduced(true)
    const { result } = renderHook(() => useIntro(1000, false))
    expect(result.current).toBe(1)
  })

  it('waits for run', () => {
    prefersReduced(false)
    vi.useFakeTimers({ toFake: ['requestAnimationFrame', 'performance'] })
    const { result, rerender } = renderHook(({ run }) => useIntro(1000, run), {
      initialProps: { run: false },
    })
    act(() => vi.advanceTimersByTime(2000))
    expect(result.current).toBe(0)

    rerender({ run: true })
    act(() => vi.advanceTimersByTime(500))
    expect(result.current).toBeGreaterThan(0)
    expect(result.current).toBeLessThan(1)
    act(() => vi.advanceTimersByTime(600))
    expect(result.current).toBe(1)
  })
})
