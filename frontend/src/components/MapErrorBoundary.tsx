import { Component, type ReactNode } from 'react'

export function MapUnavailable() {
  return (
    <div className="map map-failed" role="alert">
      <p>
        <strong>The map couldn&rsquo;t load in this browser.</strong>
        Route details, risk and the recommendation are still listed in the panel. Reloading the page
        or using a browser with graphics acceleration usually fixes it.
      </p>
    </div>
  )
}

/** Keeps the trip panel usable if the map code crashes or its download fails. */
export default class MapErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    return this.state.failed ? <MapUnavailable /> : this.props.children
  }
}
