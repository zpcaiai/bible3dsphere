"""
Unit tests for the content-theology expansion batch 2 + 3 engines
(deterministic path, no DB / no AI).

覆盖 13 个新引擎：
  assurance / forgiveness / fellowship / rule_of_life / fear_of_god / gratitude(eucharisteo)
  / holiness / neighbor_love / hope / prayer_classics / contemplation / incarnation / wisdom
契约：meta() 有 title；analyze() 返回 summary/prayer/closing/anchor/ai_used；
危机检测正反两向；formation_signal 为 4 元组；确定性；AI 关闭时回退确定性结果。
"""
import importlib
import pytest

pytestmark = pytest.mark.no_db

# (module, 正常输入, 命中分类字段名) —— 分类字段各引擎不同
ENGINES = [
    ("assurance_engine",        "我又犯了同样的罪，觉得自己根本没得救", "trigger"),
    ("forgiveness_engine",      "我被最信任的朋友背叛出卖了，放不下",   "hurt_type"),
    ("fellowship_engine",       "我对教会很失望，大家都很表面",         "struggle"),
    ("rule_of_life_engine",     "最近特别忙，一点小事就发火，没时间祷告", "symptom"),
    ("fear_of_god_engine",      "我总觉得神随时要惩罚我，很怕祂",       "state"),
    ("gratitude_engine",        "最近很平淡麻木，感受不到什么",         "mood"),
    ("holiness_engine",         "我想胜过我的坏脾气和苦毒",             "focus"),
    ("neighbor_love_engine",    "我总怕麻烦，多一事不如少一事，不想伸手", "inward_curve"),
    ("hope_engine",             "我失去了至亲，很想念很哀伤",           "shadow"),
    ("prayer_classics_engine",  "我不会祷告，也不知道说什么",           "block"),
    ("contemplation_engine",    "我最近很焦虑，一直担心未来会不好",     "state"),
    ("incarnation_engine",      "觉得没人懂我的软弱，神大概也不懂",     "facet"),
    ("wisdom_engine",           "我总是管不住嘴，冲动说错话得罪人",     "domain"),
]

CRISIS_INPUTS = ["我想死了不想活了", "撑不下去了想消失", "自杀", "去死算了"]


def _mod(name):
    return importlib.import_module(name)


@pytest.mark.parametrize("modname,normal,cls_field", ENGINES)
def test_meta_has_title_and_verse(modname, normal, cls_field):
    m = _mod(modname)
    meta = m.meta()
    assert isinstance(meta, dict)
    assert meta.get("title"), f"{modname}.meta() 缺 title"
    assert meta.get("verse"), f"{modname}.meta() 缺 verse 锚点"


@pytest.mark.parametrize("modname,normal,cls_field", ENGINES)
def test_analyze_contract(modname, normal, cls_field):
    m = _mod(modname)
    r = m.analyze(normal, use_ai=False)
    assert isinstance(r, dict)
    for k in ("summary", "prayer", "closing", "anchor", "ai_used"):
        assert k in r, f"{modname}.analyze() 缺字段 {k}"
    assert r["ai_used"] is False
    # anchor 是一处经文对象
    assert isinstance(r["anchor"], dict) and (r["anchor"].get("ref") or r["anchor"].get("text"))
    # 命中了某个分类
    assert isinstance(r.get(cls_field), dict) and r[cls_field].get("name"), f"{modname} 分类字段 {cls_field} 异常"


@pytest.mark.parametrize("modname,normal,cls_field", ENGINES)
def test_no_false_positive_crisis(modname, normal, cls_field):
    m = _mod(modname)
    r = m.analyze(normal, use_ai=False)
    assert r["crisis"] is False, f"{modname} 对正常输入误报危机"
    assert r.get("crisis_note", "") == ""


@pytest.mark.parametrize("modname,_n,_c", ENGINES)
@pytest.mark.parametrize("crisis_text", CRISIS_INPUTS)
def test_crisis_detection(modname, _n, _c, crisis_text):
    m = _mod(modname)
    r = m.analyze(crisis_text, use_ai=False)
    assert r["crisis"] is True, f"{modname} 漏报危机: {crisis_text}"
    assert r["crisis_note"], f"{modname} 危机文案为空"


@pytest.mark.parametrize("modname,normal,cls_field", ENGINES)
def test_formation_signal_shape(modname, normal, cls_field):
    m = _mod(modname)
    r = m.analyze(normal, use_ai=False)
    sig = m.formation_signal(r)
    assert isinstance(sig, tuple) and len(sig) == 4
    tags, loop_broken, reflection, intensity = sig
    assert isinstance(tags, list) and all(isinstance(t, str) for t in tags) and tags
    assert isinstance(loop_broken, bool) and isinstance(reflection, bool)
    assert isinstance(intensity, (int, float)) and intensity >= 0
    # 危机时应降权且 loop_broken=False
    rc = m.analyze("我想死了", use_ai=False)
    sc = m.formation_signal(rc)
    assert sc[1] is False and sc[3] <= sig[3]


@pytest.mark.parametrize("modname,normal,cls_field", ENGINES)
def test_determinism(modname, normal, cls_field):
    m = _mod(modname)
    a = m.analyze(normal, use_ai=False)
    b = m.analyze(normal, use_ai=False)
    assert a["summary"] == b["summary"] and a["prayer"] == b["prayer"]
    assert a[cls_field] == b[cls_field]


@pytest.mark.parametrize("modname,normal,cls_field", ENGINES)
def test_ai_fallback_is_deterministic(modname, normal, cls_field):
    """无 provider 时 use_ai=True 应回退确定性结果（ai_used=False，不抛异常）。"""
    m = _mod(modname)
    r = m.analyze(normal, use_ai=True)
    assert r["ai_used"] is False
    assert r["summary"]


@pytest.mark.parametrize("modname,normal,cls_field", ENGINES)
def test_empty_input_safe(modname, normal, cls_field):
    m = _mod(modname)
    r = m.analyze("", use_ai=False)
    assert isinstance(r, dict) and r["crisis"] is False and r["summary"]


# ── 分支专项测试 ──

def test_assurance_routes_legalism():
    m = _mod("assurance_engine")
    r = m.analyze("我灵修做得不够，神大概不满意我", use_ai=False)
    assert r["lean"] in ("legalist", "experiential")
    r2 = m.analyze("反正有恩典，怎么活都无所谓", use_ai=False)
    assert r2["lean"] == "antinomian"


def test_forgiveness_abuse_branch_safety_first():
    m = _mod("forgiveness_engine")
    r = m.analyze("他一直家暴打我，还威胁我", use_ai=False)
    assert r["abuse_flag"] is True
    assert r["abuse_note"] and "安全" in r["distinction"]
    # 施虐处境不催逼和好：practices 转向保护
    assert any("安全" in p for p in r["practices"])
    fs = m.formation_signal(r)
    assert fs[1] is False  # loop_broken 降权，标记需真人介入


def test_forgiveness_distinguishes_forgiveness_from_reconciliation():
    m = _mod("forgiveness_engine")
    r = m.analyze("我被朋友骗了很多钱", use_ai=False)
    assert "和好" in r["distinction"] and "饶恕" in r["distinction"]
    assert len(r["reach_steps"]) == 5


def test_gratitude_hard_eucharisteo_defers_to_lament():
    m = _mod("gratitude_engine")
    r = m.analyze("我正在很深的难处里，失去了亲人，很痛", use_ai=False)
    assert r["hard_mode"] is True
    assert r["lament_link"]  # 转介哀歌，不否认痛苦


def test_gratitude_count_mode_offers_lenses():
    m = _mod("gratitude_engine")
    r = m.analyze("最近有点不满，总觉得别人更好", use_ai=False)
    assert r["mood"]["mode"] == "count"
    assert isinstance(r["gift_lenses"], list) and len(r["gift_lenses"]) >= 3


def test_holiness_put_off_put_on_pair_and_gospel_order():
    m = _mod("holiness_engine")
    r = m.analyze("我想胜过情欲的挣扎", use_ai=False)
    assert r["mortify"]["put_off"] and r["vivify"]["put_on"]
    assert r["gospel_order_note"]
    # 律法主义口吻会被校正
    r2 = m.analyze("我要胜过这罪才配被神爱", use_ai=False)
    assert r2["legalist_lean"] is True


def test_neighbor_love_gives_concrete_step_and_form():
    m = _mod("neighbor_love_engine")
    r = m.analyze("我只顾自己往上爬，顾不上别人", use_ai=False)
    assert r["suggested_form"]["name"] and r["suggested_form"]["how"]
    assert r["concrete_step"]


def test_contemplation_and_incarnation_have_doctrine_guardrail():
    for name in ("contemplation_engine", "incarnation_engine"):
        m = _mod(name)
        r = m.analyze("我想更深地亲近神", use_ai=False)
        assert r.get("doctrine_note"), f"{name} 缺教义护栏"
    # theosis 明确不等于人变成神
    inc = _mod("incarnation_engine").analyze("我觉得自己改变不了", use_ai=False)
    assert "本体" in inc["doctrine_note"]


def test_rule_of_life_prescribes_counter_practice():
    m = _mod("rule_of_life_engine")
    r = m.analyze("我停不下来，一闲下来就焦虑", use_ai=False)
    assert r["prescribed_practice"]["name"]
    assert isinstance(r["rhythm_layers"], list) and len(r["rhythm_layers"]) == 3


def test_wisdom_roots_in_fear_of_the_lord():
    m = _mod("wisdom_engine")
    r = m.analyze("我在一笔大的消费上拿不定主意", use_ai=False)
    assert r["principle"] and r["wise_step"]
    assert "雅3:17" in r["from_above_test"] or "从上头" in r["from_above_test"]
