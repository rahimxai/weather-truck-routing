import type { HeatmapRequest, HeatmapResponse, PlanRequest, PlanResponse, Place } from './types'

export class ApiError extends Error {
  code: string
  status: number

  constructor(message: string, code: string, status: number) {
    super(message)
    this.code = code
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let resp: Response
  try {
    resp = await fetch(path, init)
  } catch (e) {
    if (init?.signal?.aborted) throw e
    throw new ApiError("Can't reach the server. Check your connection and try again.", 'NETWORK', 0)
  }

  // Read as text first: a misrouted request can come back as an HTML page.
  const text = await resp.text()
  let data: unknown
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = null
  }

  if (!resp.ok) {
    const err = (data as { error?: { code: string; message: string } } | null)?.error
    throw new ApiError(
      err?.message ?? `The server had a problem (${resp.status}). Try again.`,
      err?.code ?? `HTTP_${resp.status}`,
      resp.status,
    )
  }
  if (data === null) {
    throw new ApiError(
      'The server sent an unexpected response. Try again.',
      'BAD_RESPONSE',
      resp.status,
    )
  }
  return data as T
}

export function planTrip(body: PlanRequest, signal?: AbortSignal) {
  return request<PlanResponse>('/api/plan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
}

export function geocode(q: string, signal?: AbortSignal) {
  return request<Place[]>(`/api/geocode?q=${encodeURIComponent(q)}`, { signal })
}

export function fetchHeatmap(body: HeatmapRequest, signal?: AbortSignal) {
  return request<HeatmapResponse>('/api/heatmap', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
}
