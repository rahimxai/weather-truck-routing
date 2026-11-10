import { describe, expect, it } from 'vitest'
import {
  bandLabels,
  NO_TRAVEL_LOAD_LB,
  RAIN_IN_HR,
  SEVERE_LOAD_LB,
  SNOW_IN_HR,
  WIND_MPH,
} from './riskRules'
import risk from '../../../backend/routing/domain/risk.py?raw'

function tuple(name: string) {
  const m = risk.match(new RegExp(`^${name} = \\(([^)]*)\\)`, 'm'))
  if (!m) throw new Error(`${name} not found in risk.py`)
  return m[1].split(',').map(Number)
}

function constant(name: string) {
  const m = risk.match(new RegExp(`^${name} = ([\\d_]+)`, 'm'))
  if (!m) throw new Error(`${name} not found in risk.py`)
  return Number(m[1].replaceAll('_', ''))
}

describe('map key matches the backend rules', () => {
  it('wind', () => expect(WIND_MPH).toEqual(tuple('WIND_MPH')))
  it('rain', () => expect(RAIN_IN_HR).toEqual(tuple('RAIN_IN_HR')))
  it('snow', () => expect(SNOW_IN_HR).toEqual(tuple('SNOW_IN_HR')))
  it('load', () => {
    expect(NO_TRAVEL_LOAD_LB).toBe(constant('NO_TRAVEL_LOAD_LB'))
    expect(SEVERE_LOAD_LB).toBe(constant('SEVERE_LOAD_LB'))
  })
})

describe('bandLabels', () => {
  it('wind tops out at 55+', () =>
    expect(bandLabels(WIND_MPH, 0, false)).toEqual(['under 25', '25–35', '35–45', '45–55', '55+']))

  it('rain tops out over 1.00', () =>
    expect(bandLabels(RAIN_IN_HR, 2, true)).toEqual([
      'under 0.10',
      '0.10–0.25',
      '0.25–0.50',
      '0.50–1.00',
      'over 1.00',
    ]))
})
