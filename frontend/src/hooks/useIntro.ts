import { useEffect, useState } from 'react'
import { easeOutCubic, reducedMotion } from '../lib/motion'

/** 0 -> 1 over `duration` ms once `run` is true (eased), or straight to 1 when motion is reduced. */
export function useIntro(duration: number, run = true) {
  const [progress, setProgress] = useState(() => (reducedMotion() ? 1 : 0))

  useEffect(() => {
    if (!run || reducedMotion()) return
    let raf = 0
    const start = performance.now()
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      setProgress(easeOutCubic(t))
      if (t < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [duration, run])

  return progress
}
