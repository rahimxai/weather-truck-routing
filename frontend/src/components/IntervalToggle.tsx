import type { Interval } from '../api/types'

const OPTIONS: Interval[] = [10, 25, 50]

interface Props {
  value: Interval
  onChange: (value: Interval) => void
}

export default function IntervalToggle({ value, onChange }: Props) {
  return (
    <fieldset className="field interval">
      <legend>Check weather every</legend>
      <div className="segmented">
        {OPTIONS.map((n) => (
          <label key={n} className={n === value ? 'on' : undefined}>
            <input
              type="radio"
              name="interval"
              value={n}
              checked={n === value}
              onChange={() => onChange(n)}
            />
            {n} mi
          </label>
        ))}
      </div>
    </fieldset>
  )
}
