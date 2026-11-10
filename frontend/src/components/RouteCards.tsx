import type { PlanResponse } from '../api/types'
import RouteCard from './RouteCard'

interface Props {
  plan: PlanResponse
  focusedId: string
  onFocus: (id: string) => void
}

export default function RouteCards({ plan, focusedId, onFocus }: Props) {
  const ranked = [...plan.routes].sort((a, b) => a.rank - b.rank)
  return (
    <ol className="routes reveal" aria-label="Routes, safest first">
      {ranked.map((route, i) => (
        <RouteCard
          key={route.id}
          order={i}
          route={route}
          recommended={route.id === plan.recommended_id}
          focused={route.id === focusedId}
          reason={plan.explanation}
          onFocus={() => onFocus(route.id)}
        />
      ))}
    </ol>
  )
}

export function RouteCardsSkeleton() {
  return (
    <ol className="routes skeleton" aria-hidden="true">
      {[0, 1, 2].map((i) => (
        <li key={i} className="route">
          <span className="bone wide" />
          <span className="bone" />
          <span className="bone strip-bone" />
        </li>
      ))}
    </ol>
  )
}
