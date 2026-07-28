"""
Media router — 多模态输出底座 (/api/tts/script, /api/media/*)

  POST /api/tts/script                            分步引导旁白：逐段合成 + 段间真实静音，返回单文件 + cue points
  GET  /api/tts/script/audio/{name}               取回上面按内容哈希缓存的音频
  POST /api/media/card                            服务端渲染信息卡 PNG（推送/邮件/离线场景，无 canvas 可用）
  POST /api/media/testimony-clip                  见证 → 竖版短视频（异步 job）
  GET  /api/media/testimony-clip/status/{job_id}  任务状态轮询（与 /api/film/status 同一套 JOBS）
  POST /api/media/illustrate                      Gemini 经文/场景配图 → R2（含内容护栏）
  GET  /api/media/illustration/{name}             R2 未配置时的本地取图兜底

对应 bible3dsphereWeb/docs/MULTIMODAL_OPPORTUNITY_AUDIT_2026-07.md §6 的四个后端缺口。

一律复用既有底座，不重复造：
  · TTS 多级兜底         routers/verse.py: synthesize_speech()（ElevenLabs → edge-tts → gTTS → Google）
  · 视频流水线           routers/film_studio.py: tts_to_file / kenburns_clip / concat_all / upload_r2 / JOBS
  · 图卡版式             bible3dsphereWeb/src/lib/media/cardStudio.js（本文件是它的服务端等价实现）
"""
# 注意：这里刻意不写 `from __future__ import annotations`。
# slowapi 的 @limiter.limit 会把端点函数包一层，FastAPI 解析注解时用的是包装函数的
# __globals__（slowapi 模块），本模块里的 Pydantic 模型在那里不存在。一旦注解被
# PEP 563 变成字符串，ScriptTTSRequest 就永远停在 ForwardRef，app.openapi() 直接抛错——
# 整个 /docs 与 OpenAPI schema 都会挂掉，不只是这一条路由。
# 全仓 223 个 router 里只有本文件同时用到「__future__ 注解 + 限流 + Body 模型」这三样，
# 所以此前没有先例。verse.py（同样是限流 + Body）也没有这一行，这里与它保持一致。

import asyncio
import base64
import hashlib
import json
import logging
import os
import random
import re
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Body, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from core.ratelimit import limiter

try:  # 与其它 router 一致：优先 backend/ 下的绝对导入，包式导入作兜底
    from routers import film_studio as fs
    from routers.verse import synthesize_speech
except ImportError:  # pragma: no cover
    from backend.routers import film_studio as fs  # type: ignore
    from backend.routers.verse import synthesize_speech  # type: ignore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["media"])

_state: dict[str, Any] = {}


def init_media_router(*, get_db=None, release_db=None, get_session_user=None,
                      handle_exc=None) -> None:
    """与其它 router 相同的注入约定（main.py 统一按这个签名调用）。

    本域不落库、鉴权走 film_studio._require_film_user，所以注入的助手目前只作为
    _state 里的可选依赖保留，供后续把生成记录落库时直接取用。
    """
    _state.update(locals())


# ── 产物目录：沿用 film_studio 的输出根，避免再引入一套路径/清理策略 ──────────────
MEDIA_DIR = fs.FILM_DIR / "media"
SCRIPT_AUDIO_DIR = MEDIA_DIR / "tts_script"
ILLUSTRATION_DIR = MEDIA_DIR / "illustrations"
TESTIMONY_SLIDE_DIR = MEDIA_DIR / "testimony"
for _d in (MEDIA_DIR, SCRIPT_AUDIO_DIR, ILLUSTRATION_DIR, TESTIMONY_SLIDE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

_HASH_NAME_RE = re.compile(r"^[0-9a-f]{32}\.(mp3|png)$")


def _content_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


# ══════════════════════════════════════════════════════════════════════════════
# 1) POST /api/tts/script —— 分步引导旁白（分段合成 + 真实静音留白 + cue points）
# ══════════════════════════════════════════════════════════════════════════════

class ScriptStep(BaseModel):
    text: str = Field(default="", max_length=1200)
    # 前端 useGuidedAudio 用的是 pauseAfter，规范字段名是 pause_after_seconds，两个都收
    pause_after_seconds: float = Field(default=0.0, ge=0.0, le=300.0, alias="pauseAfter")
    label: str = Field(default="", max_length=40)

    model_config = {"populate_by_name": True}


class ScriptTTSRequest(BaseModel):
    steps: list[ScriptStep] = Field(..., min_length=1, max_length=24)
    language_code: str = Field(default="cmn-CN", max_length=20)
    voice_name: str = Field(default="zh-CN-XiaoxiaoNeural", max_length=64)
    lead_in_seconds: float = Field(default=0.0, ge=0.0, le=30.0)
    # 默认只回 audio_url（音频走 GET 长缓存）；需要一次拿全时置 true 附带 base64
    inline_audio: bool = False


MAX_SCRIPT_CHARS = int(os.getenv("TTS_SCRIPT_MAX_CHARS", "6000"))
_SCRIPT_LOCK = threading.Lock()


_FF_TIME_RE = re.compile(r"time=(\d+):(\d{2}):(\d{2}(?:\.\d+)?)")


def _decoded_dur(path: Path) -> float:
    """解码后的真实时长（秒）。

    不用 ffprobe 的容器时长：mp3 头里带编码器 delay/padding，容器时长会比实际解码出的
    音频长几十毫秒，逐段累加会让 cue 点整体偏移。浏览器播放时走的是 gapless 解码后的
    时间轴，所以这里用 `ffmpeg -f null -` 报的解码时长对齐它。失败时退回 ffprobe。
    """
    try:
        r = subprocess.run(["ffmpeg", "-v", "error", "-stats", "-i", str(path), "-f", "null", "-"],
                           capture_output=True, text=True, timeout=60)
        matches = _FF_TIME_RE.findall((r.stderr or "") + (r.stdout or ""))
        if matches:
            h, m, sec = matches[-1]
            return int(h) * 3600 + int(m) * 60 + float(sec)
    except Exception:  # noqa: BLE001
        pass
    return fs._audio_dur(path)


def _silence_input(seconds: float) -> list[str]:
    """一段 lavfi 静音输入。用真实静音而不是客户端定时器，成品音频离线/后台播放也不会走样。"""
    return ["-f", "lavfi", "-t", f"{max(0.0, seconds):.3f}", "-i", "anullsrc=r=44100:cl=mono"]


def _concat_audio(parts: list[tuple[str, Any]], out: Path) -> bool:
    """parts = [("file", path) | ("silence", seconds)]，统一重采样后 concat 成单个 mp3。

    用 concat *滤镜* 而不是 concat demuxer：各引擎产出的 mp3 采样率/声道并不一致
    （edge-tts 24k、ElevenLabs 44.1k、gTTS 24k），demuxer 直拼会串音或变速。
    """
    if not parts:
        return False
    cmd: list[str] = ["ffmpeg", "-y"]
    for kind, val in parts:
        if kind == "file":
            cmd += ["-i", str(val)]
        else:
            cmd += _silence_input(float(val))
    filt = "".join(
        f"[{i}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=mono[a{i}];"
        for i in range(len(parts))
    )
    filt += "".join(f"[a{i}]" for i in range(len(parts)))
    filt += f"concat=n={len(parts)}:v=0:a=1[out]"
    cmd += ["-filter_complex", filt, "-map", "[out]",
            "-c:a", "libmp3lame", "-q:a", "4", "-ar", "44100", "-ac", "1", str(out)]
    return fs._ff(cmd)


@router.post("/tts/script")
@limiter.limit("10/minute")
async def tts_script(payload: ScriptTTSRequest = Body(...), request: Request = None) -> dict:
    """引导式播报合成：逐段 TTS → 段间插入请求时长的真实静音 → 合成单个 mp3 + cue points。

    Lectio / 省察 / 呼吸这类操练的关键在「念完之后的安静」，所以留白必须进音频本身，
    客户端只需按 cues[].offset_sec 驱动倒计时与高亮，不必自己拼接多个音频源。
    """
    steps = payload.steps
    total_chars = sum(len((s.text or "").strip()) for s in steps)
    if total_chars > MAX_SCRIPT_CHARS:
        raise HTTPException(status_code=413, detail=f"脚本过长（{total_chars} 字，上限 {MAX_SCRIPT_CHARS} 字）")
    if total_chars == 0 and not any(s.pause_after_seconds for s in steps):
        raise HTTPException(status_code=400, detail="脚本为空")

    norm = {
        "v": 1,
        "voice": payload.voice_name,
        "lang": payload.language_code,
        "lead_in": round(payload.lead_in_seconds, 2),
        "steps": [{"t": (s.text or "").strip(), "p": round(s.pause_after_seconds, 2)} for s in steps],
    }
    key = _content_hash(norm)
    audio_path = SCRIPT_AUDIO_DIR / f"{key}.mp3"
    meta_path = SCRIPT_AUDIO_DIR / f"{key}.json"

    # ── 内容哈希缓存：同一篇灵修/同一段引导词重复打开时不再重复合成（也不再重复计费）──
    if audio_path.exists() and audio_path.stat().st_size > 256 and meta_path.exists():
        try:
            cached = json.loads(meta_path.read_text(encoding="utf-8"))
            cached["cached"] = True
            if payload.inline_audio:
                cached["audio_base64"] = base64.b64encode(audio_path.read_bytes()).decode()
            return cached
        except Exception as exc:  # noqa: BLE001 — 缓存损坏就当未命中，重新合成
            logger.warning("[media] tts/script cache unreadable (%s), resynthesizing", exc)

    tmp_dir = SCRIPT_AUDIO_DIR / f"_tmp_{key}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    parts: list[tuple[str, Any]] = []
    cues: list[dict] = []
    offset = float(payload.lead_in_seconds)
    if payload.lead_in_seconds > 0:
        parts.append(("silence", payload.lead_in_seconds))

    try:
        for i, step in enumerate(steps):
            text = (step.text or "").strip()
            speech_sec = 0.0
            if text:
                audio_bytes = await synthesize_speech(text, voice_name=payload.voice_name)
                seg = tmp_dir / f"{i:02d}.mp3"
                seg.write_bytes(audio_bytes)
                speech_sec = _decoded_dur(seg)
                if speech_sec <= 0:
                    raise HTTPException(status_code=502, detail="TTS 合成结果不可读（ffprobe 无法解析）")
                parts.append(("file", str(seg)))
            pause_sec = float(step.pause_after_seconds)
            cues.append({
                "index": i,
                "label": step.label or "",
                "offset_sec": round(offset, 3),
                "speech_sec": round(speech_sec, 3),
                "pause_sec": round(pause_sec, 3),
                "end_sec": round(offset + speech_sec + pause_sec, 3),
            })
            offset += speech_sec + pause_sec
            if pause_sec > 0:
                parts.append(("silence", pause_sec))

        with _SCRIPT_LOCK:      # ffmpeg 输出同名文件，避免并发同哈希请求互相覆盖
            if not _concat_audio(parts, audio_path):
                raise HTTPException(status_code=502, detail="音频拼接失败（ffmpeg）")

        # 总时长用 cue 累加值：和 cue 点同一把尺子，客户端倒计时不会在最后一步对不上
        duration = round(offset, 3) or fs._audio_dur(audio_path)
        result = {
            "ok": True,
            "hash": key,
            "cached": False,
            "mime": "audio/mpeg",
            "duration_sec": round(duration, 3),
            "audio_url": f"/api/tts/script/audio/{key}.mp3",
            "cues": cues,
        }
        meta_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        if payload.inline_audio:
            result["audio_base64"] = base64.b64encode(audio_path.read_bytes()).decode()
        return result
    finally:
        for f in tmp_dir.glob("*.mp3"):
            try:
                f.unlink()
            except Exception:
                pass
        try:
            tmp_dir.rmdir()
        except Exception:
            pass


@router.get("/tts/script/audio/{name}")
def tts_script_audio(name: str) -> FileResponse:
    """按内容哈希命名，内容不可变 —— 可以放心让浏览器长缓存。"""
    if not _HASH_NAME_RE.match(name) or not name.endswith(".mp3"):
        raise HTTPException(status_code=404, detail="Audio not found")
    p = SCRIPT_AUDIO_DIR / name
    if not p.exists():
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(str(p), media_type="audio/mpeg",
                        headers={"Cache-Control": "public, max-age=31536000, immutable",
                                 "Accept-Ranges": "bytes"})


# ══════════════════════════════════════════════════════════════════════════════
# 2) POST /api/media/card —— 服务端图卡渲染（cardStudio.js 的 Pillow 等价实现）
# ══════════════════════════════════════════════════════════════════════════════

def _hex_rgb(value: str) -> tuple:
    v = value.lstrip("#")
    return (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16))


def _rgba(r: int, g: int, b: int, alpha: float) -> tuple:
    return (r, g, b, max(0, min(255, int(round(alpha * 255)))))


# 与 src/lib/media/cardStudio.js 的 CARD_TEMPLATES 逐字对应，改一边要同步改另一边
CARD_TEMPLATES: dict[str, dict] = {
    "dawn":  {"name": "晨光", "stops": [(0.0, "#2b1d4f"), (0.55, "#7a3b67"), (1.0, "#e8945a")],
              "ink": "#fff7ec", "sub": _rgba(255, 247, 236, 0.74), "rule": _rgba(255, 247, 236, 0.22)},
    "sea":   {"name": "深海", "stops": [(0.0, "#0a1f33"), (0.60, "#10405e"), (1.0, "#1d6f86")],
              "ink": "#eafaff", "sub": _rgba(234, 250, 255, 0.72), "rule": _rgba(234, 250, 255, 0.22)},
    "olive": {"name": "橄榄", "stops": [(0.0, "#1c2a17"), (0.60, "#3c5230"), (1.0, "#7a8f54")],
              "ink": "#f6f8ec", "sub": _rgba(246, 248, 236, 0.74), "rule": _rgba(246, 248, 236, 0.22)},
    "ink":   {"name": "墨夜", "stops": [(0.0, "#0c0d12"), (1.0, "#23263a")],
              "ink": "#f2ecdd", "sub": _rgba(242, 236, 221, 0.68), "rule": _rgba(242, 236, 221, 0.20)},
    "calm":  {"name": "静蓝", "stops": [(0.0, "#0b1622"), (0.62, "#123049"), (1.0, "#1b4a63")],
              "ink": "#eaf4ff", "sub": _rgba(234, 244, 255, 0.72), "rule": _rgba(234, 244, 255, 0.20)},
}

CARD_SIZES = {"4:5": (1080, 1350), "9:16": (1080, 1920)}
PAD = 84

_FONT_CANDIDATES = [p for p in [
    fs.FONT_PATH,
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
] if p and Path(p).exists()]
_FONT_CACHE: dict = {}


def _font(size: int):
    """wqy-microhei 只有一个字重，粗体用 stroke_width 近似（见 _draw_text）。"""
    if size in _FONT_CACHE:
        return _FONT_CACHE[size]
    from PIL import ImageFont
    font = None
    for path in _FONT_CANDIDATES:
        try:
            font = ImageFont.truetype(path, size)
            break
        except Exception:
            continue
    if font is None:
        logger.warning("[media] no CJK truetype font found (%s); falling back to bitmap font",
                       fs.FONT_PATH or "none")
        font = ImageFont.load_default()
    _FONT_CACHE[size] = font
    return font


# cardStudio.js 的分词规则：CJK/全角逐字，拉丁按词 —— 断行必须保持一致，否则同一份
# 内容在客户端与服务端会排出两种版式。
_TOKEN_RE = re.compile(r"[一-鿿　-〿＀-￯]|\S+|\s+")


def _measure(font, text: str) -> float:
    try:
        return float(font.getlength(text))
    except AttributeError:  # 位图字体兜底
        return float(font.getbbox(text)[2] if text else 0)


def _wrap(font, text: str, max_width: float) -> list[str]:
    lines: list[str] = []
    line = ""
    for tk in _TOKEN_RE.findall(str(text)):
        test = line + tk
        if _measure(font, test) > max_width and line.strip():
            lines.append(line.rstrip())
            line = "" if tk.isspace() else tk
        else:
            line = test
    if line.strip():
        lines.append(line.rstrip())
    return lines


def _draw_text(draw, xy, text: str, font, fill, *, bold: bool = False, anchor: str = "ls") -> None:
    # anchor="ls" = 左对齐 + 基线对齐，等价于 canvas 默认的 alphabetic baseline
    kwargs = {"font": font, "fill": fill, "anchor": anchor}
    if bold:
        kwargs.update(stroke_width=1, stroke_fill=fill)
    try:
        draw.text(xy, text, **kwargs)
    except (TypeError, ValueError):   # 位图字体不支持 anchor/stroke
        draw.text(xy, text, font=font, fill=fill)


def _gradient(width: int, height: int, stops: list):
    """线性渐变，方向与 cardStudio 的 createLinearGradient(0,0,W*0.4,H) 一致。"""
    import numpy as np
    from PIL import Image
    dx, dy = width * 0.4, float(height)
    den = dx * dx + dy * dy
    xs = np.arange(width, dtype=np.float32)
    ys = np.arange(height, dtype=np.float32)
    t = np.clip((xs[None, :] * dx + ys[:, None] * dy) / den, 0.0, 1.0)
    arr = np.zeros((height, width, 3), dtype=np.float32)
    pts = [(float(at), _hex_rgb(color)) for at, color in stops]
    for i in range(len(pts) - 1):
        a0, c0 = pts[i]
        a1, c1 = pts[i + 1]
        span = max(1e-6, a1 - a0)
        m = (t >= a0) & (t <= a1)
        local = ((t - a0) / span)[..., None]
        seg = np.array(c0, dtype=np.float32) * (1 - local) + np.array(c1, dtype=np.float32) * local
        arr[m] = seg[m]
    arr[t <= pts[0][0]] = np.array(pts[0][1], dtype=np.float32)
    arr[t >= pts[-1][0]] = np.array(pts[-1][1], dtype=np.float32)
    return Image.fromarray(arr.astype("uint8"), "RGB")


def render_info_card(spec: dict, *, width: int = 1080, height: int = 1350) -> bytes:
    """渲染一张信息卡，返回 PNG 字节。版式逐段对齐 cardStudio.js: renderInfoCard()。"""
    from PIL import ImageDraw

    tpl = CARD_TEMPLATES.get(str(spec.get("template") or ""), CARD_TEMPLATES["calm"])
    img = _gradient(width, height, tpl["stops"]).convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")   # RGBA 模式才能画半透明文字/分隔线

    # 极轻的颗粒，压掉大面积渐变的色带
    rng = random.Random(_content_hash(spec) if spec else "card")
    for i in range(900):
        color = (255, 255, 255, 9) if i % 2 else (0, 0, 0, 9)
        x = rng.random() * width
        y = rng.random() * height
        draw.rectangle([x, y, x + 2, y + 2], fill=color)

    ink = _hex_rgb(tpl["ink"])
    sub = tpl["sub"]
    max_w = width - PAD * 2
    y = PAD + 24

    badge = str(spec.get("badge") or "").strip()
    if badge:
        f = _font(26)
        tw = _measure(f, badge)
        bw, bh = tw + 36, 52
        draw.rounded_rectangle([PAD, y, PAD + bw, y + bh], radius=26, fill=(255, 255, 255, 36))
        _draw_text(draw, (PAD + 18, y + bh / 2), badge, f, ink, bold=True, anchor="lm")
        y += bh + 34

    kicker = str(spec.get("kicker") or "").strip()
    if kicker:
        f = _font(28)
        _draw_text(draw, (PAD, y + 28), kicker, f, sub)
        y += 56

    title = str(spec.get("title") or "").strip()
    if title:
        f = _font(62)
        for ln in _wrap(f, title, max_w):
            y += 78
            _draw_text(draw, (PAD, y), ln, f, ink, bold=True)
        y += 18

    subtitle = str(spec.get("subtitle") or "").strip()
    if subtitle:
        f = _font(30)
        for ln in _wrap(f, subtitle, max_w):
            y += 44
            _draw_text(draw, (PAD, y), ln, f, sub)
        y += 12

    sections = [s for s in (spec.get("sections") or [])
                if s and (any(str(i or "").strip() for i in (s.get("items") or [])) or s.get("heading"))]
    for sec in sections:
        y += 42
        if y > height - PAD - 120:
            continue
        draw.line([(PAD, y - 22), (width - PAD, y - 22)], fill=tpl["rule"], width=2)
        heading = str(sec.get("heading") or "").strip()
        if heading:
            fh = _font(30)
            y += 22
            _draw_text(draw, (PAD, y), heading, fh, ink, bold=True)
            y += 12
        emphasis = bool(sec.get("emphasis"))
        size = 38 if emphasis else 32
        fi = _font(size)
        for item in (sec.get("items") or []):
            text = str(item or "").strip()
            if not text:
                continue
            for li, ln in enumerate(_wrap(fi, text, max_w - 34)):
                y += size + 14
                if y > height - PAD - 70:
                    break
                if li == 0:
                    r = 6
                    cy = y - size / 3
                    draw.ellipse([PAD + 8 - r, cy - r, PAD + 8 + r, cy + r], fill=sub)
                _draw_text(draw, (PAD + 34, y), ln, fi, ink if emphasis else sub, bold=emphasis)

    footer = str(spec.get("footer") or "").strip()
    if footer:
        f = _font(24)
        lines = _wrap(f, footer, max_w)
        fy = height - PAD - (len(lines) - 1) * 34
        for ln in lines:
            _draw_text(draw, (PAD, fy), ln, f, sub)
            fy += 34

    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


class CardSection(BaseModel):
    heading: str = Field(default="", max_length=60)
    items: list[str] = Field(default_factory=list, max_length=12)
    emphasis: bool = False


class CardRequest(BaseModel):
    template: str = Field(default="calm", max_length=20)
    aspect: str = Field(default="4:5", max_length=8)     # 4:5 图卡 / 9:16 竖版
    badge: str = Field(default="", max_length=24)
    kicker: str = Field(default="", max_length=60)
    title: str = Field(default="", max_length=160)
    subtitle: str = Field(default="", max_length=400)
    sections: list[CardSection] = Field(default_factory=list, max_length=6)
    footer: str = Field(default="", max_length=200)


@router.post("/media/card")
@limiter.limit("30/minute")
async def media_card(payload: CardRequest = Body(...), request: Request = None) -> Response:
    """服务端渲染信息卡 PNG。推送/邮件/离线场景没有 canvas，只能在服务端出图。"""
    if payload.aspect not in CARD_SIZES:
        raise HTTPException(status_code=400, detail=f"aspect 仅支持 {'/'.join(CARD_SIZES)}")
    if payload.template and payload.template not in CARD_TEMPLATES:
        raise HTTPException(status_code=400, detail=f"未知模板：{payload.template}")
    if not any([payload.title, payload.subtitle, payload.kicker, payload.footer, payload.sections]):
        raise HTTPException(status_code=400, detail="卡片内容为空")
    width, height = CARD_SIZES[payload.aspect]
    spec = payload.model_dump()
    try:
        png = await asyncio.to_thread(render_info_card, spec, width=width, height=height)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("[media] card render failed: %s", exc)
        raise HTTPException(status_code=500, detail="图卡渲染失败") from exc
    return Response(content=png, media_type="image/png",
                    headers={"Content-Disposition": 'inline; filename="card.png"',
                             "Cache-Control": "no-store"})


# ══════════════════════════════════════════════════════════════════════════════
# 3) POST /api/media/testimony-clip —— 见证 → 竖版短视频（异步 job）
# ══════════════════════════════════════════════════════════════════════════════

TESTIMONY_MAX_TEXT = int(os.getenv("TESTIMONY_CLIP_MAX_CHARS", "4000"))
TESTIMONY_MAX_AUDIO_BYTES = int(os.getenv("TESTIMONY_CLIP_MAX_AUDIO_BYTES", str(10 * 1024 * 1024)))
TESTIMONY_MAX_SLIDES = int(os.getenv("TESTIMONY_CLIP_MAX_SLIDES", "8"))
VERTICAL = (1080, 1920)


def _chunk_text(text: str, *, max_len: int = 46, max_chunks: int = TESTIMONY_MAX_SLIDES) -> list[str]:
    """按句断句再按屏聚合。一屏一句话，短视频才读得完。"""
    sentences: list[str] = []
    for para in re.split(r"[\n\r]+", text):
        para = para.strip()
        if not para:
            continue
        for s in re.split(r"(?<=[。！？!?；;])", para):
            s = s.strip()
            if s:
                sentences.append(s)
    chunks: list[str] = []
    cur = ""
    for s in sentences:
        while len(s) > max_len * 2:      # 超长单句强切，避免一屏塞不下
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(s[:max_len])
            s = s[max_len:]
        if not cur:
            cur = s
        elif len(cur) + len(s) <= max_len:
            cur += s
        else:
            chunks.append(cur)
            cur = s
    if cur:
        chunks.append(cur)
    if len(chunks) > max_chunks:
        head = chunks[:max_chunks - 1]
        head.append("".join(chunks[max_chunks - 1:]))
        chunks = head
    return chunks


def _mux_av(video: Path, audio: Path, out: Path) -> bool:
    return fs._ff(["ffmpeg", "-y", "-i", str(video), "-i", str(audio),
                   "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest", str(out)])


def _to_mp3(src: Path, out: Path) -> bool:
    return fs._ff(["ffmpeg", "-y", "-i", str(src), "-vn",
                   "-c:a", "libmp3lame", "-q:a", "4", "-ar", "44100", "-ac", "1", str(out)])


def run_testimony_pipeline(job_id: str, *, title: str, text: str, scripture: str,
                           template: str, audio_path: Optional[Path],
                           use_elevenlabs: bool) -> None:
    """竖版见证短视频：图卡 → Ken Burns → 配音（录音优先）→ 拼接 → R2。

    画面用本文件的图卡渲染器（不烧任何生成式额度），动效/拼接/上传全部复用 film_studio。
    """
    job = fs.JOBS[job_id]
    job.update(status="running", steps=[], progress=0)
    fid = job_id[:8]
    slide_dir = TESTIMONY_SLIDE_DIR / fid
    slide_dir.mkdir(parents=True, exist_ok=True)
    try:
        chunks = _chunk_text(text)
        if not chunks:
            raise RuntimeError("见证正文为空")
        fs._log(job, f"📝 见证切分为 {len(chunks)} 屏", 5)

        specs: list[dict] = [{
            "template": template, "badge": "见证", "kicker": "生命改变的故事",
            "title": title, "footer": scripture or "", "sections": [],
        }]
        for i, ch in enumerate(chunks):
            specs.append({
                "template": template, "kicker": f"{i + 1} / {len(chunks)}",
                "title": ch, "footer": scripture or "", "sections": [],
            })
        job["story"] = {"title": title,
                        "scenes": [{"id": i + 1, "subtitle_zh": (s.get("title") or "")[:18]}
                                   for i, s in enumerate(specs)],
                        "spiritual_application": {}}

        fs._log(job, "🖼 渲染竖版图卡…", 10)
        images: list[Path] = []
        for i, spec in enumerate(specs):
            png = render_info_card(spec, width=VERTICAL[0], height=VERTICAL[1])
            p = slide_dir / f"slide_{i:02d}.png"
            p.write_bytes(png)
            images.append(p)

        # 录音见证优先：本人的声音比任何 TTS 都有说服力
        global_audio: Optional[Path] = None
        if audio_path is not None and audio_path.exists():
            conv = slide_dir / "voice.mp3"
            if _to_mp3(audio_path, conv) and conv.exists() and conv.stat().st_size > 256:
                global_audio = conv
                fs._log(job, f"🎙 使用上传的录音（{fs._audio_dur(conv):.1f}s）", 15)
            else:
                fs._log(job, "⚠️ 录音转码失败，改用 TTS 旁白")

        clips: list[Path] = []
        if global_audio is not None:
            total = max(3.0, fs._audio_dur(global_audio))
            per = max(2.5, total / len(images))
            for i, img in enumerate(images):
                base = 20 + int(i / len(images) * 60)
                fs._log(job, f"🎬 第 {i + 1}/{len(images)} 屏…", base)
                job["cur"] = i + 1
                vid = fs.CLIPS_DIR / f"{fid}_{i:02d}.mp4"
                fs.kenburns_clip(img, per, vid, zoom_in=(i % 2 == 0), size=VERTICAL)
                if vid.exists():
                    clips.append(vid)
        else:
            narrations = [f"{title}。{scripture}".strip("。 ")] + chunks
            for i, img in enumerate(images):
                base = 20 + int(i / len(images) * 60)
                fs._log(job, f"🎬 第 {i + 1}/{len(images)} 屏…", base)
                job["cur"] = i + 1
                aud = fs.AUDIO_DIR / f"{fid}_{i:02d}.mp3"
                narration = narrations[i] if i < len(narrations) else ""
                if narration:
                    asyncio.run(fs.tts_to_file(narration, aud, use_elevenlabs=use_elevenlabs))
                dur = fs._audio_dur(aud) if aud.exists() else 0.0
                dur = max(3.0, dur + 0.6) if dur else 4.0
                vid = fs.CLIPS_DIR / f"{fid}_{i:02d}.mp4"
                fs.kenburns_clip(img, dur, vid, zoom_in=(i % 2 == 0), size=VERTICAL)
                if aud.exists() and aud.stat().st_size > 256:
                    comp = fs.COMP_DIR / f"{fid}_{i:02d}.mp4"
                    if _mux_av(vid, aud, comp) and comp.exists() and comp.stat().st_size > 1024:
                        vid = comp
                if vid.exists():
                    clips.append(vid)

        if not clips:
            raise RuntimeError("没有可用片段")

        fs._log(job, "🔗 FFmpeg 拼接（竖版 1080x1920）…", 85)
        final = fs.FILM_DIR / f"{fid}_final.mp4"
        if not fs.concat_all(clips, final, fs.norm_vf(*VERTICAL)):
            raise RuntimeError("FFmpeg 拼接失败")

        if global_audio is not None:
            muxed = fs.FILM_DIR / f"{fid}_final_av.mp4"
            if _mux_av(final, global_audio, muxed) and muxed.exists() and muxed.stat().st_size > 1024:
                final.write_bytes(muxed.read_bytes())   # 保持 {fid}_final.mp4 命名，下载路由据此校验归属

        mb = round(final.stat().st_size / 1024 / 1024, 1)
        fs._log(job, f"✅ 拼接完成 {mb} MB", 92)

        r2_url = None
        try:
            fs._log(job, "☁️ 上传 R2…", 96)
            r2_url = fs.upload_r2(final, prefix=os.environ.get("R2_TESTIMONY_PREFIX", "testimony-clips/"))
            fs._log(job, f"✅ {r2_url}", 99)
        except Exception as exc:  # noqa: BLE001 — R2 未配置不该让整条流水线失败
            fs._log(job, f"⚠️ R2 跳过: {exc}")

        job.update(status="done", progress=100,
                   result={"file": final.name, "r2_url": r2_url, "mb": mb,
                           "scenes": len(clips), "aspect": "9:16",
                           "download_url": f"/api/film/download/{final.name}"})
        fs._log(job, "🎉 完成！")
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        job.update(status="error", error=str(exc))
        fs._log(job, f"❌ {exc}")


@router.post("/media/testimony-clip")
@limiter.limit("5/minute")
async def media_testimony_clip(
    request: Request,
    title: str = Form(..., max_length=80),
    text: str = Form(..., max_length=TESTIMONY_MAX_TEXT),
    scripture: str = Form("", max_length=120),
    template: str = Form("dawn", max_length=20),
    use_elevenlabs: bool = Form(False),
    audio: Optional[UploadFile] = File(None),
) -> dict:
    """见证 → 竖版短视频。异步返回 job_id，用 /api/media/testimony-clip/status/{job_id} 轮询。"""
    user = fs._require_film_user(request)
    title = title.strip()
    text = text.strip()
    if not title or not text:
        raise HTTPException(status_code=400, detail="标题与见证正文不能为空")
    if template not in CARD_TEMPLATES:
        raise HTTPException(status_code=400, detail=f"未知模板：{template}")

    # 与 /api/film/start 相同的并发守卫：同一台机器上并行跑 ffmpeg/付费 TTS = 双倍开销
    running = [j for j in fs.JOBS.values() if j.get("status") == "running"]
    if running:
        raise HTTPException(
            status_code=429,
            detail=f"已有任务在生成中（{running[0]['job_id'][:8]}…，进度 {running[0].get('progress', 0)}%），"
                   "请等它完成，避免重复扣费",
        )

    jid = str(uuid.uuid4())
    audio_path: Optional[Path] = None
    if audio is not None and audio.filename:
        content_type = (audio.content_type or "").split(";")[0].strip().lower()
        if content_type and not content_type.startswith("audio/"):
            raise HTTPException(status_code=415, detail="仅支持音频文件")
        blob = await audio.read(TESTIMONY_MAX_AUDIO_BYTES + 1)
        if len(blob) > TESTIMONY_MAX_AUDIO_BYTES:
            raise HTTPException(status_code=413, detail="录音文件过大")
        if blob:
            audio_path = fs.UPLOAD_DIR / f"{jid}_voice.bin"
            audio_path.write_bytes(blob)

    fs.JOBS[jid] = {"job_id": jid, "status": "queued", "progress": 0, "owner": user["email"],
                    "kind": "testimony-clip", "steps": [], "cur": 0,
                    "story": None, "result": None, "error": None}
    threading.Thread(
        target=run_testimony_pipeline,
        args=(jid,),
        kwargs={"title": title, "text": text, "scripture": scripture.strip(),
                "template": template, "audio_path": audio_path,
                "use_elevenlabs": bool(use_elevenlabs)},
        daemon=True,
    ).start()
    return {"job_id": jid, "status": "queued",
            "status_url": f"/api/media/testimony-clip/status/{jid}",
            "sse_url": f"/api/film/sse/{jid}"}


@router.get("/media/testimony-clip/status/{job_id}")
def media_testimony_clip_status(job_id: str, request: Request) -> dict:
    """与 /api/film/status/{jid} 同一份 JOBS 与同一套归属校验（SSE 也可直接用 /api/film/sse）。"""
    user = fs._require_film_user(request)
    job = fs.JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("owner") != user["email"]:
        raise HTTPException(status_code=403, detail="无权访问该任务")
    return job


# ══════════════════════════════════════════════════════════════════════════════
# 4) POST /api/media/illustrate —— Gemini 经文/场景配图（含内容护栏）
# ══════════════════════════════════════════════════════════════════════════════

# ── 护栏（audit §7 明确要求）───────────────────────────────────────────────────
# 1. 不生成基督的面容：历世历代教会对圣像的争议不是我们该用生成模型去"解决"的，
#    而且模型生成的"耶稣脸"必然带上训练数据的种族/审美偏见。
# 2. 不可视化创伤与自伤：把创伤画出来会造成二次暴露，自伤画面则有模仿风险。
#    这类请求应当被引导到 /api/crisis 的关怀路径，而不是被画出来。
_CHRIST_RE = re.compile(
    r"(耶稣|基督|主耶稣|救世主|救主|弥赛亚|人子|jesus|christ|messiah)", re.IGNORECASE)
_FACE_RE = re.compile(
    r"(脸|臉|面容|面孔|面貌|容貌|长相|樣貌|肖像|画像|畫像|头像|特写|正脸|正面像|五官|眼睛|微笑的"
    r"|face|facial|portrait|close[\s-]?up|headshot|visage|countenance|selfie|likeness)",
    re.IGNORECASE)
_DIVINE_FACE_RE = re.compile(r"(上帝|天父|真神|耶和华|神)的(脸|臉|面|面容|面孔|容貌|样子|模样)")
_TRAUMA_RE = re.compile(
    r"(自杀|自殺|自尽|轻生|自残|自傷|自伤|割腕|割脉|上吊|悬梁|跳楼|跳桥|服毒|吞药|吞藥|遗书|遺書"
    r"|尸体|屍體|遗体|血腥|虐待|家暴|家庭暴力|殴打致|凌虐|酷刑|刑求|强奸|強姦|性侵|猥亵|乱伦"
    r"|凶杀|谋杀|自焚|勒死|掐死|窒息死|断肢|残肢|伤痕累累|遍体鳞伤"
    r"|suicid|self[\s-]?harm|self[\s-]?injur|slit[\s\w]*wrist|cut[\s\w]*wrist|overdos|noose"
    r"|hang(ing)?\s+(my|him|her|them)self|corpse|dead\s+body|gore|gory|mutilat|dismember"
    r"|rape|sexual\s+assault|molest|incest|torture|domestic\s+violence|graphic\s+violence"
    r"|bleeding\s+out|blood[\s\w]*pool)",
    re.IGNORECASE)

_NO_CHRIST_FACE_DIRECTIVE = (
    "Never render the face or facial features of Jesus Christ. If He must appear, show Him only "
    "from behind, in silhouette, at a great distance, with the face out of frame, or represented "
    "by light, hands, footprints, or an empty space."
)


def illustration_guardrail(prompt: str) -> Optional[dict]:
    """命中护栏返回拒绝说明，否则返回 None。"""
    text = prompt or ""
    if _TRAUMA_RE.search(text):
        return {
            "code": "trauma_or_self_harm",
            "reason": "这个描述涉及创伤、暴力或自我伤害的画面，我们不生成这类图像。",
            "guidance": "把创伤画出来会造成二次暴露，自伤画面还有模仿风险。"
                        "如果此刻你或你关心的人正处在危险中，请用「危机关怀」（/api/crisis）里的"
                        "安全计划与本地热线，或立即联系可信任的人。需要配图时，可以改成盼望的意象："
                        "破晓的天光、被扶起的手、旷野中的水泉。",
        }
    if _DIVINE_FACE_RE.search(text) or (_CHRIST_RE.search(text) and _FACE_RE.search(text)):
        return {
            "code": "christ_face",
            "reason": "我们不生成基督（或神）的面容。",
            "guidance": "模型画出来的「耶稣脸」只是训练数据的平均值，会把某种族与审美当作定论，"
                        "也越过了教会历来对圣像的审慎。可以改成：背影、逆光剪影、远景、"
                        "只画手或脚踪、空的坟墓、被光照亮的众人。",
        }
    return None


class IllustrateRequest(BaseModel):
    prompt: str = Field(..., min_length=2, max_length=1200)
    reference: str = Field(default="", max_length=120)      # 经文出处，仅作元数据
    aspect_ratio: str = Field(default="4:5", max_length=8)
    style: str = Field(default="reverent illustration, painterly, soft natural light", max_length=120)
    historical_context: bool = True                          # 附加 film_studio 的一世纪美术设定


_ASPECTS = {"1:1", "3:4", "4:3", "9:16", "16:9", "4:5", "5:4", "2:3", "3:2"}
# Imagen 只认这 5 种，走兜底路径时映射过去
_IMAGEN_ASPECT = {"1:1": "1:1", "3:4": "3:4", "4:5": "3:4", "2:3": "3:4", "4:3": "4:3",
                  "5:4": "4:3", "3:2": "4:3", "9:16": "9:16", "16:9": "16:9"}


def _gemini_key() -> str:
    return (os.environ.get("GEMINI_API_KEY", "")
            or os.environ.get("GOOGLE_API_KEY", "")
            or os.environ.get("GEMINI_API_CHAT_KEY", "")).strip()


def _generate_illustration(prompt: str, aspect: str) -> tuple:
    """返回 (image_bytes, mime, model)。先 Gemini 图像模型，再 Imagen 兜底。

    契约按 google-genai(>=1.0,<2.0) 实测：
      · client.models.generate_content(...) → candidates[].content.parts[].inline_data.{data,mime_type}
      · client.models.generate_images(...)  → generated_images[].image.image_bytes / .rai_filtered_reason
    """
    key = _gemini_key()
    if not key:
        raise HTTPException(status_code=503, detail="未配置 GEMINI_API_KEY / GOOGLE_API_KEY，配图不可用")
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key)
    model = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

    cfg_kwargs: dict = {}
    modalities = os.environ.get("GEMINI_IMAGE_RESPONSE_MODALITIES", "").strip()
    if modalities:
        cfg_kwargs["response_modalities"] = [m.strip() for m in modalities.split(",") if m.strip()]
    try:
        # image_config 是较新 SDK 才有的字段；旧版本直接不传，让模型用默认比例
        config = types.GenerateContentConfig(
            image_config=types.ImageConfig(aspect_ratio=aspect), **cfg_kwargs)
    except Exception:  # noqa: BLE001
        config = types.GenerateContentConfig(**cfg_kwargs) if cfg_kwargs else None

    last_err: Optional[Exception] = None
    try:
        resp = client.models.generate_content(model=model, contents=prompt, config=config)
        for cand in (resp.candidates or []):
            for part in ((cand.content.parts if cand.content else None) or []):
                blob = getattr(part, "inline_data", None)
                if blob is not None and getattr(blob, "data", None):
                    return blob.data, (blob.mime_type or "image/png"), model
        last_err = RuntimeError("Gemini 未返回图像数据")
    except Exception as exc:  # noqa: BLE001
        if fs._is_spend_cap(exc):
            raise HTTPException(status_code=429, detail="Gemini 项目月度支出上限已满，请稍后再试") from exc
        last_err = exc
        logger.warning("[media] gemini image model failed (%s), trying Imagen", exc)

    imagen_model = os.environ.get("IMAGEN_MODEL", "imagen-4.0-generate-001")
    try:
        resp = client.models.generate_images(
            model=imagen_model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=_IMAGEN_ASPECT.get(aspect, "1:1"),
                output_mime_type="image/png",
            ),
        )
        for gen in (resp.generated_images or []):
            if getattr(gen, "rai_filtered_reason", None):
                raise HTTPException(status_code=422,
                                    detail=f"上游安全过滤拒绝了这个提示词：{gen.rai_filtered_reason}")
            image = getattr(gen, "image", None)
            if image is not None and getattr(image, "image_bytes", None):
                return image.image_bytes, (image.mime_type or "image/png"), imagen_model
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        if fs._is_spend_cap(exc):
            raise HTTPException(status_code=429, detail="Gemini 项目月度支出上限已满，请稍后再试") from exc
        last_err = exc
        logger.warning("[media] imagen fallback failed: %s", exc)

    raise HTTPException(status_code=502, detail=f"图像生成失败：{last_err}")


@router.post("/media/illustrate")
@limiter.limit("6/minute")
async def media_illustrate(payload: IllustrateRequest = Body(...), request: Request = None) -> dict:
    """经文/场景 AI 配图。命中护栏时返回 ok=false 的拒绝说明，不调用生成模型、不计费。"""
    fs._require_film_user(request)
    if payload.aspect_ratio not in _ASPECTS:
        raise HTTPException(status_code=400, detail=f"aspect_ratio 仅支持 {'/'.join(sorted(_ASPECTS))}")

    prompt = payload.prompt.strip()
    refusal = illustration_guardrail(f"{prompt} {payload.reference} {payload.style}")
    if refusal:
        logger.info("[media] illustrate refused: %s", refusal["code"])
        return {"ok": False, "refused": True, **refusal}

    mentions_christ = bool(_CHRIST_RE.search(prompt))
    pieces = [prompt]
    if payload.style:
        pieces.append(f"Style: {payload.style}.")
    if payload.historical_context:
        pieces.append(fs.FIRST_CENTURY_ISRAEL_VISUAL_CONTEXT)
    # 即便没命中拒绝规则，只要提到基督就把"不画面容"作为硬性画面指令带到生成边界
    if mentions_christ:
        pieces.append(_NO_CHRIST_FACE_DIRECTIVE)
    pieces.append("No text, no watermark, no logo, no gore, no distressing imagery.")
    full_prompt = " ".join(p.strip() for p in pieces if p and p.strip())

    key = _content_hash({"p": full_prompt, "a": payload.aspect_ratio,
                         "m": os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")})
    png_path = ILLUSTRATION_DIR / f"{key}.png"
    meta_path = ILLUSTRATION_DIR / f"{key}.json"

    if png_path.exists() and png_path.stat().st_size > 256 and meta_path.exists():
        try:                                     # 同一提示词不重复计费
            cached = json.loads(meta_path.read_text(encoding="utf-8"))
            cached["cached"] = True
            return cached
        except Exception:  # noqa: BLE001
            pass

    image_bytes, mime, model = await asyncio.to_thread(
        _generate_illustration, full_prompt, payload.aspect_ratio)
    png_path.write_bytes(image_bytes)

    r2_url = None
    try:
        r2_url = fs.upload_r2(png_path, prefix=os.environ.get("R2_ILLUSTRATION_PREFIX", "illustrations/"),
                              content_type=mime or "image/png")
    except Exception as exc:  # noqa: BLE001 — R2 未配置时退回本地取图路由
        logger.warning("[media] illustration R2 upload skipped: %s", exc)

    result = {
        "ok": True,
        "refused": False,
        "cached": False,
        "hash": key,
        "url": r2_url or f"/api/media/illustration/{key}.png",
        "r2_url": r2_url,
        "local_url": f"/api/media/illustration/{key}.png",
        "mime": mime or "image/png",
        "bytes": len(image_bytes),
        "model": model,
        "aspect_ratio": payload.aspect_ratio,
        "reference": payload.reference,
        "guardrail": {"christ_face_directive": mentions_christ},
    }
    meta_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result


@router.get("/media/illustration/{name}")
def media_illustration_file(name: str, request: Request) -> FileResponse:
    """R2 未配置（或 CDN 尚未同步）时的本地取图兜底。需登录，与 film 下载同口径。"""
    fs._require_film_user(request)
    if not _HASH_NAME_RE.match(name) or not name.endswith(".png"):
        raise HTTPException(status_code=404, detail="Image not found")
    p = ILLUSTRATION_DIR / name
    if not p.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(p), media_type="image/png",
                        headers={"Cache-Control": "private, max-age=86400"})
