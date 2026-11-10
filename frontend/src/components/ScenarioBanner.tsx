import type { Scenario } from '../api/types'

const NAMES: Record<Scenario, string> = { winter_storm: 'simulated winter storm' }

/** Shown whenever results use demo weather, so they can't be mistaken for a forecast. */
export default function ScenarioBanner({
  scenario,
  compact = false,
}: {
  scenario: Scenario
  compact?: boolean
}) {
  if (compact) {
    return (
      <p className="scenario-pill" role="note">
        Demo weather: {NAMES[scenario]}
      </p>
    )
  }
  return (
    <div className="scenario-banner" role="note">
      <strong>Demo weather</strong>
      <p>
        These routes use a {NAMES[scenario]}, not the real forecast. Untick &ldquo;Use demo
        weather&rdquo; and plan again for live conditions.
      </p>
    </div>
  )
}
