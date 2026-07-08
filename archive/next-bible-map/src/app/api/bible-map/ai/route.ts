import { NextResponse } from 'next/server'
import type { ApiResult } from '@/features/bible-map/domain/types'

export const dynamic = 'force-dynamic'

interface AiRequestBody {
  kind?: string
  name?: string
  context?: string
}
interface AiResponseData {
  commentary: string
  source: 'llm' | 'template'
}

function template(name: string): string {
  return (
    `关于「${name}」，这里从四个维度作教学性讲解：\n\n` +
    `① 历史背景：该地点/人物在圣经历史脉络中的位置与年代背景。\n` +
    `② 地理意义：所处地形、交通与战略价值如何影响事件发展。\n` +
    `③ 属灵意义：经文借此彰显的神的属性、救赎主题与信仰功课。\n` +
    `④ 现代应用：对今日信徒在信心、顺服与使命上的提醒。\n\n` +
    `（配置 OPENAI_API_KEY 后，本段将由大模型生成更完整的讲解。）`
  )
}

interface ChatChoice {
  message?: { content?: unknown }
}
interface ChatResponse {
  choices?: ChatChoice[]
}

export async function POST(req: Request): Promise<NextResponse<ApiResult<AiResponseData>>> {
  try {
    const body = (await req.json().catch(() => ({}))) as AiRequestBody
    const name = (body.name ?? '所选内容').toString()
    const apiKey = process.env.OPENAI_API_KEY
    if (!apiKey) {
      return NextResponse.json({ success: true, data: { commentary: template(name), source: 'template' } })
    }

    const baseUrl = process.env.OPENAI_BASE_URL ?? 'https://api.openai.com/v1'
    const model = process.env.OPENAI_MODEL ?? 'gpt-4o-mini'
    const prompt =
      `你是圣经历史地理教学助手。请用简体中文，针对「${name}」` +
      `（类型：${body.kind ?? '未知'}${body.context ? '；背景：' + body.context : ''}），` +
      `从历史背景、地理意义、属灵意义、现代应用四个维度，写一段约200字、温暖而准确的讲解。注明属近似教学说明。`

    const res = await fetch(`${baseUrl}/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({
        model,
        messages: [{ role: 'user', content: prompt }],
        temperature: 0.7,
      }),
    })
    if (!res.ok) {
      return NextResponse.json({ success: true, data: { commentary: template(name), source: 'template' } })
    }
    const json = (await res.json()) as ChatResponse
    const content = json.choices?.[0]?.message?.content
    const commentary = typeof content === 'string' && content.trim().length > 0 ? content : template(name)
    return NextResponse.json({ success: true, data: { commentary, source: 'llm' } })
  } catch (e) {
    const error = e instanceof Error ? e.message : '未知错误'
    return NextResponse.json({ success: false, error }, { status: 500 })
  }
}
