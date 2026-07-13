#!/usr/bin/env python3
"""
圣经电影视频生成工作台
用法:
  pip install fastapi uvicorn anthropic google-genai httpx python-multipart
  export ANTHROPIC_API_KEY="sk-ant-..."
  export GEMINI_API_KEY="AIza..."
  python video_studio_server.py
  然后浏览器访问 http://localhost:8765
"""

import os
import re
import sys
import json
import time
import uuid
import asyncio
import subprocess
import threading
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── 存储目录 ──────────────────────────────────────────────────────────────────
WORK_DIR = Path("./video_studio_output")
CLIPS_DIR = WORK_DIR / "clips"
WORK_DIR.mkdir(parents=True, exist_ok=True)
CLIPS_DIR.mkdir(parents=True, exist_ok=True)

# ── 内存 Job 状态存储 ──────────────────────────────────────────────────────────
JOBS: dict[str, dict] = {}   # job_id → {scene_id, status, progress, video_file, error}

# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(title="圣经视频生成工作台")
# 安全 CORS：默认放开（保持现有行为不变）；生产可设 ALLOWED_ORIGINS（逗号分隔）收敛来源
_cors_env = os.environ.get("ALLOWED_ORIGINS", "*")
_cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()] or ["*"]
if "*" in _cors_origins:
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                       allow_methods=["*"], allow_headers=["*"])
else:
    app.add_middleware(CORSMiddleware, allow_origins=_cors_origins, allow_credentials=True,
                       allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                       allow_headers=["Authorization", "Content-Type", "X-Requested-With"])
app.mount("/clips", StaticFiles(directory=str(CLIPS_DIR)), name="clips")


# ── 故事解析 ──────────────────────────────────────────────────────────────────
def parse_story(text: str) -> dict:
    """解析故事板文本，提取标题、风格、角色、场景列表。"""
    text = text.strip()
    lines = text.split('\n')
    title = lines[0].strip() if lines else "未命名故事"

    style_m = re.search(r'Style:\s*(.*?)(?=\nMain Characters?:|\nStoryboard:)', text, re.DOTALL | re.IGNORECASE)
    chars_m = re.search(r'Main Characters?:\s*(.*?)(?=\nStoryboard:)', text, re.DOTALL | re.IGNORECASE)

    style = style_m.group(1).strip() if style_m else ""
    characters = chars_m.group(1).strip() if chars_m else ""

    # 提取场景：支持  "* Scene N:"  "- Scene N:"  "Scene N:"  "N." 和 "Final scene:"
    scenes = []
    # 普通场景
    for m in re.finditer(
        r'[*\-•]?\s*Scene\s+(\d+)[:.]\s*(.+?)(?=\n[*\-•]?\s*(?:Scene\s+\d+|Final\s+scene):|$)',
        text, re.DOTALL | re.IGNORECASE
    ):
        num = int(m.group(1))
        desc = m.group(2).strip().replace('\n', ' ')
        scenes.append({"id": num, "title": f"Scene {num}", "description": desc})

    # Final scene
    final_m = re.search(
        r'[*\-•]?\s*Final\s+scene[:.]\s*(.+?)(?=\nNo subtitles|$)',
        text, re.DOTALL | re.IGNORECASE
    )
    if final_m:
        num = len(scenes) + 1 if not any(s["id"] == len(scenes) + 1 for s in scenes) else max(s["id"] for s in scenes) + 1
        desc = final_m.group(1).strip().replace('\n', ' ')
        scenes.append({"id": num, "title": f"Final Scene", "description": desc})

    # 按 id 排序去重
    seen = set()
    deduped = []
    for s in sorted(scenes, key=lambda x: x["id"]):
        if s["id"] not in seen:
            seen.add(s["id"])
            deduped.append(s)

    # 每个场景构建完整 Veo Prompt
    suffix = "16:9 aspect ratio, 4K cinematic quality, realistic lighting, no text, no subtitles, no watermarks."
    for s in deduped:
        char_brief = characters[:400].replace('\n', ' ') if characters else ""
        style_brief = style[:300].replace('\n', ' ') if style else ""
        s["prompt"] = (
            f"{s['description']} "
            f"Style: {style_brief}. "
            f"Characters: {char_brief}. "
            f"{suffix}"
        )

    return {
        "title": title,
        "style": style,
        "characters": characters,
        "scenes": deduped,
    }


# ── Veo 3.1 生成器（后台线程） ─────────────────────────────────────────────────
def _run_veo_job(job_id: str, prompt: str, output_path: Path, api_key: str):
    """在后台线程中调用 Veo 3.1 生成视频。"""
    job = JOBS[job_id]
    job["status"] = "generating"
    job["progress"] = 5

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        job["progress"] = 10

        operation = client.models.generate_videos(
            model="veo-3.1-generate-preview",
            prompt=prompt,
            config=types.GenerateVideosConfig(
                aspect_ratio="16:9",
                video_format="mp4",
            ),
        )
        job["progress"] = 20

        waited = 0
        max_wait = 600
        poll_interval = 15
        while not operation.done:
            time.sleep(poll_interval)
            waited += poll_interval
            operation = client.operations.get(operation)
            # 进度 20→85 在等待期间线性增长
            job["progress"] = min(85, 20 + int(65 * waited / max_wait))
            if waited >= max_wait:
                raise TimeoutError(f"Veo 生成超时 ({max_wait}s)")

        if not operation.result or not operation.result.generated_videos:
            raise RuntimeError("Veo 返回结果为空")

        video_uri = operation.result.generated_videos[0].video.uri
        job["progress"] = 88

        # 下载视频
        url = video_uri
        if "googleapis.com" in url and "key=" not in url:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}key={api_key}"

        with httpx.Client(timeout=120, follow_redirects=True) as hclient:
            with hclient.stream("GET", url) as resp:
                resp.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in resp.iter_bytes(65536):
                        f.write(chunk)

        job["status"]     = "done"
        job["progress"]   = 100
        job["video_file"] = output_path.name

    except Exception as e:
        job["status"] = "error"
        job["error"]  = str(e)
        print(f"[JOB {job_id}] 错误: {e}")


# ── API 路由 ──────────────────────────────────────────────────────────────────
class ParseRequest(BaseModel):
    text: str

class GenerateRequest(BaseModel):
    scene_id: int
    prompt: str
    api_key: str

class MergeRequest(BaseModel):
    filenames: list[str]

@app.post("/api/parse")
def api_parse(req: ParseRequest):
    result = parse_story(req.text)
    return result

@app.post("/api/generate")
def api_generate(req: GenerateRequest, background_tasks: BackgroundTasks):
    if not req.api_key:
        raise HTTPException(400, "需要提供 GEMINI_API_KEY")
    job_id = str(uuid.uuid4())
    filename = f"scene_{req.scene_id:02d}_{job_id[:8]}.mp4"
    output_path = CLIPS_DIR / filename
    JOBS[job_id] = {
        "job_id":    job_id,
        "scene_id":  req.scene_id,
        "status":    "pending",
        "progress":  0,
        "video_file": None,
        "error":     None,
    }
    t = threading.Thread(
        target=_run_veo_job,
        args=(job_id, req.prompt, output_path, req.api_key),
        daemon=True
    )
    t.start()
    return {"job_id": job_id}

@app.get("/api/jobs/{job_id}")
def api_job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job

@app.post("/api/merge")
def api_merge(req: MergeRequest):
    if not req.filenames:
        raise HTTPException(400, "没有文件可合成")
    concat_file = WORK_DIR / "concat_list.txt"
    with open(concat_file, "w") as f:
        for name in req.filenames:
            p = CLIPS_DIR / name
            if p.exists():
                f.write(f"file '{p.resolve()}'\n")
    out = WORK_DIR / "final_output.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(500, f"FFmpeg 错误: {result.stderr[-1000:]}")
    return {"filename": "final_output.mp4", "size_mb": round(out.stat().st_size / 1024 / 1024, 1)}

@app.get("/clips_list")
def clips_list():
    files = sorted(CLIPS_DIR.glob("*.mp4"))
    return [{"name": f.name, "size_mb": round(f.stat().st_size / 1024 / 1024, 1)} for f in files]

@app.get("/final_video")
def get_final_video():
    p = WORK_DIR / "final_output.mp4"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(str(p), media_type="video/mp4", filename="biblical_film.mp4")

# ── 前端 HTML ─────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>圣经电影生成工作台</title>
<style>
  :root {
    --bg: #0d0d1a; --panel: #13132a; --card: #1a1a35;
    --border: rgba(255,255,255,0.08); --accent: #5856d6;
    --gold: #ffd60a; --green: #30d158; --red: #ff453a;
    --text: rgba(255,255,255,0.9); --muted: rgba(255,255,255,0.45);
    --blue: #0a84ff;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: -apple-system, "PingFang SC", sans-serif; min-height: 100vh; }

  /* Layout */
  .layout { display: grid; grid-template-columns: 420px 1fr; height: 100vh; overflow: hidden; }
  .left-panel { background: var(--panel); border-right: 1px solid var(--border); display: flex; flex-direction: column; overflow: hidden; }
  .right-panel { display: flex; flex-direction: column; overflow: hidden; }

  /* Header */
  .header { padding: 16px 20px; border-bottom: 1px solid var(--border); background: rgba(88,86,214,0.1); }
  .header h1 { font-size: 16px; font-weight: 700; color: var(--gold); }
  .header p { font-size: 11px; color: var(--muted); margin-top: 3px; }

  /* Left — prompt input */
  .prompt-section { flex: 1; padding: 16px; display: flex; flex-direction: column; gap: 10px; overflow: auto; }
  textarea#story-input {
    flex: 1; min-height: 300px; background: rgba(255,255,255,0.04);
    border: 1px solid var(--border); border-radius: 10px; color: var(--text);
    font-family: inherit; font-size: 12px; line-height: 1.7; padding: 12px;
    resize: none; outline: none;
  }
  textarea#story-input:focus { border-color: rgba(88,86,214,0.5); }

  .api-row { display: flex; gap: 8px; align-items: center; }
  input#api-key {
    flex: 1; padding: 9px 12px; border-radius: 8px;
    border: 1px solid var(--border); background: rgba(255,255,255,0.04);
    color: var(--text); font-size: 13px; outline: none;
  }
  input#api-key::placeholder { color: var(--muted); font-size: 12px; }

  .btn { padding: 9px 18px; border-radius: 8px; border: none; cursor: pointer; font-size: 13px; font-weight: 600; transition: opacity .15s; }
  .btn:hover { opacity: .85; }
  .btn-primary { background: var(--accent); color: #fff; }
  .btn-gold { background: linear-gradient(135deg, #f7b731, var(--gold)); color: #000; }
  .btn-green { background: var(--green); color: #000; }
  .btn-sm { padding: 6px 12px; font-size: 12px; }
  .btn:disabled { opacity: .4; cursor: default; }

  /* Story info */
  .story-info { padding: 12px; background: rgba(88,86,214,0.08); border-radius: 10px; border: 1px solid rgba(88,86,214,0.2); font-size: 12px; color: var(--muted); }
  .story-info strong { color: var(--text); }

  /* Right — scenes grid */
  .scenes-header { padding: 14px 18px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 10px; }
  .scenes-header h2 { font-size: 14px; font-weight: 600; flex: 1; }
  .scenes-grid { flex: 1; overflow-y: auto; padding: 14px 18px; display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; align-content: start; }

  /* Scene card */
  .scene-card {
    background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; transition: border .2s;
  }
  .scene-card.done { border-color: rgba(48,209,88,0.35); }
  .scene-card.generating { border-color: rgba(88,86,214,0.5); }
  .scene-card.error { border-color: rgba(255,69,58,0.4); }

  .card-video { width: 100%; aspect-ratio: 16/9; background: #000; display: none; }
  .card-video.visible { display: block; }
  .card-thumb {
    width: 100%; aspect-ratio: 16/9; background: linear-gradient(135deg,#1a1035,#0d0d20);
    display: flex; align-items: center; justify-content: center; font-size: 28px; opacity: .5;
  }
  .card-thumb.hidden { display: none; }
  .card-body { padding: 10px 12px; }
  .card-num { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }
  .card-title { font-size: 13px; font-weight: 600; margin: 3px 0; }
  .card-desc { font-size: 11px; color: var(--muted); line-height: 1.6; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

  /* Progress bar */
  .progress-wrap { margin: 8px 0; height: 4px; background: rgba(255,255,255,0.08); border-radius: 2px; display: none; }
  .progress-wrap.visible { display: block; }
  .progress-bar { height: 100%; border-radius: 2px; background: var(--accent); transition: width .5s; }

  .card-status { font-size: 11px; margin: 4px 0; }
  .status-pending { color: var(--muted); }
  .status-generating { color: #5ac8fa; }
  .status-done { color: var(--green); }
  .status-error { color: var(--red); }

  .card-actions { margin-top: 8px; display: flex; gap: 6px; }

  /* Bottom bar */
  .bottom-bar { padding: 12px 18px; border-top: 1px solid var(--border); display: flex; align-items: center; gap: 10px; background: var(--panel); }
  .done-count { font-size: 12px; color: var(--muted); flex: 1; }

  /* Empty state */
  .empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; gap: 12px; opacity: .4; }
  .empty-state .icon { font-size: 48px; }
  .empty-state p { font-size: 14px; }

  /* Toast */
  .toast { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); background: var(--card); border: 1px solid var(--border); padding: 10px 20px; border-radius: 8px; font-size: 13px; z-index: 9999; opacity: 0; transition: opacity .3s; pointer-events: none; }
  .toast.show { opacity: 1; }
</style>
</head>
<body>
<div class="layout">
  <!-- Left: prompt input -->
  <div class="left-panel">
    <div class="header">
      <h1>🎬 圣经电影生成工作台</h1>
      <p>Veo 3.1 · 逐镜头生成 · FFmpeg合成</p>
    </div>
    <div class="prompt-section">
      <div style="font-size:12px;color:var(--muted);margin-bottom:4px;">粘贴故事板 →</div>
      <textarea id="story-input" placeholder="粘贴完整故事板文本...

示例格式：
《约瑟》(Joseph)
Style: Ancient Canaan...
Main Characters: Joseph...
Storyboard:
* Scene 1: Jacob presents...
* Scene 2: Joseph shares...
...
* Final scene: ..."></textarea>
      <button class="btn btn-primary" onclick="parseStory()">✦ 解析故事板</button>

      <div class="api-row">
        <input id="api-key" type="password" placeholder="Gemini API Key (AIza...)" />
      </div>

      <div id="story-info" style="display:none" class="story-info"></div>
    </div>
  </div>

  <!-- Right: scenes -->
  <div class="right-panel">
    <div class="scenes-header">
      <h2 id="scenes-title">镜头列表</h2>
      <button class="btn btn-gold btn-sm" id="gen-all-btn" onclick="generateAll()" style="display:none">⚡ 全部生成</button>
    </div>

    <div id="scenes-grid" class="scenes-grid">
      <div class="empty-state">
        <div class="icon">🎞️</div>
        <p>解析故事板后，镜头将显示在这里</p>
      </div>
    </div>

    <div class="bottom-bar">
      <span class="done-count" id="done-count"></span>
      <button class="btn btn-green" id="merge-btn" onclick="mergeAll()" style="display:none">🎬 合成最终视频</button>
    </div>
  </div>
</div>
<div class="toast" id="toast"></div>

<script>
let scenes = [];
let jobs = {};       // scene_id → job_id
let completedFiles = {}; // scene_id → filename
let genAllQueue = [];
let genAllRunning = false;

// ── 解析 ─────────────────────────────────────────────────────────────────────
async function parseStory() {
  const text = document.getElementById('story-input').value.trim();
  if (!text) return toast('请先粘贴故事板文本');
  try {
    const r = await fetch('/api/parse', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({text})
    });
    const data = await r.json();
    scenes = data.scenes || [];
    showStoryInfo(data);
    renderScenes();
    toast(`✦ 解析完成 — ${scenes.length} 个镜头`);
  } catch(e) { toast('解析失败: ' + e.message); }
}

function showStoryInfo(data) {
  const el = document.getElementById('story-info');
  el.style.display = 'block';
  el.innerHTML = `<strong>${data.title}</strong><br>
    <span style="color:var(--muted)">${data.scenes.length} 个镜头 · 约 ${Math.round(data.scenes.length * 7 / 60)} 分钟视频</span>`;
}

// ── 渲染场景卡片 ──────────────────────────────────────────────────────────────
function renderScenes() {
  const grid = document.getElementById('scenes-grid');
  if (!scenes.length) { grid.innerHTML = ''; return; }

  document.getElementById('scenes-title').textContent = `镜头列表 (${scenes.length})`;
  document.getElementById('gen-all-btn').style.display = '';

  grid.innerHTML = scenes.map(s => `
    <div class="scene-card" id="card-${s.id}">
      <div class="card-thumb" id="thumb-${s.id}">🎬</div>
      <video class="card-video" id="video-${s.id}" controls playsinline></video>
      <div class="card-body">
        <div class="card-num">Scene ${s.id}</div>
        <div class="card-title">${s.title}</div>
        <div class="card-desc">${s.description}</div>
        <div class="progress-wrap" id="progress-wrap-${s.id}">
          <div class="progress-bar" id="progress-bar-${s.id}" style="width:0%"></div>
        </div>
        <div class="card-status status-pending" id="status-${s.id}">待生成</div>
        <div class="card-actions">
          <button class="btn btn-primary btn-sm" id="btn-${s.id}" onclick="generateScene(${s.id})">生成</button>
        </div>
      </div>
    </div>
  `).join('');

  updateDoneCount();
}

// ── 生成单个镜头 ──────────────────────────────────────────────────────────────
async function generateScene(sceneId) {
  const apiKey = document.getElementById('api-key').value.trim();
  if (!apiKey) return toast('请先输入 Gemini API Key');
  const scene = scenes.find(s => s.id === sceneId);
  if (!scene) return;

  setCardState(sceneId, 'generating', '请求中…', 5);
  document.getElementById(`btn-${sceneId}`).disabled = true;

  try {
    const r = await fetch('/api/generate', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ scene_id: sceneId, prompt: scene.prompt, api_key: apiKey })
    });
    const { job_id } = await r.json();
    jobs[sceneId] = job_id;
    pollJob(sceneId, job_id);
  } catch(e) {
    setCardState(sceneId, 'error', '请求失败: ' + e.message, 0);
    document.getElementById(`btn-${sceneId}`).disabled = false;
  }
}

// ── 轮询 Job 状态 ─────────────────────────────────────────────────────────────
function pollJob(sceneId, jobId) {
  const interval = setInterval(async () => {
    try {
      const r = await fetch(`/api/jobs/${jobId}`);
      const job = await r.json();

      setCardState(sceneId, job.status, statusText(job), job.progress || 0);

      if (job.status === 'done') {
        clearInterval(interval);
        completedFiles[sceneId] = job.video_file;
        showVideo(sceneId, `/clips/${job.video_file}`);
        document.getElementById(`btn-${sceneId}`).disabled = false;
        updateDoneCount();
        toast(`✅ Scene ${sceneId} 生成完成`);
        if (genAllRunning) nextInQueue();
      } else if (job.status === 'error') {
        clearInterval(interval);
        document.getElementById(`btn-${sceneId}`).disabled = false;
        if (genAllRunning) nextInQueue();
      }
    } catch(e) { /* ignore poll errors */ }
  }, 3000);
}

function statusText(job) {
  if (job.status === 'pending') return '排队中…';
  if (job.status === 'generating') return `生成中… ${job.progress || 0}%`;
  if (job.status === 'done') return '✅ 完成';
  if (job.status === 'error') return '❌ ' + (job.error || '错误');
  return job.status;
}

function setCardState(sceneId, status, text, progress) {
  const card = document.getElementById(`card-${sceneId}`);
  const statusEl = document.getElementById(`status-${sceneId}`);
  const progressWrap = document.getElementById(`progress-wrap-${sceneId}`);
  const progressBar = document.getElementById(`progress-bar-${sceneId}`);
  if (!card) return;

  card.className = 'scene-card ' + (['done','generating','error'].includes(status) ? status : '');
  statusEl.className = 'card-status status-' + (status === 'pending' ? 'pending' : status);
  statusEl.textContent = text;
  progressWrap.className = 'progress-wrap' + (status === 'generating' ? ' visible' : '');
  progressBar.style.width = progress + '%';
}

function showVideo(sceneId, src) {
  document.getElementById(`thumb-${sceneId}`).className = 'card-thumb hidden';
  const v = document.getElementById(`video-${sceneId}`);
  v.src = src;
  v.className = 'card-video visible';
}

// ── 全部生成 ──────────────────────────────────────────────────────────────────
async function generateAll() {
  const apiKey = document.getElementById('api-key').value.trim();
  if (!apiKey) return toast('请先输入 Gemini API Key');
  // 只队列未完成的
  genAllQueue = scenes.filter(s => !completedFiles[s.id]).map(s => s.id);
  if (!genAllQueue.length) return toast('所有镜头均已生成');
  genAllRunning = true;
  toast(`开始批量生成 ${genAllQueue.length} 个镜头（依次进行）`);
  nextInQueue();
}

function nextInQueue() {
  if (!genAllQueue.length) { genAllRunning = false; toast('🎉 全部生成完毕！'); return; }
  const id = genAllQueue.shift();
  generateScene(id);
}

// ── 合成最终视频 ──────────────────────────────────────────────────────────────
async function mergeAll() {
  const files = scenes
    .filter(s => completedFiles[s.id])
    .sort((a, b) => a.id - b.id)
    .map(s => completedFiles[s.id]);

  if (files.length < 2) return toast('至少需要 2 个完成的片段才能合成');
  toast(`合成 ${files.length} 个片段，请稍候…`);
  document.getElementById('merge-btn').disabled = true;

  try {
    const r = await fetch('/api/merge', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ filenames: files })
    });
    const data = await r.json();
    toast(`🎬 合成完成！大小 ${data.size_mb} MB`);
    // 在底部显示下载链接
    document.getElementById('done-count').innerHTML +=
      ` · <a href="/final_video" style="color:var(--gold);text-decoration:none" download>⬇ 下载最终视频</a>`;
  } catch(e) {
    toast('合成失败: ' + e.message);
  } finally {
    document.getElementById('merge-btn').disabled = false;
  }
}

// ── 工具函数 ──────────────────────────────────────────────────────────────────
function updateDoneCount() {
  const done = Object.keys(completedFiles).length;
  const total = scenes.length;
  const el = document.getElementById('done-count');
  el.textContent = total ? `${done} / ${total} 个镜头已完成` : '';
  const mergeBtn = document.getElementById('merge-btn');
  if (done >= 2) mergeBtn.style.display = '';
  else mergeBtn.style.display = 'none';
}

let toastTimer;
function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 3500);
}

// 页面加载时从 localStorage 恢复 API Key
window.onload = () => {
  const saved = localStorage.getItem('gemini_api_key');
  if (saved) document.getElementById('api-key').value = saved;
  document.getElementById('api-key').addEventListener('change', e => {
    localStorage.setItem('gemini_api_key', e.target.value);
  });
};
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return HTML


# ── 启动 ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    for k in ["ANTHROPIC_API_KEY", "GEMINI_API_KEY"]:
        if not os.environ.get(k):
            print(f"[WARN] 环境变量 {k} 未设置，可在页面内输入 API Key")
    print("=" * 50)
    print("🎬 圣经电影生成工作台")
    print("浏览器访问: http://localhost:8765")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="warning")
