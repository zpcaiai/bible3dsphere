"""
test_expansion_pack.py — content-theology-expansion 批次的引擎级测试。
只测纯函数引擎与内容目录（stdlib-only），不依赖 DB/fastapi。
CI/本机可用 pytest 运行；也可 `python3 tests/test_expansion_pack.py` 直接跑。
"""
from __future__ import annotations
import importlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEXT_ENGINES = {  # engine module -> (main callable name, sample kwargs)
    "lament_engine": ("compose", {"text": "我失去了亲人，觉得神很沉默"}),
    "tender_heart_engine": ("comfort", {"text": "我又搞砸了，觉得神对我很失望"}),
    "formation_liturgy_engine": ("analyze", {"habit": "总是忍不住刷手机比较"}),
    "spirits_engine": ("discern", {"text": "这几天读经祷告都很枯干，提不起劲"}),
    "union_engine": ("assess", {"struggle": "我觉得自己一无是处"}),
    "delight_engine": ("reframe", {"duty": "读经对我像例行公事"}),
    "contentment_engine": ("analyze", {"lack": "工资太低，总觉得钱不够"}),
    "ordo_amoris_engine": ("analyze", {"loves": ["工作", "家人", "手机"]}),
}
RATING_ENGINES = {
    "affections_engine": ("assess", {"ratings": {"beauty": 0.8, "humility": 0.3, "renewal": 0.6,
                                                 "christlike": 0.5, "hunger": 0.2, "fruit": 0.7}}),
    "emotionally_healthy_engine": ("assess", {"ratings": {"self_awareness": 0.7, "past": 0.2,
                                              "limits": 0.5, "grief": 0.3, "sabbath": 0.4, "beneath": 0.6}}),
    "renovation_engine": ("assess", {"ratings": {"mind": 0.7, "will": 0.3, "body": 0.5, "social": 0.2, "soul": 0.6}}),
}
ALL = ["lament_engine", "affections_engine", "ordo_amoris_engine", "tender_heart_engine",
       "formation_liturgy_engine", "spirits_engine", "union_engine", "delight_engine",
       "emotionally_healthy_engine", "contentment_engine", "know_god_engine",
       "renovation_engine", "chinese_devotion_engine"]


def test_meta_is_serializable_dict():
    for name in ALL:
        e = importlib.import_module(name)
        m = e.meta()
        assert isinstance(m, dict) and m, name + " meta empty"
        json.dumps(m, ensure_ascii=False)  # must be JSONB-serializable


def test_formation_signal_shape():
    for name in ALL:
        e = importlib.import_module(name)
        sig = e.formation_signal({})
        assert isinstance(sig, tuple) and len(sig) == 4, name + " bad formation_signal"
        cats, lb, refl, emo = sig
        assert isinstance(cats, list) and isinstance(lb, bool) and isinstance(refl, bool)
        assert isinstance(emo, (int, float))


def test_text_engines_run_and_serialize():
    for mod, (fn, kw) in TEXT_ENGINES.items():
        e = importlib.import_module(mod)
        r = getattr(e, fn)(**kw)
        assert isinstance(r, dict) and r, mod + " empty result"
        json.dumps(r, ensure_ascii=False)


def test_rating_engines_run():
    for mod, (fn, kw) in RATING_ENGINES.items():
        e = importlib.import_module(mod)
        r = getattr(e, fn)(**kw)
        assert isinstance(r, dict) and r, mod + " empty result"
        json.dumps(r, ensure_ascii=False)


def test_know_god_both_paths():
    e = importlib.import_module("know_god_engine")
    by_need = e.meditate(need="我好孤独，没人懂我")
    by_attr = e.meditate(attribute="triune_love")
    assert isinstance(by_need, dict) and by_need
    assert isinstance(by_attr, dict) and by_attr


def test_crisis_detection_across_text_engines():
    """自伤词必须被侦测并给出温柔求助提示（安全关键）。"""
    crisis_text = "我不想活了，撑不下去了"
    checks = {
        "lament_engine": ("compose", {"text": crisis_text}),
        "tender_heart_engine": ("comfort", {"text": crisis_text}),
        "spirits_engine": ("discern", {"text": crisis_text}),
        "union_engine": ("assess", {"struggle": crisis_text}),
    }
    for mod, (fn, kw) in checks.items():
        e = importlib.import_module(mod)
        r = getattr(e, fn)(**kw)
        assert r.get("crisis") is True, mod + " failed to flag crisis"
        # crisis 情形下 loop_broken 应为 False（不算突破，先安全）
        _, lb, _, _ = e.formation_signal(r)
        assert lb is False, mod + " should not mark loop_broken in crisis"


def test_content_catalog():
    c = importlib.import_module("expansion_content")
    assert c.meta()["book_count"] >= 30
    assert c.meta()["hymn_count"] >= 10
    assert all("public_domain" in b for b in c.BOOKS)
    assert len(c.list_books("H")) >= 3  # 华人本土灵修 not empty
    json.dumps(c.BOOKS, ensure_ascii=False)
    json.dumps(c.HYMNS, ensure_ascii=False)


def test_chinese_devotion():
    e = importlib.import_module("chinese_devotion_engine")
    assert len(e.meta()["authors"]) >= 3
    assert e.search("受苦")["results"], "search returned nothing"
    r = e.meditate("我为信仰受了很多苦")
    assert isinstance(r, dict) and r.get("entry")
    assert e.meditate("我不想活了")["crisis"] is True


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn(); passed += 1
        print(f"  PASS {fn.__name__}")
    print(f"\n{passed}/{len(fns)} tests passed")
