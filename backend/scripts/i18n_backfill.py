#!/usr/bin/env python3
"""国际化阶段一 —— 参考/种子内容 zh→en 一次性回填。

只翻译「_en 列为空」的行，可安全重复运行（断点续跑）。
复用 query_emotion_verses.call_chat（多供应商回退 + 缓存）。
圣经专名走受控词表保证一致（以法莲→Ephraim）。

用法：
    cd backend && DATABASE_URL=... python scripts/i18n_backfill.py
    # 可选：只跑某张表
    python scripts/i18n_backfill.py --only seekers_class_courses
    # 预览不写库
    python scripts/i18n_backfill.py --dry-run
"""
from __future__ import annotations
import os, sys, json, argparse, time

# 让脚本能 import 仓库根的 query_emotion_verses
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
for p in (_ROOT, os.path.join(_ROOT, "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

import psycopg2  # noqa: E402
from query_emotion_verses import call_chat  # noqa: E402

# ── 圣经专名受控词表（zh → en）。逐步补充；模型对表外术语用通用英文圣经译名。──
GLOSSARY: dict[str, str] = {
    "犹大": "Judah", "便雅悯": "Benjamin", "以法莲": "Ephraim", "玛拿西": "Manasseh",
    "西玛拿西": "Manasseh (West)", "东玛拿西": "Manasseh (East)", "但": "Dan",
    "亚设": "Asher", "拿弗他利": "Naphtali", "西布伦": "Zebulun", "以萨迦": "Issachar",
    "迦得": "Gad", "流便": "Reuben", "西缅": "Simeon", "利未": "Levi",
    "亚述": "Assyria", "巴比伦": "Babylon", "波斯": "Persia", "希腊": "Greece", "罗马": "Rome",
    "摩押": "Moab", "埃及": "Egypt", "推罗": "Tyre", "耶路撒冷": "Jerusalem",
    "俄陀聂": "Othniel", "以笏": "Ehud", "底波拉": "Deborah", "巴拉": "Barak",
    "基甸": "Gideon", "耶弗他": "Jephthah", "参孙": "Samson",
    "兰塞": "Rameses", "疏割": "Succoth", "以倘": "Etham", "耶利哥": "Jericho",
    "西奈": "Sinai", "迦南": "Canaan", "约旦河": "Jordan River",
}

SYS_PROMPT = (
    "You are a professional translator for a Chinese Christian Bible app. "
    "Translate the given Simplified-Chinese text into natural, reverent English. "
    "Use standard English Bible proper nouns (ESV style). "
    "Follow this controlled glossary EXACTLY for any term that appears: "
    + json.dumps(GLOSSARY, ensure_ascii=False)
    + ". Output ONLY the English translation, no quotes, no notes, no explanations."
)

# (表, 主键列, [(中文源列, 英文目标列), ...])
TARGETS = [
    ("bible_territories", "id", [("description", "description_en")]),
    ("bible_events", "id", [("description", "description_en"), ("spiritual_meaning", "spiritual_meaning_en")]),
    ("bible_prophecies", "id", [("description", "description_en"), ("fulfillment_description", "fulfillment_description_en")]),
    ("bible_campaigns", "id", [("description", "description_en")]),
    ("geo_events", "event_id", [("title", "title_en"), ("summary", "summary_en")]),
    ("seekers_class_courses", "id",
     [("title", "title_en"), ("teacher", "teacher_en"), ("scripture", "scripture_en"), ("description", "description_en")]),
]


def translate(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    # 词表直命中（单个专名）直接用，省一次调用
    if text in GLOSSARY:
        return GLOSSARY[text]
    out = call_chat(SYS_PROMPT, text).strip().strip('"').strip()
    return out


def detect_pk(cur, table: str, preferred: str) -> str:
    """有的表主键不一定叫 id；探测可用主键列。"""
    cur.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name=%s", (table,))
    cols = {r[0] for r in cur.fetchall()}
    for cand in (preferred, "id", "event_id", "entity_id"):
        if cand in cols:
            return cand
    raise RuntimeError(f"{table}: 找不到主键列")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="只处理某张表")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.3, help="每次翻译间隔秒")
    args = ap.parse_args()

    db = os.getenv("DATABASE_URL", "")
    if not db:
        sys.exit("DATABASE_URL 未设置")
    conn = psycopg2.connect(db)
    conn.autocommit = False
    total = 0
    try:
        for table, pk_pref, fields in TARGETS:
            if args.only and table != args.only:
                continue
            with conn.cursor() as cur:
                pk = detect_pk(cur, table, pk_pref)
                # 取任一 _en 为空且对应中文非空的行
                where = " OR ".join(
                    f"(({en} IS NULL OR {en}='') AND {zh} IS NOT NULL AND {zh}<>'')"
                    for zh, en in fields
                )
                src_cols = ", ".join(zh for zh, _ in fields)
                cur.execute(f"SELECT {pk}, {src_cols} FROM {table} WHERE {where}")
                rows = cur.fetchall()
                print(f"[{table}] 待回填 {len(rows)} 行", flush=True)
                for row in rows:
                    rid = row[0]
                    sets, vals = [], []
                    for idx, (zh, en) in enumerate(fields):
                        zh_val = row[idx + 1]
                        if zh_val and str(zh_val).strip():
                            en_val = translate(str(zh_val))
                            if en_val:
                                sets.append(f"{en}=%s")
                                vals.append(en_val)
                                time.sleep(args.sleep)
                    if not sets:
                        continue
                    total += 1
                    if args.dry_run:
                        print(f"  [dry] {table}.{rid}: " + " | ".join(f"{s.split('=')[0]}={v[:40]}" for s, v in zip(sets, vals)))
                    else:
                        vals.append(rid)
                        cur.execute(f"UPDATE {table} SET {', '.join(sets)} WHERE {pk}=%s", vals)
                        print(f"  ✓ {table}.{rid}", flush=True)
                if not args.dry_run:
                    conn.commit()
        print(f"完成，回填 {total} 行" + ("（dry-run 未写库）" if args.dry_run else ""), flush=True)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
