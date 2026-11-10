// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import type { Checkpoint } from '../api/types'
import CheckpointPopup from './CheckpointPopup'

afterEach(cleanup)

const cp = (road: string | null) =>
  ({
    mile: 450,
    lon: -99,
    lat: 41,
    eta: '2026-11-12T20:00:00Z',
    covered_mi: 25,
    road,
    weather: { wind_mph: 20, gust_mph: 30, rain_in_hr: 0, snow_in_hr: 0 },
    level: 'LOW',
    levels: { wind: 'LOW', rain: 'LOW', snow: 'LOW' },
    reason: 'Low risk',
  }) as Checkpoint

describe('CheckpointPopup', () => {
  it('names the highway', () => {
    render(<CheckpointPopup cp={cp('I-80')} />)
    expect(screen.getByText('On I-80')).toBeTruthy()
  })

  it('leaves the road out on unnumbered streets', () => {
    const { container } = render(<CheckpointPopup cp={cp(null)} />)
    expect(container.querySelector('.cp-place')).toBeNull()
  })
})
