"""Unit tests for expansion batch 5 engines (emotional/pastoral/life-stage),
deterministic path, no DB / no AI."""
import importlib
import pytest

pytestmark = pytest.mark.no_db

ENGINES = [
    ("anger_engine",             "我一点就炸，事后很后悔"),
    ("loneliness_engine",        "没人懂我，觉得不被看见"),
    ("perfectionism_engine",     "我做什么都觉得不够好"),
    ("envy_engine",              "见不得别人成功，很眼红"),
    ("burnout_engine",           "我烧干了，什么都给不出"),
    ("comfort_engine",           "朋友丧亲了，我不知道说什么"),
    ("prodigal_engine",          "为远离神的孩子揪心"),
    ("acedia_engine",            "什么都不想做，提不起劲"),
    ("conscience_engine",        "为圣经没禁止的事一直定罪自己"),
    ("second_coming_engine",     "我属灵懈怠，活得像主不回来"),
    ("chronic_suffering_engine", "慢性病看不到尽头，日复一日"),
    ("parenting_engine",         "管孩子越管越僵，总靠吼"),
    ("aging_engine",             "觉得老了没用了，不被需要"),
]
CRISIS = ["我想死了不想活了", "撑不下去了想消失", "自杀", "去死算了"]


def _m(n):
    return importlib.import_module(n)


@pytest.mark.parametrize("mod,normal", ENGINES)
def test_meta(mod, normal):
    meta = _m(mod).meta()
    assert meta.get("title") and meta.get("verse") and meta.get("core")


@pytest.mark.parametrize("mod,normal", ENGINES)
def test_analyze_contract(mod, normal):
    r = _m(mod).analyze(normal, use_ai=False)
    for k in ("summary", "prayer", "closing", "anchor", "ai_used", "state"):
        assert k in r, f"{mod} 缺 {k}"
    assert r["ai_used"] is False
    assert isinstance(r["anchor"], dict) and (r["anchor"].get("ref") or r["anchor"].get("text"))
    assert isinstance(r["state"], dict) and r["state"].get("name")


@pytest.mark.parametrize("mod,normal", ENGINES)
def test_no_false_positive(mod, normal):
    r = _m(mod).analyze(normal, use_ai=False)
    assert r["crisis"] is False and r.get("crisis_note", "") == ""


@pytest.mark.parametrize("mod,_n", ENGINES)
@pytest.mark.parametrize("ct", CRISIS)
def test_crisis(mod, _n, ct):
    r = _m(mod).analyze(ct, use_ai=False)
    assert r["crisis"] is True and r["crisis_note"]


@pytest.mark.parametrize("mod,normal", ENGINES)
def test_formation_and_determinism(mod, normal):
    m = _m(mod)
    r = m.analyze(normal, use_ai=False)
    sig = m.formation_signal(r)
    assert isinstance(sig, tuple) and len(sig) == 4 and isinstance(sig[0], list) and sig[0]
    sc = m.formation_signal(m.analyze("我想死了", use_ai=False))
    assert sc[1] is False and sc[3] <= sig[3]
    assert m.analyze(normal, use_ai=False)["summary"] == r["summary"]
    assert m.analyze(normal, use_ai=True)["ai_used"] is False  # 无 provider 回退


@pytest.mark.parametrize("mod,normal", ENGINES)
def test_empty_safe(mod, normal):
    r = _m(mod).analyze("", use_ai=False)
    assert r["crisis"] is False and r["summary"]


# ── 分支专项 ──

def test_anger_violence_and_steps():
    m = _m("anger_engine")
    r = m.analyze("我气到想揍他，弄死他", use_ai=False)
    assert r["violence_flag"] is True and r["violence_note"]
    assert any("安全" in p for p in r["practices"])
    assert len(m.analyze("我容易发火", use_ai=False)["four_steps"]) == 4


def test_loneliness_two_moves():
    r = _m("loneliness_engine").analyze("我很孤单，一个人", use_ai=False)
    assert r["two_moves"] and "El Roi" in r["summary"] or r["two_moves"]


def test_perfectionism_two_voices_and_shame():
    m = _m("perfectionism_engine")
    r = m.analyze("我总觉得不够好", use_ai=False)
    assert r["inner_critic"] and r["christ_voice"]
    assert m.analyze("我一无是处，我恨自己", use_ai=False)["shame_flag"] is True


def test_envy_antidote():
    assert _m("envy_engine").analyze("我很嫉妒同事", use_ai=False)["antidote"]


def test_burnout_restore_order():
    r = _m("burnout_engine").analyze("我快撑不住了，透支", use_ai=False)
    assert isinstance(r["restore_order"], list) and len(r["restore_order"]) == 3


def test_comfort_avoid_and_object_crisis():
    m = _m("comfort_engine")
    r = m.analyze("不知道怎么安慰受苦的朋友", use_ai=False)
    assert isinstance(r["avoid"], list) and r["avoid"]
    assert m.analyze("我朋友想自杀，我怎么陪他", use_ai=False)["crisis"] is True


def test_prodigal_posture():
    r = _m("prodigal_engine").analyze("为未信的配偶祷告", use_ai=False)
    assert isinstance(r["posture"], list) and len(r["posture"]) == 4


def test_acedia_distinguishes_from_depression():
    m = _m("acedia_engine")
    assert m.analyze("我什么都不想做", use_ai=False)["distinction"]


def test_conscience_scruple_and_calibrate():
    m = _m("conscience_engine")
    assert m.analyze("我不可饶恕，神不会原谅", use_ai=False)["scruple_flag"] is True
    assert m.analyze("我良心一直不安", use_ai=False)["calibrate_note"]


def test_chronic_hope_link_and_crisis_words():
    m = _m("chronic_suffering_engine")
    assert m.analyze("慢性病很久了", use_ai=False)["hope_link"]
    assert m.analyze("我想求解脱，不想拖累家人", use_ai=False)["crisis"] is True


def test_aging_crisis_words():
    assert _m("aging_engine").analyze("我活够了，求死", use_ai=False)["crisis"] is True


def test_second_coming_pictures():
    assert len(_m("second_coming_engine").meta()["pictures"]) == 3
