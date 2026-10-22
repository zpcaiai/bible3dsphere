"""Real PostgreSQL/router contract checks; no network providers or production DB.

Run explicitly with --confcutdir=backend/tests/native_sermon. This suite owns an
isolated real SQL schema and does not need the unrelated whole-app fixtures.
Authentication identities are explicit request fixtures; production auth itself
is not being certified by these router/SQL tests.
"""
import ast
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import uuid
import time
from datetime import timezone, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
import psycopg2
import pytest

from backend.routers import main_extracted_sermon as sermon
from backend.routers import personal_notes
from backend.routers import admin_content, admin_common, recycle_bin
from backend.core import migrations
from backend.routers import journal

pytestmark = pytest.mark.integration


@pytest.fixture()
def database():
    dsn = os.environ['SERMON_TEST_DATABASE_URL']
    schema = 'sermon_test_' + uuid.uuid4().hex
    admin = psycopg2.connect(dsn)
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute(f'CREATE SCHEMA {schema}')
    admin.close()

    def connect():
        return psycopg2.connect(dsn, options=f'-csearch_path={schema}')

    conn = connect()
    source = Path(sermon.__file__).parents[1] / 'db_schema.py'
    statements = [node.args[0].value for node in ast.walk(ast.parse(source.read_text()))
                  if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                  and node.func.attr == 'execute' and node.args
                  and isinstance(node.args[0], ast.Constant)
                  and isinstance(node.args[0].value, str)]
    with conn.cursor() as cur:
        cur.execute(next(sql for sql in statements if 'CREATE TABLE IF NOT EXISTS sermon_journals (' in sql))
        for fragment in ['CREATE TABLE IF NOT EXISTS personal_notes (',
                         'CREATE TABLE IF NOT EXISTS prayers (',
                         'CREATE TABLE IF NOT EXISTS evangelism_prayers (',
                         'CREATE TABLE IF NOT EXISTS devotion_journals (',
                         'ALTER TABLE personal_notes ADD COLUMN shared_at',
                         'CREATE TABLE IF NOT EXISTS note_interactions (',
                         'source_sermon_id INTEGER REFERENCES',
                         'CREATE UNIQUE INDEX IF NOT EXISTS idx_note_source_sermon']:
            cur.execute(next(sql for sql in statements if fragment in sql))
        cur.execute(next(sql for sql in admin_common._TABLES_SQL.split(';') if 'CREATE TABLE IF NOT EXISTS admin_audit_log' in sql))
        cur.execute('SELECT version()')
        assert 'PostgreSQL 17.' in cur.fetchone()[0]
    conn.commit()
    conn.close()
    yield connect


@pytest.fixture()
def client(database, monkeypatch):
    monkeypatch.setattr(sermon, '_get_db', database)
    monkeypatch.setattr(sermon, '_release_db', lambda conn: conn.close())
    monkeypatch.setattr(sermon, '_get_session_user', lambda request: {
        'email': request.headers['authorization'][7:]
    } if request.headers.get('authorization', '').startswith('Bearer ') else None)
    monkeypatch.setattr(sermon, '_is_admin', lambda email: email == 'owner@example.test')
    # Execute the actual production display formatter. It rounds to minutes;
    # write guards must not silently inherit that lossy presentation format.
    source = Path(sermon.__file__).parents[1] / 'main.py'
    tree = ast.parse(source.read_text())
    node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == '_to_shanghai_iso')
    namespace = {'timezone':timezone, '_SHANGHAI_TZ':timezone(timedelta(hours=8))}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), namespace)
    monkeypatch.setattr(sermon, '_to_shanghai_iso', namespace['_to_shanghai_iso'])
    app = FastAPI()
    app.include_router(sermon.router)
    for name in ['_get_db', '_release_db', '_get_session_user', '_to_shanghai_iso']:
        monkeypatch.setattr(personal_notes, name, getattr(sermon, name))
    monkeypatch.setattr(personal_notes, '_sanitize_text', lambda text: text)
    monkeypatch.setattr(personal_notes, '_validate_date_str', lambda text: text)
    app.include_router(personal_notes.router)
    for name in ['_get_db', '_release_db', '_get_session_user', '_to_shanghai_iso', '_is_admin']:
        monkeypatch.setattr(recycle_bin, name, getattr(sermon, name))
    for key, value in [('get_db',database), ('release_db',sermon._release_db), ('get_session_user',sermon._get_session_user), ('is_admin',sermon._is_admin)]:
        monkeypatch.setitem(admin_common._state, key, value)
    app.include_router(admin_content.router)
    app.include_router(recycle_bin.router)
    for key,value in [('get_db',database),('release_db',sermon._release_db),('get_session_user',sermon._get_session_user),('sanitize_text',lambda text:text),('validate_date_str',lambda text:text),('to_shanghai_iso',sermon._to_shanghai_iso)]:
        monkeypatch.setitem(journal._state,key,value)
    app.include_router(journal.router)
    return TestClient(app)


OWNER = {'Authorization': 'Bearer owner@example.test'}
OTHER = {'Authorization': 'Bearer other@example.test'}


def test_equal_timestamp_pages_have_stable_unique_order(client,database):
    for i in range(3):
        assert client.post('/api/personal/notes',headers=OWNER,json={
            'id':f'note-{i}','date':'2026-10-23','observation':str(i),'shared':True,
        }).status_code == 200
        assert client.post('/api/devotion/journals',headers=OWNER,json={
            'date':f'2026-10-{20+i}','reflection':str(i),'create_only':True,
        }).status_code == 200
    with database() as conn, conn.cursor() as cur:
        cur.execute("UPDATE personal_notes SET shared_at='2026-10-23 00:00:00'")
        cur.execute("UPDATE devotion_journals SET updated_at='2026-10-23 00:00:00'")
    notes = [client.get(f'/api/shared/notes?limit=1&page={p}',headers=OWNER).json()['items'][0]['id'] for p in range(1,4)]
    journals = [client.get(f'/api/devotion/journals?limit=1&offset={p}',headers=OWNER).json()['items'][0]['id'] for p in range(3)]
    assert notes == ['note-2','note-1','note-0']
    assert journals == sorted(set(journals),reverse=True)
    assert len(journals) == 3


def test_amen_toggles_serialize_and_recheck_visibility_after_wait(client, database):
    created = client.post('/api/personal/notes', headers=OWNER, json={
        'date':'2026-10-23', 'observation':'Concurrent reactions', 'shared':True,
        'create_only':True,
    })
    assert created.status_code == 200
    item = client.get('/api/shared/notes', headers=OTHER).json()['items'][0]
    path = f"/api/shared/notes/{item['id']}/amen"
    # Two requests for the same real row represent two serialized toggles.
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: client.post(path, headers=OTHER), range(2)))
    assert [r.status_code for r in results] == [200,200]
    assert sorted(r.json()['amen_by_me'] for r in results) == [False,True]
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM note_interactions WHERE note_id=%s',(item['id'],))
        assert cur.fetchone()[0] == 0

    # Hold the actual visibility lock while the API waits; withdrawal commits
    # first, so the blocked request must re-read false and reject the reaction.
    holder = database()
    with holder.cursor() as cur:
        cur.execute('SELECT shared FROM personal_notes WHERE id=%s FOR UPDATE',(item['id'],))
    try:
        with ThreadPoolExecutor(1) as pool:
            pending = pool.submit(lambda: client.post(path,headers=OTHER))
            deadline = time.monotonic()+10
            waiting = False
            while time.monotonic() < deadline:
                with database() as probe, probe.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM pg_stat_activity WHERE wait_event_type='Lock' AND query LIKE 'SELECT shared FROM personal_notes%FOR UPDATE%'")
                    waiting = cur.fetchone()[0] > 0
                if waiting:
                    break
                time.sleep(0.01)
            if not waiting:
                holder.rollback()
            assert waiting, 'API must acquire the real publication row lock'
            with holder.cursor() as cur:
                cur.execute('UPDATE personal_notes SET shared=FALSE,shared_at=NULL WHERE id=%s',(item['id'],))
            holder.commit()
            assert pending.result(timeout=10).status_code == 404
    finally:
        holder.rollback()
        holder.close()


def test_owner_share_real_wall_update_withdraw_delete(client, database):
    journal = post(client, full_payload('2026年10月18日')).json()['journal']
    path = f"/api/sermon/journals/{journal['id']}/share"
    assert client.post(path).status_code == 401
    assert client.post(path, headers=OTHER).status_code == 403
    assert client.post(path, headers=OWNER).json() == {'ok': True, 'shared': True}
    wall = client.get('/api/shared/notes', headers=OTHER).json()
    assert wall['total'] == 1
    item = wall['items'][0]
    assert item['source_sermon_id'] == journal['id']
    assert item['publication_kind'] == 'sermon'
    assert 'owner@example.test' not in json.dumps(item)
    assert item['is_own'] is False
    for value in ['2026年10月18日', 'Question 1', 'Study', 'Practice 1', 'Conclusion']:
        assert value in item['observation']
    assert client.get(f"/api/sermon/journals/{journal['id']}", headers=OWNER).json()['journal']['shared'] is True
    assert post(client, {**full_payload('2026年10月18日'), 'summary':'Updated projection'}).status_code == 200
    assert 'Updated projection' in client.get('/api/shared/notes', headers=OTHER).json()['items'][0]['observation']
    # Fresh physical connection observes committed state, not an in-memory return.
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT COUNT(*), bool_and(shared) FROM personal_notes WHERE source_sermon_id=%s', (journal['id'],))
        assert cur.fetchone() == (1, True)
    assert client.post(path, headers=OWNER).json()['shared'] is False
    assert client.get('/api/shared/notes', headers=OTHER).json()['total'] == 0
    assert client.post(path, headers=OWNER).json()['shared'] is True
    assert client.delete(f"/api/sermon/journals/{journal['id']}", headers=OWNER).status_code == 200
    assert client.get('/api/shared/notes', headers=OTHER).json()['total'] == 0
    assert client.post(path, headers=OWNER).status_code == 404
    stored(database)


def test_wall_metadata_and_page_bounds(client):
    assert client.post('/api/personal/notes',headers=OWNER,json={'id':'plain','date':'2026-10-18','observation':'Personal','shared':True}).status_code == 200
    wall=client.get('/api/shared/notes?page=1&limit=1',headers=OTHER)
    assert wall.status_code == 200
    note=wall.json()['items'][0]
    assert note['id']=='plain' and note['source_sermon_id'] is None
    assert note['publication_kind']=='personal'
    for query in ['page=0','limit=0','limit=51']:
        assert client.get('/api/shared/notes?'+query,headers=OWNER).status_code == 422


def test_personal_note_guards_pages_and_complete_roundtrip(client, database):
    payload=dict(id='note-1',date='2026-10-18',scripture='Acts 1',observation='Observed',reflection='Reflected',application='Applied',prayer='Prayed',mood='peace',shared=True,author='Author',avatar='https://example.test/a.png',create_only=True)
    created=client.post('/api/personal/notes',headers=OWNER,json=payload)
    assert created.status_code == 200
    note=created.json()['note']
    assert note['sharedAt'] is not None
    assert client.post('/api/personal/notes',headers=OWNER,json=payload).status_code == 409
    assert client.post('/api/personal/notes',headers=OTHER,json={**payload,'create_only':False}).status_code == 403
    for key in ['scripture','observation','reflection','application','prayer','mood','shared','author','avatar']:
        assert note[key]==payload[key]
    edited=client.post('/api/personal/notes',headers=OWNER,json={**payload,'create_only':False,'expected_write_version':note['write_version'],'observation':'Edited'})
    assert edited.status_code == 200
    assert client.post('/api/personal/notes',headers=OWNER,json={**payload,'create_only':False,'expected_write_version':note['write_version']}).status_code == 409
    current=edited.json()['note']
    assert client.post('/api/personal/notes/note-1/share',headers=OWNER).json()['shared'] is False
    assert client.post('/api/personal/notes',headers=OWNER,json={**payload,'create_only':False,'expected_write_version':current['write_version']}).status_code == 409
    for _ in range(2):
        assert client.post('/api/personal/notes',headers=OWNER,json={'date':'2026-10-18','observation':'Same date, distinct note','create_only':True}).status_code == 200
    page=client.get('/api/personal/notes?limit=1&offset=1',headers=OWNER).json()
    assert page['total']==3 and len(page['items'])==1
    assert page['write_guards']=={'create_only':True,'version':True}
    assert client.get('/api/personal/notes',headers=OTHER).json()['total']==0
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT COUNT(DISTINCT id) FROM personal_notes')
        assert cur.fetchone()[0]==3


def test_personal_concurrent_create_only_has_one_winner(client):
    def create(_):return client.post('/api/personal/notes',headers=OWNER,json={'id':'shared-id','date':'2026-10-18','observation':'Concurrent','create_only':True})
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(response.status_code for response in pool.map(create,range(2)))==[200,409]


def test_devotion_guarded_roundtrip_and_legacy_compatibility(client, database):
    payload=dict(date='2026-10-18',title='Title',scripture='John 1',observation='Observe',reflection='Reflect',application='Apply',prayer='Pray',mood='peace')
    path='/api/devotion/journals'
    created=client.post(path,headers=OWNER,json={**payload,'create_only':True})
    assert created.status_code==200
    original=created.json()['journal']
    assert client.post(path,headers=OWNER,json={**payload,'create_only':True}).status_code==409
    edit={**payload,'expected_id':original['id'],'expected_write_version':original['write_version'],'observation':'Edited'}
    assert client.post(path,headers=OWNER,json=edit).status_code==200
    assert client.post(path,headers=OWNER,json=edit).status_code==409
    assert client.post(path,headers=OWNER,json={**edit,'date':'2026-10-19'}).status_code==409
    legacy=client.post(path,headers=OWNER,json={**payload,'observation':'Legacy Web'})
    assert legacy.status_code==200 and legacy.json()['journal']['id']==original['id']
    page=client.get(path+'?limit=1&offset=0',headers=OWNER).json()
    assert page['total']==1 and page['items'][0]['observation']=='Legacy Web'
    assert page['write_guards']=={'create_only':True,'identity':True,'version':True}
    assert client.get(path,headers=OTHER).json()['total']==0
    assert client.post(path,json=payload).status_code==401


def test_devotion_concurrent_create_is_atomic(client):
    def create(_):return client.post('/api/devotion/journals',headers=OWNER,json={'date':'2026-10-18','title':'Concurrent','create_only':True})
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(response.status_code for response in pool.map(create,range(2)))==[200,409]


def test_explicit_withdraw_retries_cannot_republish_private_content(client):
    assert client.post('/api/personal/notes',headers=OWNER,json={'id':'private-note','date':'2026-10-18','observation':'Private'}).status_code==200
    note_path='/api/personal/notes/private-note/share'
    for desired in [True,True,False,False]:
        result=client.post(note_path,headers=OWNER,json={'shared':desired})
        assert result.status_code==200 and result.json()['shared'] is desired
    sermon_journal=post(client,full_payload()).json()['journal']
    sermon_path=f"/api/sermon/journals/{sermon_journal['id']}/share"
    for desired in [True,True,False,False]:
        assert client.post(sermon_path,headers=OWNER,json={'shared':desired}).json()['shared'] is desired
    assert client.get('/api/shared/notes',headers=OWNER).json()['total']==0
    assert client.get('/api/shared/notes',headers=OWNER).json()['share_state_supported'] is True


def test_concurrent_share_toggles_are_serialized(client, database):
    journal = post(client, full_payload()).json()['journal']
    path = f"/api/sermon/journals/{journal['id']}/share"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: client.post(path, headers=OWNER), range(2)))
    assert all(result.status_code == 200 for result in results)
    assert sorted(result.json()['shared'] for result in results) == [False, True]
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT shared FROM personal_notes WHERE source_sermon_id=%s', (journal['id'],))
        assert cur.fetchall() == [(False,)]


def test_personal_note_endpoints_cannot_mutate_canonical_publication(client, database):
    journal = post(client, full_payload()).json()['journal']
    assert client.post(f"/api/sermon/journals/{journal['id']}/share", headers=OWNER).status_code == 200
    wall = client.get('/api/shared/notes', headers=OWNER).json()
    note = wall['items'][0]
    note_id = note['id']
    assert client.get('/api/personal/notes', headers=OWNER).json()['items'] == []
    assert client.post('/api/personal/notes', headers=OWNER, json={'id':note_id,'date':'2026-10-18','observation':'tamper'}).status_code == 409
    assert client.delete(f'/api/personal/notes/{note_id}', headers=OWNER).status_code == 409
    assert client.post(f'/api/personal/notes/{note_id}/share', headers=OWNER).status_code == 409
    assert client.get('/api/shared/notes', headers=OTHER).json()['items'][0]['observation'] == note['observation']
    # Ordinary notes retain their existing lifecycle and are separate rows.
    own = client.post('/api/personal/notes', headers=OWNER, json={'id':'ordinary','date':'2026-10-18','observation':'Own note'})
    assert own.status_code == 200
    assert client.post('/api/personal/notes/ordinary/share', headers=OWNER).json()['shared'] is True
    assert client.delete('/api/personal/notes/ordinary', headers=OWNER).status_code == 200


def test_admin_delete_recycle_and_purge_preserve_source_ownership(client, database):
    journal = post(client, full_payload()).json()['journal']
    path = f"/api/sermon/journals/{journal['id']}/share"
    assert client.post(path, headers=OWNER).status_code == 200
    note_id = client.get('/api/shared/notes', headers=OWNER).json()['items'][0]['id']
    admin_path = f"/api/admin/sermon-journals/{journal['id']}/delete"
    assert client.post(admin_path, headers=OTHER).status_code == 403
    assert client.post(admin_path, headers=OWNER).status_code == 200
    assert client.get('/api/shared/notes', headers=OTHER).json()['total'] == 0
    recycle = client.get('/api/recycle-bin', headers=OWNER)
    assert recycle.status_code == 200, recycle.text
    assert [item['type'] for item in recycle.json()['items']] == ['sermon']
    assert client.post(f'/api/recycle-bin/personal/{note_id}/restore', headers=OWNER).status_code == 409
    assert client.post(f"/api/recycle-bin/sermon/{journal['id']}/restore", headers=OWNER).status_code == 200
    assert client.get('/api/shared/notes', headers=OTHER).json()['total'] == 0  # explicit republication only
    assert client.post(path, headers=OWNER).json()['shared'] is True
    assert client.post(admin_path, headers=OWNER).status_code == 200
    with database() as conn, conn.cursor() as cur:
        cur.execute("UPDATE sermon_journals SET deleted_at=NOW()-INTERVAL '31 days' WHERE id=%s", (journal['id'],))
        cur.execute('SELECT COUNT(*) FROM admin_audit_log')
        assert cur.fetchone()[0] == 2
    assert client.get('/api/recycle-bin', headers=OWNER).status_code == 200
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM sermon_journals')
        assert cur.fetchone()[0] == 0
        cur.execute('SELECT COUNT(*) FROM personal_notes')
        assert cur.fetchone()[0] == 0


def test_production_versioned_migration_is_durable_idempotent_and_non_destructive(client, database, tmp_path):
    source = Path(sermon.__file__).parents[1] / 'migrations' / '0244_sermon_shared_publications.sql'
    sql = source.read_text()
    # Emulate the existing base schema before this version is installed.
    with database() as conn, conn.cursor() as cur:
        cur.execute('ALTER TABLE personal_notes DROP COLUMN source_sermon_id')
        cur.execute("INSERT INTO personal_notes(id,email,note_date,observation) VALUES ('legacy','owner@example.test',CURRENT_DATE,'Preserve me')")
        dsn = conn.dsn
    (tmp_path / source.name).write_text(sql)
    applied = migrations.run_migrations(dsn, tmp_path, strict=True)
    assert [record.version for record in applied] == ['0244']
    assert migrations.run_migrations(dsn, tmp_path, strict=True) == []
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT observation, source_sermon_id FROM personal_notes WHERE id=\'legacy\'')
        assert cur.fetchone() == ('Preserve me', None)
        cur.execute("SELECT checksum FROM schema_migrations WHERE version='0244'")
        assert cur.fetchone()[0] == hashlib.sha256(source.read_bytes()).hexdigest()
        # Bootstrap repeating the same DDL must also be harmless.
        cur.execute(sql)
    journal = post(client, full_payload()).json()['journal']
    assert client.post(f"/api/sermon/journals/{journal['id']}/share", headers=OWNER).json()['shared'] is True
    assert client.get('/api/shared/notes', headers=OTHER).json()['total'] == 1


def full_payload(date='2026-10-18'):
    return dict(date=date, title='Sermon', preacher='Preacher', scripture='Acts 1',
                summary='Summary', questions=['Question 1'], bible_study='Study',
                practices=['Practice 1'], reflection='Reflection', lesson='Lesson',
                encouragement='Encouragement', conclusion='Conclusion', phase='active')


def post(client, payload):
    return client.post('/api/sermon/journals', headers=OWNER, json=payload)


def stored(database):
    with database() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT row_to_json(s) FROM sermon_journals s ORDER BY id')
            data = [row[0] for row in cur.fetchall()]
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    print('REAL_SQL_POSTIMAGE_SHA256', digest)
    return data


def test_create_only_conflict_does_not_erase_web_fields(client, database):
    assert post(client, full_payload()).status_code == 200
    before = stored(database)
    assert post(client, {'date': '2026-10-18', 'title': 'Blank native draft', 'create_only': True}).status_code == 409
    assert stored(database) == before


def test_native_can_verify_write_capabilities_before_mutating(client):
    result = client.get('/api/sermon/journals', headers=OWNER)
    assert result.status_code == 200
    assert result.json()['write_guards'] == {'create_only': True, 'identity': True, 'updated_at': True}


def test_same_minute_edits_keep_distinct_write_tokens(client, database):
    original = post(client, full_payload()).json()['journal']
    with database() as conn, conn.cursor() as cur:
        cur.execute("UPDATE sermon_journals SET updated_at='2026-10-18 01:01:01.123456' WHERE id=%s", (original['id'],))
    first = client.get(f"/api/sermon/journals/{original['id']}", headers=OWNER).json()['journal']
    assert first['updated_at'].endswith('01:01:01.123456')
    with database() as conn, conn.cursor() as cur:
        cur.execute("UPDATE sermon_journals SET summary='newer', updated_at='2026-10-18 01:01:02.123456' WHERE id=%s", (original['id'],))
    second = client.get(f"/api/sermon/journals/{original['id']}", headers=OWNER).json()['journal']
    assert first['updated_at'] != second['updated_at']
    assert post(client, {**full_payload(), 'expected_id':original['id'], 'expected_updated_at':first['updated_at']}).status_code == 409
    assert stored(database)[0]['summary'] == 'newer'
    with database() as conn, conn.cursor() as cur:
        cur.execute('UPDATE sermon_journals SET updated_at=NULL WHERE id=%s', (original['id'],))
    assert post(client, {**full_payload(), 'expected_updated_at':first['updated_at']}).status_code == 409


def test_complete_guarded_edit_and_stale_version(client, database):
    original = post(client, full_payload()).json()['journal']
    payload = {**full_payload(), 'expected_id': original['id'],
               'expected_updated_at': original['updated_at'], 'summary': 'Edited summary'}
    saved = post(client, payload)
    assert saved.status_code == 200
    for key in ['questions', 'bible_study', 'reflection', 'lesson', 'encouragement', 'conclusion', 'practices']:
        assert saved.json()['journal'][key] == original[key]
    before = stored(database)
    assert post(client, payload).status_code == 409
    assert stored(database) == before


def test_identity_and_date_changes_cannot_create_implicit_copy(client, database):
    original = post(client, full_payload()).json()['journal']
    before = stored(database)
    assert post(client, {**full_payload(), 'expected_id': original['id'] + 1}).status_code == 409
    assert post(client, {**full_payload('2026-10-25'), 'expected_id': original['id']}).status_code == 409
    assert stored(database) == before


def test_legacy_web_upsert_remains_compatible(client, database):
    first = post(client, full_payload()).json()['journal']
    changed = {**full_payload(), 'title': 'Web edit'}
    second = post(client, changed).json()['journal']
    assert first['id'] == second['id']
    assert second['title'] == 'Web edit'
    assert len(stored(database)) == 1


def test_concurrent_create_only_has_one_commit(client, database):
    with ThreadPoolExecutor(2) as pool:
        statuses = list(pool.map(lambda _: post(client, {**full_payload(), 'create_only': True}).status_code, range(2)))
    assert sorted(statuses) == [200, 409]
    assert len(stored(database)) == 1


def test_deleted_and_unauthenticated_journal_writes_are_denied(client, database):
    assert client.post('/api/sermon/journals', json=full_payload()).status_code == 401
    item = post(client, full_payload()).json()['journal']
    assert client.delete('/api/sermon/journals/' + str(item['id']), headers=OWNER).status_code == 200
    before = stored(database)
    assert post(client, full_payload()).status_code == 409
    assert stored(database) == before
