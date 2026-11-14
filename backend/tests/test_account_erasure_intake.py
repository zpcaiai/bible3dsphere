"""Exercise account deletion from authenticated HTTP intake to operator receipt."""

from contextlib import closing
import hashlib
import json
import socket
import threading
from uuid import UUID

import httpx
import psycopg2
import pytest
import uvicorn

from core.security import hash_password
from scripts.execute_account_erasure import execute_erasure
from test_account_erasure_executor import ROOT
from test_ordo_account_custody_http import OWNER, accounts, isolated_dsn


@pytest.mark.no_db
def test_intake_to_erasure_rejects_cached_session(isolated_dsn, monkeypatch):
    import main

    dsn, postgres_pid = isolated_dsn
    tokens = accounts(dsn)
    password = "fixture-password-only"
    with closing(psycopg2.connect(dsn)) as conn, conn, conn.cursor() as cur:
        cur.execute((ROOT / "migrations/0248_account_erasure_receipts.sql").read_text())
        cur.execute("UPDATE users SET password_hash = %s WHERE email = %s",
                    (hash_password(password), OWNER))
    from routers import main_extracted_auth_email as auth
    connect = lambda: psycopg2.connect(dsn)
    for module in (main, auth):
        monkeypatch.setattr(module, "_get_db", connect)
        monkeypatch.setattr(module, "_release_db", psycopg2.extensions.connection.close)
    server = uvicorn.Server(uvicorn.Config(main.app, lifespan="off", log_level="warning"))
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]})
        thread.start()
        try:
            base = f"http://127.0.0.1:{listener.getsockname()[1]}"
            with httpx.Client(base_url=base, timeout=5) as client:
                token = tokens[OWNER]
                headers = {"Authorization": "Bearer " + token}
                me = client.get("/api/auth/me", headers=headers)
                me.raise_for_status()
                user = me.json()["user"]
                with main._SESSION_LOCK:
                    monkeypatch.setitem(main._SESSION_STORE, token, user)
                payload = {"password": password, "confirmation": "REQUEST_ACCOUNT_DELETION"}
                response = client.post("/api/auth/account-deletion", headers=headers, json=payload)
                assert response.status_code == 202, response.text
                assert response.json()["status"] == "pending_review"
                assert response.json()["deletion_completed"] is False
                request_id = UUID(response.json()["request_id"])
                assert client.get("/api/auth/me", headers=headers).status_code == 401
                execute_erasure(dsn, request_id)
                with main._SESSION_LOCK:
                    monkeypatch.setitem(main._SESSION_STORE, token, user)
                assert client.get("/api/auth/me", headers=headers).status_code == 401
                with pytest.raises(main.HTTPException) as rejection:
                    main._make_session(user)
                assert rejection.value.status_code == 401
                with closing(psycopg2.connect(dsn)) as conn, conn.cursor() as cur:
                    cur.execute("SELECT request_id::text FROM account_erasure_receipts")
                    postimage = cur.fetchall()
                assert postimage == [(str(request_id),)]
                print(json.dumps({"postgres_pid": postgres_pid, "http_thread": thread.native_id,
                                  "post_image_sha256": hashlib.sha256(json.dumps(postimage).encode()).hexdigest()}))
        finally:
            server.should_exit = True
            thread.join(timeout=10)
        assert not thread.is_alive()
