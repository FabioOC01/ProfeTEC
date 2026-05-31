const PALETTES = {
  amber:  ['#fdf0e4', '#f7a87e', '#c46c34', '#fde4d2'],
  mint:   ['#e2f0ea', '#7db89e', '#4a8a6e', '#d0e8db'],
  lav:    ['#efebf8', '#9789d1', '#6a5da8', '#e0daf2'],
}

export default function CourseCover({ variant = 'amber', size = 'tall' }) {
  const p = PALETTES[variant] || PALETTES.amber
  const h = size === 'tall' ? 130 : 80
  return (
    <div
      style={{
        height: h,
        width: '100%',
        background: p[0],
        borderRadius: 'var(--r-lg) var(--r-lg) 0 0',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <svg
        viewBox="0 0 400 200"
        preserveAspectRatio="xMidYMid slice"
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
      >
        <circle cx="60"  cy="160" r="80"  fill={p[1]} opacity=".55" />
        <circle cx="320" cy="40"  r="110" fill={p[3]} />
        <circle cx="280" cy="170" r="55"  fill={p[2]} opacity=".75" />
        <path
          d="M0 130 Q 100 90 200 120 T 400 110"
          fill="none"
          stroke={p[2]}
          strokeWidth="2"
          opacity=".45"
        />
        <path
          d="M0 150 Q 100 110 200 140 T 400 130"
          fill="none"
          stroke={p[2]}
          strokeWidth="2"
          opacity=".25"
        />
      </svg>
    </div>
  )
}

export function colorForIndex(i) {
  const order = ['amber', 'mint', 'lav']
  return order[i % order.length]
}
