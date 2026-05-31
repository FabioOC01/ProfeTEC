import { useEffect, useRef } from 'react'
import Icon from './Icon.jsx'

/**
 * Floating source card. `chunk` shape:
 *   { nombre_doc, pagina, fragmento, score?, tipo? }
 * `anchor` = { x, y } in viewport coordinates.
 */
export default function CitationPopover({ index, chunk, anchor, onClose }) {
  const ref = useRef(null)

  useEffect(() => {
    function onDoc(e) {
      if (ref.current && !ref.current.contains(e.target) && !e.target.closest('.cite')) {
        onClose()
      }
    }
    function onEsc(e) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('mousedown', onDoc)
    document.addEventListener('keydown', onEsc)
    return () => {
      document.removeEventListener('mousedown', onDoc)
      document.removeEventListener('keydown', onEsc)
    }
  }, [onClose])

  if (!chunk) return null

  const left = Math.min(anchor?.x ?? 0, window.innerWidth - 380)
  const top = (anchor?.y ?? 0) + 8

  return (
    <div
      ref={ref}
      className="fade-up"
      style={{
        position: 'fixed',
        zIndex: 80,
        top,
        left,
        width: 360,
        background: 'var(--surface)',
        border: '1px solid var(--ink-100)',
        borderRadius: 'var(--r-lg)',
        boxShadow: 'var(--sh-pop)',
        padding: 16,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 10 }}>
        <div
          style={{
            width: 28,
            height: 28,
            flex: 'none',
            borderRadius: 6,
            background: 'var(--cite-bg)',
            color: 'var(--cite-fg)',
            display: 'grid',
            placeItems: 'center',
            fontFamily: 'var(--font-mono)',
            fontWeight: 600,
            fontSize: 13,
          }}
        >
          {index}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontSize: 14,
              fontWeight: 600,
              lineHeight: 1.25,
              color: 'var(--ink-900)',
            }}
          >
            {chunk.nombre_doc || 'Documento del curso'}
          </div>
          <div style={{ fontSize: 12, color: 'var(--ink-500)', marginTop: 2 }}>
            {chunk.tipo && (
              <>
                <span className="t-mono">{chunk.tipo.toUpperCase()}</span> ·{' '}
              </>
            )}
            <span>pág. {chunk.pagina ?? '—'}</span>
          </div>
        </div>
        <button
          onClick={onClose}
          className="btn btn-ghost"
          style={{ padding: 4, borderRadius: 8 }}
          aria-label="Cerrar"
        >
          <Icon name="x" size={14} />
        </button>
      </div>

      <div
        style={{
          padding: 12,
          background: 'var(--paper-2)',
          borderRadius: 10,
          fontSize: 13,
          lineHeight: 1.55,
          color: 'var(--ink-700)',
          borderLeft: '3px solid var(--cite-ring)',
          marginBottom: 10,
          maxHeight: 180,
          overflowY: 'auto',
        }}
      >
        “{chunk.fragmento}”
      </div>

      {chunk.score != null && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: 12,
          }}
        >
          <span className="t-muted">
            relevancia{' '}
            <span className="t-mono" style={{ color: 'var(--ink-700)' }}>
              {Math.round(chunk.score * 100)}%
            </span>
          </span>
        </div>
      )}
    </div>
  )
}
