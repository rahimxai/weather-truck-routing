import type { Metric } from '../api/types'
import { localTime } from '../lib/format'
import type { Timeline, TimelineAction } from '../lib/timeline'

const METRICS: { id: Metric; label: string }[] = [
  { id: 'risk', label: 'Overall' },
  { id: 'wind', label: 'Wind' },
  { id: 'rain', label: 'Rain' },
  { id: 'snow', label: 'Snow' },
]

interface Props {
  start: number
  time: Timeline
  dispatch: (a: TimelineAction) => void
  metric: Metric
  onMetric: (m: Metric) => void
  visible: boolean
  onVisible: (v: boolean) => void
  heatReady: boolean
  note?: string
}

export default function HeatmapSlider(props: Props) {
  const { start, time, dispatch, metric, onMetric, visible, onVisible, heatReady, note } = props
  const label = localTime(new Date(start + time.hour * 3_600_000).toISOString())
  const after = time.hour === 0 ? 'Departure' : `+${time.hour} h`

  return (
    <div className="timebar" role="group" aria-label="Weather and trucks over the next 48 hours">
      <button
        type="button"
        className="play"
        aria-label={time.playing ? 'Pause' : 'Play'}
        onClick={() => dispatch({ type: time.playing ? 'pause' : 'play' })}
      >
        <svg viewBox="0 0 16 16" aria-hidden="true">
          {time.playing ? <path d="M4 2h3v12H4zM9 2h3v12H9z" /> : <path d="M4 2l10 6-10 6z" />}
        </svg>
      </button>
      <input
        type="range"
        className="hours"
        min={0}
        max={time.last}
        step={1}
        value={time.hour}
        aria-label="Hours after departure"
        aria-valuetext={`${after}, ${label}`}
        onChange={(e) => dispatch({ type: 'seek', hour: Number(e.target.value) })}
      />
      <output className="when">
        <b>{label}</b>
        <span>{after}</span>
      </output>
      <div className="layer-controls">
        <label className="toggle">
          <input
            type="checkbox"
            checked={visible}
            disabled={!heatReady}
            onChange={(e) => onVisible(e.target.checked)}
          />
          Weather
        </label>
        <div className="segmented small" role="radiogroup" aria-label="Weather shown">
          {METRICS.map((m) => (
            <label key={m.id} className={m.id === metric ? 'on' : undefined}>
              <input
                type="radio"
                name="metric"
                value={m.id}
                checked={m.id === metric}
                disabled={!heatReady || !visible}
                onChange={() => onMetric(m.id)}
              />
              {m.label}
            </label>
          ))}
        </div>
      </div>
      {note && (
        <p className="timebar-note" role="status">
          {note}
        </p>
      )}
    </div>
  )
}
