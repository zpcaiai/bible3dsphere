#!/usr/bin/env python3
"""
圣经电影全自动生成工作台 — HuggingFace 部署版
Pipeline:
  输入故事板
    → Claude 拆分25镜头+旁白+字幕+属灵应用
    → Veo 3.1 生成25个视频片段
    → Google TTS/edge-tts 合成旁白配音
    → FFmpeg 逐镜头合成（字幕+旁白）
    → FFmpeg 生成20秒属灵应用结尾
    → FFmpeg 拼接完整视频
    → 上传 Cloudflare R2
    → 返回播放 URL

依赖:
  pip install fastapi uvicorn anthropic google-genai httpx
              boto3 pillow python-multipart edge-tts

环境变量（可在 HF Spaces Secrets 中设置）:
  ANTHROPIC_API_KEY, GEMINI_API_KEY,
  R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY,
  R2_BUCKET_NAME, R2_VIDEO_PREFIX (default: "biblical-films/")
  VIDEO_CDN_BASE (e.g. https://cdn.holiness.uk)
"""

import os, re, sys, json, time, uuid, asyncio, threading, subprocess, io, textwrap
from pathlib import Path
from typing import Generator
import httpx
import uvicorn
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_OK = True
except ImportError:
    PIL_OK = False

# ── 存储目录 ──────────────────────────────────────────────────────────────────
WORK_DIR  = Path("./film_output")
CLIPS_DIR = WORK_DIR / "clips"
AUDIO_DIR = WORK_DIR / "audio"
COMP_DIR  = WORK_DIR / "composed"   # clips with subtitle+audio baked in
for d in [CLIPS_DIR, AUDIO_DIR, COMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── 全局 Job 状态 ─────────────────────────────────────────────────────────────
JOBS: dict[str, dict] = {}  # job_id → { status, progress, steps, result, error }

# ── FastAPI ───────────────────────────────────────────────────────────────────
app = FastAPI(title="圣经电影工作台")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/clips",    StaticFiles(directory=str(CLIPS_DIR)),  name="clips")
app.mount("/composed", StaticFiles(directory=str(COMP_DIR)),   name="composed")
app.mount("/film_output", StaticFiles(directory=str(WORK_DIR)), name="output")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Claude 拆分场景
# ══════════════════════════════════════════════════════════════════════════════
def split_with_claude(story_text: str, api_key: str, num_scenes: int = 25) -> dict:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    system = textwrap.dedent(f"""
        You are a professional biblical film director and scriptwriter.
        Given a storyboard, produce exactly {num_scenes} scene entries + 1 spiritual_application.
        Return ONLY valid JSON (no markdown, no explanation) in this schema:
        {{
          "title": "film title",
          "scenes": [
            {{
              "id": 1,
              "video_prompt": "Detailed Veo 3 prompt (3-5 sentences). Include: camera angle, lighting, character description, action, emotion. End with: 16:9 aspect ratio, 4K cinematic, no text, no subtitles.",
              "narration_zh": "Chinese narration sentence (15-30 chars) — spoken aloud during this clip.",
              "subtitle_zh": "Chinese subtitle (10-20 chars) — shown at bottom of screen."
            }},
            ...
          ],
          "spiritual_application": {{
            "title_zh": "结语标题 (e.g. 约瑟的故事告诉我们：)",
            "lines_zh": ["第一行 (20-30字)", "第二行", "第三行"],
            "scripture_zh": "经文引用 (e.g. 创世记50:20)",
            "narration_zh": "完整旁白段落，用于配音 (60-100字)",
            "duration_sec": 20
          }}
        }}
        Keep character descriptions consistent across all scene prompts.
        All narration/subtitle text must be in Simplified Chinese (简体中文).
    """)

    resp = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": f"Storyboard:\n\n{story_text}"}],
    )
    raw = resp.content[0].text.strip()
    raw = re.sub(r'^```[a-z]*\n?', '', raw)
    raw = re.sub(r'\n?```$', '', raw)
    return json.loads(raw)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Veo 3.1 生成视频片段
# ══════════════════════════════════════════════════════════════════════════════
def generate_veo_clip(prompt: str, output_path: Path, api_key: str,
                       poll_cb=None, max_wait=600) -> bool:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key)
    try:
        op = client.models.generate_videos(
            model="veo-3.1-generate-preview",
            prompt=prompt,
            config=types.GenerateVideosConfig(aspect_ratio="16:9", video_format="mp4"),
        )
        waited = 0
        while not op.done:
            time.sleep(15)
            waited += 15
            op = client.operations.get(op)
            if poll_cb:
                poll_cb(f"Veo 生成中 {waited}s…")
            if waited >= max_wait:
                raise TimeoutError("Veo 生成超时")

        uri = op.result.generated_videos[0].video.uri
        url = uri + (f"&key={api_key}" if "googleapis.com" in uri and "key=" not in uri else "")
        with httpx.Client(timeout=120, follow_redirects=True) as hc:
            with hc.stream("GET", url) as r:
                r.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in r.iter_bytes(65536):
                        f.write(chunk)
        return True
    except Exception as e:
        print(f"[VEO] Error: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Google TTS / edge-tts 生成旁白音频
# ══════════════════════════════════════════════════════════════════════════════
async def tts_to_file(text: str, output_path: Path) -> bool:
    """优先 edge-tts（小晓）；失败则写静音占位。"""
    try:
        import edge_tts
        com = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural", rate="+0%")
        buf = io.BytesIO()
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        if buf.tell() > 0:
            with open(output_path, "wb") as f:
                f.write(buf.getvalue())
            return True
    except Exception as e:
        print(f"[TTS] edge-tts error: {e}")

    # 回退：生成静音 mp3（避免 FFmpeg 无轨道报错）
    _run_ff([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
        "-t", "7", "-q:a", "9", "-acodec", "libmp3lame", str(output_path)
    ])
    return False


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — FFmpeg 合成单镜头（字幕 + 旁白）
# ══════════════════════════════════════════════════════════════════════════════
FONT_PATH = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"  # HF Docker
if not Path(FONT_PATH).exists():
    FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if not Path(FONT_PATH).exists():
    FONT_PATH = ""  # system default

def compose_clip(video_path: Path, audio_path: Path, subtitle_zh: str,
                  output_path: Path) -> bool:
    """合并视频 + 音频 + 中文字幕。"""
    font_opt = f":fontfile={FONT_PATH}" if FONT_PATH else ""
    text_escaped = subtitle_zh.replace("'", "\\'").replace(":", "\\:")
    drawtext = (
        f"drawtext=text='{text_escaped}'"
        f"{font_opt}"
        f":fontsize=36:fontcolor=white"
        f":x=(w-text_w)/2:y=h-80"
        f":borderw=3:bordercolor=black@0.8"
        f":shadowx=2:shadowy=2:shadowcolor=black@0.5"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-vf", drawtext,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    return _run_ff(cmd)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 5 — 生成属灵应用结尾片段（20秒）
# ══════════════════════════════════════════════════════════════════════════════
def create_spiritual_scene(sp: dict, audio_path: Path, output_path: Path) -> bool:
    """黑底金字属灵应用场景（20秒）。"""
    title    = sp.get("title_zh", "属灵应用")
    lines    = sp.get("lines_zh", [])
    scripture = sp.get("scripture_zh", "")
    duration  = sp.get("duration_sec", 20)

    if PIL_OK:
        # 用 Pillow 渲染更精美的文字图
        W, H = 1920, 1080
        img = Image.new("RGB", (W, H), (10, 10, 26))
        draw = ImageDraw.Draw(img)
        # 顶部金色标题
        try:
            fnt_title = ImageFont.truetype(FONT_PATH, 56) if FONT_PATH else ImageFont.load_default()
            fnt_body  = ImageFont.truetype(FONT_PATH, 42) if FONT_PATH else ImageFont.load_default()
            fnt_ref   = ImageFont.truetype(FONT_PATH, 32) if FONT_PATH else ImageFont.load_default()
        except Exception:
            fnt_title = fnt_body = fnt_ref = ImageFont.load_default()

        y = 200
        draw.text((W//2, y), title, font=fnt_title, fill=(255, 214, 10), anchor="mm")
        y += 100
        # 分割线
        draw.line([(W//2 - 200, y), (W//2 + 200, y)], fill=(255, 214, 10, 100), width=2)
        y += 40
        for line in lines:
            draw.text((W//2, y), line, font=fnt_body, fill=(240, 240, 255), anchor="mm")
            y += 70
        y += 20
        if scripture:
            draw.text((W//2, y), f"— {scripture}", font=fnt_ref, fill=(180, 160, 255), anchor="mm")

        img_path = WORK_DIR / "spiritual_bg.png"
        img.save(str(img_path))
        # 图→视频
        bg_video = WORK_DIR / "spiritual_bg.mp4"
        _run_ff([
            "ffmpeg", "-y", "-loop", "1", "-i", str(img_path),
            "-t", str(duration), "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-vf", "scale=1920:1080", str(bg_video),
        ])
    else:
        # Pillow 不可用：纯黑底+FFmpeg drawtext
        bg_video = WORK_DIR / "spiritual_bg.mp4"
        font_opt = f":fontfile={FONT_PATH}" if FONT_PATH else ""
        all_text = title + " " + " ".join(lines)
        text_esc = all_text.replace("'", "\\'").replace(":", "\\:")
        _run_ff([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=0x0a0a1a:size=1920x1080:rate=25",
            "-t", str(duration),
            "-vf", (
                f"drawtext=text='{text_esc}'"
                f"{font_opt}:fontsize=40:fontcolor=white"
                f":x=(w-text_w)/2:y=(h-text_h)/2"
                f":borderw=3:bordercolor=black"
            ),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(bg_video),
        ])

    # 合成旁白音频
    cmd = [
        "ffmpeg", "-y",
        "-i", str(bg_video),
        "-i", str(audio_path),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-shortest", str(output_path),
    ]
    return _run_ff(cmd)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 6 — FFmpeg 拼接全部片段
# ══════════════════════════════════════════════════════════════════════════════
def concat_clips(clip_paths: list[Path], output_path: Path) -> bool:
    concat_file = WORK_DIR / "concat_list.txt"
    with open(concat_file, "w") as f:
        for p in clip_paths:
            if p.exists() and p.stat().st_size > 1024:
                f.write(f"file '{p.resolve()}'\n")
    return _run_ff([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c:v", "libx264", "-preset", "slow", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(output_path),
    ])


# ══════════════════════════════════════════════════════════════════════════════
# STEP 7 — 上传 Cloudflare R2
# ══════════════════════════════════════════════════════════════════════════════
def upload_to_r2(file_path: Path, prefix: str = "biblical-films/") -> str:
    account_id = os.environ.get("R2_ACCOUNT_ID", "")
    access_key = os.environ.get("R2_ACCESS_KEY_ID", "")
    secret_key = os.environ.get("R2_SECRET_ACCESS_KEY", "")
    bucket     = os.environ.get("R2_BUCKET_NAME", "")
    cdn_base   = os.environ.get("VIDEO_CDN_BASE", f"https://{bucket}.r2.dev").rstrip("/")

    if not all([account_id, access_key, secret_key, bucket]):
        raise ValueError("R2 env vars not configured")

    import boto3
    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )
    key = prefix + file_path.name
    s3.upload_file(str(file_path), bucket, key,
                   ExtraArgs={"ContentType": "video/mp4"})
    return f"{cdn_base}/{key}"


# ══════════════════════════════════════════════════════════════════════════════
# 主流水线（后台线程）
# ══════════════════════════════════════════════════════════════════════════════
def _run_ff(cmd: list) -> bool:
    r = subprocess.run(cmd, capture_output=True)
    return r.returncode == 0

def log(job: dict, msg: str, progress: int = None):
    job["steps"].append(msg)
    if progress is not None:
        job["progress"] = progress
    print(f"[PIPELINE] {msg}")

def run_pipeline(job_id: str, story_text: str, config: dict):
    job = JOBS[job_id]
    job["status"]   = "running"
    job["steps"]    = []
    job["progress"] = 0

    anthropic_key = config.get("anthropic_key") or os.environ.get("ANTHROPIC_API_KEY", "")
    gemini_key    = config.get("gemini_key")    or os.environ.get("GEMINI_API_KEY", "")
    num_scenes    = config.get("num_scenes", 25)
    film_id       = job_id[:8]

    try:
        # ── Step 1: Claude ────────────────────────────────────────────────
        log(job, "🤖 Claude 正在拆分镜头…", 3)
        story = split_with_claude(story_text, anthropic_key, num_scenes)
        scenes = story["scenes"]
        sp     = story.get("spiritual_application", {})
        log(job, f"✅ 拆分完成，共 {len(scenes)} 个镜头", 8)
        job["story"] = story

        total_work = len(scenes) * 3 + 5  # 每镜头3步 + 合成步

        # ── Step 2+3+4: 逐镜头生成 ────────────────────────────────────────
        composed_clips: list[Path] = []
        for i, scene in enumerate(scenes):
            sid = scene["id"]
            base_progress = 8 + int(i / len(scenes) * 75)
            log(job, f"🎬 Scene {sid}/{len(scenes)}: Veo 生成中…", base_progress)
            job["current_scene"] = sid

            clip_path  = CLIPS_DIR / f"{film_id}_scene_{sid:02d}.mp4"
            audio_path = AUDIO_DIR / f"{film_id}_scene_{sid:02d}.mp3"
            comp_path  = COMP_DIR  / f"{film_id}_scene_{sid:02d}.mp4"

            # 2a: Veo
            if not (clip_path.exists() and clip_path.stat().st_size > 1024):
                ok = generate_veo_clip(
                    scene["video_prompt"], clip_path, gemini_key,
                    poll_cb=lambda m: log(job, f"  Scene {sid}: {m}")
                )
                if not ok:
                    log(job, f"  ⚠️ Scene {sid} Veo 失败，跳过")
                    composed_clips.append(clip_path)
                    continue
            else:
                log(job, f"  Scene {sid}: 复用已有片段")

            # 2b: TTS
            log(job, f"  Scene {sid}: 生成旁白…")
            asyncio.run(tts_to_file(scene.get("narration_zh", ""), audio_path))

            # 2c: Compose
            log(job, f"  Scene {sid}: 合成字幕+旁白…")
            compose_clip(clip_path, audio_path, scene.get("subtitle_zh", ""), comp_path)
            composed_clips.append(comp_path if comp_path.exists() else clip_path)

            log(job, f"  ✅ Scene {sid} 完成", base_progress + 2)
            time.sleep(3)  # 速率限制

        # ── Step 5: 属灵应用结尾 ──────────────────────────────────────────
        log(job, "✨ 生成属灵应用结尾场景…", 85)
        sp_audio = AUDIO_DIR / f"{film_id}_spiritual.mp3"
        sp_clip  = COMP_DIR  / f"{film_id}_spiritual.mp4"
        asyncio.run(tts_to_file(sp.get("narration_zh", ""), sp_audio))
        create_spiritual_scene(sp, sp_audio, sp_clip)
        if sp_clip.exists():
            composed_clips.append(sp_clip)

        # ── Step 6: FFmpeg 拼接 ────────────────────────────────────────────
        log(job, "🔗 FFmpeg 拼接最终视频…", 90)
        final_path = WORK_DIR / f"{film_id}_final.mp4"
        ok = concat_clips(composed_clips, final_path)
        if not ok or not final_path.exists():
            raise RuntimeError("FFmpeg 拼接失败")
        size_mb = round(final_path.stat().st_size / 1024 / 1024, 1)
        log(job, f"✅ 拼接完成 ({size_mb} MB)", 95)

        # ── Step 7: 上传 R2 ────────────────────────────────────────────────
        r2_url = None
        try:
            log(job, "☁️ 上传到 Cloudflare R2…", 97)
            r2_url = upload_to_r2(final_path)
            log(job, f"✅ 上传完成: {r2_url}", 99)
        except Exception as e:
            log(job, f"⚠️ R2 上传跳过 ({e})，可从本地下载")

        job["status"]   = "done"
        job["progress"] = 100
        job["result"]   = {
            "local_file":  final_path.name,
            "r2_url":      r2_url,
            "size_mb":     size_mb,
            "scene_count": len(scenes),
        }
        log(job, "🎉 全部完成！")

    except Exception as e:
        import traceback
        job["status"] = "error"
        job["error"]  = str(e)
        log(job, f"❌ 错误: {e}")
        print(traceback.format_exc())


# ══════════════════════════════════════════════════════════════════════════════
# API 端点
# ══════════════════════════════════════════════════════════════════════════════
class StartRequest(BaseModel):
    story_text:    str
    anthropic_key: str = ""
    gemini_key:    str = ""
    num_scenes:    int = 25

@app.post("/api/start")
def api_start(req: StartRequest):
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"job_id": job_id, "status": "queued", "progress": 0,
                    "steps": [], "current_scene": 0, "story": None,
                    "result": None, "error": None}
    t = threading.Thread(
        target=run_pipeline,
        args=(job_id, req.story_text, {
            "anthropic_key": req.anthropic_key,
            "gemini_key":    req.gemini_key,
            "num_scenes":    req.num_scenes,
        }),
        daemon=True,
    )
    t.start()
    return {"job_id": job_id}

@app.get("/api/status/{job_id}")
def api_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        from fastapi import HTTPException
        raise HTTPException(404, "Job not found")
    return job

@app.get("/api/sse/{job_id}")
def api_sse(job_id: str):
    """Server-Sent Events 实时进度流。"""
    def event_stream() -> Generator[str, None, None]:
        last_step_count = 0
        while True:
            job = JOBS.get(job_id)
            if not job:
                yield "data: {\"error\": \"job not found\"}\n\n"
                return
            # 只发送新 step 和状态变化
            steps = job.get("steps", [])
            new_steps = steps[last_step_count:]
            last_step_count = len(steps)
            payload = {
                "status":        job["status"],
                "progress":      job["progress"],
                "current_scene": job.get("current_scene", 0),
                "new_steps":     new_steps,
                "result":        job.get("result"),
                "error":         job.get("error"),
            }
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            if job["status"] in ("done", "error"):
                return
            time.sleep(2)

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.get("/download/{filename}")
def download(filename: str):
    p = WORK_DIR / filename
    if not p.exists():
        from fastapi import HTTPException
        raise HTTPException(404)
    return FileResponse(str(p), media_type="video/mp4",
                        filename=filename, headers={"Accept-Ranges": "bytes"})


# ══════════════════════════════════════════════════════════════════════════════
# 前端 HTML
# ══════════════════════════════════════════════════════════════════════════════
HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>圣经电影生成工作台</title>
<style>
:root{--bg:#0a0a1a;--panel:#12122a;--card:#181830;--border:rgba(255,255,255,0.08);
 --accent:#5856d6;--gold:#ffd60a;--green:#30d158;--red:#ff453a;--blue:#0a84ff;
 --text:rgba(255,255,255,0.92);--muted:rgba(255,255,255,0.45);}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--text);font-family:-apple-system,"PingFang SC",sans-serif;min-height:100vh;}
.layout{display:grid;grid-template-columns:420px 1fr;height:100vh;overflow:hidden;}
.left{background:var(--panel);border-right:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden;}
.right{display:flex;flex-direction:column;overflow:hidden;}
.header{padding:16px 20px 14px;border-bottom:1px solid var(--border);background:linear-gradient(135deg,rgba(88,86,214,0.2),rgba(255,214,10,0.06));}
.header h1{font-size:16px;font-weight:800;color:var(--gold);letter-spacing:.03em;}
.header p{font-size:11px;color:var(--muted);margin-top:3px;}
.left-body{flex:1;padding:16px;display:flex;flex-direction:column;gap:10px;overflow-y:auto;}
label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;}
textarea,input{background:rgba(255,255,255,0.04);border:1px solid var(--border);border-radius:8px;color:var(--text);font-family:inherit;outline:none;transition:border .15s;}
textarea:focus,input:focus{border-color:rgba(88,86,214,0.5);}
#story{width:100%;height:280px;font-size:12px;line-height:1.7;padding:12px;resize:none;}
.row{display:flex;gap:8px;}
.row input{flex:1;padding:8px 10px;font-size:12px;}
.btn{padding:10px 18px;border-radius:8px;border:none;cursor:pointer;font-size:13px;font-weight:700;transition:opacity .15s,transform .1s;}
.btn:hover{opacity:.88;transform:translateY(-1px);}
.btn:active{transform:translateY(0);}
.btn:disabled{opacity:.4;cursor:default;transform:none;}
.btn-primary{background:linear-gradient(135deg,var(--accent),#7b79f0);color:#fff;width:100%;}
.btn-dl{background:var(--green);color:#000;padding:8px 16px;font-size:12px;}
.num-row{display:flex;align-items:center;gap:10px;}
.num-row label{flex:1;}
.num-row input[type=number]{width:70px;padding:6px 8px;font-size:13px;text-align:center;}
/* Right */
.right-header{padding:14px 18px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px;}
.right-header h2{font-size:14px;font-weight:600;flex:1;}
.progress-section{padding:16px 18px;border-bottom:1px solid var(--border);}
.big-progress{height:10px;background:rgba(255,255,255,0.08);border-radius:5px;overflow:hidden;margin:10px 0 6px;}
.big-bar{height:100%;background:linear-gradient(90deg,var(--accent),var(--gold));border-radius:5px;transition:width .6s;}
.pct{font-size:12px;color:var(--muted);}
.scenes-grid{flex:1;overflow-y:auto;padding:14px 18px;display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px;align-content:start;}
.scene-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:12px;font-size:12px;}
.scene-card.active{border-color:var(--accent);background:rgba(88,86,214,0.08);}
.scene-card.done{border-color:rgba(48,209,88,0.3);}
.scene-card.skip{opacity:.45;}
.sc-num{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;}
.sc-title{font-weight:700;margin:3px 0;}
.sc-status{color:var(--muted);margin-top:4px;}
.sc-status.act{color:#5ac8fa;}
.sc-status.ok{color:var(--green);}
.log-box{height:180px;overflow-y:auto;padding:10px 18px;font-size:11px;line-height:1.8;color:var(--muted);border-top:1px solid var(--border);}
.log-box p{padding:1px 0;}
.log-box .ok{color:var(--green);}
.log-box .err{color:var(--red);}
.result-bar{padding:12px 18px;border-top:1px solid var(--border);background:var(--panel);display:flex;align-items:center;gap:12px;}
.result-bar a{color:var(--gold);text-decoration:none;font-size:13px;}
.result-bar a:hover{text-decoration:underline;}
video{width:100%;border-radius:8px;margin-top:8px;background:#000;}
</style>
</head>
<body>
<div class="layout">
<!-- LEFT: 输入 -->
<div class="left">
  <div class="header">
    <h1>🎬 圣经电影全自动生成工作台</h1>
    <p>Claude · Veo 3.1 · TTS · 字幕 · FFmpeg · Cloudflare R2</p>
  </div>
  <div class="left-body">
    <label>故事板（粘贴完整格式）</label>
    <textarea id="story" placeholder="《约瑟》 (Joseph)
Style: Ancient Canaan and Imperial Egypt around 1700 BC...
Main Characters: Joseph: ...
Storyboard:
* Scene 1: Jacob presents a beautiful, multicolored coat...
* Scene 2: Joseph shares his dreams...
...
* Final scene: Joseph stands with his unified family...
No subtitles. No text on screen.
属灵应用旁白：
约瑟的故事告诉我们：
有时候神的方法和人的方法不一样。
当我们愿意顺服神时，神能成就人做不到的事情。"></textarea>

    <label>API Keys（未填则使用服务器环境变量）</label>
    <div class="row">
      <input id="ak" type="password" placeholder="Anthropic API Key (sk-ant-)"/>
    </div>
    <div class="row">
      <input id="gk" type="password" placeholder="Gemini API Key (AIza...)"/>
    </div>

    <div class="num-row">
      <label>镜头数量</label>
      <input type="number" id="num-scenes" value="25" min="5" max="30"/>
    </div>

    <button class="btn btn-primary" id="start-btn" onclick="startJob()">⚡ 开始生成完整视频</button>
    <div id="job-id-display" style="font-size:11px;color:var(--muted);text-align:center"></div>
  </div>
</div>

<!-- RIGHT: 进度 + 场景卡片 -->
<div class="right">
  <div class="right-header">
    <h2 id="film-title">待生成</h2>
    <span id="status-badge" style="font-size:12px;color:var(--muted)"></span>
  </div>

  <div class="progress-section" id="prog-section" style="display:none">
    <div style="font-size:12px;color:var(--muted)">整体进度</div>
    <div class="big-progress"><div class="big-bar" id="big-bar" style="width:0%"></div></div>
    <div class="pct" id="pct-text">0%</div>
  </div>

  <div class="scenes-grid" id="scenes-grid">
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;opacity:.3;gap:12px;grid-column:1/-1;">
      <div style="font-size:48px">🎞️</div>
      <div style="font-size:14px">输入故事板并点击开始</div>
    </div>
  </div>

  <div class="log-box" id="log-box"></div>
  <div class="result-bar" id="result-bar" style="display:none"></div>
</div>
</div>

<script>
let jobId = null;
let evtSource = null;
let scenes = [];

function startJob() {
  const story = document.getElementById('story').value.trim();
  if (!story) return alert('请输入故事板文本');
  const ak = document.getElementById('ak').value.trim();
  const gk = document.getElementById('gk').value.trim();
  const ns = parseInt(document.getElementById('num-scenes').value) || 25;

  document.getElementById('start-btn').disabled = true;
  document.getElementById('prog-section').style.display = '';
  document.getElementById('result-bar').style.display = 'none';
  document.getElementById('log-box').innerHTML = '';
  document.getElementById('scenes-grid').innerHTML = '<div style="color:var(--muted);font-size:13px;padding:20px">初始化中…</div>';

  fetch('/api/start', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({story_text:story, anthropic_key:ak, gemini_key:gk, num_scenes:ns})
  })
  .then(r => r.json())
  .then(d => {
    jobId = d.job_id;
    document.getElementById('job-id-display').textContent = 'Job: ' + jobId;
    listenSSE(jobId);
  })
  .catch(e => {
    alert('启动失败: ' + e);
    document.getElementById('start-btn').disabled = false;
  });
}

function listenSSE(id) {
  if (evtSource) evtSource.close();
  evtSource = new EventSource('/api/sse/' + id);
  evtSource.onmessage = e => {
    const d = JSON.parse(e.data);
    updateProgress(d.progress || 0);
    if (d.new_steps) d.new_steps.forEach(addLog);
    if (d.status === 'running' && d.current_scene > 0 && scenes.length > 0) {
      highlightScene(d.current_scene);
    }
    if (d.status === 'done') {
      onDone(d.result);
      evtSource.close();
    }
    if (d.status === 'error') {
      onError(d.error);
      evtSource.close();
    }
    // Build scene cards from story data lazily
    fetch('/api/status/' + id)
      .then(r => r.json())
      .then(job => {
        if (job.story && scenes.length === 0) renderSceneCards(job.story);
      });
  };
  evtSource.onerror = () => evtSource.close();
}

function renderSceneCards(story) {
  scenes = story.scenes || [];
  document.getElementById('film-title').textContent = story.title || '生成中…';
  const grid = document.getElementById('scenes-grid');
  const sp = story.spiritual_application || {};
  const all = [...scenes, {id: scenes.length+1, subtitle_zh: sp.title_zh || '属灵应用', narration_zh: '🙏 结尾属灵应用'}];
  grid.innerHTML = all.map(s => `
    <div class="scene-card" id="sc-${s.id}">
      <div class="sc-num">${s.id <= scenes.length ? 'Scene ' + s.id : '🙏 结尾'}</div>
      <div class="sc-title">${truncate(s.subtitle_zh || s.title_zh || '', 18)}</div>
      <div class="sc-status" id="sc-st-${s.id}">待生成</div>
    </div>
  `).join('');
}

function highlightScene(id) {
  document.querySelectorAll('.scene-card').forEach(c => c.classList.remove('active'));
  const el = document.getElementById('sc-' + id);
  if (el) {
    el.classList.add('active');
    el.scrollIntoView({behavior:'smooth', block:'nearest'});
    document.getElementById('sc-st-' + id).className = 'sc-status act';
    document.getElementById('sc-st-' + id).textContent = '生成中…';
  }
}

function updateProgress(pct) {
  document.getElementById('big-bar').style.width = pct + '%';
  document.getElementById('pct-text').textContent = pct + '%';
}

function addLog(msg) {
  const box = document.getElementById('log-box');
  const p = document.createElement('p');
  p.textContent = msg;
  if (msg.includes('✅') || msg.includes('🎉')) p.className = 'ok';
  if (msg.includes('❌') || msg.includes('错误')) p.className = 'err';
  box.appendChild(p);
  box.scrollTop = box.scrollHeight;
}

function onDone(result) {
  updateProgress(100);
  document.getElementById('status-badge').textContent = '✅ 完成';
  document.getElementById('start-btn').disabled = false;

  // Mark all scenes done
  document.querySelectorAll('.scene-card').forEach(c => {
    c.classList.remove('active'); c.classList.add('done');
  });
  document.querySelectorAll('[id^=sc-st-]').forEach(el => {
    el.className = 'sc-status ok'; el.textContent = '✅';
  });

  // Result bar
  const bar = document.getElementById('result-bar');
  bar.style.display = 'flex';
  let html = `<span style="color:var(--green);font-weight:700">🎉 生成完成 · ${result.scene_count} 镜头 · ${result.size_mb} MB</span>`;
  if (result.r2_url) {
    html += `<a href="${result.r2_url}" target="_blank">☁️ Cloudflare 播放</a>`;
  }
  if (result.local_file) {
    html += `<a href="/download/${result.local_file}" class="btn btn-dl" download>⬇ 下载视频</a>`;
  }
  bar.innerHTML = html;
  addLog('🎉 全部完成！');
}

function onError(err) {
  document.getElementById('status-badge').textContent = '❌ 错误';
  document.getElementById('start-btn').disabled = false;
  addLog('❌ ' + err);
}

function truncate(s, n) { return s.length > n ? s.slice(0,n) + '…' : s; }

// 持久化 API Keys
window.onload = () => {
  ['ak','gk'].forEach(id => {
    const v = localStorage.getItem('bibfilm_' + id);
    if (v) document.getElementById(id).value = v;
    document.getElementById(id).addEventListener('change', e => localStorage.setItem('bibfilm_' + id, e.target.value));
  });
};
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return HTML


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8765))
    print("=" * 55)
    print("🎬 圣经电影全自动生成工作台")
    print(f"   http://localhost:{port}")
    print("   需要环境变量: ANTHROPIC_API_KEY, GEMINI_API_KEY")
    print("   R2上传: R2_ACCOUNT_ID/R2_ACCESS_KEY_ID/R2_SECRET_ACCESS_KEY/R2_BUCKET_NAME")
    print("=" * 55)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
