// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Checkpoint, Level, RoutePlan } from '../api/types'
import RouteCard from './RouteCard'

afterEach(cleanup)

const cp = (level: Level, covered_mi: number) => ({ level, covered_mi }) as Checkpoint

function route(over: Partial<RoutePlan> = {}): RoutePlan {
  return {
    id: 'B',
    rank: 1,
    distance_mi: 100,
    duration_s: 7200,
    departure: '2026-11-12T14:00:00Z',
    arrival: '2026-11-12T16:00:00Z',
    geometry: [],
    segments: [],
    checkpoints: [cp('LOW', 25), cp('SEVERE', 25), cp('LOW', 50)],
    summary: {
      miles_by_level: { LOW: 75, MODERATE: 0, HIGH: 0, SEVERE: 25, NO_TRAVEL: 0 },
      avg_risk: 0.75,
    },
    ...over,
  }
}

describe('RouteCard', () => {
  it('shows the reason only on the recommended route', () => {
    const { rerender } = render(
      <RouteCard route={route()} recommended focused reason="Because." onFocus={() => {}} />,
    )
    expect(screen.getByText('Recommended')).toBeTruthy()
    expect(screen.getByText('Because.')).toBeTruthy()

    rerender(
      <RouteCard
        route={route({ rank: 2 })}
        recommended={false}
        focused={false}
        reason="Because."
        onFocus={() => {}}
      />,
    )
    expect(screen.getByText('Choice 2')).toBeTruthy()
    expect(screen.queryByText('Because.')).toBeNull()
  })

  it('lists miles by level, worst first', () => {
    render(<RouteCard route={route()} recommended focused onFocus={() => {}} />)
    const items = screen.getByRole('list', { name: 'Miles by risk level' }).textContent
    expect(items).toBe('Severe 25 miLow 75 mi')
  })

  it('describes where the risk is for screen readers', () => {
    render(<RouteCard route={route()} recommended focused onFocus={() => {}} />)
    expect(screen.getByRole('img').getAttribute('aria-label')).toBe(
      'Risk along route B: Low from mile 0 to 25, Severe from mile 25 to 50, Low from mile 50 to 100',
    )
  })

  it('places strip pieces by mile', () => {
    const { container } = render(
      <RouteCard route={route()} recommended focused onFocus={() => {}} />,
    )
    const widths = [...container.querySelectorAll<HTMLElement>('.strip-bar span')].map(
      (s) => `${s.style.left}/${s.style.width}`,
    )
    expect(widths).toEqual(['0%/25%', '25%/25%', '50%/50%'])
  })

  it('focuses the route when pressed', async () => {
    const onFocus = vi.fn()
    render(<RouteCard route={route()} recommended={false} focused={false} onFocus={onFocus} />)
    const btn = screen.getByRole('button', { name: /Route B/ })
    expect(btn.getAttribute('aria-pressed')).toBe('false')
    await userEvent.click(btn)
    expect(onFocus).toHaveBeenCalledOnce()
  })
})
