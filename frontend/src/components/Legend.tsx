import { LEVELS, RISK } from '../lib/riskColors'

export default function Legend() {
  return (
    <div className="legend" aria-label="Risk levels">
      {LEVELS.map((level) => (
        <span key={level}>
          <i style={{ background: RISK[level].hex }} aria-hidden="true" />
          {RISK[level].label}
        </span>
      ))}
    </div>
  )
}
