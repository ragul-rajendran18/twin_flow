import type { ReactNode } from 'react'

export type BadgeTone = 'normal' | 'moderate' | 'high' | 'info' | 'muted' | 'success' | 'warning' | 'danger'

const TONE_CLASS: Record<BadgeTone, string> = {
  normal: 'badge badge-normal',
  moderate: 'badge badge-moderate',
  high: 'badge badge-high',
  info: 'badge badge-info',
  muted: 'badge badge-muted',
  success: 'badge badge-success',
  warning: 'badge badge-warning',
  danger: 'badge badge-danger',
}

export function toneForLevel(level: string | null | undefined): BadgeTone {
  switch ((level ?? '').toUpperCase()) {
    case 'HIGH':
      return 'high'
    case 'MODERATE':
      return 'moderate'
    case 'LOW':
      return 'warning'
    case 'NORMAL':
    case 'LOW_RISK':
      return 'normal'
    default:
      return 'muted'
  }
}

export default function Badge({ tone, children }: { tone: BadgeTone; children: ReactNode }) {
  return <span className={TONE_CLASS[tone]}>{children}</span>
}
