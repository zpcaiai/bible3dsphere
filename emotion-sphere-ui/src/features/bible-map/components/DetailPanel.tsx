'use client'
import type { BibleMapSelection } from '../domain/types'
import { formatYear } from '../lib/format'
import { STATUS_COLORS } from '../lib/colors'

interface Props {
  selection: BibleMapSelection | null
}

const STATUS_LABEL: Record<string, string> = {
  stable: '稳固', disputed: '争夺中', oppressed: '受压制', lost: '失守', empire: '帝国',
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3 py-0.5 text-sm">
      <span className="text-gray-400">{label}</span>
      <span className="text-right text-gray-100">{value}</span>
    </div>
  )
}

export function DetailPanel({ selection }: Props) {
  if (!selection) {
    return (
      <div className="rounded-xl border border-white/10 bg-white/5 p-4">
        <div className="text-sm text-gray-400">
          点击地图上的支派 / 帝国疆域，或左侧事件、图层中的预言与战役，查看详情。
        </div>
      </div>
    )
  }

  if (selection.kind === 'territory' && selection.territory) {
    const t = selection.territory
    return (
      <div className="rounded-xl border border-white/10 bg-white/5 p-4">
        <div className="mb-2 flex items-center gap-2">
          <span className="h-3 w-3 rounded-sm" style={{ background: STATUS_COLORS[t.status] }} />
          <h3 className="text-lg font-bold text-white">{t.nameZh}</h3>
          <span className="text-xs text-gray-400">{t.name}</span>
        </div>
        <Row label="类型" value={t.ownerType === 'tribe' ? '支派' : '帝国'} />
        <Row label="时期" value={`${formatYear(t.startYear)} – ${t.endYear === null ? '今' : formatYear(t.endYear)}`} />
        <Row label="控制指数" value={`${t.controlScore} / 100`} />
        <Row label="状态" value={STATUS_LABEL[t.status] ?? t.status} />
        {t.description && <p className="mt-2 text-sm leading-relaxed text-gray-300">{t.description}</p>}
      </div>
    )
  }

  if (selection.kind === 'prophecy' && selection.prophecy) {
    const p = selection.prophecy
    return (
      <div className="rounded-xl border border-white/10 bg-white/5 p-4">
        <h3 className="mb-2 text-lg font-bold text-white">{p.book} {p.chapterStart}{p.chapterEnd ? `-${p.chapterEnd}` : ''} · 论{p.targetNationZh}</h3>
        <Row label="对象" value={`${p.targetNationZh} (${p.targetNation})`} />
        <Row label="类型" value={p.prophecyType} />
        <Row label="发出" value={p.sourceLocation} />
        {p.fulfillmentYear !== null && <Row label="应验" value={formatYear(p.fulfillmentYear)} />}
        <p className="mt-2 text-sm leading-relaxed text-gray-300">{p.description}</p>
        {p.fulfillmentDescription && (
          <p className="mt-2 rounded-lg bg-emerald-500/10 p-2 text-sm leading-relaxed text-emerald-300">
            应验：{p.fulfillmentDescription}
          </p>
        )}
      </div>
    )
  }

  if (selection.kind === 'campaign' && selection.campaign) {
    const c = selection.campaign
    return (
      <div className="rounded-xl border border-white/10 bg-white/5 p-4">
        <h3 className="mb-2 text-lg font-bold text-white">{c.nameZh}</h3>
        <Row label="名称" value={c.name} />
        {c.commanderZh && <Row label="统帅" value={c.commanderZh} />}
        <Row label="年代" value={formatYear(c.startYear)} />
        {c.book && <Row label="经文" value={`${c.book} ${c.chapter ?? ''}`} />}
        {c.description && <p className="mt-2 text-sm leading-relaxed text-gray-300">{c.description}</p>}
      </div>
    )
  }

  if (selection.kind === 'event' && selection.event) {
    const e = selection.event
    return (
      <div className="rounded-xl border border-white/10 bg-white/5 p-4">
        <h3 className="mb-2 text-lg font-bold text-white">{e.titleZh}</h3>
        <Row label="年代" value={formatYear(e.startYear)} />
        {e.locationName && <Row label="地点" value={e.locationName} />}
        {e.book && <Row label="经文" value={`${e.book} ${e.chapter ?? ''}`} />}
        {e.description && <p className="mt-2 text-sm leading-relaxed text-gray-300">{e.description}</p>}
        {e.spiritualMeaning && (
          <p className="mt-2 rounded-lg bg-amber-500/10 p-2 text-sm leading-relaxed text-amber-200">
            属灵意义：{e.spiritualMeaning}
          </p>
        )}
      </div>
    )
  }

  return null
}
