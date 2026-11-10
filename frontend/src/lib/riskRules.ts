// The assessment's thresholds, for the map key. Must match backend/routing/domain/risk.py;
// riskRules.test.ts reads that file and fails if they drift apart.
export const WIND_MPH = [25, 35, 45, 55]
export const RAIN_IN_HR = [0.1, 0.25, 0.5, 1.0]
export const SNOW_IN_HR = [0.5, 1.0, 2.0, 3.0]
export const NO_TRAVEL_LOAD_LB = 30_000
export const SEVERE_LOAD_LB = 40_000

/** Low to No Travel labels for one condition. Wind's top band is >=, rain and snow's is >. */
export function bandLabels(cuts: number[], digits: number, strictTop: boolean) {
  const n = cuts.map((c) => c.toFixed(digits))
  return [
    `under ${n[0]}`,
    `${n[0]}–${n[1]}`,
    `${n[1]}–${n[2]}`,
    `${n[2]}–${n[3]}`,
    strictTop ? `over ${n[3]}` : `${n[3]}+`,
  ]
}
