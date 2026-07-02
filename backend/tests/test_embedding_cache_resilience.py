import numpy as np
import pytest
import requests

pytestmark = pytest.mark.no_db


def test_synthetic_embedding_cache_miss_returns_vectors_without_saving(monkeypatch, tmp_path):
    import query_emotion_verses as qev

    features = [
        {
            "layer": "test-layer",
            "feature_id": 1,
            "source_keyword": "feeling",
            "explanation": "offline startup",
        },
        {
            "layer": "test-layer",
            "feature_id": 2,
            "source_keyword": "peace",
            "explanation": "offline startup",
        },
    ]
    cache_file = tmp_path / "emotion_feature_embedding_cache.gemini-embedding-001.json"

    def synthetic_embeddings(texts):
        qev._LAST_EMBEDDINGS_SYNTHETIC = True
        return np.asarray([qev._local_embedding(text) for text in texts], dtype=np.float32)

    monkeypatch.setattr(qev, "get_embeddings", synthetic_embeddings)

    loaded_features, embeddings = qev.load_or_build_feature_embeddings(features, str(cache_file))

    assert loaded_features == features
    assert embeddings.shape == (2, qev.EMBED_DIM)
    assert not np.allclose(embeddings, 0)
    assert np.allclose(np.linalg.norm(embeddings, axis=1), 1.0)
    assert not cache_file.exists()


def test_gemini_embedding_auth_error_disables_provider(monkeypatch):
    import query_emotion_verses as qev

    calls = {"count": 0}

    class Response:
        status_code = 403
        text = '{"error":{"status":"PERMISSION_DENIED","message":"denied access"}}'

    def deny_access(*_args, **_kwargs):
        calls["count"] += 1
        exc = requests.exceptions.HTTPError("403 Client Error")
        exc.response = Response()
        raise exc

    qev._EMBED_PROVIDER_DISABLED.clear()
    monkeypatch.setattr(qev, "GEMINI_API_CHAT_KEY", "test-key")
    monkeypatch.setattr(qev, "_GEMINI_EMBED_ACTIVE", None)
    monkeypatch.setattr(qev, "post_with_retry", deny_access)

    with pytest.raises(requests.exceptions.HTTPError):
        qev._embed_via_gemini(["first"])
    with pytest.raises(RuntimeError, match="gemini embeddings disabled"):
        qev._embed_via_gemini(["second"])

    assert calls["count"] == 1
    qev._EMBED_PROVIDER_DISABLED.clear()


def test_concurrent_gemini_embeddings_probe_auth_error_once(monkeypatch):
    import query_emotion_verses as qev

    calls = {"count": 0}

    class Response:
        status_code = 403
        text = '{"error":{"status":"PERMISSION_DENIED","message":"denied access"}}'

    def deny_access(*_args, **_kwargs):
        calls["count"] += 1
        exc = requests.exceptions.HTTPError("403 Client Error")
        exc.response = Response()
        raise exc

    qev._EMBED_PROVIDER_DISABLED.clear()
    monkeypatch.setattr(qev, "EMBED_PROVIDER", "gemini")
    monkeypatch.setattr(qev, "GEMINI_API_CHAT_KEY", "test-key")
    monkeypatch.setattr(qev, "SILICONFLOW_API_KEY", "")
    monkeypatch.setattr(qev, "EMBED_FALLBACK_URL", "")
    monkeypatch.setattr(qev, "EMBED_FALLBACK_KEY", "")
    monkeypatch.setattr(qev, "_GEMINI_EMBED_ACTIVE", None)
    monkeypatch.setattr(qev, "_EMBED_DIM_ACTUAL", None)
    monkeypatch.setattr(qev, "post_with_retry", deny_access)

    embeddings = qev.get_embeddings(["a", "b", "c", "d"])

    assert calls["count"] == 1
    assert embeddings.shape == (4, qev.EMBED_DIM)
    assert not np.allclose(embeddings, 0)
    assert np.allclose(np.linalg.norm(embeddings, axis=1), 1.0)
    assert qev._LAST_EMBEDDINGS_SYNTHETIC is True
    qev._EMBED_PROVIDER_DISABLED.clear()
