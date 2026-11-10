export const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

// Shared by the map draw-on and the CSS strip-map reveal so the two stay in step.
export const DRAW_MS = 1400

export const easeOutCubic = (t: number) => 1 - (1 - t) ** 3
