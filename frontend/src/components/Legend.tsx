import { useCallback, useRef, useState } from 'react'
import { LEVELS, RISK } from '../lib/riskColors'
import MapKey from './MapKey'

export default function Legend() {
  const [open, setOpen] = useState(false)
  const button = useRef<HTMLButtonElement>(null)
  const close = useCallback(() => {
    setOpen(false)
    button.current?.focus()
  }, [])

  return (
    <>
      <div className="legend" aria-label="Risk levels">
        {LEVELS.map((level) => (
          <span key={level}>
            <i style={{ background: RISK[level].hex }} aria-hidden="true" />
            {RISK[level].label}
          </span>
        ))}
        <button
          ref={button}
          type="button"
          className="legend-help"
          aria-expanded={open}
          aria-controls="map-key"
          aria-label="Guide to the map"
          onClick={() => (open ? close() : setOpen(true))}
        >
          Guide
        </button>
      </div>
      {open && <MapKey id="map-key" onClose={close} />}
    </>
  )
}
