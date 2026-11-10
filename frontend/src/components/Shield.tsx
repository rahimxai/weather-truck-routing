/** Route letter in an interstate-style shield. */
export default function Shield({ id, active }: { id: string; active: boolean }) {
  return (
    <svg className={`shield${active ? ' active' : ''}`} viewBox="0 0 32 34" aria-hidden="true">
      <path d="M3 3c5 1.6 9 1.6 13 0 4 1.6 8 1.6 13 0 1.6 5 2 9.5 2 13 0 8.6-6 14-15 16C7 30 1 24.6 1 16 1 12.5 1.4 8 3 3z" />
      <text x="16" y="22.5" textAnchor="middle">
        {id}
      </text>
    </svg>
  )
}
