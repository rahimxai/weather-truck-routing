import { useEffect, useId, useRef, useState } from 'react'
import { ApiError, geocode } from '../api/client'
import type { Place } from '../api/types'

export interface PlaceField {
  text: string
  place: Place | null
}

interface Props {
  label: string
  placeholder: string
  value: PlaceField
  onChange: (value: PlaceField) => void
}

export default function PlaceAutocomplete({ label, placeholder, value, onChange }: Props) {
  const id = useId()
  const [options, setOptions] = useState<Place[]>([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const [note, setNote] = useState('')
  const timer = useRef<number | undefined>(undefined)
  const inFlight = useRef<AbortController | null>(null)

  useEffect(
    () => () => {
      window.clearTimeout(timer.current)
      inFlight.current?.abort()
    },
    [],
  )

  function search(q: string) {
    window.clearTimeout(timer.current)
    inFlight.current?.abort()
    if (q.trim().length < 2) {
      setOptions([])
      setNote('')
      return
    }
    // Wait for a pause in typing so each keystroke doesn't hit the geocoder.
    timer.current = window.setTimeout(async () => {
      const ctrl = new AbortController()
      inFlight.current = ctrl
      try {
        const found = await geocode(q.trim(), ctrl.signal)
        setOptions(found)
        setActive(found.length ? 0 : -1)
        setNote(found.length ? '' : 'No matches. Try a city and state.')
      } catch (e) {
        if (ctrl.signal.aborted) return
        setOptions([])
        setNote(e instanceof ApiError ? e.message : "Search isn't working right now.")
      }
    }, 250)
  }

  function pick(place: Place) {
    onChange({ text: place.label, place })
    setOpen(false)
    setOptions([])
    setNote('')
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (!open || !options.length) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive((i) => (i + 1) % options.length)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((i) => (i - 1 + options.length) % options.length)
    } else if (e.key === 'Enter' && active >= 0) {
      e.preventDefault()
      pick(options[active])
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  const showList = open && options.length > 0
  const listId = `${id}-list`

  return (
    <div className="field place">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="text"
        role="combobox"
        autoComplete="off"
        spellCheck={false}
        placeholder={placeholder}
        aria-autocomplete="list"
        aria-expanded={showList}
        aria-controls={listId}
        aria-activedescendant={showList && active >= 0 ? `${id}-opt-${active}` : undefined}
        aria-describedby={note ? `${id}-note` : undefined}
        value={value.text}
        onChange={(e) => {
          onChange({ text: e.target.value, place: null })
          setOpen(true)
          search(e.target.value)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={onKeyDown}
      />
      {showList && (
        <ul id={listId} role="listbox" className="options">
          {options.map((p, i) => (
            <li
              key={`${p.label}-${p.lat}-${p.lon}`}
              id={`${id}-opt-${i}`}
              role="option"
              aria-selected={i === active}
              className={i === active ? 'active' : undefined}
              // mousedown, not click: it fires before the input's blur closes the list.
              onMouseDown={(e) => {
                e.preventDefault()
                pick(p)
              }}
              onMouseEnter={() => setActive(i)}
            >
              {p.label}
            </li>
          ))}
        </ul>
      )}
      {note && open && (
        <p id={`${id}-note`} className="hint">
          {note}
        </p>
      )}
    </div>
  )
}
