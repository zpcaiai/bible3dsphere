"""
video_gen.py — 圣经短视频生成器
生成 9:16 竖屏 MP4（720×1280），适合微信视频号 / 抖音。

技术栈：Pillow + numpy + ffmpeg（系统）
TTS：优先 Google TTS REST API，可选 edge_tts 降级
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

import httpx
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ── 尺寸与帧率 ────────────────────────────────────────────────────────────────
W, H       = 720, 1280   # 9:16 竖屏
FPS        = 24
INTRO_SECS = 3.0
OUTRO_SECS = 2.5
MIN_VERSE  = 2.0         # 每节最少显示秒数
MAX_VERSES = 12          # 单次最多生成节数（防止视频过长）

# 深色属灵色板：(渐变顶色, 渐变底色, 强调色, 正文色)
PALETTES: List[Tuple] = [
    ((8,  14, 36), (18, 34, 68), (80,  160, 255), (210, 228, 255)),  # 深蓝·海
    ((18, 8,  38), (36, 16, 68), (160, 110, 255), (228, 215, 255)),  # 深紫·荣耀
    ((8,  28, 16), (14, 52, 28), (80,  210, 140), (208, 255, 225)),  # 深绿·生命
    ((28, 18, 6),  (52, 30, 10), (255, 188, 72),  (255, 244, 208)),  # 琥珀·智慧
    ((6,  22, 30), (12, 44, 56), (72,  220, 220), (208, 248, 255)),  # 深青·平安
]

_FONT_DIR = Path(__file__).parent / 'assets' / 'fonts'


# ── 字体管理 ──────────────────────────────────────────────────────────────────

def _ensure_font() -> Optional[str]:
    """返回可用的中文字体路径；必要时下载 WQY Microhei。"""
    candidates = [
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/arphic/uming.ttc',
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/STHeiti Light.ttc',
        'C:/Windows/Fonts/msyh.ttc',
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    # 尝试下载 WQY Microhei (~4 MB)
    font_path = _FONT_DIR / 'WenQuanYiMicroHei.ttf'
    if font_path.exists():
        return str(font_path)
    try:
        _FONT_DIR.mkdir(parents=True, exist_ok=True)
        import urllib.request
        url = ('https://github.com/anthonyfok/fonts-wqy-microhei'
               '/raw/master/WenQuanYiMicroHei.ttf')
        print(f'[video_gen] 下载中文字体 → {font_path}')
        urllib.request.urlretrieve(url, str(font_path))
        return str(font_path)
    except Exception as e:
        print(f'[video_gen] 字体下载失败: {e}')
        return None


_FONT_CACHE: dict = {}


def _font(size: int) -> ImageFont.FreeTypeFont:
    if size in _FONT_CACHE:
        return _FONT_CACHE[size]
    path = _ensure_font()
    f = ImageFont.truetype(path, size) if path else ImageFont.load_default()
    _FONT_CACHE[size] = f
    return f


# ── 帧绘制工具 ────────────────────────────────────────────────────────────────

def _clamp_rgb(t: Tuple) -> Tuple[int, int, int]:
    return tuple(max(0, min(255, int(v))) for v in t)  # type: ignore


def _gradient_bg(top: Tuple, bot: Tuple) -> np.ndarray:
    """生成顶底渐变背景数组 (H, W, 3)。"""
    t = np.linspace(0, 1, H).reshape(H, 1, 1)
    row = np.array(top) * (1 - t) + np.array(bot) * t   # (H, 1, 3)
    return np.tile(row.astype(np.uint8), (1, W, 1))      # (H, W, 3)


def _add_glow(arr: np.ndarray, cx: int, cy: int, r: int,
              color: Tuple, alpha: float = 0.20) -> np.ndarray:
    """添加径向软光晕。"""
    y_idx, x_idx = np.ogrid[:H, :W]
    dist = np.sqrt((x_idx - cx) ** 2 + (y_idx - cy) ** 2).astype(np.float32)
    mask = np.exp(-dist / r) * alpha                        # (H, W)
    glow = np.array(color, dtype=np.float32) * mask[:, :, None]
    return np.clip(arr.astype(np.float32) + glow, 0, 255).astype(np.uint8)


def _wrap_cn(text: str, max_chars: int = 15) -> List[str]:
    """中文按字符数折行（在标点处断行优先）。"""
    puncts = set('，。！？、；：—…」』')
    lines, buf = [], []
    for ch in text:
        buf.append(ch)
        if len(buf) >= max_chars and ch in puncts:
            lines.append(''.join(buf))
            buf = []
    if buf:
        lines.append(''.join(buf))
    return lines or [text]


def _draw_lines(draw: ImageDraw.Draw,
                lines: List[str],
                font: ImageFont.FreeTypeFont,
                cx: int, cy: int,
                fill: Tuple,
                line_gap: int = 16) -> None:
    """居中多行文字，带一像素黑色投影。"""
    line_h = [font.getbbox(l)[3] - font.getbbox(l)[1] for l in lines]
    total = sum(line_h) + line_gap * (len(lines) - 1)
    y = cy - total // 2
    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        lw = bbox[2] - bbox[0]
        x = cx - lw // 2
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0))
        draw.text((x, y), line, font=font, fill=fill)
        y += line_h[i] + line_gap


def _make_intro_frame(book: str, chapter: int, pal: int) -> np.ndarray:
    top, bot, accent, txt = PALETTES[pal]
    arr = _gradient_bg(top, bot)
    arr = _add_glow(arr, W // 2, H // 2, H // 3, accent, 0.22)
    img = Image.fromarray(arr)
    draw = ImageDraw.Draw(img)

    # 装饰横线
    lc = _clamp_rgb(tuple(c + 30 for c in accent))
    draw.line([(W // 2 - 120, H // 2 - 110), (W // 2 + 120, H // 2 - 110)],
              fill=lc, width=2)
    draw.line([(W // 2 - 120, H // 2 + 110), (W // 2 + 120, H // 2 + 110)],
              fill=lc, width=2)

    _draw_lines(draw, [book], _font(72), W // 2, H // 2 - 50, txt)
    _draw_lines(draw, [f'第 {chapter} 章'], _font(40), W // 2, H // 2 + 60,
                _clamp_rgb(tuple(c + 40 for c in accent)))
    _draw_lines(draw, ['属灵星球 · 圣经通读'], _font(22),
                W // 2, H - 80, (140, 150, 170))
    return np.array(img)


def _make_verse_frame(verse_num: int, verse_text: str,
                      ref: str, progress: float, pal: int) -> np.ndarray:
    """progress 0–1：章节整体进度。"""
    top, bot, accent, txt = PALETTES[pal]
    arr = _gradient_bg(top, bot)
    arr = _add_glow(arr, W // 2, H // 2 - 80, H // 4, accent, 0.16)
    img = Image.fromarray(arr)
    draw = ImageDraw.Draw(img)

    # 顶部经文参考
    draw.text((44, 56), ref, font=_font(26),
              fill=_clamp_rgb(tuple(c + 30 for c in accent)))

    # 节码徽章（小圆圈）
    badge_cy = 160
    r = 30
    draw.ellipse([(W // 2 - r, badge_cy - r), (W // 2 + r, badge_cy + r)],
                 fill=_clamp_rgb(tuple(c // 5 for c in accent)))
    vnum_str = str(verse_num)
    vbbox = _font(26).getbbox(vnum_str)
    draw.text((W // 2 - (vbbox[2] - vbbox[0]) // 2,
               badge_cy - (vbbox[3] - vbbox[1]) // 2),
              vnum_str, font=_font(26), fill=accent)

    # 经文正文（居中，自动折行）
    lines = _wrap_cn(verse_text, max_chars=15)
    _draw_lines(draw, lines, _font(44), W // 2, H // 2 + 40, txt, line_gap=18)

    # 底部进度条
    bar_y, bx0, bx1 = H - 60, 60, W - 60
    draw.rectangle([(bx0, bar_y), (bx1, bar_y + 3)], fill=(60, 65, 80))
    prog_x = bx0 + int((bx1 - bx0) * max(0.0, min(1.0, progress)))
    if prog_x > bx0:
        draw.rectangle([(bx0, bar_y), (prog_x, bar_y + 3)], fill=accent)

    return np.array(img)


def _make_outro_frame(pal: int) -> np.ndarray:
    top, bot, accent, txt = PALETTES[pal]
    arr = _gradient_bg(top, bot)
    arr = _add_glow(arr, W // 2, H // 2, H // 3, accent, 0.22)
    img = Image.fromarray(arr)
    draw = ImageDraw.Draw(img)
    lc = _clamp_rgb(tuple(c + 30 for c in accent))
    draw.line([(W // 2 - 120, H // 2 - 80), (W // 2 + 120, H // 2 - 80)],
              fill=lc, width=2)
    _draw_lines(draw, ['愿神的话语', '住在你心中'], _font(52),
                W // 2, H // 2 + 10, txt, line_gap=20)
    _draw_lines(draw, ['属灵星球 · 圣经通读'], _font(24),
                W // 2, H // 2 + 150, (140, 150, 170))
    return np.array(img)


# ── TTS 音频生成 ───────────────────────────────────────────────────────────────

async def _tts_google(text: str, api_key: str) -> bytes:
    """Google TTS REST API → MP3 字节。"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f'https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}',
            json={
                'input': {'text': text},
                'voice': {
                    'languageCode': 'cmn-CN',
                    'name': 'cmn-CN-Wavenet-A',
                    'ssmlGender': 'FEMALE',
                },
                'audioConfig': {
                    'audioEncoding': 'MP3',
                    'speakingRate': 0.85,
                    'pitch': 0.0,
                },
            },
        )
        resp.raise_for_status()
    return base64.b64decode(resp.json()['audioContent'])


async def _tts_edge(text: str) -> bytes:
    """edge_tts XiaoxiaoNeural → MP3 字节（备用）。"""
    import edge_tts  # 可选依赖
    buf = io.BytesIO()
    communicate = edge_tts.Communicate(text, voice='zh-CN-XiaoxiaoNeural', rate='-5%')
    async for chunk in communicate.stream():
        if chunk['type'] == 'audio':
            buf.write(chunk['data'])
    return buf.getvalue()


async def _generate_audio(text: str, api_key: Optional[str]) -> Optional[bytes]:
    """尝试 Google TTS → edge_tts → 返回 None（无声）。"""
    if api_key:
        try:
            return await _tts_google(text, api_key)
        except Exception as e:
            print(f'[video_gen] Google TTS 失败: {e}')
    try:
        return await _tts_edge(text)
    except Exception as e:
        print(f'[video_gen] edge_tts 失败: {e}')
    return None


# ── ffmpeg 工具 ───────────────────────────────────────────────────────────────

def _audio_duration(path: str) -> float:
    """用 ffprobe 读取音频时长（秒）。"""
    try:
        r = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json',
             '-show_streams', path],
            capture_output=True, text=True, timeout=10,
        )
        for s in json.loads(r.stdout).get('streams', []):
            if 'duration' in s:
                return float(s['duration'])
    except Exception:
        pass
    return 0.0


def _encode_video(frames_dir: str, out_path: str) -> None:
    """将 frames_dir/frame_*.png 编码为无音频 MP4。"""
    subprocess.run(
        ['ffmpeg', '-y',
         '-framerate', str(FPS),
         '-i', os.path.join(frames_dir, 'frame_%06d.png'),
         '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
         '-pix_fmt', 'yuv420p', out_path],
        check=True, capture_output=True,
    )


def _mux(video: str, audio: str, out_path: str) -> None:
    """合并视频 + 音频。"""
    subprocess.run(
        ['ffmpeg', '-y',
         '-i', video, '-i', audio,
         '-c:v', 'copy', '-c:a', 'aac', '-shortest', out_path],
        check=True, capture_output=True,
    )


def _concat_audio(audio_paths: List[str], out_path: str, tmp: Path) -> None:
    """按顺序拼接多段 MP3。"""
    lst = tmp / '_concat.txt'
    lst.write_text('\n'.join(f"file '{p}'" for p in audio_paths))
    subprocess.run(
        ['ffmpeg', '-y',
         '-f', 'concat', '-safe', '0', '-i', str(lst),
         '-c', 'copy', out_path],
        check=True, capture_output=True,
    )


# ── 主入口 ────────────────────────────────────────────────────────────────────

async def generate_bible_video(
    book: str,
    chapter: int,
    verses: List[dict],       # [{'verse': int, 'text': str}, ...]
    api_key: Optional[str] = None,
) -> bytes:
    """
    生成圣经章节短视频，返回 MP4 字节。
    verses 建议 ≤ MAX_VERSES 节，避免视频过长。
    """
    if not verses:
        raise ValueError('verses 不能为空')
    verses = verses[:MAX_VERSES]

    # 章节哈希决定色板，同章永远同色
    pal = abs(hash(f'{book}{chapter}')) % len(PALETTES)

    with tempfile.TemporaryDirectory() as _tmp:
        tmp = Path(_tmp)
        frames_dir = tmp / 'frames'
        frames_dir.mkdir()

        # ── 1. 并发生成各节 TTS 音频 ─────────────────────────────────────
        print(f'[video_gen] TTS × {len(verses)} 节...', flush=True)
        audio_tasks = [_generate_audio(v['text'], api_key) for v in verses]
        audio_results = await asyncio.gather(*audio_tasks, return_exceptions=True)

        audio_paths: List[Optional[str]] = []
        durations: List[float] = []
        for i, (v, result) in enumerate(zip(verses, audio_results)):
            ap = None
            if isinstance(result, bytes) and result:
                ap = str(tmp / f'a{i:03d}.mp3')
                Path(ap).write_bytes(result)
            audio_paths.append(ap)
            if ap:
                d = _audio_duration(ap)
                durations.append(max(d, MIN_VERSE))
            else:
                # 无 TTS：按字数估算（150字/分钟）
                durations.append(max(MIN_VERSE, len(v['text']) / 150 * 60))

        # ── 2. 拼接完整音轨 ───────────────────────────────────────────────
        valid_audios = [ap for ap in audio_paths if ap]
        full_audio: Optional[str] = None
        if valid_audios:
            full_audio = str(tmp / 'full.mp3')
            _concat_audio(valid_audios, full_audio, tmp)

        # ── 3. 渲染视频帧（每节一张静帧，用硬链接复用） ─────────────────
        print('[video_gen] 渲染帧...', flush=True)
        frame_idx = 0
        total_secs = sum(durations)

        def save_static(arr: np.ndarray, n_frames: int) -> None:
            nonlocal frame_idx
            base = frames_dir / f'base_{frame_idx:06d}.png'
            Image.fromarray(arr).save(str(base))
            for _ in range(n_frames):
                dest = frames_dir / f'frame_{frame_idx:06d}.png'
                try:
                    os.link(str(base), str(dest))
                except OSError:
                    import shutil
                    shutil.copy2(str(base), str(dest))
                frame_idx += 1
            os.unlink(str(base))  # 删除 base，只保留 frame_ 文件

        # Intro
        save_static(_make_intro_frame(book, chapter, pal),
                    int(INTRO_SECS * FPS))

        # 各节
        cum = 0.0
        for i, v in enumerate(verses):
            ref = f'{book} {chapter}:{v["verse"]}'
            progress = (cum + durations[i] / 2) / total_secs if total_secs > 0 else 0
            arr = _make_verse_frame(v['verse'], v['text'], ref, progress, pal)
            save_static(arr, max(1, int(durations[i] * FPS)))
            cum += durations[i]

        # Outro
        save_static(_make_outro_frame(pal), int(OUTRO_SECS * FPS))

        # ── 4. ffmpeg 编码 ────────────────────────────────────────────────
        print('[video_gen] ffmpeg 编码...', flush=True)
        silent = str(tmp / 'silent.mp4')
        _encode_video(str(frames_dir), silent)

        final = str(tmp / 'final.mp4')
        if full_audio:
            _mux(silent, full_audio, final)
        else:
            os.rename(silent, final)

        print('[video_gen] 完成 ✓', flush=True)
        return Path(final).read_bytes()
