import { useState } from 'react'
import { geocode } from '../api/client'
import type { Interval, Place, PlanRequest } from '../api/types'
import { nextQuarterHour, toLocalInput, zoneName } from '../lib/format'
import IntervalToggle from './IntervalToggle'
import PlaceAutocomplete, { type PlaceField } from './PlaceAutocomplete'

const MAX_LOAD = 80_000
const DAY_MS = 86_400_000
// Matches the server's grace for clocks that disagree by a few minutes.
const PAST_GRACE_MS = 10 * 60_000

interface Props {
  busy: boolean
  onSubmit: (req: PlanRequest) => void
}

const empty: PlaceField = { text: '', place: null }

export default function TripForm({ busy, onSubmit }: Props) {
  const [from, setFrom] = useState(empty)
  const [to, setTo] = useState(empty)
  const [departure, setDeparture] = useState(() => toLocalInput(nextQuarterHour()))
  const [load, setLoad] = useState('42000')
  const [interval, setIntervalMi] = useState<Interval>(25)
  const [demo, setDemo] = useState(false)
  const [turns, setTurns] = useState(0)
  const [error, setError] = useState('')
  const [resolving, setResolving] = useState(false)
  // Picker bounds, fixed when the form opens; submit re-checks against the real clock.
  const [limits] = useState(() => ({
    min: toLocalInput(new Date()),
    max: toLocalInput(new Date(Date.now() + 7 * DAY_MS)),
  }))

  // Typed text without a picked suggestion: take the geocoder's best match.
  async function resolve(field: PlaceField, what: string, set: (f: PlaceField) => void) {
    if (field.place) return field.place
    const q = field.text.trim()
    if (!q) throw new Error(`Enter a ${what}.`)
    const found = await geocode(q)
    if (!found.length) throw new Error(`Couldn't find "${q}". Try a city and state.`)
    set({ text: found[0].label, place: found[0] })
    return found[0]
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    const dep = new Date(departure)
    const now = Date.now()
    if (Number.isNaN(dep.getTime())) return setError('Pick a departure time.')
    if (dep.getTime() < now - PAST_GRACE_MS)
      return setError('Departure is in the past. Pick a time from now on.')
    if (dep.getTime() > now + 7 * DAY_MS)
      return setError('Forecasts only go 7 days out. Pick an earlier departure.')

    const loadLb = Number(load)
    if (load.trim() === '' || !(loadLb >= 0 && loadLb <= MAX_LOAD))
      return setError('Load must be between 0 and 80,000 lb.')

    let origin: Place
    let destination: Place
    setResolving(true)
    try {
      origin = await resolve(from, 'starting point', setFrom)
      destination = await resolve(to, 'destination', setTo)
    } catch (err) {
      return setError(err instanceof Error ? err.message : String(err))
    } finally {
      setResolving(false)
    }
    if (origin.lat === destination.lat && origin.lon === destination.lon)
      return setError('Start and destination are the same place.')

    onSubmit({
      origin,
      destination,
      departure: dep.toISOString(),
      load_lb: loadLb,
      interval_mi: interval,
      scenario: demo ? 'winter_storm' : null,
    })
  }

  const working = busy || resolving

  return (
    <form className="trip" onSubmit={submit} noValidate>
      <div className="places">
        {/* Same start and end dots as the map, joined by the route line. */}
        <div className="rail" aria-hidden="true">
          <span className="dot start" />
          <span className="rail-line" />
          <span className="dot end" />
        </div>
        <div className="place-fields">
          <PlaceAutocomplete
            label="From"
            placeholder="City, address or place"
            value={from}
            onChange={setFrom}
          />
          <PlaceAutocomplete
            label="To"
            placeholder="City, address or place"
            value={to}
            onChange={setTo}
          />
        </div>
        <button
          type="button"
          className="swap"
          aria-label="Swap start and destination"
          onClick={() => {
            setFrom(to)
            setTo(from)
            setTurns((n) => n + 1)
          }}
        >
          <svg viewBox="0 0 16 16" aria-hidden="true" style={{ rotate: `${turns * 180}deg` }}>
            <path d="M5 2v10M2 9l3 3 3-3M11 14V4M8 7l3-3 3 3" />
          </svg>
        </button>
      </div>
      <div className="row">
        <div className="field">
          <label htmlFor="departure">
            Departure <span className="unit">{zoneName()}</span>
          </label>
          <input
            id="departure"
            type="datetime-local"
            value={departure}
            min={limits.min}
            max={limits.max}
            onChange={(e) => setDeparture(e.target.value)}
          />
        </div>
        <div className="field load">
          <label htmlFor="load">
            Load <span className="unit">lb</span>
          </label>
          <input
            id="load"
            type="number"
            inputMode="numeric"
            min={0}
            max={MAX_LOAD}
            step={1000}
            value={load}
            onChange={(e) => setLoad(e.target.value)}
          />
        </div>
      </div>
      <IntervalToggle value={interval} onChange={setIntervalMi} />
      <div className="demo-toggle">
        <input
          id="demo"
          type="checkbox"
          checked={demo}
          aria-describedby="demo-note"
          onChange={(e) => setDemo(e.target.checked)}
        />
        <div>
          <label htmlFor="demo">Use demo weather</label>
          <small id="demo-note">
            A simulated winter storm across the middle of the trip, for when the real forecast is
            calm.
          </small>
        </div>
      </div>
      <button type="submit" className="primary" disabled={working}>
        {working ? 'Planning routes...' : 'Plan routes'}
      </button>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </form>
  )
}
