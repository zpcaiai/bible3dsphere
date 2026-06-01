#!/usr/bin/env bash
# 备选：用 Cloudflare 官方 wrangler 上传（无需 aws-cli）。先： npm i -g wrangler && wrangler login
#   export R2_BUCKET=biblesphere-hymns
#   export R2_PREFIX=hymns
#   bash scripts/hymns/upload_to_r2_wrangler.sh
set -euo pipefail
: "${R2_BUCKET:?需要 R2_BUCKET}"
R2_PREFIX="${R2_PREFIX:-hymns}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$(cd "$HERE/../../public/hymns" && pwd)"
shopt -s nullglob
for f in "$SRC"/*.mp3; do
  base="$(basename "$f")"
  echo "↑ $base"
  wrangler r2 object put "${R2_BUCKET}/${R2_PREFIX}/${base}" --file "$f" --content-type "audio/mpeg"
done
echo "✅ 完成。别忘了开桶公开访问 + 设 VITE_HYMN_AUDIO_BASE。"
