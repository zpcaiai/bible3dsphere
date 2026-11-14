"""Exercise Ordo with the public PostgreSQL schema and two real HTTP workers."""
import ast
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, closing, contextmanager
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time

from fastapi import FastAPI
import httpx
import psycopg2
import pytest

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "migrations/0233_emd_erasure_propagation.sql"
ADDITIVE = ROOT / "migrations/0247_ordo_account_custody.sql"
OWNER, OTHER = "ordo-owner@example.test", "ordo-other@example.test"
ROUTE = "/api/ordo-amoris"
LOCK = 470247


def schema(dsn):
    tree = ast.parse((ROOT / "db_schema.py").read_text())
    statements = [node.args[0].value for node in ast.walk(tree)
                  if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                  and node.func.attr == "execute" and node.args
                  and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)]
    with closing(psycopg2.connect(dsn)) as conn, conn, conn.cursor() as cur:
        for name in ("users", "user_tokens", "ordo_amoris_records"):
            statement, = (s for s in statements if f"CREATE TABLE IF NOT EXISTS {name} (" in s)
            cur.execute(statement)
        cur.execute("ALTER TABLE users ADD COLUMN is_banned boolean DEFAULT false")
        cur.execute(ORIGINAL.read_text())
        cur.execute(ADDITIVE.read_text())
        cur.execute(ADDITIVE.read_text())


def accounts(dsn):
    tokens = {key: secrets.token_urlsafe(24)
              for key in (OWNER, OTHER, "expired", "mismatch", "revoked")}
    with closing(psycopg2.connect(dsn)) as conn, conn, conn.cursor() as cur:
        for email in (OWNER, OTHER):
            cur.execute("INSERT INTO users(email) VALUES (%s) RETURNING id", (email,))
            uid, = cur.fetchone()
            for key in ((OWNER, "expired", "mismatch", "revoked") if email == OWNER else (OTHER,)):
                cur.execute(
                    "INSERT INTO user_tokens(token,email,data,expires_at) "
                    "VALUES(%s,%s,%s,NOW()+%s::interval)",
                    (tokens[key], email, json.dumps({"id": uid + (key == "mismatch"), "email": email}),
                     "-1 minute" if key == "expired" else "10 minutes"),
                )
    return tokens


def rows(dsn):
    with closing(psycopg2.connect(dsn)) as conn, conn, conn.cursor() as cur:
        cur.execute("SELECT email,input_text FROM ordo_amoris_records ORDER BY email,input_text")
        return cur.fetchall()


def erase(dsn):
    with closing(psycopg2.connect(dsn)) as conn, conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM erase_user_data(%s)", (OWNER,))
        return dict(cur.fetchall())


@contextmanager
def worker(dsn, directory, label):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    with (directory / f"{label}.log").open("xb") as out:
        child = subprocess.Popen(
            [sys.executable, __file__, str(port)],
            env={**os.environ, "ORDO_TEST_DSN": dsn}, stdout=out, stderr=subprocess.STDOUT,
        )
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=5) as client:
                deadline = time.monotonic() + 12
                while time.monotonic() < deadline:
                    assert child.poll() is None
                    try:
                        if client.get("/openapi.json").is_success:
                            break
                    except httpx.TransportError:
                        time.sleep(.1)
                else:
                    raise AssertionError("Ordo HTTP worker did not start")
                yield child.pid, client
        finally:
            child.terminate()
            child.wait(timeout=15)


@pytest.fixture
def isolated_dsn(tmp_path):
    pg = Path(os.environ.get("ORDO_PG_BIN", "/opt/homebrew/opt/postgresql@17/bin"))
    assert (pg / "initdb").is_file(), "Set ORDO_PG_BIN to the PostgreSQL bin directory"
    data = tmp_path / "pg"
    sock = Path("/tmp") / ("ordos-" + secrets.token_hex(6))
    sock.mkdir()
    try:
        subprocess.run([pg/"initdb", "-D", data, "-U", "postgres", "--auth-local=trust",
                        "--auth-host=reject", "--encoding=UTF8", "--no-locale"], check=True)
        subprocess.run([pg/"pg_ctl", "-D", data, "-l", tmp_path/"pg.log", "-o",
                        f"-c listen_addresses='' -k {sock}", "-w", "start"], check=True)
        try:
            dsn = f"host={sock} user=postgres dbname=postgres"
            schema(dsn)
            yield dsn, int((data/"postmaster.pid").read_text().splitlines()[0])
        finally:
            subprocess.run([pg/"pg_ctl", "-D", data, "-m", "fast", "-w", "stop"], check=True)
    finally:
        shutil.rmtree(sock)


@pytest.mark.no_db  # The test owns a separate PostgreSQL cluster.
def test_ordo_rejects_revoked_sessions_and_erases_a_racing_save(isolated_dsn, tmp_path):
    dsn, pg_pid = isolated_dsn
    tokens = accounts(dsn)
    bearer = lambda token: {"Authorization": f"Bearer {token}"}
    cookie = {"Cookie": f"biblesphere_session={tokens[OWNER]}"}
    with ExitStack() as stack:
        p1, a = stack.enter_context(worker(dsn, tmp_path, "http-a"))
        p2, b = stack.enter_context(worker(dsn, tmp_path, "http-b"))
        assert p1 != p2 and min(p1, p2, pg_pid) > 0
        for headers in ({}, bearer(tokens["expired"]), bearer(tokens["mismatch"])):
            assert a.get(ROUTE + "/history", headers=headers).status_code == 401
            assert a.post(ROUTE + "/record", headers=headers, json={}).status_code == 401
        for client, headers, content in ((a, cookie, "owner"), (b, bearer(tokens[OTHER]), "other")):
            assert client.post(ROUTE + "/record", headers=headers,
                               json={"input_text": content}).is_success
            history = client.get(ROUTE + "/history", headers=headers)
            history.raise_for_status()
            assert [r["input_text"] for r in history.json()["items"]] == [content]
        assert b.get(ROUTE + "/history", headers=bearer(tokens[OWNER])).is_success
        assert a.get(ROUTE + "/history", headers=bearer(tokens["revoked"])).is_success
        with closing(psycopg2.connect(dsn)) as conn, conn, conn.cursor() as cur:
            cur.execute("DELETE FROM user_tokens WHERE token = %s", (tokens["revoked"],))
        for client in (a, b):
            assert client.get(ROUTE + "/history", headers=bearer(tokens["revoked"])).status_code == 401
            assert client.post(ROUTE + "/record", headers=bearer(tokens["revoked"]), json={}).status_code == 401

        # Pause the real erasure transaction after its Ordo sweep but before
        # deleting users. The late save commits in the other HTTP worker.
        with closing(psycopg2.connect(dsn)) as control, control.cursor() as cur:
            cur.execute(f"""CREATE FUNCTION pause_session_delete() RETURNS trigger AS $$
                BEGIN PERFORM pg_advisory_xact_lock({LOCK}); RETURN OLD; END;
                $$ LANGUAGE plpgsql""")
            cur.execute("CREATE TRIGGER pause_session_delete BEFORE DELETE ON user_tokens "
                        "FOR EACH ROW EXECUTE FUNCTION pause_session_delete()")
            control.commit()
            cur.execute("SELECT pg_advisory_lock(%s)", (LOCK,))
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(erase, dsn)
                try:
                    for _ in range(200):
                        cur.execute("SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' "
                                    "AND objid = %s AND NOT granted", (LOCK,))
                        if cur.fetchone()[0] == 1:
                            break
                        time.sleep(.025)
                    else:
                        raise AssertionError("Erasure did not reach the session deletion latch")
                    result = b.post(ROUTE + "/record", headers=bearer(tokens[OWNER]),
                                    json={"input_text": "racing save"})
                    result.raise_for_status()
                    assert (OWNER, "racing save") in rows(dsn)
                finally:
                    cur.execute("SELECT pg_advisory_unlock(%s)", (LOCK,))
                erased = future.result(timeout=10)
        expected = [(OTHER, "other")]
        assert erased["users"] == 1 and erased["user_tokens"] == 3
        assert rows(dsn) == expected
        for client in (a, b):
            for headers in (bearer(tokens[OWNER]), cookie):
                assert client.get(ROUTE + "/history", headers=headers).status_code == 401
                assert client.post(ROUTE + "/record", headers=headers,
                                   json={"input_text": "recreate"}).status_code == 401
        assert rows(dsn) == expected
        print(json.dumps({"postgres_pid": pg_pid, "http_pids": [p1, p2], "erasure": erased,
                          "post_image_sha256": hashlib.sha256(json.dumps(rows(dsn)).encode()).hexdigest()}))


@pytest.mark.no_db  # The test owns a separate PostgreSQL cluster.
def test_ordo_closes_when_legacy_rows_prevent_applying_custody_migration(isolated_dsn, tmp_path):
    dsn, pg_pid = isolated_dsn
    tokens = accounts(dsn)
    orphan = ("orphan@example.test", "preserved prior reflection")
    with closing(psycopg2.connect(dsn)) as conn, conn.cursor() as cur:
        cur.execute("ALTER TABLE ordo_amoris_records DROP CONSTRAINT ordo_amoris_records_account_fk")
        cur.execute("INSERT INTO ordo_amoris_records(id,email,input_text) VALUES ('legacy',%s,%s)", orphan)
        conn.commit()
        with pytest.raises(psycopg2.errors.ForeignKeyViolation):
            cur.execute(ADDITIVE.read_text())
        conn.rollback()
    with worker(dsn, tmp_path, "http") as (pid, client):
        headers = {"Authorization": f"Bearer {tokens[OWNER]}"}
        assert client.get(ROUTE + "/history", headers=headers).status_code == 503
        assert client.post(ROUTE + "/record", headers=headers,
                           json={"input_text": "must not persist"}).status_code == 503
        assert rows(dsn) == [orphan]
        print(json.dumps({"postgres_pid": pg_pid, "http_pid": pid, "preserved_rows": 1,
                          "post_image_sha256": hashlib.sha256(json.dumps(rows(dsn)).encode()).hexdigest()}))


@pytest.mark.no_db
@pytest.mark.parametrize(
    "definition",
    [
        "FOREIGN KEY (route) REFERENCES users(email) ON UPDATE CASCADE ON DELETE CASCADE",
        "FOREIGN KEY (email) REFERENCES users(openid) ON UPDATE CASCADE ON DELETE CASCADE",
        "FOREIGN KEY (email) REFERENCES users(email) ON DELETE CASCADE",
    ],
    ids=["wrong-source-key", "wrong-target-key", "missing-update-cascade"],
)
def test_ordo_closes_on_same_named_incompatible_foreign_key(isolated_dsn, tmp_path, definition):
    dsn, pg_pid = isolated_dsn
    tokens = accounts(dsn)
    with closing(psycopg2.connect(dsn)) as conn, conn, conn.cursor() as cur:
        cur.execute("ALTER TABLE ordo_amoris_records DROP CONSTRAINT ordo_amoris_records_account_fk")
        cur.execute("UPDATE users SET openid = %s WHERE email = %s", (OWNER, OTHER))
        cur.execute(
            f"ALTER TABLE ordo_amoris_records ADD CONSTRAINT ordo_amoris_records_account_fk {definition}"
        )
        cur.execute(
            "INSERT INTO ordo_amoris_records(id,email,input_text,route) VALUES ('old',%s,%s,NULL)",
            (OWNER, "preserved practice"),
        )

    expected = [(OWNER, "preserved practice")]
    with worker(dsn, tmp_path, "incompatible-fk") as (pid, client):
        headers = {"Authorization": f"Bearer {tokens[OWNER]}"}
        history_code = client.get(ROUTE + "/history", headers=headers).status_code
        write_code = client.post(ROUTE + "/record", headers=headers,
                                 json={"input_text": "unexpected write", "route": OTHER}).status_code
        print(json.dumps({"postgres_pid": pg_pid, "http_pid": pid, "history": history_code,
                          "record": write_code}), flush=True)
        assert (history_code, write_code) == (503, 503)

    with closing(psycopg2.connect(dsn)) as conn, conn.cursor() as cur:
        with pytest.raises(psycopg2.errors.CheckViolation, match="incompatible foreign key"):
            cur.execute(ADDITIVE.read_text())
        conn.rollback()
        cur.execute(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conrelid = 'public.ordo_amoris_records'::regclass "
            "AND conname = 'ordo_amoris_records_account_fk'"
        )
        assert cur.fetchone() == (definition,)
    assert rows(dsn) == expected
    print(json.dumps({"post_image_sha256": hashlib.sha256(json.dumps(rows(dsn)).encode()).hexdigest()}))


if __name__ == "__main__":
    import uvicorn
    from routers.ordo_amoris import init_ordo_amoris_router, router

    dsn = os.environ["ORDO_TEST_DSN"]
    init_ordo_amoris_router(get_db=lambda: psycopg2.connect(dsn),
                           release_db=psycopg2.extensions.connection.close,
                           get_session_user=None, to_shanghai_iso=None)
    app = FastAPI()
    app.include_router(router)
    uvicorn.run(app, host="127.0.0.1", port=int(sys.argv[1]))

