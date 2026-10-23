"""Actual loopback HTTP proof for the domain router, not production auth/DB.

Only the session identity is a test fixture. Catalog, retrieval, citations,
context validation, response gates and HTTP serialization execute real code.
"""
import hmac
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest

pytestmark = pytest.mark.no_db


def domain_test_app(session_token):
    from fastapi import FastAPI
    from routers import digital_human
    app = FastAPI()

    def fixture_identity(request):
        return {"email": "local-domain-fixture@example.test"} if hmac.compare_digest(request.cookies.get("dh_local_test", ""), session_token) else None

    digital_human.init_digital_human_router(get_session_user=fixture_identity, is_admin=lambda _email: False)
    app.include_router(digital_human.router)
    return app


def test_actual_child_http_executes_catalog_study_and_context(tmp_path):
    token = secrets.token_urlsafe(24)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        listener.listen()
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        for key in list(env):
            if key.startswith("DIGITAL_HUMAN_") or key in {"LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"}:
                env.pop(key)
        with (tmp_path / "owned-server.log").open("w") as log:
            child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "serve-fd", str(listener.fileno()), token], pass_fds=(listener.fileno(),), stdout=log, stderr=log, env=env)
            try:
                def request(path, payload=None, authenticated=True):
                    headers = {"Content-Type": "application/json"}
                    if authenticated:
                        headers["Cookie"] = f"dh_local_test={token}"
                    req = Request(f"http://127.0.0.1:{port}/api/v1/digital-human{path}", headers=headers, data=json.dumps(payload).encode() if payload is not None else None)
                    try:
                        with urlopen(req, timeout=5) as response:
                            return response.status, json.load(response)
                    except HTTPError as error:
                        return error.code, json.load(error)

                deadline = time.monotonic() + 30
                while True:
                    assert child.poll() is None, (tmp_path / "owned-server.log").read_text()
                    try:
                        status, catalog = request("/catalog")
                        break
                    except (URLError, TimeoutError):
                        if time.monotonic() >= deadline:
                            raise
                        time.sleep(0.05)
                assert status == 200 and len(catalog["characters"]) == 100
                assert request("/catalog", authenticated=False)[0] == 401
                status, study = request("/characters/eve/study")
                assert status == 200
                assert study["topics"][2]["canonicalReferences"] == ["Genesis 4:1-2", "Genesis 4:25"]
                status, first = request("/turns", {"characterId": "david", "question": "你如何面对歌利亚？"})
                assert status == 200 and first["state"] == "TEXT_ONLY"
                status, anointing = request("/turns", {"characterId": "david", "question": "撒母耳为什么膏立你？"})
                assert status == 200 and anointing["state"] == "TEXT_ONLY"
                assert [ref["locator"] for ref in anointing["response"]["references"]] == ["1 Samuel 16:13"]
                assert anointing["response"]["relatedCharacters"] == ["samuel"]
                assert anointing["response"]["contentReviewState"] == "THEOLOGY_REVIEW"
                assert anointing["response"]["speechApproved"] is False
                assert request("/turns", {"characterId": "david", "question": "你为什么膏立撒母耳？"})[1]["state"] == "BLOCKED"
                print("actual_anointing_http_response=" + json.dumps(anointing, ensure_ascii=False))
                status, followup = request("/turns", {"characterId": "david", "question": "相关经文呢？", "context": {"characterId": "david", "topicIds": first["response"]["relatedEvents"]}})
                assert status == 200
                assert "session-topic-context" in followup["response"]["warnings"]
                assert [item["locator"] for item in followup["response"]["references"]] == ["1 Samuel 17"]
                assert request("/turns", {"characterId": "paul", "question": "出处呢？", "context": {"characterId": "david", "topicIds": ["david-goliath"]}})[0] == 422
                assert request("/turns", {"characterId": "moses", "question": "出埃及时的法老到底是谁？"})[1]["state"] == "BLOCKED"
                for cid, question, first_refs, next_refs in [
                    ("moses", "过红海的记载是什么？", ["Exodus 14"], ["Exodus 14"]),
                    ("peter", "你为什么在海面上沉下去？", ["Matthew 14:28-31"], ["Matthew 14:28-31"]),
                    ("paul", "你为什么与巴拿巴分开？", ["Acts 15:36-41"], ["Acts 15:36-41"]),
                    ("ruth", "你为什么到波阿斯田里拾穗？", ["Ruth 2"], ["Ruth 2"]),
                    ("samuel", "你为什么膏立大卫？", ["1 Samuel 16:13"], ["1 Samuel 16:1-13"]),
                ]:
                    status, initial = request("/turns", {"characterId": cid, "question": question, "sessionId": "native-" + cid})
                    assert status == 200
                    assert [ref["locator"] for ref in initial["response"]["references"]] == first_refs
                    status, continued = request("/turns", {
                        "characterId": cid, "question": "这些经文的出处呢？", "sessionId": "native-" + cid,
                        "context": {"characterId": cid, "topicIds": initial["response"]["relatedEvents"]},
                    })
                    assert status == 200
                    assert continued["response"]["characterId"] == cid
                    assert [ref["locator"] for ref in continued["response"]["references"]] == next_refs
                    assert "session-topic-context" in continued["response"]["warnings"]
                    assert continued["response"]["speechApproved"] is False
                    assert continued["response"]["contentReviewState"] == "THEOLOGY_REVIEW"
                    print("actual_other_character_http=" + json.dumps({"first": initial, "followup": continued}, ensure_ascii=False))
                runtime = request("/runtime")[1]
                assert runtime["readiness"]["runtimeReadyCharacterCount"] == 0
                assert runtime["readiness"]["productAssurance"] == "NOT_CERTIFIED"
                assert child.pid > 0
                print(f"native_child_pid={child.pid}; real_loopback_http=true; authentication=fixture-only; database=NOT_RUN; voice=NOT_RUN")
            finally:
                child.terminate()
                child.wait(timeout=10)


if __name__ == "__main__":
    import uvicorn
    app = domain_test_app(sys.argv[3])
    if sys.argv[1] == "serve-fd":
        uvicorn.run(app, fd=int(sys.argv[2]), log_level="error")
    elif sys.argv[1] == "serve-port":
        uvicorn.run(app, host="127.0.0.1", port=int(sys.argv[2]), log_level="error")
    else:
        raise SystemExit("expected serve-fd or serve-port")
