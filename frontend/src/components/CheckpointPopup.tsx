import type { Checkpoint, Level } from '../api/types'
import { localTime } from '../lib/format'
import { RISK, textOn } from '../lib/riskColors'

function Tag({ level }: { level: Level }) {
  return (
    <span className="tag" style={{ background: RISK[level].hex, color: textOn(level) }}>
      {RISK[level].label}
    </span>
  )
}

export default function CheckpointPopup({ cp }: { cp: Checkpoint }) {
  const wx = cp.weather
  return (
    <div className="cp">
      <div className="cp-head">
        <strong>Mile {cp.mile.toLocaleString('en-US')}</strong>
        <Tag level={cp.level} />
      </div>
      <p className="cp-eta">Truck arrives {localTime(cp.eta)}</p>
      <p className="cp-reason">{cp.reason}</p>
      <dl className="cp-wx">
        <dt>Wind</dt>
        <dd>
          {wx.wind_mph} mph, gusts {wx.gust_mph} <Tag level={cp.levels.wind} />
        </dd>
        <dt>Rain</dt>
        <dd>
          {wx.rain_in_hr.toFixed(2)} in/hr <Tag level={cp.levels.rain} />
        </dd>
        <dt>Snow</dt>
        <dd>
          {wx.snow_in_hr.toFixed(2)} in/hr <Tag level={cp.levels.snow} />
        </dd>
      </dl>
    </div>
  )
}
