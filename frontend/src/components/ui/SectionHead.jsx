export default function SectionHead({ eyebrow, title, action }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-end',
        justifyContent: 'space-between',
        gap: 12,
        marginBottom: 16,
      }}
    >
      <div style={{ minWidth: 0 }}>
        {eyebrow && <div className="t-eyebrow" style={{ marginBottom: 6 }}>{eyebrow}</div>}
        <h2 style={{ margin: 0 }}>{title}</h2>
      </div>
      {action}
    </div>
  )
}
