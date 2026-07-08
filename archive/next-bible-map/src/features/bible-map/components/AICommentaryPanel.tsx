'use client'
import { useState } from 'react'
import type { BibleMapSelection } from '../domain/types'

interface Props {
  selection: BibleMapSelection | null
}

interface AiData {
  commentary: string
  source: 'llm' | 'template'
}
interface AiResult {
  success: boolean
  data?: AiData
  error?: string
}

function subjectName(s: BibleMapSelection): string {
  if (s.kind === 'territory' && s.territory) return s.territory.nameZh
  if (s.kind === 'prophecy' && s.prophecy) return `${s.prophecy.book}论${s.prophecy.targetNationZh}的预言`
  if (s.kind === 'campaign' && s.campaign) return s.campaign.nameZh
  if (s.kind === 'event' && s.event) return s.event.titleZh
  return '所选内容'
}

export function AICommentaryPanel({ selection }: Props) {
  const name = selection ? subjectName(selection) : null
  const [loading, setLoading] = useState(false)
  const [text, setText] = useState<string | null>(null)
  const [llm, setLlm] = useState(false)

  async function generate(): Promise<void> {
    if (!selection || !name) return
    setLoading(true)
    setText(null)
    try {
      const res = await fetch('/api/bible-map/ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind: selection.kind, name }),
      })
      const json = (await res.json()) as AiResult
      if (json.success && json.data) {
        setText(json.data.commentary)
        setLlm(json.data.source === 'llm')
      } else {
        setText('生成失败，请稍后再试。')
      }
    } catch {
      setText('生成失败（网络错误）。')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-xl border border-white/10 bg-gradient-to-br from-indigo-500/10 to-fuchsia-500/10 p-4">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-base">🤖</span>
          <h3 className="text-sm font-bold text-indigo-200">AI 讲解</h3>
        </div>
        {name && (
          <button
            type="button"
            onClick={generate}
            disabled={loading}
            className="rounded-md border border-indigo-400/40 bg-indigo-400/15 px-2.5 py-1 text-xs font-medium text-indigo-200 disabled:opacity-50"
          >
            {loading ? '生成中…' : '✨ 生成讲解'}
          </button>
        )}
      </div>
      {!name ? (
        <p className="text-sm leading-relaxed text-gray-400">
          选择一个支派、帝国、预言、战役或事件，点「生成讲解」从历史背景、地理意义、属灵意义与现代应用四个维度获取讲解。
        </p>
      ) : text ? (
        <>
          <p className="whitespace-pre-line text-sm leading-relaxed text-gray-200">{text}</p>
          <p className="mt-2 text-[10px] text-gray-500">{llm ? '由大模型生成' : '模板文本（未配置 OPENAI_API_KEY）'}</p>
        </>
      ) : (
        <p className="text-sm leading-relaxed text-gray-300">
          关于「{name}」，点击「✨ 生成讲解」从历史背景、地理意义、属灵意义和现代应用四个维度获取解释。
        </p>
      )}
    </div>
  )
}
