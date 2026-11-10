import { useEffect, useState } from 'react'
import { ApiError, fetchHeatmap } from '../api/client'
import type { PlanResponse } from '../api/types'
import { toHeatmap, type Heatmap } from '../lib/heatmap'

export type HeatmapState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; heat: Heatmap }
  | { status: 'error'; message: string }

type Result = { plan: PlanResponse; heat?: Heatmap; error?: string }

// One quiet retry for a busy or flaky upstream (Open-Meteo rate limits come and go).
const RETRY_MS = 4000
const retryable = (e: unknown) => e instanceof ApiError && (e.status === 0 || e.status >= 502)

/** Fetches the corridor heatmap once per plan, after the routes are on screen. */
export function useHeatmap(plan: PlanResponse | null, loadLb: number | null): HeatmapState {
  const [result, setResult] = useState<Result | null>(null)

  useEffect(() => {
    if (!plan || loadLb === null) return
    const ctrl = new AbortController()
    let timer = 0
    const load = (retries: number) =>
      fetchHeatmap(
        {
          routes: plan.routes.map((r) => r.geometry),
          departure: plan.routes[0].departure,
          load_lb: loadLb,
          // Always the plan's own scenario, so live and demo weather never mix.
          scenario: plan.scenario,
        },
        ctrl.signal,
      )
        .then((resp) => setResult({ plan, heat: toHeatmap(resp) }))
        .catch((e) => {
          if (ctrl.signal.aborted) return
          if (retries > 0 && retryable(e)) {
            timer = window.setTimeout(() => load(retries - 1), RETRY_MS)
            return
          }
          setResult({
            plan,
            error: e instanceof ApiError ? e.message : "Couldn't load the weather layer.",
          })
        })
    load(1)
    return () => {
      ctrl.abort()
      window.clearTimeout(timer)
    }
  }, [plan, loadLb])

  if (!plan) return { status: 'idle' }
  // A result for an older plan means the new one is still on its way.
  if (result?.plan !== plan) return { status: 'loading' }
  if (result.heat) return { status: 'ready', heat: result.heat }
  return { status: 'error', message: result.error ?? "Couldn't load the weather layer." }
}
