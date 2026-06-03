import './bible-map.css'
import { useState } from 'react'
import { BibleMapClient } from './components/BibleMapClient'
import { TempleSandbox } from './components/TempleSandbox'

interface Props {
  onBack?: () => void
}

// Vite 入口：圣经地图集（A 策略，新独立视图）。地图视图 / 3D 圣殿沙盘内部切换。
export default function BibleAtlasPage({ onBack }: Props) {
  const [view, setView] = useState<'map' | 'temple'>('map')

  if (view === 'temple') {
    return (
      <div className="h-full w-full overflow-hidden bg-[#0b1220] text-gray-200">
        <TempleSandbox onBack={() => setView('map')} />
      </div>
    )
  }

  return (
    <div className="flex h-full w-full flex-col overflow-y-auto bg-[#0b1220] text-gray-200">
      <header className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <div className="flex items-center gap-3">
          {onBack && (
            <button onClick={onBack} className="rounded-lg border border-white/15 bg-white/5 px-2.5 py-1.5 text-sm text-gray-200 hover:bg-white/10">
              ‹
            </button>
          )}
          <div>
            <h1 className="text-lg font-bold text-white">圣经地图集 · Bible Atlas</h1>
            <p className="text-xs text-gray-400">十二支派 · 士师 · 列国兴衰 · 先知预言 · 帝国扩张 · 基甸战役</p>
          </div>
        </div>
        <button
          onClick={() => setView('temple')}
          className="rounded-lg border border-amber-400/40 bg-amber-400/10 px-3 py-1.5 text-sm text-amber-300 hover:bg-amber-400/20"
        >
          🏛️ 3D 圣殿沙盘
        </button>
      </header>
      <div className="flex-1">
        <BibleMapClient />
      </div>
    </div>
  )
}
