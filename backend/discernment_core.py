"""
discernment_core.py — 统一辨识内核（facade / 收敛层）

把既有多套「诊断/辨识」引擎收敛到一个入口 + 一套归一化输出，按 lens 选透镜：
  - worldview（默认）：复用 worldview_orchestrator.run_pipeline（危机守卫→世界观诊断→偶像→真理→叙事→操练 的既有闭环）
  - gospel：复用 gospel_engine（事件→感受→渴望→惧怕→相信 的福音病历）
  - stronghold：复用 stronghold_rag 检索相关营垒模式
不替换任何既有引擎/路由（仍可独立使用）；本层只做「统一入口 + 统一形状 + 写入成长事件」。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

LENSES = {
    "worldview": "世界观诊断（默认）· 含偶像/真理/叙事/操练闭环",
    "gospel": "福音诊断 · 事件→感受→渴望→惧怕→相信",
    "stronghold": "营垒辨识 · 检索相关营垒模式与解药",
}


def meta() -> Dict[str, Any]:
    return {"lenses": [{"key": k, "desc": v} for k, v in LENSES.items()], "default": "worldview"}


def _imp(name: str):
    last = name.rsplit(".", 1)[-1]
    for full in ("backend." + name, name):
        try:
            return __import__(full, fromlist=[last])
        except Exception:
            continue
    return None


def _ai_default(v: Optional[bool]) -> bool:
    if v is not None:
        return bool(v)
    llm = _imp("worldview_llm")
    try:
        return bool(llm and llm.available())
    except Exception:
        return False


def _blank(lens: str) -> Dict[str, Any]:
    return {"ok": True, "lens": lens, "blocked": False, "summary": "",
            "findings": [], "idols": [], "scriptureRefs": [], "recommendedNextAgents": [], "raw": {}}


def diagnose(*, email: Optional[str] = None, lens: str = "worldview", text: str = "",
             inputs: Optional[Dict[str, str]] = None, source_type: str = "journal",
             locale: str = "zh-CN", use_ai: Optional[bool] = None,
             persist_event: bool = True) -> Dict[str, Any]:
    lens = (lens or "worldview").lower()
    if lens not in LENSES:
        lens = "worldview"
    out = _blank(lens)
    ai = _ai_default(use_ai)
    try:
        if lens == "gospel":
            ge = _imp("gospel_engine")
            if ge is None:
                out["ok"] = False; out["error"] = "gospel_engine unavailable"; return out
            res = ge.analyze(inputs or {"belief": text, "feeling": text}, use_ai=ai)
            out["raw"] = res
            out["summary"] = res.get("summary", "") or ""
            idol = res.get("idol_name")
            sc = res.get("scripture") or {}
            out["scriptureRefs"] = [sc.get("ref")] if sc.get("ref") else []
            if idol:
                out["idols"] = [idol]
            out["findings"] = [{
                "title": res.get("emotion", "") or "福音诊断",
                "coreLie": res.get("unbelief", ""),
                "idol": idol,
                "gospelTruth": res.get("gospel_truth", ""),
                "scriptureRefs": out["scriptureRefs"],
                "severity": "amber",
            }]
        elif lens == "stronghold":
            rag = _imp("routers.stronghold_rag")
            kn = _imp("stronghold_knowledge")
            try:
                docs = kn.corpus_documents() if (kn and hasattr(kn, "corpus_documents")) else []
            except Exception:
                docs = []
            try:
                hits = rag.retrieve(text, docs, top_k=6) if (rag and docs) else []
            except Exception:
                hits = []
            out["raw"] = {"retrieved": hits[:6]}
            out["summary"] = "为你的描述检索到 %d 条相关营垒/教义资料。" % len(hits)
            for d in (hits[:6] or []):
                out["findings"].append({
                    "title": d.get("title") or d.get("name") or d.get("code") or "营垒模式",
                    "coreLie": d.get("core_lie") or d.get("coreLie") or "",
                    "gospelTruth": d.get("gospel_truth") or d.get("gospelTruth") or "",
                    "scriptureRefs": d.get("scriptures") or [],
                    "severity": "amber",
                })
        else:  # worldview（默认）— 复用既有闭环管线
            orch = _imp("worldview_orchestrator")
            if orch is None:
                out["ok"] = False; out["error"] = "worldview_orchestrator unavailable"; return out
            res = orch.run_pipeline(user_id=email or "anon", text=text,
                                    source_type=source_type, locale=locale, use_ai=ai)
            out["raw"] = res
            out["blocked"] = bool(res.get("blocked"))
            if out["blocked"]:
                out["crisis"] = res.get("crisis")
            else:
                diag = res.get("diagnosis") or {}
                out["summary"] = diag.get("profileSummary", "") or ""
                out["idols"] = [(x.get("name") if isinstance(x, dict) else x)
                                for x in ((res.get("idols") or {}).get("suggestedTargets", []) or [])]
                out["recommendedNextAgents"] = res.get("recommendedNextAgents", []) or []
                refs = []
                for b in (diag.get("extractedBeliefs") or [])[:5]:
                    anchors = b.get("scriptureAnchors") or b.get("scriptureRefs") or []
                    refs.extend(anchors)
                    out["findings"].append({
                        "title": b.get("beliefStatement", "") or "世界观信念",
                        "coreLie": b.get("beliefStatement", ""),
                        "idol": None,
                        "gospelTruth": b.get("biblicalCounterTruth") or b.get("biblicalTruth", "") or "",
                        "scriptureRefs": anchors,
                        "severity": "amber",
                    })
                out["scriptureRefs"] = list(dict.fromkeys([r for r in refs if r]))
    except Exception as exc:
        out["ok"] = False
        out["error"] = str(exc)

    if persist_event and email and out.get("ok") and not out.get("blocked"):
        try:
            fe = _imp("formation_events")
            if fe:
                fe.record_event(email, "discernment", "diagnosis", domain=lens,
                                title="辨识诊断 · %s" % LENSES.get(lens, lens),
                                summary=out.get("summary", ""),
                                severity="amber" if out.get("idols") else "green",
                                refs=out.get("scriptureRefs", []), payload={"lens": lens})
        except Exception:
            pass
    return out
