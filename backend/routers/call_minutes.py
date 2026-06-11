"""
通话 AI 纪要 —— 祷告会/查经通话的本地转写文本 → LLM 总结。
输出：要点纪要 + 代祷事项清单（前端可一键存入祷告墙）。
无 LLM key 时回退为结构化模板（按行抽取要点）。
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx
from fastapi import APIRouter, Request

from core.ratelimit import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/call", tags=["call-minutes"])

MAX_TRANSCRIPT = 8000


def _fallback(transcript: str) -> dict[str, Any]:
    """无 LLM 时的朴素纪要：取较长的句子当要点，含"祷告/代祷/求"的句子当代祷事项。
    多人转写行（"名字：内容"）保留名字前缀，使代祷清单仍能按人归属。"""
    items: list[str] = []
    points: list[str] = []
    for raw in transcript.split("\n"):
        m = re.match(r"^([^：:]{1,20})[：:]\s*(.+)$", raw.strip())
        name, body = (m.group(1), m.group(2)) if m else ("", raw.strip())
        for s in re.split(r"[。！？!?]+", body):
            s = s.strip()
            if len(s) < 8:
                continue
            tagged = f"【{name}】{s}" if name else s
            if re.search(r"祷告|代祷|求主|求神|纪念|记念|医治|保守|带领", s):
                items.append(tagged)
            else:
                points.append(tagged)
    return {
        "summary": "（未配置 AI，以下为自动摘录）\n" + "\n".join(f"· {p}" for p in points[:6]),
        "prayerItems": items[:10],
        "source": "template",
    }


@router.post("/minutes")
@limiter.limit("10/minute")
async def minutes(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        body = {}
    transcript = str(body.get("transcript") or "").strip()[:MAX_TRANSCRIPT]
    title = re.sub(r"[\x00-\x1f<>{}]", "", str(body.get("title") or ""))[:60]
    if len(transcript) < 20:
        return {"success": False, "error": "记录内容太短，无法生成纪要"}

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"success": True, "data": _fallback(transcript)}

    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    prompt = (
        f"以下是一次教会线上聚会（{title or '祷告会/查经'}）的语音转写记录，"
        "行首「名字：」表示说话人。请用简体中文输出 JSON（不要任何其他文字）："
        '{"summary": "5条以内的要点纪要，每条一行以·开头", '
        '"prayerItems": ["【名字】润色后的代祷事项", ...]}'
        "。代祷事项要求：①按说话人归属，每条以【名字】开头（无名字则省略）；"
        "②把口语转写润色为通顺得体的书面代祷句（纠正转写错字、去掉语气词），"
        "保留原意不添油加醋；③每条≤50字、可直接发到代祷墙；④同一人多个事项分条列出；"
        "没有明确代祷内容就返回空数组。转写记录：\n" + transcript
    )
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3},
            )
        if resp.status_code == 200:
            content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            content = re.sub(r"^```(json)?|```$", "", content.strip(), flags=re.M).strip()
            parsed = json.loads(content)
            summary = str(parsed.get("summary") or "").strip()
            items = [str(x).strip()[:80] for x in (parsed.get("prayerItems") or []) if str(x).strip()][:10]
            if summary:
                return {"success": True, "data": {"summary": summary, "prayerItems": items, "source": "llm"}}
    except Exception as e:
        logger.warning("call-minutes llm: %s", e)
    return {"success": True, "data": _fallback(transcript)}
