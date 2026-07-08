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
    """对自由文本做危机扫描。命中返回危机指引 dict，否则 None。

    统一走 crisis_engine.triage()（含中/英文，覆盖直接自杀意念 / 自伤 / 伤人 /
    医疗急症等模式），不再只依赖 detect_spiritual_crisis（仅中文、仅属灵子类，
    漏掉「想死 / 自杀 / kill myself」等直接表达与全部英文）。任一路命中即给温柔指引。
    返回结构与旧版保持兼容：仍含 type/route/message/note，另附 riskLevel/riskTypes
    供调用方按需使用（旧调用方只读 type/route/message/note，不受影响）。
    """
    blob = "\n".join(t for t in texts if t and t.strip())
    if not blob.strip():
        return None
    try:
        from crisis_engine import triage, detect_spiritual_crisis
    except Exception:
        try:
            from backend.crisis_engine import triage, detect_spiritual_crisis  # type: ignore
        except Exception:
            return None

    # 主路：完整分级（中/英 + 直接自杀意念）。绝不因异常吞掉危机——异常时退回属灵子类判断。
    risk_level = "green"
    risk_types: list = []
    try:
        tri = triage(blob) or {}
        risk_level = tri.get("riskLevel", "green")
        risk_types = list(tri.get("riskTypes") or [])
    except Exception:
        pass

    # 辅路：属灵危机子类型（用于挑选更贴切的安慰文案 type）。
    spiritual = None
    try:
        spiritual = detect_spiritual_crisis(blob)
    except Exception:
        spiritual = None

    # 触发条件：triage 判定非 green（含英文/直接自杀意念），或命中任一风险类型，
    # 或识别到属灵危机子类。任一成立即附危机指引，但绝不阻断用户的正常保存。
    triggered = (risk_level in ("yellow", "orange", "red")) or bool(risk_types) or bool(spiritual)
    if not triggered:
        return None

    ctype = spiritual or (risk_types[0] if risk_types else "condemnation")
    return {
        "type": ctype,
        "route": "/api/crisis",
        "riskLevel": risk_level,
        "riskTypes": risk_types,
        "message": "我听见你字里行间的重担。此刻你的安全与被陪伴，比完成这个操练更重要。",
        "note": "你并不孤单。若愿意，可以现在联系一位信任的人，或在「危机陪伴」里获得即时支持。",
    }
