"""Tests for the stronghold RAG retrieval (pure, keyword mode, no DB/key)."""
from routers.stronghold_rag import retrieve, keyword_score, tokenize, cosine, build_context_bundle
from stronghold_knowledge import corpus_documents

DOCS = corpus_documents()


def test_corpus_size():
    assert len(DOCS) == 18 + 19


def test_retrieve_by_code_boost():
    r = retrieve("我必须成功才有价值", DOCS, stronghold_codes=["achievement_idolatry"], top_k=5)
    assert r[0]["id"] == "sh::achievement_idolatry"


def test_retrieve_keyword_only():
    r = retrieve("我想掌控一切，事情不确定就焦虑", DOCS, top_k=5)
    assert any(d["id"] == "sh::control_idolatry" for d in r)


def test_doctrine_boost():
    r = retrieve("恩典", DOCS, doctrine_codes=["grace"], top_k=5)
    assert any(d["id"] == "doc::grace" for d in r)


def test_cosine():
    assert abs(cosine([1, 0], [1, 0]) - 1.0) < 1e-9
    assert abs(cosine([1, 0], [0, 1])) < 1e-9


def test_context_bundle_shape():
    r = retrieve("苦难 为什么 神不爱我", DOCS, stronghold_codes=["suffering_objection"], top_k=6)
    b = build_context_bundle("苦难", r, ["suffering_objection"], ["god_love"], "comfort")
    assert "pastoralSafetyContext" in b
    assert b["retrievedDocuments"]
    assert any(c["code"] == "suffering_objection" for c in b["strongholdContext"])
