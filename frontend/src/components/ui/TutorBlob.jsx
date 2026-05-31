import { useEffect, useRef, useState } from 'react'

const PALETTES = {
  amber: { a: 'var(--amber-300)', b: 'var(--amber-500)', ring: 'var(--amber-500)' },
  lav: { a: 'var(--lav-200)', b: 'var(--lav-500)', ring: 'var(--lav-500)' },
  mint: { a: 'var(--mint-300)', b: 'var(--mint-500)', ring: 'var(--mint-500)' },
}

// Caras disponibles. `thinking` (legacy) equivale a expression="thinking".
const TUTOR_EXPRESSIONS = ['happy', 'thinking', 'wink', 'surprised', 'sleepy', 'content']

function Eye({ side, expr }) {
  const isLeft = side === 'left'
  const pos = isLeft ? { left: '30%' } : { right: '30%' }

  // Ojo cerrado (línea): dormido, o el ojo derecho del guiño
  if (expr === 'sleepy' || (expr === 'wink' && !isLeft)) {
    return (
      <div
        style={{
          position: 'absolute', top: '48%', ...pos,
          width: '12%', height: '3%',
          background: 'var(--ink-900)', borderRadius: 3, opacity: 0.85,
        }}
      />
    )
  }

  // Ojos sonrientes (arco hacia arriba): contento
  if (expr === 'content') {
    return (
      <div
        style={{
          position: 'absolute', top: '45%', ...pos,
          width: '12%', height: '8%',
          borderTop: '2.5px solid var(--ink-900)',
          borderRadius: '90% 90% 0 0 / 100% 100% 0 0',
          opacity: 0.85,
        }}
      />
    )
  }

  // Punto redondo con parpadeo (más grande si está sorprendido)
  const big = expr === 'surprised'
  return (
    <div
      style={{
        position: 'absolute', top: '44%', ...pos,
        width: big ? '12%' : '10%', height: big ? '16%' : '14%',
        background: 'var(--ink-900)', borderRadius: '50%',
        animation: 'blink 4.2s ease-in-out infinite',
      }}
    />
  )
}

function Mouth({ expr }) {
  // Boca pequeña redonda (pensando)
  if (expr === 'thinking') {
    return (
      <div
        style={{
          position: 'absolute', top: '62%', left: '44%',
          width: '12%', height: '12%',
          background: 'var(--ink-900)', borderRadius: '50%', opacity: 0.55,
        }}
      />
    )
  }
  // Boca abierta "O" (sorpresa)
  if (expr === 'surprised') {
    return (
      <div
        style={{
          position: 'absolute', top: '60%', left: '42%',
          width: '16%', height: '18%',
          background: 'var(--ink-900)', borderRadius: '50%', opacity: 0.6,
        }}
      />
    )
  }
  // Línea suave (dormido)
  if (expr === 'sleepy') {
    return (
      <div
        style={{
          position: 'absolute', top: '64%', left: '43%',
          width: '14%', height: '5%',
          borderBottom: '2px solid var(--ink-900)',
          borderRadius: '0 0 40% 40%', opacity: 0.5,
        }}
      />
    )
  }
  // Sonrisa (happy / wink / content)
  return (
    <div
      style={{
        position: 'absolute', top: '61%', left: '40%',
        width: '20%', height: '10%',
        borderBottom: '2px solid var(--ink-900)',
        borderRadius: '0 0 40% 40% / 0 0 90% 90%', opacity: 0.7,
      }}
    />
  )
}

export default function TutorBlob({ size = 56, thinking = false, mode = 'directo', tone, expression }) {
  const socratico = mode === 'socratico'
  // `thinking` (legacy) tiene prioridad; si no, usa `expression`; por defecto, feliz.
  const expr = thinking ? 'thinking' : TUTOR_EXPRESSIONS.includes(expression) ? expression : 'happy'
  const isThinking = expr === 'thinking'

  // Color: `tone` explícito tiene prioridad; si no, según el modo pedagógico
  // (ámbar = directo, lavanda = socrático).
  const palette = PALETTES[tone] || (socratico ? PALETTES.lav : PALETTES.amber)
  const fillA = palette.a
  const fillB = palette.b
  const ringColor = palette.ring

  // Dispara una animación de "pop" + halo cada vez que cambia el modo,
  // sin animar en el primer render.
  const [pulseKey, setPulseKey] = useState(0)
  const firstRender = useRef(true)
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false
      return
    }
    setPulseKey((k) => k + 1)
  }, [mode])

  const popping = pulseKey > 0

  return (
    <div style={{ width: size, height: size, position: 'relative', flex: 'none' }}>
      {/* Halo que se expande al cambiar de modo */}
      {popping && (
        <span
          key={`ring-${pulseKey}`}
          style={{
            position: 'absolute',
            inset: -2,
            borderRadius: '50%',
            border: `2px solid ${ringColor}`,
            animation: 'blob-ring .55s ease-out forwards',
            pointerEvents: 'none',
          }}
        />
      )}

      <div
        key={`body-${pulseKey}`}
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '60% 40% 55% 45% / 50% 60% 40% 50%',
          background: `radial-gradient(circle at 35% 30%, ${fillA} 0%, ${fillB} 70%)`,
          transition: 'background .45s ease',
          animation: popping
            ? `blob-pop .6s cubic-bezier(.34,1.56,.64,1), ${
                isThinking ? 'blob-breathe 1.6s ease-in-out .6s infinite' : 'blob-breathe 5s ease-in-out .6s infinite'
              }`
            : isThinking
              ? 'blob-breathe 1.6s ease-in-out infinite'
              : 'blob-breathe 5s ease-in-out infinite',
          boxShadow:
            'inset -4px -6px 12px rgba(0,0,0,.08), inset 4px 6px 14px rgba(255,255,255,.45)',
        }}
      />
      {/* eyes */}
      <Eye side="left" expr={expr} />
      <Eye side="right" expr={expr} />
      {/* mouth */}
      <Mouth expr={expr} />
      {/* cheeks */}
      <div
        style={{
          position: 'absolute',
          top: '57%',
          left: '18%',
          width: '12%',
          height: '8%',
          background: 'rgba(216,90,71,.3)',
          borderRadius: '50%',
          filter: 'blur(2px)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          top: '57%',
          right: '18%',
          width: '12%',
          height: '8%',
          background: 'rgba(216,90,71,.3)',
          borderRadius: '50%',
          filter: 'blur(2px)',
        }}
      />
    </div>
  )
}
