#!/usr/bin/env python3
"""把 9 首诗歌 mp3 上传到 Cloudflare R2（桶 sabbath, 前缀 hymns/）。

用法（在仓库根目录）：
    pip install boto3
    export R2_ACCOUNT_ID=...   R2_ACCESS_KEY_ID=...   R2_SECRET_ACCESS_KEY=...   R2_BUCKET_NAME=sabbath
    python scripts/upload_hymns_r2.py

上传后这些文件的公开地址为  {VIDEO_CDN_BASE 或 https://<bucket>.r2.dev}/hymns/<id>.mp3
把该公开前缀（到 /hymns 为止）设到前端 VITE_HYMN_AUDIO_BASE 即可。
"""
import os, sys, glob, pathlib

def main():
    import boto3
    aid = os.environ["R2_ACCOUNT_ID"]; ak = os.environ["R2_ACCESS_KEY_ID"]
    sk = os.environ["R2_SECRET_ACCESS_KEY"]; bkt = os.environ.get("R2_BUCKET_NAME", "sabbath")
    cdn = os.environ.get("VIDEO_CDN_BASE", f"https://{bkt}.r2.dev").rstrip("/")
    s3 = boto3.client("s3", endpoint_url=f"https://{aid}.r2.cloudflarestorage.com",
                      aws_access_key_id=ak, aws_secret_access_key=sk, region_name="auto")
    src_dir = pathlib.Path(__file__).resolve().parents[1] / "emotion-sphere-ui" / "public" / "hymns"
    files = sorted(glob.glob(str(src_dir / "*.mp3")))
    if not files:
        print(f"未找到 mp3，请确认目录：{src_dir}"); sys.exit(1)
    for f in files:
        name = pathlib.Path(f).name
        key = f"hymns/{name}"
        s3.upload_file(f, bkt, key, ExtraArgs={"ContentType": "audio/mpeg",
                                               "CacheControl": "public, max-age=31536000"})
        print(f"  ✅ {key}  ->  {cdn}/{key}")
    print(f"\n完成。把 VITE_HYMN_AUDIO_BASE 设为：{cdn}/hymns")

if __name__ == "__main__":
    main()
