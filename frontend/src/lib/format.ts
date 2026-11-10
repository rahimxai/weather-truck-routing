export function miles(n: number) {
  const digits = n >= 100 ? 0 : 1
  return `${n.toLocaleString('en-US', { maximumFractionDigits: digits })} mi`
}

export function duration(seconds: number) {
  const total = Math.round(seconds / 60)
  const h = Math.floor(total / 60)
  const m = total % 60
  if (h === 0) return `${m} min`
  return m ? `${h} h ${m} min` : `${h} h`
}

const timeFmt = new Intl.DateTimeFormat(undefined, {
  weekday: 'short',
  hour: 'numeric',
  minute: '2-digit',
  timeZoneName: 'short',
})

/** ISO time from the API, shown in the viewer's own time zone. */
export function localTime(iso: string) {
  return timeFmt.format(new Date(iso))
}

export function zoneName(date = new Date()) {
  return (
    new Intl.DateTimeFormat(undefined, { timeZoneName: 'short' })
      .formatToParts(date)
      .find((p) => p.type === 'timeZoneName')?.value ?? ''
  )
}

const pad = (n: number) => String(n).padStart(2, '0')

/** Value for <input type="datetime-local">, which has no time zone and means local time. */
export function toLocalInput(d: Date) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** The next quarter hour from now, so the default departure is never in the past. */
export function nextQuarterHour(now = new Date()) {
  const d = new Date(now)
  d.setSeconds(0, 0)
  d.setMinutes(Math.ceil((d.getMinutes() + 1) / 15) * 15)
  return d
}
