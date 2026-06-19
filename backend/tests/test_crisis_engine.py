"""Crisis Care 危机守护 — stateless engine + simulation test suite.

Mirrors the spec's crisis simulation cases plus extra guards. These tests do
not touch the database, so they are marked ``no_db``.

Safety contract under test:
  * Never returns "no risk" for self-harm/suicide language.
  * Red rules (plan/means/time/imminent action) take precedence.
  * LLM and history can only RAISE the level, never lower it.
"""
import pytest

import crisis_engine as ce

pytestmark = pytest.mark.no_db


# ── spec simulation cases ─────────────────────────────────────────────────────
def test_case1_passive_suicidal_is_orange():
    r = ce.triage("我不想活了。")
    assert r["riskLevel"] == "orange"
    assert "suicidal_ideation" in r["riskTypes"]
    assert r["requiresDirectSafetyQuestion"] is True


def test_case2_explicit_plan_is_red():
    r = ce.triage("我今晚已经准备好药了。")
    assert r["riskLevel"] == "red"
    assert r["requiresHumanEscalation"] is True
    assert r["recommendedWorkflow"] == "red_emergency"


def test_case3_post_sin_despair_at_least_orange():
    # "我不配活" is death-adjacent -> must be at least orange
    r = ce.triage("我犯罪太多，神不会赦免我，我不配活。")
    assert ce._LEVEL_RANK[r["riskLevel"]] >= ce._LEVEL_RANK["orange"]
    assert "suicidal_ideation" in r["riskTypes"]


def test_case4_addiction_relapse_flow():
    r = ce.triage("我现在快要控制不住去看色情内容了。")
    assert "addiction_relapse" in r["riskTypes"]
    assert ce._LEVEL_RANK[r["riskLevel"]] >= ce._LEVEL_RANK["yellow"]


def test_case5_trauma_dissociation():
    r = ce.triage("我感觉自己又回到那件事里了，身体动不了。")
    assert "dissociation" in r["riskTypes"] or "trauma_trigger" in r["riskTypes"]


def test_case6_mild_distress_not_red():
    r = ce.triage("我今天压力很大，想哭。")
    assert r["riskLevel"] in ("green", "yellow")
    assert r["riskLevel"] != "red"


# ── red marker precedence ─────────────────────────────────────────────────────
@pytest.mark.parametrize("text", [
    "站在天台上，现在就要结束。",
    "绳子已经系好了，再见了这个世界。",
    "我把刀放在手边了，今晚就了结。",
    "我吞了一整瓶安眠药。",
])
def test_red_markers_force_red(text):
    assert ce.triage(text)["riskLevel"] == "red"


def test_harm_to_others_detected():
    r = ce.triage("我想杀了他，让他付出代价。")
    assert "harm_to_others" in r["riskTypes"]
    assert ce._LEVEL_RANK[r["riskLevel"]] >= ce._LEVEL_RANK["orange"]


def test_domestic_violence_detected():
    r = ce.triage("他正在打我，我很害怕。")
    assert "domestic_violence" in r["riskTypes"]


# ── never under-triage / never say "no risk" ──────────────────────────────────
def test_triage_always_returns_valid_level():
    for text in ["", "你好", "今天天气不错", "我想死", "我不配活着"]:
        r = ce.triage(text)
        assert r["riskLevel"] in ce.RISK_LEVELS


def test_llm_can_only_raise_not_lower():
    # an orange text with an LLM "green" verdict must stay orange
    r = ce.triage("我不想活了。", llm_level="green")
    assert r["riskLevel"] == "orange"
    # an LLM "red" can raise a yellow
    r2 = ce.triage("我现在快控制不住想喝酒。", llm_level="red")
    assert r2["riskLevel"] == "red"


def test_history_raises_floor_to_yellow():
    r = ce.triage("今天有点累。", context_levels=["orange", "orange", "yellow"])
    assert ce._LEVEL_RANK[r["riskLevel"]] >= ce._LEVEL_RANK["yellow"]


# ── multi-region resources (verified numbers) ─────────────────────────────────
@pytest.mark.parametrize("locale,code", [
    ("zh-TW", "TW"), ("zh_CN", "CN"), ("zh-HK", "HK"),
    ("en-US", "US"), ("fr", "TW"), (None, "TW"), ("zh-MO", "HK"),
])
def test_resolve_region(locale, code):
    assert ce.resolve_region(locale) == code


def test_resources_have_verified_numbers():
    tw = ce.get_resources("zh-TW")
    contacts = [r["contact"] for r in tw["resources"]]
    assert "1925" in contacts and "1995" in contacts
    cn = ce.get_resources("zh-CN")
    assert any("82951332" in r["contact"] for r in cn["resources"])
    us = ce.get_resources("en-US")
    assert any(r["contact"] == "988" for r in us["resources"])
    hk = ce.get_resources("zh-HK")
    assert any("2389 2222" in r["contact"] for r in hk["resources"])


def test_every_region_has_emergency_resource():
    for code in ("TW", "CN", "HK", "US", "INTL"):
        block = ce.CRISIS_RESOURCES[code]
        assert any(r["type"] == "emergency" for r in block["resources"])


# ── safety check state machine ────────────────────────────────────────────────
def test_safety_check_yes_yes_escalates_red():
    s1 = ce.safety_check_step("ask_intent", None)
    assert s1["state"] == "ask_intent"
    s2 = ce.safety_check_step("ask_intent", True)
    assert s2["state"] == "ask_plan"
    s3 = ce.safety_check_step("ask_plan", True)
    assert s3["escalate"] is True and s3["state"] == "escalate_red"


def test_safety_check_no_intent_stabilizes():
    s = ce.safety_check_step("ask_intent", False)
    assert s["state"] == "stabilize"
    assert s["escalate"] is False


def test_safety_check_no_plan_creates_plan():
    s = ce.safety_check_step("ask_plan", False)
    assert s["state"] == "create_safety_plan"


# ── safety plan ───────────────────────────────────────────────────────────────
def test_safety_plan_template_has_required_parts():
    plan = ce.build_safety_plan("zh-TW")
    assert plan["warningSigns"] and plan["internalCopingStrategies"]
    assert plan["professionalResources"]            # real resources for region
    assert plan["emergencyMessageTemplate"]         # copy-paste help text
    assert plan["spiritualAnchors"]
    assert plan["regionCode"] == "TW"


# ── escalation ────────────────────────────────────────────────────────────────
def test_red_emergency_message_has_resources_and_copytext():
    msg = ce.red_emergency_message("zh-TW")
    assert msg["copyText"]
    assert msg["resources"]
    assert msg["regionCode"] == "TW"


def test_guardian_alert_text_varies_by_level():
    red = ce.guardian_alert_text("red")
    yellow = ce.guardian_alert_text("yellow")
    assert "紧急" in red
    assert red != yellow


# ── spiritual care: no forbidden phrases, conviction vs condemnation ──────────
def test_spiritual_comfort_avoids_forbidden_phrases():
    for ctype in ce.SPIRITUAL_CRISIS_TYPES:
        body = ce.spiritual_comfort(ctype)["body"]
        for bad in ce.FORBIDDEN_PHRASES:
            assert bad not in body, f"forbidden phrase '{bad}' leaked for {ctype}"


def test_detect_spiritual_crisis():
    assert ce.detect_spiritual_crisis("神不要我了，我永远不会被赦免") == "condemnation"
    assert ce.detect_spiritual_crisis("我是不是没得救") == "loss_of_assurance"
    assert ce.detect_spiritual_crisis("教会伤害了我") == "church_trauma"


def test_comfort_returns_scripture():
    out = ce.spiritual_comfort("post_sin_despair")
    assert out["scripture"]["ref"] and out["scripture"]["text"]


# ── post-crisis ───────────────────────────────────────────────────────────────
def test_post_crisis_phases():
    allp = ce.post_crisis_all()
    assert set(allp.keys()) == set(ce.POST_CRISIS_PHASES)
    assert ce.post_crisis_tasks("24h")
    # unknown phase falls back to 24h, never empty
    assert ce.post_crisis_tasks("bogus")


# ── pfa / addiction / trauma scripts present ─────────────────────────────────
def test_pfa_scripts_present():
    assert "5" in ce.grounding_54321()
    assert ce.breathing_guide(3)
    assert ce.pfa_stabilize("panic_attack")


def test_addiction_and_trauma_scripts():
    assert "10" in ce.ten_minute_delay()
    assert ce.HALT_PROMPT
    assert "现在" in ce.trauma_grounding()


# ── formation bridge (危机后 → 模式库) ─────────────────────────────────────────
def test_formation_seed_is_non_condemning_and_valid():
    seed = ce.formation_seed(["addiction_relapse"])
    assert seed["primarySinPattern"] in ce.FORMATION_SIN_PATTERNS
    assert seed["duration"] == "30_days"
    assert seed["intensity"] == "light"
    # must NOT imply the crisis itself is sin
    assert "不是说你的危机就是某种罪" in seed["note"]


def test_formation_seed_defaults_gentle():
    assert ce.formation_seed([])["primarySinPattern"] == "spiritual_numbness"
    # suicide/self-harm/trauma must map to the gentle, non-accusatory default
    assert ce.formation_seed(["suicidal_ideation"])["primarySinPattern"] == "spiritual_numbness"
    assert ce.formation_seed(["harm_to_others"])["primarySinPattern"] == "hatred_division"


# ── guardian SMS channel (degrades gracefully) ───────────────────────────────
def test_notify_graceful_without_credentials():
    import notify
    res = notify.send_sms("+10000000000", "test", meta={"level": "red"})
    assert res["ok"] is False
    # no env creds in test → not_configured (or network exception if creds present)
    assert res["status"] in ("not_configured", "twilio_exception", "webhook_exception")
    assert notify.send_sms("", "x")["status"] == "no_recipient"


# ── notify channel dispatch (wechat/sms/webhook degrade) ─────────────────────
def test_notify_send_notification_degrades():
    import notify
    # no creds in test env → not_configured regardless of requested methods
    r = notify.send_notification(body="alert", methods=["sms"], phone="123")
    assert r["ok"] is False
    assert r["status"] in ("not_configured", "twilio_exception", "webhook_exception")
    assert isinstance(notify.configured_channels(), list)


def test_notify_has_no_wechat():
    import notify
    assert not hasattr(notify, "send_wechat_template")
    assert "wechat" not in notify.configured_channels()


def test_caregiver_gate_requires_verified_email_account():
    import routers.crisis as rc
    from fastapi import HTTPException
    rc._state["get_session_user"] = lambda req: {"email": "Pastor@X.com", "login_type": "email"}
    assert rc._require_verified_caregiver(None) == "pastor@x.com"  # normalized
    rc._state["get_session_user"] = lambda req: {"email": "w@x.com", "login_type": "wechat"}
    try:
        rc._require_verified_caregiver(None)
        assert False, "wechat account should be rejected"
    except HTTPException as e:
        assert e.status_code == 403
    rc._state["get_session_user"] = lambda req: {"email": ""}
    try:
        rc._require_verified_caregiver(None)
        assert False, "no email should be rejected"
    except HTTPException as e:
        assert e.status_code == 401


def test_mask_email_and_share_expiry():
    import routers.crisis as rc
    from datetime import datetime, timezone
    assert rc._mask_email("alice@example.com") == "a***@example.com"
    assert rc._mask_email("a@x.com") == "*@x.com"
    assert rc._mask_email("noatsign") == "noatsign"
    assert rc._share_expiry(None) is None
    assert rc._share_expiry(0) is None
    exp = rc._share_expiry(30)
    assert exp is not None and exp > datetime.now(timezone.utc)
