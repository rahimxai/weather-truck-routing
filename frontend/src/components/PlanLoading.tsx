import { RouteCardsSkeleton } from './RouteCards'

function Truck() {
  return (
    <svg className="lane-truck" viewBox="0 0 40 20" aria-hidden="true">
      <rect x="0" y="2" width="25" height="12" rx="1.5" />
      <path d="M26.5 6h6.5l4.5 4.5V14h-11z" />
      <circle cx="7" cy="16" r="2.6" />
      <circle cx="19" cy="16" r="2.6" />
      <circle cx="32" cy="16" r="2.6" />
    </svg>
  )
}

/** A truck rolling down a lane while the plan is worked out. No fake step-by-step progress. */
export default function PlanLoading() {
  return (
    <>
      <div className="plan-loading">
        <div className="lane" aria-hidden="true">
          <Truck />
        </div>
        <p className="loading-note">
          Finding truck routes and checking the forecast along each one. Long trips take a few
          seconds.
        </p>
      </div>
      <RouteCardsSkeleton />
    </>
  )
}
