#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
列出 ElevenLabs 里适合中文（且优美自然）的女声，方便挑一个填进
ELEVENLABS_VOICE_ID。

用法：
    export ELEVENLABS_API_KEY=你的key
    python3 scripts/list_elevenlabs_zh_voices.py            # 默认：女声 + 中文
    python3 scripts/list_elevenlabs_zh_voices.py --all      # 不限性别
    python3 scripts/list_elevenlabs_zh_voices.py --mine     # 同时列出你账号已添加的音色
    python3 scripts/list_elevenlabs_zh_voices.py --limit 40 # 多列一些

说明：
  · 中英双语建议用多语模型 eleven_multilingual_v2 —— 同一音色自动按文本切换
    中/英，音色统一，所以一个多语女声就同时覆盖 EN 模式，无需再选英文女声。
  · 脚本从 ElevenLabs「共享音色库」按 language=zh 拉取，并附试听链接 preview_url，
    你点开听满意了，把对应 voice_id 复制到 .env 的 ELEVENLABS_VOICE_ID 即可。
"""
import argparse
import os
import sys
import urllib.request
import urllib.parse
import json

API = "https://api.elevenlabs.io"


def _get(path: str, params: dict, key: str) -> dict:
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"xi-api-key": key, "accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _row(name, vid, gender, lang, desc, preview):
    name = (name or "")[:18].ljust(18)
    gender = (gender or "?")[:6].ljust(6)
    lang = (lang or "")[:10].ljust(10)
    desc = (desc or "").replace("\n", " ")[:40]
    print(f"  {name} {gender} {lang} {vid:<24} {desc}")
    if preview:
        print(f"      试听: {preview}")


def list_shared(key: str, gender: str | None, limit: int) -> None:
    params = {"page_size": min(limit, 100), "language": "zh"}
    if gender:
        params["gender"] = gender
    try:
        data = _get("/v1/shared-voices", params, key)
    except Exception as e:  # noqa: BLE001
        print(f"[!] 拉取共享音色库失败：{e}", file=sys.stderr)
        return
    voices = data.get("voices", [])[:limit]
    if not voices:
        print("  （没拉到结果，可改用 --all 放宽性别，或加大 --limit）")
        return
    print(f"\n=== 共享音色库 · 支持中文{('· ' + gender) if gender else ''} · 共 {len(voices)} 个 ===")
    print(f"  {'名字':<18} {'性别':<6} {'语言':<10} {'voice_id':<24} 描述")
    for v in voices:
        labels = v.get("labels", {}) or {}
        _row(
            v.get("name"),
            v.get("voice_id", ""),
            v.get("gender") or labels.get("gender"),
            v.get("language") or labels.get("language") or labels.get("accent"),
            v.get("description") or labels.get("description") or labels.get("use_case"),
            v.get("preview_url"),
        )


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
        _row(
            v.get("name"),
            v.get("voice_id", ""),
            labels.get("gender"),
            labels.get("language") or labels.get("accent"),
            labels.get("description") or labels.get("use_case"),
            v.get("preview_url"),
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="列出适合中文的 ElevenLabs 女声")
    ap.add_argument("--all", action="store_true", help="不限性别（默认只列女声）")
    ap.add_argument("--mine", action="store_true", help="同时列出账号已添加的音色")
    ap.add_argument("--limit", type=int, default=25, help="最多列出多少个（默认 25）")
    args = ap.parse_args()

    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        print("✗ 未设置 ELEVENLABS_API_KEY。先：export ELEVENLABS_API_KEY=你的key", file=sys.stderr)
        return 1

    gender = None if args.all else "female"
    list_shared(key, gender, args.limit)
    if args.mine:
        list_mine(key)

    print("\n挑好后：把 voice_id 填到 .env 的 ELEVENLABS_VOICE_ID，")
    print("并保持 ELEVENLABS_MODEL=eleven_multilingual_v2（中英双语共用一个音色）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
