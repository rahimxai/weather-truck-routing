import { useEffect, useRef } from 'react'
import { LEVELS, RISK } from '../lib/riskColors'
import {
  bandLabels,
  NO_TRAVEL_LOAD_LB,
  RAIN_IN_HR,
  SEVERE_LOAD_LB,
  SNOW_IN_HR,
  WIND_MPH,
} from '../lib/riskRules'

const wind = bandLabels(WIND_MPH, 0, false)
const rain = bandLabels(RAIN_IN_HR, 2, true)
const snow = bandLabels(SNOW_IN_HR, 1, true)
const lb = (n: number) => `${n.toLocaleString('en-US')} lb`

interface Props {
  id: string
  onClose: () => void
}

/** What the colours, squares and trucks mean, opened from the legend. */
export default function MapKey({ id, onClose }: Props) {
  const ref = useRef<HTMLElement>(null)

  useEffect(() => {
    ref.current?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <section id={id} ref={ref} className="map-key" tabIndex={-1} aria-labelledby={`${id}-title`}>
      <div className="map-key-head">
        <h2 id={`${id}-title`}>How to read the map</h2>
        <button type="button" className="map-key-close" aria-label="Close" onClick={onClose}>
          <svg viewBox="0 0 12 12" aria-hidden="true">
            <path d="M2 2l8 8M10 2l-8 8" />
          </svg>
        </button>
      </div>

      {/* Only the body scrolls: a scrolling box with its own background leaves a white
          band over the WebGL map in Chromium, so the background stays on the outer box. */}
      <div className="map-key-body" tabIndex={0}>
        <h3>Risk levels</h3>
        <p>Each checkpoint takes the worst of its wind, rain and snow.</p>
        <table>
          <thead>
            <tr>
              <th scope="col">Level</th>
              <th scope="col">Wind mph</th>
              <th scope="col">Rain in/hr</th>
              <th scope="col">Snow in/hr</th>
            </tr>
          </thead>
          <tbody>
            {LEVELS.map((level, i) => (
              <tr key={level}>
                <th scope="row">
                  <i style={{ background: RISK[level].hex }} aria-hidden="true" />
                  {RISK[level].label}
                </th>
                <td>{wind[i]}</td>
                <td>{rain[i]}</td>
                <td>{snow[i]}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="map-key-note">A range starts at its first number, so 35 mph is High.</p>

        <h3>Heavy loads</h3>
        <ul>
          <li>
            Over {lb(NO_TRAVEL_LOAD_LB)}, wind of {wind[3]} mph is No Travel.
          </li>
          <li>
            Over {lb(SEVERE_LOAD_LB)}, wind of {wind[2]} mph is Severe.
          </li>
        </ul>

        <h3>On the map</h3>
        <ul>
          <li>Route colors are the risk when your truck reaches each stretch.</li>
          <li>
            Squares are the forecast around the routes at the hour on the slider. Overall, Wind,
            Rain and Snow switch what they show.
          </li>
          <li>Letters are where each truck would be at that hour.</li>
        </ul>

        <h3>The recommendation</h3>
        <p>
          Fewest No Travel miles, then fewest Severe, then fewest High, then the lowest average
          risk, then the shortest drive.
        </p>
      </div>
    </section>
  )
}
