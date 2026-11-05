import type { SVGProps } from 'react'

type P = SVGProps<SVGSVGElement>

function Icon({ children, ...props }: P) {
  return (
    <svg
      width={16}
      height={16}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  )
}

export const ChevronLeft = (p: P) => (
  <Icon {...p}>
    <path d="m15 18-6-6 6-6" />
  </Icon>
)
export const ChevronRight = (p: P) => (
  <Icon {...p}>
    <path d="m9 18 6-6-6-6" />
  </Icon>
)
export const ChevronUp = (p: P) => (
  <Icon {...p}>
    <path d="m18 15-6-6-6 6" />
  </Icon>
)
export const ChevronDown = (p: P) => (
  <Icon {...p}>
    <path d="m6 9 6 6 6-6" />
  </Icon>
)
export const ListIcon = (p: P) => (
  <Icon {...p}>
    <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />
  </Icon>
)
export const InfoIcon = (p: P) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="10" />
    <path d="M12 16v-4M12 8h.01" />
  </Icon>
)
export const KeyboardIcon = (p: P) => (
  <Icon {...p}>
    <rect x="2" y="6" width="20" height="12" rx="2" />
    <path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M8 14h8" />
  </Icon>
)
export const SunIcon = (p: P) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
  </Icon>
)
export const MoonIcon = (p: P) => (
  <Icon {...p}>
    <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
  </Icon>
)
export const MonitorIcon = (p: P) => (
  <Icon {...p}>
    <rect x="2" y="3" width="20" height="14" rx="2" />
    <path d="M8 21h8M12 17v4" />
  </Icon>
)
export const TerminalIcon = (p: P) => (
  <Icon {...p}>
    <path d="m4 17 6-6-6-6M12 19h8" />
  </Icon>
)
export const CheckIcon = (p: P) => (
  <Icon {...p} strokeWidth={3}>
    <path d="M20 6 9 17l-5-5" />
  </Icon>
)
export const XIcon = (p: P) => (
  <Icon {...p}>
    <path d="M18 6 6 18M6 6l12 12" />
  </Icon>
)
export const WarnIcon = (p: P) => (
  <Icon {...p}>
    <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
    <path d="M12 9v4M12 17h.01" />
  </Icon>
)
export const MaximizeIcon = (p: P) => (
  <Icon {...p}>
    <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
  </Icon>
)
export const MinimizeIcon = (p: P) => (
  <Icon {...p}>
    <path d="M4 14h6v6M20 10h-6V4M14 10l7-7M3 21l7-7" />
  </Icon>
)
export const TableIcon = (p: P) => (
  <Icon {...p}>
    <rect x="3" y="4" width="18" height="16" rx="2" />
    <path d="M3 10h18M3 15h18M9 4v16" />
  </Icon>
)
export const GridIcon = (p: P) => (
  <Icon {...p}>
    <rect x="3" y="3" width="7" height="7" rx="1" />
    <rect x="14" y="3" width="7" height="7" rx="1" />
    <rect x="3" y="14" width="7" height="7" rx="1" />
    <rect x="14" y="14" width="7" height="7" rx="1" />
  </Icon>
)
export const ImageIcon = (p: P) => (
  <Icon {...p}>
    <rect x="3" y="4" width="18" height="16" rx="2" />
    <circle cx="9" cy="10" r="2" />
    <path d="m21 16-5-5-8 8" />
  </Icon>
)
export const BracesIcon = (p: P) => (
  <Icon {...p}>
    <path d="M8 3H7a2 2 0 0 0-2 2v5a2 2 0 0 1-2 2 2 2 0 0 1 2 2v5a2 2 0 0 0 2 2h1M16 3h1a2 2 0 0 1 2 2v5a2 2 0 0 0 2 2 2 2 0 0 0-2 2v5a2 2 0 0 1-2 2h-1" />
  </Icon>
)
export const CodeIcon = (p: P) => (
  <Icon {...p}>
    <path d="m16 18 6-6-6-6M8 6l-6 6 6 6" />
  </Icon>
)
export const TextIcon = (p: P) => (
  <Icon {...p}>
    <path d="M4 6h16M4 12h16M4 18h10" />
  </Icon>
)
export const CopyIcon = (p: P) => (
  <Icon {...p}>
    <rect x="9" y="9" width="12" height="12" rx="2" />
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
  </Icon>
)
export const DatabaseIcon = (p: P) => (
  <Icon {...p}>
    <ellipse cx="12" cy="5" rx="9" ry="3" />
    <path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5M3 12c0 1.7 4 3 9 3s9-1.3 9-3" />
  </Icon>
)
