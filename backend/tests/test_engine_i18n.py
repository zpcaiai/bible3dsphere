"""Real-data tests for engine_i18n (no mock): deterministic ESV reference
conversion + graceful zh fallback + zh passthrough. LLM prose path is verified
live with a real API key (see outputs/verify_en_live.py)."""
import importlib
import pytest
import engine_i18n as I

pytestmark = pytest.mark.no_db


@pytest.mark.parametrize("zh,en", [
    ("弗4:26", "Eph 4:26"), ("撒上18:8-9", "1 Sam 18:8-9"), ("诗119:103", "Ps 119:103"),
    ("约壹1:9", "1 John 1:9"), ("林后5:21", "2 Cor 5:21"), ("帖前4:16-18", "1 Thess 4:16-18"),
    ("创16:13", "Gen 16:13"), ("来12:14", "Heb 12:14"), ("提前1:5", "1 Tim 1:5"),
    ("代下7:14", "2 Chr 7:14"), ("约叁1:4", "3 John 1:4"), ("哀3:22-23", "Lam 3:22-23"),
])
def test_reference_conversion(zh, en):
    assert I.is_reference(zh) is True
    assert I.convert_reference(zh) == en


def test_not_a_reference():
    for s in ["我心里柔和谦卑", "凡事谢恩", "God is good", "腓立比书是保罗写的"]:
        assert I.is_reference(s) is False


def test_zh_passthrough_unchanged():
    r = {"summary": "愤怒可以带到神面前", "anchor": {"ref": "弗4:26", "text": "生气却不要犯罪"}}
    out = I.localize(r, "zh")
    assert out is r or out == r
    assert "lang" not in out and out["anchor"]["ref"] == "弗4:26"


def test_en_fallback_without_llm_preserves_zh_but_converts_refs():
    r = {"crisis": False, "summary": "愤怒可以带到神面前",
         "anchor": {"ref": "弗4:26", "text": "生气却不要犯罪"},
         "practices": ["插一个停顿"], "ai_used": False}
    out = I.localize(r, "en", settings=None)  # no provider configured -> graceful fallback
    assert out["lang"] == "en" and out["en_localized"] is False
    assert out["anchor"]["ref"] == "Eph 4:26"          # deterministic ref conversion still applies
    assert out["summary"] == "愤怒可以带到神面前"        # prose stays Chinese (no LLM)
    assert out["practices"] == ["插一个停顿"]


@pytest.mark.parametrize("name", ["assurance", "anger", "chronic_suffering", "holy_spirit", "aging"])
def test_real_engine_output_localizes_without_error(name):
    m = importlib.import_module(f"{name}_engine")
    r = m.analyze("我很挣扎，需要帮助", use_ai=False)
    out = I.localize(r, "en", settings=None)
    assert out["lang"] == "en"
    # every scripture ref in a real engine result converts to English (no CJK book left)
    ref = out["anchor"]["ref"]
    assert not any('一' <= c <= '鿿' for c in ref)
