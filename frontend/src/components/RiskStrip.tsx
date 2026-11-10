import type { RoutePlan } from '../api/types'
import { miles } from '../lib/format'
import { RISK } from '../lib/riskColors'
import { riskSpans } from '../lib/route'

/** The route as a straight strip map: where along the drive each risk level sits. */
export default function RiskStrip({ route }: { route: RoutePlan }) {
  const total = route.distance_mi || 1
  const spans = riskSpans(route.checkpoints)
  const pct = (mi: number) => `${(mi / total) * 100}%`
  const described = spans
    .map((s) => `${RISK[s.level].label} from mile ${Math.round(s.start)} to ${Math.round(s.end)}`)
    .join(', ')

  return (
    <div className="strip" role="img" aria-label={`Risk along route ${route.id}: ${described}`}>
      <div className="strip-bar">
        {spans.map((s) => (
          <span
            key={s.start}
            style={{
              left: pct(s.start),
              width: pct(s.end - s.start),
              background: RISK[s.level].hex,
            }}
          />
        ))}
      </div>
      <div className="strip-scale" aria-hidden="true">
        <span>0</span>
        <span>{miles(route.distance_mi / 2)}</span>
        <span>{miles(route.distance_mi)}</span>
      </div>
    </div>
  )
}
