'use client'
import { LAYERS } from '../domain/constants'
import type { BibleLayer } from '../domain/types'
import { cn } from '@/lib/utils'

interface Props {
  layer: BibleLayer
  onLayerChange: (layer: BibleLayer) => void
}

export function LayerSwitcher({ layer, onLayerChange }: Props) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-3">
      <div className="mb-2 text-xs text-gray-400">图层</div>
      <div className="flex flex-wrap gap-2">
        {LAYERS.map((l) => (
          <button
            key={l.id}
            type="button"
            onClick={() => onLayerChange(l.id)}
            className={cn(
              'rounded-lg border px-3 py-1.5 text-sm font-medium transition',
              layer === l.id
                ? 'border-amber-400/60 bg-amber-400/15 text-amber-300'
                : 'border-white/10 bg-white/5 text-gray-300 hover:bg-white/10',
            )}
          >
            {l.label}
          </button>
        ))}
      </div>
    </div>
  )
}
