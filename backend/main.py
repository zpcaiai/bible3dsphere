import json
import sys
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from query_emotion_verses import assess_psychological_state, query_emotion_verses
from web_emotion_query import HISTORY_FILE, load_history, save_history_entry

LAYOUT_FILE = ROOT_DIR / 'emotion_sphere_layout.json'
MATCHES_FILE = ROOT_DIR / 'emotion_exemplar_verse_matches.json'
FRONTEND_DIST = ROOT_DIR / 'emotion-sphere-ui' / 'dist'


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    topFeatures: int = Field(default=5, ge=1, le=20)
    topVerses: int = Field(default=5, ge=1, le=20)
    languageFilter: str = Field(default='both')
    includeGuidance: bool = False


class GuidanceRequest(BaseModel):
    query: str = Field(min_length=1)


app = FastAPI(title='Bible Emotion Sphere API')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


def load_json_file(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, 'r', encoding='utf-8') as file:
        return json.load(file)


def build_feature_match_map() -> dict[str, dict]:
    match_map = {}
    for item in load_json_file(MATCHES_FILE):
        key = f"{item.get('layer')}:{item.get('feature_id')}"
        match_map[key] = item
    return match_map


@app.get('/api/health')
def health() -> dict:
    return {'ok': True}


@app.get('/api/layout')
def get_layout() -> dict:
    layout = load_json_file(LAYOUT_FILE)
    return {'items': layout, 'count': len(layout)}


@app.get('/api/history')
def get_history() -> dict:
    return {'items': load_history()}


@app.get('/api/feature')
def get_feature(key: str = Query(min_length=1)) -> dict:
    item = build_feature_match_map().get(key)
    if item is None:
        raise HTTPException(status_code=404, detail='Feature not found')
    return item


@app.post('/api/guidance')
def get_guidance(payload: GuidanceRequest) -> dict:
    try:
        return assess_psychological_state(payload.query.strip())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post('/api/query')
def post_query(payload: QueryRequest) -> dict:
    query_text = payload.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail='Missing query')

    try:
        started_at = time.perf_counter()
        result = query_emotion_verses(
            query_text=query_text,
            top_features=payload.topFeatures,
            top_verses_per_language=payload.topVerses,
            include_guidance=payload.includeGuidance,
        )
        result['query_latency_ms'] = round((time.perf_counter() - started_at) * 1000, 2)
        save_history_entry(query_text, payload.topFeatures, payload.topVerses, payload.languageFilter, result)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if FRONTEND_DIST.exists():
    app.mount('/assets', StaticFiles(directory=FRONTEND_DIST / 'assets'), name='assets')


@app.get('/{full_path:path}')
def serve_frontend(full_path: str, request: Request):
    if full_path.startswith('api/'):
        raise HTTPException(status_code=404, detail='Not found')

    if FRONTEND_DIST.exists():
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / 'index.html')

    raise HTTPException(status_code=404, detail='Frontend build output not found. Run npm run build in emotion-sphere-ui first.')
