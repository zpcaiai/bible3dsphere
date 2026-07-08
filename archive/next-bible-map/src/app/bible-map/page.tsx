import Link from 'next/link'
import { BibleMapClient } from '@/features/bible-map/components/BibleMapClient'

export const metadata = {
  title: '圣经地图 · Bible Map',
}

export default function BibleMapPage() {
  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <div>
          <h1 className="text-lg font-bold text-white">圣经地图 · Bible Map</h1>
          <p className="text-xs text-gray-400">十二支派分地 · 士师时代 · 列国兴衰 · 先知预言 · 帝国扩张 · 基甸战役</p>
        </div>
        <Link href="/bible-map/temple" className="rounded-lg border border-amber-400/40 bg-amber-400/10 px-3 py-1.5 text-sm text-amber-300 hover:bg-amber-400/20">
          🏛️ 3D 圣殿沙盘
        </Link>
      </header>
      <BibleMapClient />
    </div>
  )
}
