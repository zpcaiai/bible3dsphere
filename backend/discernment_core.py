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
    "checkup": "心灵体检 · 钟马田属灵低潮自评（inputs=各症状 0–10）",
    "idolatry": "偶像辨识 · 内心依附省察（inputs={ratings:[{target_type,..dims}], signals?}）",
    "decision": "决策辨识 · 动机/恐惧/偶像省察（inputs={title,context,urgency?} 或 text）",
    "truth": "真理映射 · 谎言→圣经真理重构（inputs={beliefs:[...]} 或 text 单条）",
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
            # 保留关键行为：安全审查 + 统一诊断记录（diagnosis_hub 内部已写成长事件）
            try:
                saf = _imp("routers.theological_safety")
                if saf and email and hasattr(saf, "safety_review_and_log"):
                    _txt = "\n".join(str(v) for v in res.values() if isinstance(v, str))
                    _s = saf.safety_review_and_log(email=email, content=_txt, content_type="gospel_diagnosis")
                    out["safety_status"] = _s.get("review_status")
                    if _s.get("review_status") == "blocked":
                        out["safety_notice"] = "此内容可能涉及危机安全，请尽快联系可信的属灵同伴、牧者、家人或当地紧急服务；不要仅依赖属灵操练。"
            except Exception:
                pass
            try:
                dh = _imp("diagnosis_hub")
                if dh and email and hasattr(dh, "record_from_gospel"):
                    dh.record_from_gospel(email, None, res)
            except Exception:
                pass
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
        elif lens == "checkup":
            ce = _imp("checkup_engine")
            if ce is None:
                out["ok"] = False; out["error"] = "checkup_engine unavailable"; return out
            ratings = inputs or {}
            res = ce.analyze(ratings, use_ai=ai)
            out["raw"] = res
            out["summary"] = res.get("summary", "") or ""
            sc = res.get("scripture") or {}
            if isinstance(sc, dict) and sc.get("ref"):
                out["scriptureRefs"] = [sc["ref"]]
            lvl = res.get("level")
            sev = "red" if lvl == "高" else "amber" if lvl in ("中", "轻") else "green"
            out["severity"] = sev
            for it in (res.get("items") or [])[:4]:
                isc = it.get("scripture") or {}
                ref = isc.get("ref") if isinstance(isc, dict) else None
                if ref and ref not in out["scriptureRefs"]:
                    out["scriptureRefs"].append(ref)
                out["findings"].append({
                    "title": it.get("name", "") or "属灵低潮",
                    "coreLie": it.get("root", ""),
                    "idol": None,
                    "gospelTruth": it.get("deficit", "") or it.get("preach", ""),
                    "scriptureRefs": [ref] if ref else [],
                    "practice": it.get("practice", ""),
                    "severity": sev,
                })
        elif lens == "idolatry":
            ie = _imp("idolatry_engine")
            if ie is None:
                out["ok"] = False; out["error"] = "idolatry_engine unavailable"; return out
            payload = inputs or {}
            ratings = payload.get("ratings") or payload.get("patterns") or []
            res = ie.assess(ratings, payload.get("signals"))
            out["raw"] = res
            out["summary"] = res.get("summary", "") or ""
            top = res.get("top") or {}
            if top.get("name"):
                out["idols"] = [top["name"]]
            risk = top.get("risk_level") or ""
            out["severity"] = "red" if risk == "high" else "amber" if risk in ("elevated", "medium") else "green"
            for pt in (res.get("patterns") or [])[:4]:
                sc = pt.get("scripture") or {}
                ref = sc.get("ref") if isinstance(sc, dict) else None
                if ref and ref not in out["scriptureRefs"]:
                    out["scriptureRefs"].append(ref)
                prisk = pt.get("risk_level")
                out["findings"].append({
                    "title": (pt.get("meta") or {}).get("name") or pt.get("target_type") or "偶像模式",
                    "coreLie": pt.get("explanation", ""),
                    "idol": (pt.get("meta") or {}).get("name"),
                    "gospelTruth": "",
                    "scriptureRefs": [ref] if ref else [],
                    "severity": "red" if prisk == "high" else "amber" if prisk == "elevated" else "green",
                })
        elif lens == "decision":
            de = _imp("decision_formation_engine")
            if de is None:
                out["ok"] = False; out["error"] = "decision_formation_engine unavailable"; return out
            payload = inputs or {}
            title = payload.get("title") or payload.get("decisionTitle") or (text[:80] if text else "一个决定")
            context = payload.get("context") or payload.get("decision_context") or text or ""
            res = de.analyze(title, context, urgency=(payload.get("urgency") or "medium"), use_ai=ai)
            out["raw"] = res
            out["summary"] = res.get("discernmentSummary", "") or ""
            out["idols"] = list(res.get("detectedIdols") or [])
            flags = res.get("redFlags") or []
            counsel = bool(res.get("counselNeeded"))
            out["severity"] = "red" if (counsel and flags) else "amber" if (out["idols"] or flags or counsel) else "green"
            out["recommendedNextAgents"] = res.get("recommendedNextAgents", []) or []
            out["findings"].append({
                "title": "下一步忠心行动",
                "coreLie": "；".join(res.get("detectedFears") or []),
                "idol": (out["idols"] or [None])[0],
                "gospelTruth": res.get("nextFaithfulStep", ""),
                "scriptureRefs": [],
                "severity": out["severity"],
            })
            for fl in flags[:3]:
                out["findings"].append({"title": "提醒", "coreLie": fl, "idol": None,
                                        "gospelTruth": "", "scriptureRefs": [], "severity": "amber"})
        elif lens == "truth":
            tm = _imp("truth_mapper_engine")
            if tm is None:
                out["ok"] = False; out["error"] = "truth_mapper_engine unavailable"; return out
            payload = inputs or {}
            beliefs = payload.get("beliefs")
            if not beliefs:
                lie = payload.get("lie") or text or ""
                beliefs = ([{"beliefStatement": lie, "domain": payload.get("domain"),
                             "idolHint": payload.get("idolHint")}] if lie else [])
            res = tm.map_beliefs(beliefs, use_ai=ai)
            out["raw"] = res
            out["summary"] = res.get("summary", "") or ""
            out["severity"] = "amber" if beliefs else "green"
            out["recommendedNextAgents"] = res.get("recommendedNextAgents", []) or []
            refs = []
            for m in (res.get("mappings") or [])[:5]:
                mrefs = m.get("scriptureRefs") or []
                refs.extend(mrefs)
                out["findings"].append({
                    "title": m.get("lieStatement", "") or "扭曲信念",
                    "coreLie": m.get("lieStatement", ""),
                    "idol": None,
                    "gospelTruth": m.get("biblicalTruth", "") or m.get("gospelReframe", ""),
                    "scriptureRefs": mrefs,
                    "severity": "amber",
                })
            out["scriptureRefs"] = list(dict.fromkeys([r for r in refs if r]))
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

    if persist_event and email and out.get("ok") and not out.get("blocked") and lens != "gospel":
        try:
            fe = _imp("formation_events")
            if fe:
                fe.record_event(email, "discernment", "diagnosis", domain=lens,
                                title="辨识诊断 · %s" % LENSES.get(lens, lens),
                                summary=out.get("summary", ""),
                                severity=out.get("severity") or ("amber" if out.get("idols") else "green"),
                                refs=out.get("scriptureRefs", []), payload={"lens": lens})
        except Exception:
            pass
    return out
