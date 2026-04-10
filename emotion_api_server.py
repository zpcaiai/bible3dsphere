#!/usr/bin/env python3
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from query_emotion_verses import (
    DEFAULT_RERANK_CANDIDATES,
    DEFAULT_RERANK_WEIGHT,
    assess_psychological_state,
    query_emotion_verses,
)
from web_emotion_query import HISTORY_FILE, load_history, save_history_entry

HOST = "127.0.0.1"
PORT = 8787
LAYOUT_FILE = Path("emotion_sphere_layout.json")
MATCHES_FILE = Path("emotion_exemplar_verse_matches.json")


def json_response(handler: BaseHTTPRequestHandler, payload: dict | list, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(body)


def load_layout() -> list[dict]:
    if not LAYOUT_FILE.exists():
        return []
    with open(LAYOUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_matches() -> list[dict]:
    if not MATCHES_FILE.exists():
        return []
    with open(MATCHES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_feature_match_map() -> dict[str, dict]:
    match_map = {}
    for item in load_matches():
        key = f"{item.get('layer')}:{item.get('feature_id')}"
        match_map[key] = item
    return match_map


class EmotionApiHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        json_response(self, {"ok": True})

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/layout":
            layout = load_layout()
            json_response(self, {"items": layout, "count": len(layout)})
            return
        if parsed.path == "/api/history":
            json_response(self, {"items": load_history()})
            return
        if parsed.path == "/api/feature":
            query = parse_qs(parsed.query)
            feature_key = query.get("key", [""])[0]
            if not feature_key:
                json_response(self, {"error": "Missing feature key"}, status=400)
                return
            match_map = build_feature_match_map()
            item = match_map.get(feature_key)
            if item is None:
                json_response(self, {"error": "Feature not found"}, status=404)
                return
            json_response(self, item)
            return
        json_response(self, {"error": "Not found"}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/guidance":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
            try:
                body = json.loads(raw_body or "{}")
            except json.JSONDecodeError:
                json_response(self, {"error": "Invalid JSON"}, status=400)
                return
            query_text = str(body.get("query", "")).strip()
            if not query_text:
                json_response(self, {"error": "Missing query"}, status=400)
                return
            try:
                guidance = assess_psychological_state(query_text)
                json_response(self, guidance)
            except Exception as exc:
                json_response(self, {"error": str(exc)}, status=500)
            return
        if parsed.path != "/api/query":
            json_response(self, {"error": "Not found"}, status=404)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
        try:
            body = json.loads(raw_body or "{}")
        except json.JSONDecodeError:
            json_response(self, {"error": "Invalid JSON body"}, status=400)
            return

        query_text = str(body.get("query", "")).strip()
        top_features = int(body.get("topFeatures", 5))
        top_verses = int(body.get("topVerses", 5))
        language_filter = str(body.get("languageFilter", "both"))

        if not query_text:
            json_response(self, {"error": "Missing query"}, status=400)
            return

        include_guidance = bool(body.get("includeGuidance", False))
        enable_rerank = bool(body.get("enableRerank", False))
        rerank_candidates = int(body.get("rerankCandidates", DEFAULT_RERANK_CANDIDATES))
        rerank_weight = float(body.get("rerankWeight", DEFAULT_RERANK_WEIGHT))
        try:
            started_at = time.perf_counter()
            result = query_emotion_verses(
                query_text=query_text,
                top_features=top_features,
                top_verses_per_language=top_verses,
                include_guidance=include_guidance,
                enable_rerank=enable_rerank,
                rerank_candidates=rerank_candidates,
                rerank_weight=rerank_weight,
            )
            result["query_latency_ms"] = round((time.perf_counter() - started_at) * 1000, 2)
            save_history_entry(query_text, top_features, top_verses, language_filter, result)
            json_response(self, result)
        except Exception as exc:
            json_response(self, {"error": str(exc)}, status=500)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), EmotionApiHandler)
    print(json.dumps({"api": f"http://{HOST}:{PORT}"}, ensure_ascii=False))
    server.serve_forever()


if __name__ == "__main__":
    main()
