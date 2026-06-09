#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
列出 ElevenLabs 里适合中文（且优美自然）的女声，方便挑一个填进
ELEVENLABS_VOICE_ID。

用法：
    export ELEVENLABS_API_KEY=你的key
    python3 scripts/list_elevenlabs_zh_voices.py            # 默认：女声 + 中文
    python3 scripts/list_elevenlabs_zh_voices.py --all      # 不限性别
    python3 scripts/list_elevenlabs_zh_voices.py --mine     # 列出你账号已添加的音色
    python3 scripts/list_elevenlabs_zh_voices.py --builtin  # 仅列内置推荐(免联网/免权限)
    python3 scripts/list_elevenlabs_zh_voices.py --limit 40

说明：
  · 中英双语建议用多语模型 eleven_multilingual_v2 —— 同一音色自动按文本切换
    中/英，音色统一，所以一个多语女声就同时覆盖 EN 模式，无需再选英文女声。
  · 共享音色库需要 key 具备「Voices: Read」权限；受限 key 会返回 401。
    读不到也没关系：下面 --builtin 的内置音色都是 ElevenLabs 自带的多语女声，
    任何账号都能直接用，把 voice_id 填进 .env 即可。
"""
import argparse
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
import json

API = "https://api.elevenlabs.io"

# 内置：ElevenLabs 自带 premade 多语女声（eleven_multilingual_v2 下中文表现自然）。
# 这些 voice_id 对所有账号可用，无需读取共享库。
BUILTIN = [
    ("Matilda",   "XrExE9yKIg1WjnnlVkGX", "温暖、知性，适合朗读/旁白"),
    ("Sarah",     "EXAVITQu4vr4xnSDxMaL", "柔和、亲切，年轻女声"),
    ("Charlotte", "XB0fDUnXU5powFXDhCwa", "温柔、略带气声，抒情"),
    ("Alice",     "Xb7hH8MSUJpSbSDYk0k2", "清晰、稳重，播报/朗读"),
    ("Lily",      "pFZP5JQG7iQjIQuC4Bku", "温暖、舒缓，适合冥想/灵修"),
    ("Jessica",   "cgSgspJ2msm6clMCkdW9", "自然、有亲和力"),
]


def _get(path: str, params: dict, key: str) -> dict:
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"xi-api-key": key, "accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _row(name, vid, gender, lang, desc, preview=None):
    name = (name or "")[:18].ljust(18)
    gender = (gender or "?")[:6].ljust(6)
    lang = (lang or "")[:10].ljust(10)
    desc = (desc or "").replace("\n", " ")[:42]
    print(f"  {name} {gender} {lang} {vid:<24} {desc}")
    if preview:
        print(f"      试听: {preview}")


def print_builtin() -> None:
    print("\n=== 内置推荐 · 多语女声（任何账号可直接用）===")
    print(f"  {'名字':<18} {'性别':<6} {'语言':<10} {'voice_id':<24} 描述")
    for name, vid, desc in BUILTIN:
        _row(name, vid, "female", "multi", desc)


def validate_key(key: str) -> bool:
    """用 /v1/voices 验 key 是否有效；返回 True=有效。"""
    try:
        _get("/v1/voices", {}, key)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("✗ key 无效或被拒（/v1/voices 返回 401）。请检查：", file=sys.stderr)
            print("  1) key 是否复制完整、无多余空格/引号；", file=sys.stderr)
            print("  2) 是否已在 ElevenLabs → Settings → API Keys 重新生成并启用；", file=sys.stderr)
            print("  3) 若用的是受限(restricted) key，给它勾上 Voices: Read 权限，", file=sys.stderr)
            print("     或改用无限制 key。", file=sys.stderr)
            return False
        print(f"✗ 验证 key 时出错：HTTP {e.code}", file=sys.stderr)
        return False
    except Exception as e:  # noqa: BLE001
        print(f"✗ 验证 key 时网络出错：{e}", file=sys.stderr)
        return False


def list_shared(key: str, gender, limit: int) -> bool:
    params = {"page_size": min(limit, 100), "language": "zh"}
    if gender:
        params["gender"] = gender
    try:
        data = _get("/v1/shared-voices", params, key)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("\n[!] 你的 key 读不了共享音色库（401，通常是权限不含 Voices: Read）。", file=sys.stderr)
            print("    没关系，直接用下面的内置推荐即可。", file=sys.stderr)
        else:
            print(f"\n[!] 拉取共享音色库失败：HTTP {e.code}", file=sys.stderr)
        return False
    except Exception as e:  # noqa: BLE001
        print(f"\n[!] 拉取共享音色库失败：{e}", file=sys.stderr)
        return False
    voices = data.get("voices", [])[:limit]
    if not voices:
        print("  （共享库没返回中文结果，可加 --all 放宽性别，或看内置推荐）")
        return False
    print(f"\n=== 共享音色库 · 支持中文{('· ' + gender) if gender else ''} · 共 {len(voices)} 个 ===")
    print(f"  {'名字':<18} {'性别':<6} {'语言':<10} {'voice_id':<24} 描述")
    for v in voices:
        labels = v.get("labels", {}) or {}
        _row(v.get("name"), v.get("voice_id", ""),
             v.get("gender") or labels.get("gender"),
             v.get("language") or labels.get("language") or labels.get("accent"),
             v.get("description") or labels.get("description") or labels.get("use_case"),
             v.get("preview_url"))
    return True


def list_mine(key: str) -> None:
    try:
        data = _get("/v1/voices", {}, key)
    except Exception as e:  # noqa: BLE001
        print(f"[!] 拉取账号音色失败：{e}", file=sys.stderr)
        return
    voices = data.get("voices", [])
    print(f"\n=== 你账号里已添加的音色 · 共 {len(voices)} 个（多语模型下都能读中文）===")
    print(f"  {'名字':<18} {'性别':<6} {'语言':<10} {'voice_id':<24} 描述")
    for v in voices:
        labels = v.get("labels", {}) or {}
        _row(v.get("name"), v.get("voice_id", ""),
             labels.get("gender"),
             labels.get("language") or labels.get("accent"),
             labels.get("description") or labels.get("use_case"),
             v.get("preview_url"))


def main() -> int:
    ap = argparse.ArgumentParser(description="列出适合中文的 ElevenLabs 女声")
    ap.add_argument("--all", action="store_true", help="不限性别（默认只列女声）")
    ap.add_argument("--mine", action="store_true", help="同时列出账号已添加的音色")
    ap.add_argument("--builtin", action="store_true", help="只看内置推荐（免联网/免权限）")
    ap.add_argument("--limit", type=int, default=25, help="共享库最多列多少个（默认 25）")
    args = ap.parse_args()

    if args.builtin:
        print_builtin()
        return 0

    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        print("✗ 未设置 ELEVENLABS_API_KEY。先：export ELEVENLABS_API_KEY=你的key", file=sys.stderr)
        print("  （或先用 --builtin 看内置推荐，不需要 key）", file=sys.stderr)
        return 1

    # 先验证 key；失败则只给内置推荐
    if not validate_key(key):
        print_builtin()
        return 1

    print("✓ key 有效。")
    ok = list_shared(key, None if args.all else "female", args.limit)
    if not ok:
        print_builtin()
    if args.mine:
        list_mine(key)

    print("\n挑好后：把 voice_id 填到 .env 的 ELEVENLABS_VOICE_ID，")
    print("并保持 ELEVENLABS_MODEL=eleven_multilingual_v2（中英双语共用一个音色）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
