#!/usr/bin/env python3
"""
大卫与歌利亚圣经电影批量生成脚本
Pipeline:
  Claude API  →  25个精细化镜头Prompt（JSON）
       ↓
  Veo 3.1 API →  25个MP4片段（并发轮询）
       ↓
  FFmpeg       →  合成约3分钟完整电影

依赖安装：
  pip install anthropic google-genai httpx
  brew install ffmpeg   (macOS)  /  apt install ffmpeg  (Linux)

运行前设置环境变量：
  export ANTHROPIC_API_KEY="sk-ant-..."
  export GEMINI_API_KEY="AIza..."
"""

import os
import sys
import time
import json
import subprocess
import re
from pathlib import Path
import httpx
import anthropic
from google import genai
from google.genai import types

# ── 配置 ──────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY", "")

OUTPUT_DIR  = Path("./david_goliath_output")
CLIPS_DIR   = OUTPUT_DIR / "clips"
PROMPTS_FILE = OUTPUT_DIR / "scene_prompts.json"
FINAL_VIDEO = OUTPUT_DIR / "david_goliath_final.mp4"

NUM_SCENES        = 25
POLL_INTERVAL_SEC = 15   # 轮询间隔
MAX_WAIT_SEC      = 600  # 单个片段最长等待时间
MAX_RETRIES       = 2    # 生成失败重试次数

# ── 主故事板（供Claude细化用）────────────────────────────────────────────────
MASTER_STORYBOARD = """
Biblical film: David and Goliath. Ancient Israel ~1000 BC.

Global style: cinematic 4K, realistic historical setting, family-friendly Christian educational,
warm natural golden-hour lighting, dramatic camera movement, consistent characters throughout,
highly detailed period-accurate costumes, realistic human motion, volumetric lighting,
epic film quality, 16:9 aspect ratio. NO subtitles, NO text, NO watermarks.

Main characters (must be consistent in every scene):
- David: young shepherd ~16 years old, humble and courageous expression, wavy brown hair,
  simple earth-tone shepherd tunic belted at waist, leather sandals, carries wooden shepherd staff,
  a leather sling hangs at his belt.
- Goliath: enormous Philistine giant, visually at least 3× taller than David, full bronze scale
  armor, bronze helmet with horsehair crest, massive bronze spear, large bronze shield, menacing
  but not demonic face, commanding physical presence.

Scene storyboard (25 scenes total):
1.  Dawn sunrise over Bethlehem hills. David leads sheep across green rolling hills. Peaceful.
2.  David sits on a rock playing his lyre/harp while sheep graze. Calm worshipful atmosphere.
3.  A lion lunges at a lamb. David sprints forward, grabs the lion, wrestles it away. Hero moment.
4.  Wide shot: Valley of Elah. Two armies face each other across the valley. Tense standoff.
5.  Philistine army camp. Goliath emerges from the crowd, walks forward, raises spear, shouts challenge.
6.  Israelite soldiers flinch and step backward in fear. King Saul watches from elevated position.
7.  David arrives at the Israelite camp, carrying a sack of food, searches for his brothers.
8.  David hears Goliath's challenge. His expression shifts from curiosity to bold determination.
9.  David stands before King Saul in the royal tent, gesturing confidently, telling of the lion and bear.
10. King Saul nods and gestures—permission granted. David's face shows grateful resolve.
11. David tries on Saul's heavy bronze armor. He removes it piece by piece—it's too cumbersome.
12. David kneels at a flowing stream. He carefully picks up five smooth round stones, holds them up.
13. David walks alone across the open valley toward Goliath. Long shot, small figure, vast landscape.
14. Goliath looks down at David and laughs loudly, mocking gesture with his massive hand.
15. David stands firm, raises one hand toward the sky, declares boldly. Close-up of his determined face.
16. David reaches into his shepherd's bag, places a stone into the sling, begins swinging it overhead.
17. Dramatic slow motion: stone arcs through the sky. Close-up of spinning stone mid-flight.
18. Stone strikes Goliath's forehead. Impact moment. Goliath's expression shifts from mocking to shock.
19. Goliath falls in slow motion, massive body hitting the ground, dust rising, earth shaking.
20. Israelite army erupts in celebration, soldiers raising swords and cheering, rushing forward.
21. David stands alone on the battlefield after victory. Calm, humble, head slightly bowed.
22. Golden sunset over the hills of Israel. Silhouette of shepherd on a hilltop with sheep.
23. Overhead aerial view of green Judean hills as the light fades to warm gold.
24. David looks toward the sky from a hillside, face full of gratitude and peace.
25. Final frame: a single oil lamp burning in the darkness. Fade to black. Hopeful and inspiring.
"""


# ── 1. Claude → 25 精细化 Prompt ─────────────────────────────────────────────

def generate_scene_prompts() -> list[dict]:
    """调用 Claude 生成 25 个 Veo-优化的镜头 Prompt。"""
    if PROMPTS_FILE.exists():
        print(f"[INFO] 发现已有 Prompt 文件 {PROMPTS_FILE}，直接加载")
        with open(PROMPTS_FILE) as f:
            return json.load(f)

    print("[STEP 1] 调用 Claude 生成 25 个镜头 Prompt …")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    system = (
        "You are a professional cinematic prompt engineer specializing in AI video generation (Veo 3). "
        "Your task: take a storyboard and expand each scene into a detailed, self-contained Veo 3 prompt. "
        "Each prompt must be 3-5 sentences, include: camera movement, lighting, character description, "
        "action, emotion, and cinematography style. Always end with: "
        "'16:9 aspect ratio, 4K cinematic quality, realistic lighting, no text, no subtitles.' "
        "Return ONLY a valid JSON array of 25 objects: "
        '[{"scene": 1, "title": "...", "prompt": "..."}, ...]'
    )

    user = (
        f"Expand this 25-scene storyboard into 25 Veo 3 video generation prompts.\n\n"
        f"{MASTER_STORYBOARD}\n\n"
        "Return only a JSON array. No markdown fences, no explanation."
    )

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=8192,
        messages=[{"role": "user", "content": user}],
        system=system,
    )

    raw = message.content[0].text.strip()
    # 去掉可能的 markdown 代码块
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    scenes = json.loads(raw)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
        json.dump(scenes, f, ensure_ascii=False, indent=2)

    print(f"[OK] 生成 {len(scenes)} 个 Prompt，已保存至 {PROMPTS_FILE}")
    return scenes


# ── 2. Veo 3.1 → MP4 ─────────────────────────────────────────────────────────

def download_video(uri: str, dest: Path, api_key: str) -> bool:
    """从 Google 存储 URI 下载视频。"""
    try:
        # 先尝试直接下载（签名 URL）
        headers = {}
        url = uri
        # 如果是 googleapis.com，附加 API Key
        if "googleapis.com" in uri and "key=" not in uri:
            sep = "&" if "?" in uri else "?"
            url = f"{uri}{sep}key={api_key}"

        with httpx.Client(timeout=120, follow_redirects=True) as client:
            with client.stream("GET", url, headers=headers) as resp:
                resp.raise_for_status()
                dest.parent.mkdir(parents=True, exist_ok=True)
                with open(dest, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=65536):
                        f.write(chunk)
        print(f"  [↓] 下载完成 → {dest.name}")
        return True
    except Exception as e:
        print(f"  [ERR] 下载失败: {e}")
        return False


def generate_clip(veo_client: genai.Client, scene: dict, output_path: Path) -> bool:
    """调用 Veo 3.1 生成单个视频片段，轮询等待，下载到 output_path。"""
    scene_num = scene["scene"]
    prompt    = scene["prompt"]

    print(f"\n[Scene {scene_num:02d}/{NUM_SCENES}] {scene.get('title', '')}")
    print(f"  Prompt: {prompt[:100]}…")

    for attempt in range(1, MAX_RETRIES + 2):
        try:
            operation = veo_client.models.generate_videos(
                model="veo-3.1-generate-preview",
                prompt=prompt,
                config=types.GenerateVideosConfig(
                    aspect_ratio="16:9",
                    video_format="mp4",
                ),
            )

            waited = 0
            while not operation.done:
                time.sleep(POLL_INTERVAL_SEC)
                waited += POLL_INTERVAL_SEC
                operation = veo_client.operations.get(operation)
                print(f"  ⏳ 等待中 … {waited}s", end="\r")
                if waited >= MAX_WAIT_SEC:
                    print(f"\n  [WARN] 等待超时 ({MAX_WAIT_SEC}s)")
                    break

            print()  # 换行

            if not operation.done or not operation.result:
                raise RuntimeError("操作未完成或无结果")

            videos = operation.result.generated_videos
            if not videos:
                raise RuntimeError("结果中无视频")

            video_uri = videos[0].video.uri
            print(f"  [URI] {video_uri[:80]}…")

            if download_video(video_uri, output_path, GEMINI_API_KEY):
                return True

        except Exception as e:
            print(f"  [ERR] 第 {attempt} 次尝试失败: {e}")
            if attempt <= MAX_RETRIES:
                sleep_sec = 30 * attempt
                print(f"  [RETRY] {sleep_sec}s 后重试…")
                time.sleep(sleep_sec)
            else:
                print(f"  [SKIP] Scene {scene_num} 跳过")
                return False

    return False


# ── 3. FFmpeg → 合成最终视频 ──────────────────────────────────────────────────

def concat_clips(clip_paths: list[Path], output: Path) -> bool:
    """使用 FFmpeg concat demuxer 合成所有片段。"""
    concat_list = output.parent / "concat_list.txt"
    valid = [p for p in clip_paths if p.exists() and p.stat().st_size > 1024]

    if not valid:
        print("[ERR] 没有有效的视频片段可合成")
        return False

    with open(concat_list, "w") as f:
        for p in valid:
            f.write(f"file '{p.resolve()}'\n")

    print(f"\n[STEP 3] FFmpeg 合成 {len(valid)} 个片段 → {output.name} …")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",           # 高质量
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERR] FFmpeg 失败:\n{result.stderr[-2000:]}")
        return False

    size_mb = output.stat().st_size / 1024 / 1024
    print(f"[OK] 最终视频: {output}  ({size_mb:.1f} MB)")
    return True


# ── 主流程 ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("大卫与歌利亚圣经电影生成脚本")
    print("=" * 60)

    # 检查 API Key
    missing = []
    if not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if missing:
        print(f"[ERR] 缺少环境变量: {', '.join(missing)}")
        sys.exit(1)

    # 检查 FFmpeg
    if subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode != 0:
        print("[ERR] 未找到 ffmpeg，请先安装: brew install ffmpeg")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Claude 生成 25 个 Prompt
    scenes = generate_scene_prompts()
    if len(scenes) != NUM_SCENES:
        print(f"[WARN] 期望 {NUM_SCENES} 个场景，实际 {len(scenes)} 个")

    # Step 2: Veo 3.1 生成 25 个视频片段
    print(f"\n[STEP 2] 开始生成 {len(scenes)} 个视频片段 …")
    veo_client = genai.Client(api_key=GEMINI_API_KEY)

    clip_paths = []
    failed_scenes = []

    for scene in scenes:
        n = scene["scene"]
        clip_path = CLIPS_DIR / f"scene_{n:02d}.mp4"
        clip_paths.append(clip_path)

        if clip_path.exists() and clip_path.stat().st_size > 1024:
            print(f"[SKIP] Scene {n:02d} 已存在，跳过生成")
            continue

        success = generate_clip(veo_client, scene, clip_path)
        if not success:
            failed_scenes.append(n)

        # 礼貌性延迟，避免触发速率限制
        if n < len(scenes):
            time.sleep(5)

    # 报告
    total    = len(scenes)
    ok_count = sum(1 for p in clip_paths if p.exists() and p.stat().st_size > 1024)
    print(f"\n[SUMMARY] 生成完成: {ok_count}/{total} 个片段成功")
    if failed_scenes:
        print(f"  失败的场景: {failed_scenes}")

    # Step 3: FFmpeg 合成
    if ok_count == 0:
        print("[ERR] 没有成功生成的片段，退出")
        sys.exit(1)

    success = concat_clips(clip_paths, FINAL_VIDEO)
    if success:
        print(f"\n✅ 完成！最终视频: {FINAL_VIDEO.resolve()}")
    else:
        print("\n❌ 合成失败，请检查日志")
        sys.exit(1)


if __name__ == "__main__":
    main()
