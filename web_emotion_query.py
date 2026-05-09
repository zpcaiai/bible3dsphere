#!/usr/bin/env python3
import html
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from query_emotion_verses import query_emotion_verses, result_to_markdown

HOST = "127.0.0.1"
PORT = 8765
HISTORY_FILE = Path("emotion_query_history.json")


def load_history() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_history_entry(query_text: str, top_features: int, top_verses: int, language_filter: str, result: dict) -> None:
    history = load_history()
    history.insert(
        0,
        {
            "query_text": query_text,
            "top_features": top_features,
            "top_verses": top_verses,
            "language_filter": language_filter,
            "selected_emotions": result.get("selected_emotions", []),
            "verse_summary": result.get("verse_summary", {}),
        },
    )
    history = history[:50]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def nav_html(active: str) -> str:
    home_class = "nav-link active" if active == "home" else "nav-link"
    history_class = "nav-link active" if active == "history" else "nav-link"
    return (
        "<div class='nav'>"
        f"<a class='{home_class}' href='/'>查询</a>"
        f"<a class='{history_class}' href='/history'>历史记录</a>"
        "</div>"
    )


def language_filter_tabs(selected: str) -> str:
    tabs = []
    for value, label in (("both", "中英双语"), ("cuv", "只看 CUV"), ("esv", "只看 ESV")):
        checked = "checked" if selected == value else ""
        tabs.append(
            "<label class='chip'>"
            f"<input type='radio' name='language_filter' value='{value}' {checked}>"
            f"<span>{label}</span>"
            "</label>"
        )
    return "".join(tabs)


def render_history_page() -> str:
    history = load_history()
    cards = []
    for idx, item in enumerate(history, start=1):
        emotion_labels = ", ".join(
            f"{feat.get('layer')}:{feat.get('feature_id')}" for feat in item.get("selected_emotions", [])[:5]
        )
        cards.append(
            "<div class='history-card'>"
            f"<div class='history-index'>#{idx}</div>"
            f"<div class='history-query'>{html.escape(str(item.get('query_text', '')))}</div>"
            f"<div class='meta'>language={html.escape(str(item.get('language_filter', 'both')))} | top_features={item.get('top_features', 0)} | top_verses={item.get('top_verses', 0)}</div>"
            f"<div class='meta'>matched emotions: {html.escape(emotion_labels)}</div>"
            "</div>"
        )

    content = "".join(cards) if cards else "<div class='empty'>还没有历史记录。</div>"
    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Emotion Verse Query History</title>
  <style>{base_styles()}</style>
</head>
<body>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">Emotion Verse Query</div>
      {nav_html('history')}
      <div class="sidebar-note">查看最近的自然语言查询与命中的 emotion features。</div>
    </aside>
    <main class="main">
      <section class="hero"><h1>查询历史</h1><p>最近 50 条记录会保存在本地 JSON 文件中。</p></section>
      <section class="panel">{content}</section>
    </main>
  </div>
</body>
</html>
"""


def base_styles() -> str:
    return """
body { font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; background: linear-gradient(180deg, #0a1020 0%, #101935 100%); color: #e8ecf3; }
.shell { display: grid; grid-template-columns: 280px 1fr; min-height: 100vh; }
.sidebar { background: rgba(8, 12, 26, 0.88); border-right: 1px solid #243052; padding: 28px 20px; }
.brand { font-size: 22px; font-weight: 700; margin-bottom: 20px; color: #f4f7ff; }
.sidebar-note { margin-top: 20px; font-size: 14px; line-height: 1.6; color: #9aa8cc; }
.nav { display: flex; flex-direction: column; gap: 10px; }
.nav-link { display: block; padding: 12px 14px; border-radius: 12px; color: #d6def5; text-decoration: none; background: #111935; border: 1px solid #2a3760; }
.nav-link.active, .nav-link:hover { background: linear-gradient(135deg, #6f7dff, #8d58ff); border-color: transparent; color: white; }
.main { padding: 28px; }
.hero { margin-bottom: 20px; }
.hero h1 { margin: 0 0 10px; font-size: 34px; }
.hero p { margin: 0; color: #a8b4d8; line-height: 1.7; }
.panel { background: rgba(17, 25, 53, 0.88); border: 1px solid #28355d; border-radius: 20px; padding: 22px; box-shadow: 0 20px 80px rgba(0,0,0,0.25); margin-bottom: 20px; }
textarea, input { width: 100%; box-sizing: border-box; background: #0f1530; color: #f3f6fc; border: 1px solid #36446f; border-radius: 14px; padding: 12px; }
textarea { min-height: 140px; resize: vertical; }
.row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 14px; }
.actions { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin-top: 16px; }
button { background: linear-gradient(135deg, #6d7cff, #8f59ff); color: white; border: none; border-radius: 14px; padding: 12px 18px; cursor: pointer; font-weight: 700; box-shadow: 0 10px 30px rgba(111,125,255,0.35); }
button:hover { filter: brightness(1.06); }
.ghost-link { color: #c8d4f8; text-decoration: none; padding: 10px 14px; border: 1px solid #36446f; border-radius: 12px; background: #111935; }
.ghost-link:hover { background: #172144; }
.error { background: #4b1f2a; color: #ffd9df; border: 1px solid #7f3143; padding: 12px; border-radius: 12px; margin-bottom: 16px; }
.meta { color: #aeb9d6; font-size: 14px; line-height: 1.6; }
.explanation { margin-top: 8px; color: #dde5f7; line-height: 1.6; }
.stats { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 12px; margin-bottom: 20px; }
.stat-card { background: #101733; border: 1px solid #2a3760; border-radius: 16px; padding: 16px; }
.stat-value { font-size: 24px; font-weight: 700; color: #ffffff; }
.stat-label { color: #9fb0d9; font-size: 13px; margin-top: 6px; }
.feature-list { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.feature-item, .history-card { background: #101733; border: 1px solid #2a3760; border-radius: 16px; padding: 16px; }
.verse-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.verse-card { background: #0f1530; border: 1px solid #2d3960; border-radius: 16px; padding: 16px; margin: 12px 0; }
.verse-ref { margin-bottom: 8px; color: #dce4ff; line-height: 1.6; }
.verse-text { white-space: pre-wrap; line-height: 1.8; color: #f4f6fb; }
pre { white-space: pre-wrap; background: #0b1126; border: 1px solid #253056; border-radius: 12px; padding: 14px; overflow-x: auto; }
.chips { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }
.chip input { display: none; }
.chip span { display: inline-block; padding: 10px 14px; border-radius: 999px; background: #101733; border: 1px solid #33416c; color: #d6def5; cursor: pointer; }
.chip input:checked + span { background: linear-gradient(135deg, #6d7cff, #8f59ff); border-color: transparent; color: white; }
.empty { color: #9aa8cc; padding: 16px 4px; }
.history-index { color: #8fa0cf; font-size: 13px; margin-bottom: 8px; }
.history-query { font-size: 18px; font-weight: 600; margin-bottom: 8px; line-height: 1.6; }
@media (max-width: 980px) { .shell { grid-template-columns: 1fr; } .sidebar { border-right: none; border-bottom: 1px solid #243052; } .verse-grid, .feature-list, .stats, .row { grid-template-columns: 1fr; } }
"""


def render_page(
    query_text: str = "",
    result: dict | None = None,
    error: str = "",
    language_filter: str = "both",
    top_features: int = 5,
    top_verses: int = 5,
) -> str:
    query_html = html.escape(query_text)
    error_html = f'<div class="error">{html.escape(error)}</div>' if error else ""
    result_html = ""

    if result:
        feature_items = []
        for item in result.get("selected_emotions", []):
            feature_items.append(
                "<div class='feature-item'>"
                f"<strong>{html.escape(item.get('layer', ''))}:{html.escape(str(item.get('feature_id', '')))}</strong> "
                f"<span class='meta'>keyword={html.escape(str(item.get('source_keyword', '')))} | similarity={item.get('similarity', 0.0):.4f}</span>"
                f"<div class='explanation'>{html.escape(str(item.get('explanation', '')))}</div>"
                "</div>"
            )

        verse_sections = []
        languages = ("cuv", "esv") if language_filter == "both" else (language_filter,)
        for language in languages:
            verse_cards = []
            for verse in result.get("verse_summary", {}).get(language, []):
                matched = ", ".join(
                    f"{feat.get('layer')}:{feat.get('feature_id')}"
                    for feat in verse.get("matched_features", [])
                )
                verse_cards.append(
                    "<div class='verse-card'>"
                    f"<div class='verse-ref'><strong>{html.escape(str(verse.get('pk_id', '')))}</strong>"
                    f" | {html.escape(str(verse.get('book_name', '')))} {html.escape(str(verse.get('chapter', '')))}:{html.escape(str(verse.get('verse', '')))}"
                    f" | score={verse.get('combined_score', 0.0):.4f}</div>"
                    f"<div class='verse-text'>{html.escape(str(verse.get('raw_text', '')))}</div>"
                    f"<div class='meta'>matched features: {html.escape(matched)}</div>"
                    "</div>"
                )
            verse_sections.append(
                "<section class='panel'>"
                f"<h3>{language.upper()}</h3>"
                + ("".join(verse_cards) if verse_cards else "<p>No verses.</p>") +
                "</section>"
            )

        markdown_preview = html.escape(result_to_markdown(result))
        stats_html = (
            "<div class='stats'>"
            f"<div class='stat-card'><div class='stat-value'>{len(result.get('selected_emotions', []))}</div><div class='stat-label'>Emotion Features</div></div>"
            f"<div class='stat-card'><div class='stat-value'>{len(result.get('verse_summary', {}).get('cuv', []))}</div><div class='stat-label'>CUV Hits</div></div>"
            f"<div class='stat-card'><div class='stat-value'>{len(result.get('verse_summary', {}).get('esv', []))}</div><div class='stat-label'>ESV Hits</div></div>"
            "</div>"
        )
        result_html = (
            "<div class='results'>"
            + stats_html
            + "<section class='panel'><h2>Matched Emotion Features</h2><div class='feature-list'>" + "".join(feature_items) + "</div></section>"
            + f"<div class='verse-grid'>{''.join(verse_sections)}</div>"
            + f"<section class='panel'><h2>Markdown Preview</h2><pre>{markdown_preview}</pre></section>"
            "</div>"
        )

    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Emotion Verse Query</title>
  <style>{base_styles()}</style>
</head>
<body>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">Emotion Verse Query</div>
      {nav_html('home')}
      <div class="sidebar-note">输入自然语言，映射到最相关的 emotion features，并汇总对应的中英双语经文。</div>
    </aside>
    <main class="main">
      <section class="hero">
        <h1>情感检索经文界面</h1>
        <p>支持自然语言情感理解、`CUV / ESV` 切换显示，以及本地查询历史记录。</p>
      </section>
      <section class="panel">
        {error_html}
        <form method="post">
          <label for="query"><strong>自然语言输入</strong></label>
          <textarea id="query" name="query">{query_html}</textarea>
          <div class="row">
            <div>
              <label for="top_features"><strong>Top emotion features</strong></label>
              <input id="top_features" name="top_features" type="number" min="1" max="20" value="{top_features}">
            </div>
            <div>
              <label for="top_verses"><strong>Top verses per language</strong></label>
              <input id="top_verses" name="top_verses" type="number" min="1" max="20" value="{top_verses}">
            </div>
          </div>
          <div class="chips">{language_filter_tabs(language_filter)}</div>
          <div class="actions">
            <button type="submit">开始查询</button>
            <a class="ghost-link" href="/history">查看历史记录</a>
          </div>
        </form>
      </section>
      {result_html}
    </main>
  </div>
</body>
</html>
"""


class EmotionQueryHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/history":
            page = render_history_page()
        else:
            page = render_page()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(page.encode("utf-8"))

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length).decode("utf-8")
        form = parse_qs(body)
        query_text = form.get("query", [""])[0].strip()
        top_features = int(form.get("top_features", ["5"])[0])
        top_verses = int(form.get("top_verses", ["5"])[0])
        language_filter = form.get("language_filter", ["both"])[0]

        if not query_text:
            page = render_page(query_text=query_text, error="请输入自然语言查询。", language_filter=language_filter, top_features=top_features, top_verses=top_verses)
        else:
            try:
                result = query_emotion_verses(
                    query_text=query_text,
                    top_features=top_features,
                    top_verses_per_language=top_verses,
                )
                save_history_entry(query_text, top_features, top_verses, language_filter, result)
                page = render_page(query_text=query_text, result=result, language_filter=language_filter, top_features=top_features, top_verses=top_verses)
            except Exception as exc:
                page = render_page(query_text=query_text, error=str(exc), language_filter=language_filter, top_features=top_features, top_verses=top_verses)

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(page.encode("utf-8"))


def main() -> None:
    server = HTTPServer((HOST, PORT), EmotionQueryHandler)
    print(json.dumps({"url": f"http://{HOST}:{PORT}"}, ensure_ascii=False))
    server.serve_forever()


if __name__ == "__main__":
    main()
