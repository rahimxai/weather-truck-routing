import type { RoutePlan } from '../api/types'
import { duration, localTime, miles } from '../lib/format'
import { RISK } from '../lib/riskColors'
import { levelTotals } from '../lib/route'
import RiskStrip from './RiskStrip'
import Shield from './Shield'

interface Props {
  order?: number
  route: RoutePlan
  recommended: boolean
  focused: boolean
  reason?: string
  onFocus: () => void
}

export default function RouteCard({
  order = 0,
  route,
  recommended,
  focused,
  reason,
  onFocus,
}: Props) {
  const classes = ['route', recommended && 'recommended', focused && 'focused'].filter(Boolean)
  return (
    <li className={classes.join(' ')} style={{ '--i': order } as React.CSSProperties}>
      <button type="button" className="route-head" aria-pressed={focused} onClick={onFocus}>
        <Shield id={route.id} active={focused} />
        <span className="route-name">
          Route {route.id}
          {recommended ? (
            <span className="route-rank badge">Recommended</span>
          ) : (
            <span className="route-rank">Choice {route.rank}</span>
          )}
        </span>
        <span className="route-stats">
          <span>
            <b>{miles(route.distance_mi)}</b>
          </span>
          <span>
            <b>{duration(route.duration_s)}</b>
          </span>
        </span>
      </button>
      {recommended && reason && <p className="reason">{reason}</p>}
      <RiskStrip route={route} />
      <div className="route-foot">
        <ul className="totals" aria-label="Miles by risk level">
          {levelTotals(route).map((t) => (
            <li key={t.level}>
              <i style={{ background: RISK[t.level].hex }} aria-hidden="true" />
              {RISK[t.level].label} {miles(t.miles)}
            </li>
          ))}
        </ul>
        <span className="arrival">Arrives {localTime(route.arrival)}</span>
      </div>
    </li>
  )
}
