'use client'
import { YEAR_MIN, YEAR_MAX, YEAR_STEP } from '../domain/constants'
import { formatYear } from '../lib/format'

interface Props {
  year: number
  onYearChange: (year: number) => void
}

export function TimelineSlider({ year, onYearChange }: Props) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-3">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-xs text-gray-400">时间轴</span>
        <span className="text-lg font-bold text-amber-400">{formatYear(year)}</span>
      </div>
      <input
        type="range"
        min={YEAR_MIN}
        max={YEAR_MAX}
        step={YEAR_STEP}
        value={year}
        onChange={(e) => onYearChange(Number.parseInt(e.target.value, 10))}
        className="w-full accent-amber-400"
        aria-label="年份时间轴"
      />
      <div className="mt-1 flex justify-between text-[10px] text-gray-500">
        <span>{formatYear(YEAR_MIN)}</span>
        <span>{formatYear(YEAR_MAX)}</span>
      </div>
    </div>
  )
}
