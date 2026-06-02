// Renderizador Markdown ligero y sin dependencias para las respuestas del tutor.
// Cubre lo que genera el modelo: **negrita**, *cursiva*, `código`, listas con
// viñetas (* / -), listas numeradas (1.) y párrafos. No pretende ser un parser
// Markdown completo; busca verse bien y no mostrar los asteriscos en crudo.

const INLINE_RE = /(\*\*([^*]+)\*\*|__([^_]+)__|\*([^*\n]+)\*|`([^`]+)`)/

function renderInline(text) {
  const nodes = []
  let remaining = text
  let key = 0
  let match
  while ((match = INLINE_RE.exec(remaining))) {
    const before = remaining.slice(0, match.index)
    if (before) nodes.push(before)
    if (match[2] !== undefined) nodes.push(<strong key={key++}>{match[2]}</strong>)
    else if (match[3] !== undefined) nodes.push(<strong key={key++}>{match[3]}</strong>)
    else if (match[4] !== undefined) nodes.push(<em key={key++}>{match[4]}</em>)
    else if (match[5] !== undefined)
      nodes.push(
        <code key={key++} style={st.code}>
          {match[5]}
        </code>,
      )
    remaining = remaining.slice(match.index + match[0].length)
  }
  if (remaining) nodes.push(remaining)
  return nodes
}

export default function Markdown({ text }) {
  if (!text) return null

  const lines = String(text).split('\n')
  const blocks = []
  let list = null

  const flushList = () => {
    if (list) {
      blocks.push(list)
      list = null
    }
  }

  lines.forEach((raw) => {
    const line = raw.trimEnd()
    const bullet = /^\s*[*-]\s+(.*)$/.exec(line)
    const numbered = /^\s*\d+\.\s+(.*)$/.exec(line)
    const heading = /^\s*#{1,4}\s+(.*)$/.exec(line)

    if (bullet) {
      if (!list || list.type !== 'ul') {
        flushList()
        list = { type: 'ul', items: [] }
      }
      list.items.push(bullet[1])
    } else if (numbered) {
      if (!list || list.type !== 'ol') {
        flushList()
        list = { type: 'ol', items: [] }
      }
      list.items.push(numbered[1])
    } else if (heading) {
      flushList()
      blocks.push({ type: 'h', text: heading[1] })
    } else if (line.trim() === '') {
      flushList()
    } else {
      flushList()
      blocks.push({ type: 'p', text: line })
    }
  })
  flushList()

  return (
    <div style={st.root}>
      {blocks.map((b, i) => {
        if (b.type === 'p') {
          return (
            <p key={i} style={st.p}>
              {renderInline(b.text)}
            </p>
          )
        }
        if (b.type === 'h') {
          return (
            <p key={i} style={st.h}>
              {renderInline(b.text)}
            </p>
          )
        }
        if (b.type === 'ul') {
          return (
            <ul key={i} style={st.list}>
              {b.items.map((it, j) => (
                <li key={j} style={st.li}>
                  {renderInline(it)}
                </li>
              ))}
            </ul>
          )
        }
        return (
          <ol key={i} style={st.list}>
            {b.items.map((it, j) => (
              <li key={j} style={st.li}>
                {renderInline(it)}
              </li>
            ))}
          </ol>
        )
      })}
    </div>
  )
}

const st = {
  root: { display: 'flex', flexDirection: 'column', gap: 8 },
  p: { margin: 0 },
  h: { margin: 0, fontWeight: 600 },
  list: { margin: 0, paddingLeft: 22, display: 'flex', flexDirection: 'column', gap: 4 },
  li: { margin: 0 },
  code: {
    fontFamily: 'var(--font-mono)',
    fontSize: '0.88em',
    background: 'var(--paper-2)',
    border: '1px solid var(--ink-100)',
    borderRadius: 4,
    padding: '1px 5px',
  },
}
