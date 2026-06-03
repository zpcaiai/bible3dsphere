'use client'
import type { BibleMapEventDTO } from '../domain/types'
import { formatYear } from '../lib/format'

interface Props {
  events: BibleMapEventDTO[]
  loading: boolean
  onSelect: (event: BibleMapEventDTO) => void
  selectedId?: string
}

export function EventPanel({ events, loading, onSelect, selectedId }: Props) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-3">
      <div className="mb-2 text-xs text-gray-400">当前年份附近事件</div>
      {loading ? (
        <div className="py-4 text-center text-sm text-gray-500">加载中…</div>
      ) : events.length === 0 ? (
        <div className="py-4 text-center text-sm text-gray-500">此年份附近暂无事件</div>
      ) : (
        <ul className="space-y-1.5">
          {events.map((e) => (
            <li key={e.id}>
              <button
                type="button"
                onClick={() => onSelect(e)}
                className={`w-full rounded-lg border px-3 py-2 text-left text-sm transition ${
                  selectedId === e.id
                    ? 'border-amber-400/60 bg-amber-400/10'
                    : 'border-white/10 bg-white/[0.03] hover:bg-white/10'
                }`}
              >
                <div className="font-semibold text-gray-100">{e.titleZh}</div>
                <div className="text-[11px] text-gray-400">
                  {formatYear(e.startYear)}
                  {e.locationName ? ` · ${e.locationName}` : ''}
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
