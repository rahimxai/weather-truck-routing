import { TripsLayer } from '@deck.gl/geo-layers'
import { ScatterplotLayer, SolidPolygonLayer, TextLayer } from '@deck.gl/layers'
import { MapboxOverlay, type MapboxOverlayProps } from '@deck.gl/mapbox'
import { useEffect, useMemo, useReducer, useState } from 'react'
import { Popup, useControl } from 'react-map-gl/maplibre'
import type { Checkpoint, LonLat, Metric, PlanResponse, Segment } from '../api/types'
import { useHeatmap } from '../hooks/useHeatmap'
import { useIntro } from '../hooks/useIntro'
import { cellColor } from '../lib/heatmap'
import { DRAW_MS } from '../lib/motion'
import { RISK } from '../lib/riskColors'
import { arrived, drawTimestamps, positionAt, track } from '../lib/route'
import { timeline } from '../lib/timeline'
import CheckpointPopup from './CheckpointPopup'
import HeatmapSlider from './HeatmapSlider'

const INK: [number, number, number] = [27, 36, 48]
const BLUE: [number, number, number] = [31, 78, 156]
const HOURS = 49
const FRAME_MS = 200 // 5 frames a second while playing
const HEAT_FADE_IN_MS = 700

type SegmentDatum = Segment & { routeId: string; ts: number[] }
type Label = { id: string; at: LonLat; focused: boolean }
type End = { at: LonLat; start: boolean }
type Truck = { id: string; at: LonLat; focused: boolean }

function DeckOverlay(props: MapboxOverlayProps) {
  const overlay = useControl(() => new MapboxOverlay(props))
  overlay.setProps(props)
  return null
}

interface Props {
  plan: PlanResponse
  focused: string
  loadLb: number
  onFocus: (id: string) => void
  onHover: (hovering: boolean) => void
}

/** Everything drawn for one plan. Keyed by plan, so a new plan starts back at hour 0. */
export default function PlanLayers({ plan, focused, loadLb, onFocus, onHover }: Props) {
  const heat = useHeatmap(plan, loadLb)
  const [time, dispatch] = useReducer(timeline, { hour: 0, playing: false, last: HOURS - 1 })
  const [metric, setMetric] = useState<Metric>('risk')
  const [showHeat, setShowHeat] = useState(true)
  const [picked, setPicked] = useState<Checkpoint | null>(null)
  const drawn = useIntro(DRAW_MS) // 0 -> 1 while the routes draw themselves on
  const start = useMemo(() => Date.parse(plan.routes[0].departure), [plan])
  const tracks = useMemo(() => plan.routes.map((r) => ({ id: r.id, t: track(r) })), [plan])
  const ready = heat.status === 'ready' ? heat.heat : null
  // Layer opacity is a uniform, so the fade never touches the colour buffers.
  const heatFade = useIntro(HEAT_FADE_IN_MS, ready !== null)

  useEffect(() => {
    if (!time.playing) return
    let raf = 0
    let last = performance.now()
    const step = (now: number) => {
      if (now - last >= FRAME_MS) {
        last = now
        dispatch({ type: 'tick' })
      }
      raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [time.playing])

  // Geometry and draw-on timestamps, worked out once per plan and focus. The animation
  // below only changes `currentTime`, so nothing is re-tessellated while it runs.
  const shapes = useMemo(() => {
    const route = plan.routes.find((r) => r.id === focused) ?? plan.routes[0]
    const segs: SegmentDatum[] = plan.routes.flatMap((r) => {
      const ts = drawTimestamps(r.segments)
      return r.segments.map((s, i) => ({ ...s, routeId: r.id, ts: ts[i] }))
    })
    return {
      route,
      mine: segs.filter((s) => s.routeId === route.id),
      others: segs.filter((s) => s.routeId !== route.id),
      labels: plan.routes.map<Label>((r) => ({
        id: r.id,
        at: r.geometry[Math.floor(r.geometry.length / 2)],
        focused: r.id === route.id,
      })),
      ends: [
        { at: route.geometry[0], start: true },
        { at: route.geometry[route.geometry.length - 1], start: false },
      ] as End[],
    }
  }, [plan, focused])

  const routeLayers = useMemo(() => {
    const { route, mine, others, labels, ends } = shapes
    const path = {
      getPath: (d: SegmentDatum) => d.path,
      getTimestamps: (d: SegmentDatum) => d.ts,
      currentTime: drawn,
      trailLength: 2, // longer than the whole 0-1 run, so nothing fades behind the pen
      fadeTrail: false,
      widthUnits: 'pixels' as const,
      capRounded: true,
      jointRounded: true,
    }
    const done = drawn >= 1
    const dist = route.distance_mi || 1

    return [
      new TripsLayer<SegmentDatum>({
        id: 'other-routes',
        data: others,
        ...path,
        getColor: (d) => [...RISK[d.level].rgb, 110],
        getWidth: 4,
        pickable: done,
      }),
      new TripsLayer<SegmentDatum>({
        id: 'focused-casing',
        data: mine,
        ...path,
        getColor: [255, 255, 255],
        getWidth: 10,
      }),
      new TripsLayer<SegmentDatum>({
        id: 'focused-route',
        data: mine,
        ...path,
        getColor: (d) => RISK[d.level].rgb,
        getWidth: 6,
        pickable: done,
      }),
      done &&
        new TextLayer<Label>({
          id: 'route-labels',
          data: labels,
          getPosition: (d) => d.at,
          getText: (d) => d.id,
          getColor: [255, 255, 255],
          getSize: 14,
          fontFamily: 'Overpass Variable, system-ui, sans-serif',
          fontWeight: 800,
          background: true,
          getBackgroundColor: (d) => (d.focused ? [...BLUE, 255] : [91, 101, 115, 230]),
          backgroundPadding: [6, 3],
          // Sit just above the line so the letter never covers a checkpoint.
          getPixelOffset: [0, -16],
          pickable: true,
        }),
      new ScatterplotLayer<Checkpoint>({
        id: 'checkpoints',
        data: route.checkpoints,
        getPosition: (d) => [d.lon, d.lat],
        getFillColor: (d) => RISK[d.level].rgb,
        getLineColor: [255, 255, 255],
        stroked: true,
        lineWidthMinPixels: 2,
        radiusUnits: 'pixels',
        // Each dot appears as the drawing line reaches it.
        getRadius: (d) => (d.mile / dist <= drawn + 1e-6 ? 5 : 0),
        updateTriggers: { getRadius: drawn },
        pickable: done,
        autoHighlight: true,
        highlightColor: [...BLUE, 255],
      }),
      new ScatterplotLayer<End>({
        id: 'ends',
        data: ends,
        getPosition: (d) => d.at,
        getFillColor: (d) => (d.start ? [255, 255, 255] : INK),
        getLineColor: INK,
        stroked: true,
        lineWidthMinPixels: 3,
        radiusUnits: 'pixels',
        getRadius: (d) => (d.start || done ? 7 : 0),
        updateTriggers: { getRadius: done },
      }),
    ]
  }, [shapes, drawn])

  // Same data and polygons every frame; only the colour accessor reruns when the hour changes.
  const heatLayer = useMemo(() => {
    if (!ready || !showHeat) return null
    const frame = ready.frames[metric]
    const offset = time.hour * ready.cells.length
    return new SolidPolygonLayer<LonLat[]>({
      id: 'heatmap',
      data: ready.cells,
      getPolygon: (d) => d,
      getFillColor: (_, { index }) => cellColor(frame[offset + index]),
      updateTriggers: { getFillColor: [metric, time.hour] },
      opacity: heatFade,
    })
  }, [ready, showHeat, metric, time.hour, heatFade])

  const truckLayers = useMemo(() => {
    const when = start + time.hour * 3_600_000
    // Arrived trucks are dropped so they don't sit on top of the destination marker.
    const trucks: Truck[] = tracks
      .filter(({ t }) => !arrived(t, when))
      .map(({ id, t }) => ({ id, at: positionAt(t, when), focused: id === focused }))
    return [
      new ScatterplotLayer<Truck>({
        id: 'trucks',
        data: trucks,
        getPosition: (d) => d.at,
        getFillColor: (d) => (d.focused ? BLUE : INK),
        getLineColor: [255, 255, 255],
        stroked: true,
        lineWidthMinPixels: 2,
        radiusUnits: 'pixels',
        getRadius: 10,
        updateTriggers: { getFillColor: focused },
      }),
      new TextLayer<Truck>({
        id: 'truck-letters',
        data: trucks,
        getPosition: (d) => d.at,
        getText: (d) => d.id,
        getColor: [255, 255, 255],
        getSize: 12,
        fontFamily: 'Overpass Variable, system-ui, sans-serif',
        fontWeight: 800,
      }),
    ]
  }, [tracks, start, time.hour, focused])

  // Trucks wait until the routes have finished drawing.
  const layers = [heatLayer, ...routeLayers, ...(drawn >= 1 ? truckLayers : [])]
  const popup = picked && shapes.route.checkpoints.includes(picked)

  const note =
    heat.status === 'loading'
      ? 'Loading the weather layer...'
      : heat.status === 'error'
        ? `Weather layer unavailable: ${heat.message}`
        : undefined

  return (
    <>
      <DeckOverlay
        layers={layers}
        onHover={(info) => onHover(Boolean(info.object))}
        onClick={(info) => {
          const id = info.layer?.id
          if (id === 'checkpoints') setPicked(info.object as Checkpoint)
          else if (id === 'other-routes') onFocus((info.object as SegmentDatum).routeId)
          else if (id === 'route-labels') onFocus((info.object as Label).id)
          else setPicked(null)
        }}
      />
      {picked && popup && (
        <Popup
          longitude={picked.lon}
          latitude={picked.lat}
          onClose={() => setPicked(null)}
          closeOnClick={false}
          maxWidth="280px"
          offset={12}
        >
          <CheckpointPopup cp={picked} />
        </Popup>
      )}
      <HeatmapSlider
        start={start}
        time={time}
        dispatch={dispatch}
        metric={metric}
        onMetric={setMetric}
        visible={showHeat}
        onVisible={setShowHeat}
        heatReady={ready !== null}
        note={note}
      />
    </>
  )
}
