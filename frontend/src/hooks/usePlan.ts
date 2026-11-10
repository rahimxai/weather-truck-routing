import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, planTrip } from '../api/client'
import type { PlanRequest, PlanResponse } from '../api/types'

export type PlanState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'done'; plan: PlanResponse; req: PlanRequest; seq: number }
  | { status: 'error'; message: string }

export function usePlan() {
  const [state, setState] = useState<PlanState>({ status: 'idle' })
  const inFlight = useRef<AbortController | null>(null)
  const seq = useRef(0)

  const run = useCallback(async (req: PlanRequest) => {
    // A new plan replaces any request still running.
    inFlight.current?.abort()
    const ctrl = new AbortController()
    inFlight.current = ctrl
    setState({ status: 'loading' })
    try {
      const plan = await planTrip(req, ctrl.signal)
      seq.current += 1
      setState({ status: 'done', plan, req, seq: seq.current })
    } catch (e) {
      if (ctrl.signal.aborted) return
      const message = e instanceof ApiError ? e.message : 'Something went wrong. Try again.'
      setState({ status: 'error', message })
    }
  }, [])

  useEffect(() => () => inFlight.current?.abort(), [])

  return { state, run }
}
