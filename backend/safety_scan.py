"""
safety_scan.py — 共享的「危机扫描」助手。

把现有 crisis_engine.detect_spiritual_crisis 接到各「自由文本反思类」端点上：
用户在省察 / 偶像监测 / 苦难反思等处写下的文字若流露属灵危机（绝望/羞耻/被定罪/
属灵虐待/教会创伤/强迫性认罪/灵性黑夜等），就在响应里附上温柔的危机指引，
引导其寻求即时陪伴——但绝不阻断用户的正常保存。

best-effort、静默失败：任何异常都返回 None，不影响调用方主流程。
（spec 安全第一原则的服务端兜底；客户端 SOS 关键词仍各自生效。）
"""
from __future__ import annotations

from typing import Optional


def scan_crisis(*texts: str) -> Optional[dict]:
    """对自由文本做属灵危机扫描。命中返回危机指引 dict，否则 None。"""
    blob = "\n".join(t for t in texts if t and t.strip())
    if not blob.strip():
        return None
    try:
        from crisis_engine import detect_spiritual_crisis
        ctype = detect_spiritual_crisis(blob)
    except Exception:
        return None
    if not ctype:
        return None
    return {
        "type": ctype,
        "route": "/api/crisis",
        "message": "我听见你字里行间的重担。此刻你的安全与被陪伴，比完成这个操练更重要。",
        "note": "你并不孤单。若愿意，可以现在联系一位信任的人，或在「危机陪伴」里获得即时支持。",
    }
