import { lazy, Suspense, useState } from 'react'
import BrandMark from './components/BrandMark'
import MapErrorBoundary from './components/MapErrorBoundary'
import PlanLoading from './components/PlanLoading'
import RouteCards from './components/RouteCards'
import ScenarioBanner from './components/ScenarioBanner'
import StatusMessage from './components/StatusMessage'
import TripForm from './components/TripForm'
import { usePlan } from './hooks/usePlan'

// The map libraries are most of the bundle; load them after the form is on screen.
const MapView = lazy(() => import('./components/MapView'))

export default function App() {
  const { state, run } = usePlan()
  const [focusedId, setFocusedId] = useState<string | null>(null)
  const plan = state.status === 'done' ? state.plan : null
  const focused = focusedId ?? plan?.recommended_id ?? null

  return (
    <div className="app">
      <aside className="panel">
        <header className="brand">
          <BrandMark />
          <div>
            <h1>Weather-Aware Truck Routing</h1>
            <p>Compare truck routes by the weather you&rsquo;ll drive through, hour by hour.</p>
          </div>
        </header>

        <TripForm
          busy={state.status === 'loading'}
          onSubmit={(req) => {
            setFocusedId(null)
            run(req)
          }}
        />

        <section className="results" aria-live="polite" aria-busy={state.status === 'loading'}>
          {state.status === 'idle' && (
            <p className="empty">
              Enter a trip to see up to three routes, ranked by the risk of the weather each one
              crosses at the time your truck gets there.
            </p>
          )}
          {state.status === 'loading' && <PlanLoading />}
          {state.status === 'error' && <StatusMessage tone="error">{state.message}</StatusMessage>}
          {state.status === 'done' && plan && focused && (
            <>
              <div className="results-head">
                <h2>
                  {plan.routes.length === 1 ? '1 route' : `${plan.routes.length} routes`}, safest
                  first
                </h2>
                <p>
                  {state.req.origin.label} to {state.req.destination.label}
                </p>
              </div>
              {plan.scenario && <ScenarioBanner scenario={plan.scenario} />}
              {plan.warnings.map((w) => (
                <StatusMessage key={w} tone={w.startsWith('Every route') ? 'danger' : 'info'}>
                  {w}
                </StatusMessage>
              ))}
              {/* Keyed per plan so the cards and strip maps animate in again for each new plan. */}
              <RouteCards key={state.seq} plan={plan} focusedId={focused} onFocus={setFocusedId} />
            </>
          )}
        </section>
      </aside>

      <main className="map-area">
        <MapErrorBoundary>
          <Suspense fallback={<div className="map map-loading">Loading map...</div>}>
            <MapView
              plan={plan}
              planKey={state.status === 'done' ? state.seq : 0}
              loadLb={state.status === 'done' ? state.req.load_lb : null}
              focusedId={focused}
              onFocus={setFocusedId}
            />
          </Suspense>
        </MapErrorBoundary>
      </main>
    </div>
  )
}
