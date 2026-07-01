"""
Unit tests for expansion batch 4 engines (person-of-God + pastoral),
deterministic path, no DB / no AI.

覆盖 10 个引擎：holy_spirit / adoption / cross / fear_of_man / providence /
repentance / doubt / generosity / humility / word_delight
"""
import importlib
import pytest

pytestmark = pytest.mark.no_db

ENGINES = [
    ("holy_spirit_engine",  "我想改变却总是无力，靠自己撑不住", "need"),
    ("adoption_engine",     "我总觉得什么都得靠自己，像个孤儿",   "state"),
    ("cross_engine",        "我一直有很深的罪咎，觉得该被罚",     "focus"),
    ("fear_of_man_engine",  "我特别在意别人评价，被批评就崩",     "form"),
    ("providence_engine",   "最近一切都失控了，乱成一团",         "situation"),
    ("repentance_engine",   "我一直自责却没有改变，走不出来",     "state"),
    ("doubt_engine",        "我最近信不动了，有很多理性疑问",     "kind"),
    ("generosity_engine",   "我钱抓得很紧，总怕不够，很不安",     "state"),
    ("humility_engine",     "我很骄傲，总想被看见、爱表现",       "state"),
    ("word_delight_engine", "读经对我像例行任务，没味道",         "block"),
]
CRISIS = ["我想死了不想活了", "撑不下去了想消失", "自杀", "去死算了"]


def _m(n):
    return importlib.import_module(n)


@pytest.mark.parametrize("mod,normal,cf", ENGINES)
def test_meta(mod, normal, cf):
    meta = _m(mod).meta()
    assert meta.get("title") and meta.get("verse") and meta.get("core")


@pytest.mark.parametrize("mod,normal,cf", ENGINES)
def test_analyze_contract(mod, normal, cf):
    r = _m(mod).analyze(normal, use_ai=False)
    for k in ("summary", "prayer", "closing", "anchor", "ai_used"):
        assert k in r, f"{mod} 缺 {k}"
    assert r["ai_used"] is False
    assert isinstance(r["anchor"], dict) and (r["anchor"].get("ref") or r["anchor"].get("text"))
    assert isinstance(r.get(cf), dict) and r[cf].get("name")


@pytest.mark.parametrize("mod,normal,cf", ENGINES)
def test_no_false_positive(mod, normal, cf):
    r = _m(mod).analyze(normal, use_ai=False)
    assert r["crisis"] is False and r.get("crisis_note", "") == ""


@pytest.mark.parametrize("mod,_n,_c", ENGINES)
@pytest.mark.parametrize("ct", CRISIS)
def test_crisis(mod, _n, _c, ct):
    r = _m(mod).analyze(ct, use_ai=False)
    assert r["crisis"] is True and r["crisis_note"]


@pytest.mark.parametrize("mod,normal,cf", ENGINES)
def test_formation_signal(mod, normal, cf):
    m = _m(mod)
    r = m.analyze(normal, use_ai=False)
    sig = m.formation_signal(r)
    assert isinstance(sig, tuple) and len(sig) == 4
    assert isinstance(sig[0], list) and sig[0]
    assert isinstance(sig[1], bool) and isinstance(sig[2], bool) and sig[3] >= 0
    sc = m.formation_signal(m.analyze("我想死了", use_ai=False))
    assert sc[1] is False and sc[3] <= sig[3]


@pytest.mark.parametrize("mod,normal,cf", ENGINES)
def test_determinism_and_ai_fallback(mod, normal, cf):
    m = _m(mod)
    a = m.analyze(normal, use_ai=False)
    b = m.analyze(normal, use_ai=True)  # 无 provider → 回退确定性
    assert b["ai_used"] is False
    assert a["summary"] == m.analyze(normal, use_ai=False)["summary"]


@pytest.mark.parametrize("mod,normal,cf", ENGINES)
def test_empty_input_safe(mod, normal, cf):
    r = _m(mod).analyze("", use_ai=False)
    assert r["crisis"] is False and r["summary"]


# ── 分支专项 ──

def test_holy_spirit_is_not_ignatian_and_has_guardrail():
    m = _m("holy_spirit_engine")
    assert "探照" in m.meta()["core"] or "荣耀基督" in m.meta()["core"]
    assert m.analyze("想被圣灵充满", use_ai=False)["doctrine_note"]


def test_adoption_warmth_fields():
    r = _m("adoption_engine").analyze("我像个奴仆总在赚神的爱", use_ai=False)
    assert r["adoption_truth"] and r["state"]["key"] in ("slave", "orphan", "distant", "fatherwound", "seek")


def test_cross_names_an_achievement():
    r = _m("cross_engine").analyze("觉得神在生我的气", use_ai=False)
    assert r["achievement"]["name"] and r["truth"]


def test_fear_of_man_reversal_and_cure():
    r = _m("fear_of_man_engine").analyze("我总是讨好别人，不敢拒绝", use_ai=False)
    assert r["root"] and r["cure"] and "敬畏神" in r["reversal"]


def test_providence_three_pillars():
    r = _m("providence_engine").analyze("想不通为什么会这样", use_ai=False)
    assert r["pillar"] and r["three_pillars"]


def test_repentance_scruple_branch():
    m = _m("repentance_engine")
    r = m.analyze("我觉得神永远不会原谅我，我不可饶恕", use_ai=False)
    assert r["scruple_flag"] is True and r["state"]["key"] == "condemn"
    assert len(r["six_elements"]) == 6
    # 世俗忧愁 vs 依神忧愁
    r2 = m.analyze("我就是怕被发现、怕丢脸", use_ai=False)
    assert r2["state"]["key"] == "worldly"


def test_doubt_kinds_and_route():
    m = _m("doubt_engine")
    assert m.analyze("有科学证据上的疑问，逻辑上矛盾", use_ai=False)["kind"]["key"] == "intellectual"
    assert m.analyze("苦难让我对神失望，祷告没用", use_ai=False)["kind"]["key"] == "wounded"
    assert m.analyze("我信不动了", use_ai=False)["next_route"]


def test_generosity_steward_identity():
    r = _m("generosity_engine").analyze("这是我挣的钱，凭什么给", use_ai=False)
    assert r["steward_reminder"] and r["state"]["key"] in ("owner", "grip", "hoard", "free", "trust")


def test_humility_distinguishes_from_self_deprecation():
    m = _m("humility_engine")
    assert m.analyze("我老是贬低自己，觉得自己很差", use_ai=False)["state"]["key"] == "selfdeprecate"
    assert "自我遗忘" in m.meta()["core"]


def test_word_delight_gives_a_practice():
    r = _m("word_delight_engine").analyze("读经像打卡，没味道", use_ai=False)
    assert r["word_practice"] and r["image"]
