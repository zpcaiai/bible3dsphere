'use client'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { MapCanvas } from './MapCanvas'
import { TimelineSlider } from './TimelineSlider'
import { LayerSwitcher } from './LayerSwitcher'
import { EventPanel } from './EventPanel'
import { DetailPanel } from './DetailPanel'
import { AICommentaryPanel } from './AICommentaryPanel'
import { DEFAULT_YEAR, DISCLAIMER } from '../domain/constants'
import { formatYear } from '../lib/format'
import { PROPHECY_COLORS } from '../lib/colors'
import { fetchTerritories, fetchEvents, fetchProphecies, fetchCampaigns } from '../lib/dataSource'
import type {
  BibleCampaignDTO,
  BibleLayer,
  BibleMapEventDTO,
  BibleMapSelection,
  BibleProphecyDTO,
  BibleTerritoryDTO,
} from '../domain/types'

export function BibleMapClient() {
  const [year, setYear] = useState<number>(DEFAULT_YEAR)
  const [layer, setLayer] = useState<BibleLayer>('tribes')
  const [territories, setTerritories] = useState<BibleTerritoryDTO[]>([])
  const [events, setEvents] = useState<BibleMapEventDTO[]>([])
  const [prophecies, setProphecies] = useState<BibleProphecyDTO[]>([])
  const [campaigns, setCampaigns] = useState<BibleCampaignDTO[]>([])
  const [eventsLoading, setEventsLoading] = useState(false)
  const [selection, setSelection] = useState<BibleMapSelection | null>(null)
  const [focusEvent, setFocusEvent] = useState<BibleMapEventDTO | null>(null)

  // 疆域：prophecies/campaigns 图层时用 all 作底图
  useEffect(() => {
    const effective: BibleLayer = layer === 'tribes' || layer === 'empires' ? layer : 'all'
    void fetchTerritories(year, effective).then(setTerritories)
  }, [year, layer])

  useEffect(() => {
    setEventsLoading(true)
    void fetchEvents(year).then((d) => {
      setEvents(d)
      setEventsLoading(false)
    })
  }, [year])

  useEffect(() => {
    void fetchProphecies().then(setProphecies)
    void fetchCampaigns().then(setCampaigns)
  }, [])

  const onTerritoryClick = useCallback((id: string) => {
    setTerritories((cur) => {
      const t = cur.find((x) => x.id === id)
      if (t) setSelection({ kind: 'territory', territory: t })
      return cur
    })
  }, [])

  const prophecyForMap = selection?.kind === 'prophecy' ? (selection.prophecy ?? null) : null
  const campaignForMap = selection?.kind === 'campaign' ? (selection.campaign ?? null) : null
  const activeTerritoryId = selection?.kind === 'territory' ? (selection.territory?.id ?? null) : null

  const leftList = useMemo(() => {
    if (layer === 'prophecies') {
      return (
        <div className="rounded-xl border border-white/10 bg-white/5 p-3">
          <div className="mb-2 text-xs text-gray-400">先知预言（点击发射预言射线）</div>
          <ul className="space-y-1.5">
            {prophecies.map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() => setSelection({ kind: 'prophecy', prophecy: p })}
                  className={`w-full rounded-lg border px-3 py-2 text-left text-sm transition ${
                    prophecyForMap?.id === p.id ? 'border-amber-400/60 bg-amber-400/10' : 'border-white/10 bg-white/[0.03] hover:bg-white/10'
                  }`}
                >
                  <span className="mr-2 inline-block h-2 w-2 rounded-full align-middle" style={{ background: PROPHECY_COLORS[p.prophecyType] }} />
                  <span className="font-semibold text-gray-100">{p.book} {p.chapterStart} · 论{p.targetNationZh}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )
    }
    if (layer === 'campaigns') {
      return (
        <div className="rounded-xl border border-white/10 bg-white/5 p-3">
          <div className="mb-2 text-xs text-gray-400">战役（点击播放路线）</div>
          <ul className="space-y-1.5">
            {campaigns.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => setSelection({ kind: 'campaign', campaign: c })}
                  className={`w-full rounded-lg border px-3 py-2 text-left text-sm transition ${
                    campaignForMap?.id === c.id ? 'border-amber-400/60 bg-amber-400/10' : 'border-white/10 bg-white/[0.03] hover:bg-white/10'
                  }`}
                >
                  <div className="font-semibold text-gray-100">{c.nameZh}</div>
                  <div className="text-[11px] text-gray-400">{formatYear(c.startYear)}{c.commanderZh ? ` · ${c.commanderZh}` : ''}</div>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )
    }
    return (
      <EventPanel
        events={events}
        loading={eventsLoading}
        selectedId={selection?.kind === 'event' ? selection.event?.id : undefined}
        onSelect={(e) => {
          setFocusEvent(e)
          setSelection({ kind: 'event', event: e })
        }}
      />
    )
  }, [layer, prophecies, campaigns, events, eventsLoading, selection, prophecyForMap, campaignForMap])

  return (
    <div className="mx-auto flex max-w-[1500px] flex-col gap-3 p-3 lg:h-[calc(100vh-2rem)] lg:flex-row">
      {/* 左栏 */}
      <aside className="flex w-full flex-col gap-3 lg:w-80 lg:overflow-y-auto">
        <LayerSwitcher layer={layer} onLayerChange={setLayer} />
        <TimelineSlider year={year} onYearChange={setYear} />
        {leftList}
      </aside>

      {/* 中间地图 */}
      <main className="flex min-h-[360px] flex-1 flex-col">
        <div className="relative flex-1">
          <MapCanvas
            territories={territories}
            prophecy={prophecyForMap}
            campaign={campaignForMap}
            focusEvent={focusEvent}
            activeTerritoryId={activeTerritoryId}
            onTerritoryClick={onTerritoryClick}
          />
        </div>
        <p className="mt-2 text-center text-[11px] leading-relaxed text-gray-500">{DISCLAIMER}</p>
      </main>

      {/* 右栏 */}
      <aside className="flex w-full flex-col gap-3 lg:w-80 lg:overflow-y-auto">
        <DetailPanel selection={selection} />
        <AICommentaryPanel selection={selection} />
      </aside>
    </div>
  )
}
