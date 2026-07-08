import type { TerritoryStatus } from '../domain/types'

export const STATUS_COLORS: Record<TerritoryStatus, string> = {
  stable: '#22c55e',
  disputed: '#eab308',
  oppressed: '#ef4444',
  lost: '#6b7280',
  empire: '#8b5cf6',
}

export function colorForStatus(status: TerritoryStatus, override?: string | null): string {
  return override || STATUS_COLORS[status] || '#3b82f6'
}

// controlScore(0-100) → fill 不透明度(0.15-0.7)
export function opacityForControl(controlScore: number): number {
  const c = Math.max(0, Math.min(100, controlScore))
  return 0.15 + (c / 100) * 0.55
}

export const PROPHECY_COLORS: Record<string, string> = {
  judgment: '#ef4444',
  restoration: '#22c55e',
  warning: '#eab308',
  messianic: '#38bdf8',
}
