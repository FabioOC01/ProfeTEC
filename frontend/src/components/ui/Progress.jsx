export default function Progress({ value = 0, color = 'var(--amber-500)' }) {
  return (
    <div
      style={{
        height: 6,
        width: '100%',
        background: 'var(--ink-100)',
        borderRadius: 99,
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          height: '100%',
          width: `${Math.max(0, Math.min(100, value))}%`,
          background: color,
          borderRadius: 99,
          transition: 'width .4s ease',
        }}
      />
    </div>
  )
}
