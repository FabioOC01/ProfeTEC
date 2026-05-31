import { useEffect, useRef, useState } from 'react'

export default function TutorBlob({ size = 56, thinking = false, mode = 'directo' }) {
  const socratico = mode === 'socratico'

  // Paleta según el modo pedagógico: ámbar (directo) vs. lavanda (socrático)
  const fillA = socratico ? 'var(--lav-200)' : 'var(--amber-300)'
  const fillB = socratico ? 'var(--lav-500)' : 'var(--amber-500)'
  const ringColor = socratico ? 'var(--lav-500)' : 'var(--amber-500)'

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
                thinking ? 'blob-breathe 1.6s ease-in-out .6s infinite' : 'blob-breathe 5s ease-in-out .6s infinite'
              }`
            : thinking
              ? 'blob-breathe 1.6s ease-in-out infinite'
              : 'blob-breathe 5s ease-in-out infinite',
          boxShadow:
            'inset -4px -6px 12px rgba(0,0,0,.08), inset 4px 6px 14px rgba(255,255,255,.45)',
        }}
      />
      {/* eyes */}
      <div
        style={{
          position: 'absolute',
          top: '44%',
          left: '30%',
          width: '10%',
          height: '14%',
          background: 'var(--ink-900)',
          borderRadius: '50%',
          animation: 'blink 4.2s ease-in-out infinite',
        }}
      />
      <div
        style={{
          position: 'absolute',
          top: '44%',
          right: '30%',
          width: '10%',
          height: '14%',
          background: 'var(--ink-900)',
          borderRadius: '50%',
          animation: 'blink 4.2s ease-in-out infinite',
        }}
      />
      {/* mouth */}
      {thinking ? (
        <div
          style={{
            position: 'absolute',
            top: '62%',
            left: '44%',
            width: '12%',
            height: '12%',
            background: 'var(--ink-900)',
            borderRadius: '50%',
            opacity: 0.55,
          }}
        />
      ) : (
        <div
          style={{
            position: 'absolute',
            top: '61%',
            left: '40%',
            width: '20%',
            height: '10%',
            borderBottom: '2px solid var(--ink-900)',
            borderRadius: '0 0 40% 40% / 0 0 90% 90%',
            opacity: 0.7,
          }}
        />
      )}
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
