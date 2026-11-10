/** App mark: a route shield with a lane line, in the same shape as the route badges. */
export default function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 32 34" aria-hidden="true">
      <path d="M3 3c5 1.6 9 1.6 13 0 4 1.6 8 1.6 13 0 1.6 5 2 9.5 2 13 0 8.6-6 14-15 16C7 30 1 24.6 1 16 1 12.5 1.4 8 3 3z" />
      <path className="mark-lane" d="M16 8v4M16 15v4M16 22v4" />
    </svg>
  )
}
