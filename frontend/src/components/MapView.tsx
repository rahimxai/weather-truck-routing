import { setWorkerUrl } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Map, NavigationControl, type MapRef } from 'react-map-gl/maplibre'
import type { PlanResponse } from '../api/types'
import { reducedMotion } from '../lib/motion'
import { bounds } from '../lib/route'
import Legend from './Legend'
import { MapUnavailable } from './MapErrorBoundary'
import PlanLayers from './PlanLayers'
import ScenarioBanner from './ScenarioBanner'

// MapLibre looks for its tile worker next to its own file, which bundling breaks
// (no streets or labels would load). Point it at the copy Vite emits instead.
setWorkerUrl(workerUrl)

const STYLE = 'https://tiles.openfreemap.org/styles/positron'
const START_VIEW = { longitude: -96, latitude: 39, zoom: 3.4 }

// MapLibre needs WebGL2 and only logs an error without it, leaving a blank map.
const hasWebGL2 = (() => {
  const gl = document.createElement('canvas').getContext('webgl2')
  gl?.getExtension('WEBGL_lose_context')?.loseContext()
  return gl !== null
})()

interface Props {
  plan: PlanResponse | null
  planKey: number
  loadLb: number | null
  focusedId: string | null
  onFocus: (id: string) => void
}

export default function MapView({ plan, planKey, loadLb, focusedId, onFocus }: Props) {
  const mapRef = useRef<MapRef>(null)
  const [hovering, setHovering] = useState(false)
  const focused = focusedId ?? plan?.recommended_id ?? null

  const fit = useCallback(() => {
    if (!plan || !mapRef.current) return
    mapRef.current.fitBounds(bounds(plan.routes), {
      // Extra room at the bottom for the time bar.
      padding: { top: 56, left: 56, right: 56, bottom: 120 },
      duration: reducedMotion() ? 0 : 900,
    })
  }, [plan])

  useEffect(fit, [fit])

  if (!hasWebGL2) return <MapUnavailable />

  return (
    <div className={`map${plan ? ' has-plan' : ''}`}>
      <Map
        ref={mapRef}
        initialViewState={START_VIEW}
        mapStyle={STYLE}
        cursor={hovering ? 'pointer' : 'grab'}
        onLoad={fit}
        dragRotate={false}
        touchPitch={false}
      >
        <NavigationControl position="top-right" showCompass={false} />
        {plan && focused && loadLb !== null && (
          <PlanLayers
            key={planKey}
            plan={plan}
            focused={focused}
            loadLb={loadLb}
            onFocus={onFocus}
            onHover={setHovering}
          />
        )}
      </Map>
      {!plan && (
        <div className="map-invite">
          <div className="invite-road" aria-hidden="true" />
          <p>
            <strong>Your routes will appear here</strong>
            Plan a trip to compare up to three truck routes and the weather along each one.
          </p>
        </div>
      )}
      <div className="map-notes">
        {plan?.scenario && <ScenarioBanner scenario={plan.scenario} compact />}
        <Legend />
      </div>
    </div>
  )
}
