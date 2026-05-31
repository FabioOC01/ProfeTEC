const PATHS = {
  home: (
    <>
      <path d="M3.5 11.5 12 4l8.5 7.5" />
      <path d="M5.5 10v9.5h13V10" />
      <path d="M10 19.5V14h4v5.5" />
    </>
  ),
  chat: (
    <>
      <path d="M4 5.5h16v11H9l-5 4z" />
      <path d="M8 10h8M8 13h5" />
    </>
  ),
  quiz: (
    <>
      <path d="M5 4.5h11l3 3v12H5z" />
      <path d="M9 10.5l2 2 4-4.5" />
      <path d="M9 16h6" />
    </>
  ),
  book: (
    <>
      <path d="M4 5.5C6.5 4 9 4 12 5.5 15 4 17.5 4 20 5.5v13C17.5 17 15 17 12 18.5 9 17 6.5 17 4 18.5z" />
      <path d="M12 5.5v13" />
    </>
  ),
  send: (
    <>
      <path d="M4 12 20 4l-3 16-5-7z" />
      <path d="M12 13 4 12" />
    </>
  ),
  sparkle: (
    <path d="M12 3.5v4M12 16.5v4M3.5 12h4M16.5 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18" />
  ),
  file: (
    <>
      <path d="M7 4h8l4 4v12H7z" />
      <path d="M15 4v4h4" />
    </>
  ),
  check: <path d="M5 12.5 9.5 17 19 7" />,
  x:     <path d="M6 6l12 12M18 6 6 18" />,
  arrow: <path d="M5 12h14M13 5l7 7-7 7" />,
  chevron: <path d="M9 6l6 6-6 6" />,
  plus:    <path d="M12 5v14M5 12h14" />,
  search: (
    <>
      <circle cx="11" cy="11" r="6.5" />
      <path d="m20 20-3.5-3.5" />
    </>
  ),
  bell: (
    <>
      <path d="M6 16h12l-1.5-2v-3.5a4.5 4.5 0 1 0-9 0V14z" />
      <path d="M10 19a2 2 0 0 0 4 0" />
    </>
  ),
  bolt:   <path d="M13 3 5 14h6l-1 7 8-11h-6z" />,
  target: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="12" r="4.5" />
      <circle cx="12" cy="12" r="1.2" />
    </>
  ),
  mic: (
    <>
      <rect x="9.5" y="3.5" width="5" height="11" rx="2.5" />
      <path d="M6 11.5a6 6 0 0 0 12 0M12 17.5V21M9 21h6" />
    </>
  ),
  paperclip: <path d="M20 11.5 12 19.5a5 5 0 0 1-7-7L13.5 4a3.5 3.5 0 0 1 5 5L10 17.5a2 2 0 0 1-3-3l7-7" />,
  user: (
    <>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M5 20c1.5-3.5 4.2-5 7-5s5.5 1.5 7 5" />
    </>
  ),
  logout: (
    <>
      <path d="M15 5h4v14h-4" />
      <path d="M3 12h13M11 7l5 5-5 5" />
    </>
  ),
  upload: (
    <>
      <path d="M12 16V4" />
      <path d="M7 9l5-5 5 5" />
      <path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
    </>
  ),
  trash: (
    <>
      <path d="M4 7h16" />
      <path d="M6 7v13a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V7" />
      <path d="M9 7V4h6v3" />
      <path d="M10 11v6M14 11v6" />
    </>
  ),
}

export default function Icon({ name, size = 18, style, ...rest }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ flex: 'none', ...style }}
      {...rest}
    >
      {PATHS[name] || null}
    </svg>
  )
}
