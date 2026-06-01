#!/usr/bin/env bash
# 把 public/hymns/*.mp3 上传到 Cloudflare R2（音频托管，配合前端 VITE_HYMN_AUDIO_BASE）。
# R2 是 S3 兼容的，这里用 aws-cli。先装：  brew install awscli
#
# 用法（在仓库根目录或 emotion-sphere-ui/ 下都行）：
#   export R2_ACCOUNT_ID=xxxxxxxxxxxxxxxxxxxx          # Cloudflare 账号 ID
#   export R2_ACCESS_KEY_ID=xxxx                      # R2 API Token 的 Access Key
#   export R2_SECRET_ACCESS_KEY=xxxx                  # R2 API Token 的 Secret
#   export R2_BUCKET=biblesphere-hymns                # 你的 R2 桶名
#   export R2_PREFIX=hymns                            # 桶内路径前缀(对应 VITE_HYMN_AUDIO_BASE 末段)
#   bash emotion-sphere-ui/scripts/hymns/upload_to_r2.sh
#   # 或：cd emotion-sphere-ui && bash scripts/hymns/upload_to_r2.sh
#
# R2 的 API Token 在 Cloudflare 控制台 → R2 → Manage R2 API Tokens 里建（要 Object Read & Write 权限）。
set -euo pipefail

: "${R2_ACCOUNT_ID:?需要 R2_ACCOUNT_ID}"
: "${R2_ACCESS_KEY_ID:?需要 R2_ACCESS_KEY_ID}"
: "${R2_SECRET_ACCESS_KEY:?需要 R2_SECRET_ACCESS_KEY}"
: "${R2_BUCKET:?需要 R2_BUCKET}"
R2_PREFIX="${R2_PREFIX:-hymns}"
ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

# 定位 mp3 目录（脚本在 emotion-sphere-ui/scripts/hymns/ 下）
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$(cd "$HERE/../../public/hymns" && pwd)"
echo "源目录: $SRC"
echo "目标:   s3://${R2_BUCKET}/${R2_PREFIX}/  (endpoint $ENDPOINT)"

shopt -s nullglob
files=("$SRC"/*.mp3)
if [ ${#files[@]} -eq 0 ]; then echo "❌ $SRC 下没有 mp3"; exit 1; fi

export AWS_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY"
export AWS_DEFAULT_REGION="auto"

n=0
for f in "${files[@]}"; do
  base="$(basename "$f")"
  echo "↑ $base"
  aws s3 cp "$f" "s3://${R2_BUCKET}/${R2_PREFIX}/${base}" \
    --endpoint-url "$ENDPOINT" \
    --content-type "audio/mpeg" \
    --cache-control "public, max-age=31536000, immutable" \
    --only-show-errors
  n=$((n+1))
done
echo "✅ 已上传 $n 个 mp3 到 R2。"
echo
echo "接下来："
echo "  1) 给桶开公开访问：R2 → 你的桶 → Settings → Public access，或绑定自定义域名（推荐）。"
echo "  2) 在 Vercel/Netlify 设构建环境变量："
echo "       VITE_HYMN_AUDIO_BASE = https://<你的R2公开域名>/${R2_PREFIX}"
echo "     （HymnPlayer 会用它拼出 <id>.mp3；不设则回退找 /hymns/<id>.mp3）"
echo "  3) 重新部署，打开 代祷→诗歌 子tab 点播放验证。"
