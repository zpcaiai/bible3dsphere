#!/usr/bin/env python3
"""
同步 R2 存储的主日学视频到数据库表 sunday_school_videos。

用法:
    cd /Users/stephen/Documents/Projects/DoctorPro/bible3dsphere
    python scripts/sync_sunday_school_videos.py [--dry-run]

环境变量:
    DATABASE_URL - PostgreSQL 连接字符串 (必需)
    R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME - R2 API 凭证
    或 R2_ENDPOINT_URL - R2/S3 兼容端点 URL
"""
import os
import sys
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

# 添加 backend 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

VIDEO_BASE_URL = os.environ.get('SUNDAY_SCHOOL_VIDEO_BASE', 'https://cdn.holiness.uk/sunday-school/')


def list_videos_from_r2():
    """从 R2 存储列出视频文件。"""
    videos = []
    
    # 尝试 boto3 S3 API
    try:
        import boto3
        from botocore.config import Config
        
        account_id = os.environ.get('R2_ACCOUNT_ID')
        access_key = os.environ.get('R2_ACCESS_KEY_ID')
        secret_key = os.environ.get('R2_SECRET_ACCESS_KEY')
        bucket = os.environ.get('R2_BUCKET_NAME', 'holiness')
        
        if account_id and access_key and secret_key:
            endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
            s3 = boto3.client(
                's3',
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=Config(signature_version='s3v4')
            )
            
            prefix = 'sunday-school/'
            paginator = s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    if not key.lower().endswith(('.mp4', '.mov', '.webm', '.m4v')):
                        continue
                    filename = key.split('/')[-1]
                    videos.append({
                        'filename': filename,
                        'title': filename.rsplit('.', 1)[0].replace('-', ' ').replace('_', ' '),
                        'video_url': f"{VIDEO_BASE_URL}{filename}",
                        'modified': obj.get('LastModified', datetime.now(timezone.utc)),
                        'size': obj.get('Size', 0)
                    })
            print(f"[sync] R2 API: 找到 {len(videos)} 个视频")
            return videos
    except Exception as e:
        print(f"[sync] R2 API 失败: {e}")
    
    # 备用: HTTP directory listing
    try:
        import httpx
        from bs4 import BeautifulSoup
        
        resp = httpx.get(VIDEO_BASE_URL, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        for link in soup.find_all('a'):
            href = link.get('href', '')
            if href.lower().endswith(('.mp4', '.mov', '.webm', '.m4v')):
                filename = href.split('/')[-1].split('?')[0]
                videos.append({
                    'filename': filename,
                    'title': filename.rsplit('.', 1)[0].replace('-', ' ').replace('_', ' '),
                    'video_url': f"{VIDEO_BASE_URL}{filename}",
                    'modified': datetime.now(timezone.utc),
                    'size': 0
                })
        print(f"[sync] HTTP listing: 找到 {len(videos)} 个视频")
    except Exception as e:
        print(f"[sync] HTTP listing 失败: {e}")
    
    return videos


def get_existing_videos(conn):
    """获取数据库中已有的视频 URL 集合。"""
    with conn.cursor() as cur:
        cur.execute("SELECT video_url FROM sunday_school_videos")
        return {row[0] for row in cur.fetchall()}


def sync_to_database(videos, dry_run=False):
    """将视频同步到数据库。"""
    import psycopg2
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("[sync] 错误: DATABASE_URL 未设置")
        sys.exit(1)
    
    conn = psycopg2.connect(database_url)
    try:
        existing_urls = get_existing_videos(conn)
        print(f"[sync] 数据库已有 {len(existing_urls)} 个视频")
        
        to_insert = [v for v in videos if v['video_url'] not in existing_urls]
        
        if not to_insert:
            print("[sync] 没有新视频需要同步")
            return 0
        
        print(f"[sync] 准备插入 {len(to_insert)} 个新视频")
        
        if dry_run:
            for v in to_insert:
                print(f"  [dry-run] 将插入: {v['title']}")
            return len(to_insert)
        
        with conn.cursor() as cur:
            for v in to_insert:
                cur.execute('''
                    INSERT INTO sunday_school_videos
                        (title, teacher, scripture, description,
                         video_url, thumbnail_url, duration_sec, sort_order, is_visible)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (video_url) DO NOTHING
                ''', (
                    v['title'][:255],
                    '',  # teacher
                    '',  # scripture
                    '',  # description
                    v['video_url'],
                    '',  # thumbnail_url
                    0,   # duration_sec
                    0,   # sort_order
                    True  # is_visible
                ))
                print(f"  [sync] 已插入: {v['title']}")
            conn.commit()
        
        print(f"[sync] 成功同步 {len(to_insert)} 个视频")
        return len(to_insert)
        
    finally:
        conn.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description='同步 R2 主日学视频到数据库')
    parser.add_argument('--dry-run', action='store_true', help='模拟运行不实际插入')
    args = parser.parse_args()
    
    print("=" * 50)
    print("主日学视频同步工具")
    print("=" * 50)
    
    # 1. 从 R2 获取视频列表
    videos = list_videos_from_r2()
    if not videos:
        print("[sync] 没有找到视频，退出")
        sys.exit(1)
    
    # 2. 同步到数据库
    count = sync_to_database(videos, dry_run=args.dry_run)
    
    print("=" * 50)
    if args.dry_run:
        print(f"[完成] 模拟模式: 将插入 {count} 个视频 (实际未写入)")
    else:
        print(f"[完成] 成功同步 {count} 个视频到数据库")
    print("=" * 50)


if __name__ == '__main__':
    main()
