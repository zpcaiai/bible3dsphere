#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_graph_db.py — read-only verification + migration dry-run for the
biblical 镜鉴 / knowledge-graph tables.

WHAT IT DOES
  1. Connects with your DATABASE_URL (read-only usage).
  2. Prints exact counts:
       - biblical_characters (active, by era, by type)            ← 镜鉴人物库
       - biblical_graph_nodes (by node_type, by importance, active) ← 知识图谱
       - biblical_graph_edges (active, by category, top rel types)
  3. Runs connectivity checks for the 12 core person-networks.
  4. (optional) --dry-run: executes the given migration .sql files inside a
       single transaction and ROLLS BACK — a real "实跑校验" against the live
       schema that persists NOTHING. Reports the row-count delta it *would* make.

SAFETY
  - Default mode issues only SELECTs.
  - --dry-run wraps everything in BEGIN … ROLLBACK; it never COMMITs.
  - Nothing in this script ever writes permanently.

USAGE
  pip install "psycopg[binary]"
  export DATABASE_URL='postgresql://user:pass@host/db?sslmode=require'
  python backend/scripts/verify_graph_db.py                 # counts + checks
  python backend/scripts/verify_graph_db.py --dry-run       # + migration dry-run (0064/0065/0066)
  python backend/scripts/verify_graph_db.py --dry-run --files 0064_*.sql 0065_*.sql 0066_*.sql
"""
import argparse, glob, os, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MIGRATIONS_DIR = HERE.parent / "migrations"


def load_url(cli_url):
    if cli_url:
        return cli_url
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    # fall back to .env / .env.local at repo root
    for env in (HERE.parent.parent / ".env.local", HERE.parent.parent / ".env",
                HERE.parent / ".env"):
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                m = re.match(r'\s*(?:export\s+)?DATABASE_URL\s*=\s*["\']?([^"\'\n]+)', line)
                if m and m.group(1).strip():
                    return m.group(1).strip()
    return None


def q1(cur, sql, params=None):
    cur.execute(sql, params or ())
    r = cur.fetchone()
    return r[0] if r else None


def section(title):
    print("\n" + "=" * 64 + f"\n{title}\n" + "=" * 64)


def counts(cur):
    section("镜鉴人物库  biblical_characters")
    total = q1(cur, "SELECT count(*) FROM biblical_characters WHERE is_active")
    print(f"  活跃人物总数: {total}")
    cur.execute("""SELECT era, count(*) FROM biblical_characters WHERE is_active
                   GROUP BY era ORDER BY count(*) DESC""")
    for era, n in cur.fetchall():
        print(f"    {era or '(空)':<14} {n}")
    cur.execute("""SELECT character_type, count(*) FROM biblical_characters WHERE is_active
                   GROUP BY character_type ORDER BY count(*) DESC""")
    print("  类型:", "  ".join(f"{t}={n}" for t, n in cur.fetchall()))

    section("知识图谱  biblical_graph_nodes")
    cur.execute("""SELECT node_type, count(*) FROM biblical_graph_nodes WHERE is_active
                   GROUP BY node_type ORDER BY count(*) DESC""")
    rows = cur.fetchall()
    for nt, n in rows:
        print(f"    {nt:<12} {n}")
    print(f"  节点合计: {sum(n for _, n in rows)}")
    char_nodes = q1(cur, "SELECT count(*) FROM biblical_graph_nodes WHERE is_active AND node_type='character'")
    print(f"  → 人物节点(character): {char_nodes}")
    cur.execute("""SELECT importance_level, count(*) FROM biblical_graph_nodes
                   WHERE is_active AND node_type='character'
                   GROUP BY importance_level ORDER BY importance_level""")
    print("  重要性分级:", "  ".join(f"{lv}={n}" for lv, n in cur.fetchall()))

    section("知识图谱关系  biblical_graph_edges")
    et = q1(cur, "SELECT count(*) FROM biblical_graph_edges WHERE is_active")
    print(f"  活跃边总数: {et}")
    cur.execute("""SELECT relationship_category, count(*) FROM biblical_graph_edges WHERE is_active
                   GROUP BY relationship_category ORDER BY count(*) DESC""")
    print("  按类别:", "  ".join(f"{c}={n}" for c, n in cur.fetchall()))
    cur.execute("""SELECT relationship_type, count(*) FROM biblical_graph_edges WHERE is_active
                   GROUP BY relationship_type ORDER BY count(*) DESC LIMIT 12""")
    print("  Top 关系类型:", "  ".join(f"{c}={n}" for c, n in cur.fetchall()))


# (a,b,rel-list) connectivity probes for the 12 subgraphs
CHECKS = [
    ("①家谱 大卫→耶稣", "大卫", "耶稣基督", ["ANCESTOR_OF"]),
    ("①家谱 亚伯拉罕→耶稣", "亚伯拉罕", "耶稣基督", ["ANCESTOR_OF"]),
    ("①家谱 马利亚→耶稣", "马利亚", "耶稣基督", ["MOTHER_OF"]),
    ("①家谱 波阿斯→俄备得", "波阿斯", "俄备得", ["FATHER_OF"]),
    ("③支派 雅各→犹大", "雅各", "犹大（雅各之子）", ["FATHER_OF"]),
    ("③支派 雅各→便雅悯", "雅各", "便雅悯（雅各之子）", ["FATHER_OF"]),
    ("⑩门徒 彼得→耶稣", "彼得", "耶稣基督", ["APOSTLE_OF"]),
    ("⑩门徒 犹大 BETRAYED 耶稣", "犹大", "耶稣基督", ["BETRAYED"]),
    ("⑧犹大世系 罗波安→亚比央", "罗波安", "亚比央", ["FATHER_OF"]),
    ("⑧犹大世系 约西亚→西底家", "约西亚", "西底家", ["FATHER_OF"]),
    ("⑥大卫 约押 KILLED 押尼珥", "约押", "押尼珥", ["KILLED"]),
    ("⑤士师 雅亿 KILLED 西西拉", "雅亿", "西西拉", ["KILLED"]),
    ("先知 拿单→大卫", "拿单", "大卫", ["PROPHET_OF", "OPPOSED"]),
    ("师徒 以利→撒母耳", "以利", "撒母耳", ["MENTOR_OF"]),
]


def edge_exists(cur, src_name, tgt_name, rels):
    cur.execute("""
        SELECT 1 FROM biblical_graph_edges e
        JOIN biblical_graph_nodes sn ON sn.id=e.source_node_id
        JOIN biblical_characters  sc ON sc.id=sn.character_id
        JOIN biblical_graph_nodes tn ON tn.id=e.target_node_id
        JOIN biblical_characters  tc ON tc.id=tn.character_id
        WHERE e.is_active AND sc.name=%s AND tc.name=%s
          AND e.relationship_type = ANY(%s) LIMIT 1
    """, (src_name, tgt_name, list(rels)))
    return cur.fetchone() is not None


def connectivity(cur):
    section("12 核心网络 连通性抽查")
    ok = 0
    for label, a, b, rels in CHECKS:
        present = edge_exists(cur, a, b, rels)
        ok += present
        print(f"  [{'✓' if present else '✗'}] {label}")
    print(f"\n  通过 {ok}/{len(CHECKS)}")


def dry_run(conn, files):
    section("迁移实跑校验 (BEGIN … ROLLBACK，零持久化)")
    paths = []
    for pat in files:
        paths += sorted(glob.glob(str(MIGRATIONS_DIR / pat)))
    if not paths:
        print("  未找到迁移文件:", files); return
    cur = conn.cursor()
    before = {t: q1(cur, f"SELECT count(*) FROM {t}")
              for t in ("biblical_characters", "biblical_graph_nodes", "biblical_graph_edges")}
    try:
        for p in paths:
            sql = Path(p).read_text(encoding="utf-8")
            print(f"  ▶ 执行 {Path(p).name} …")
            cur.execute(sql)
        after = {t: q1(cur, f"SELECT count(*) FROM {t}")
                 for t in before}
        print("\n  将会新增 (rollback 前的预期增量):")
        for t in before:
            print(f"    {t:<26} {before[t]} → {after[t]}  (+{after[t]-before[t]})")
        print("\n  ✅ 全部迁移在真实 schema 上执行成功（即将回滚，不持久化）。")
    except Exception as e:
        print(f"\n  ❌ 迁移执行失败: {type(e).__name__}: {e}")
        raise
    finally:
        conn.rollback()
        print("  ↩ 已回滚，数据库未被改动。")


def main():
    ap = argparse.ArgumentParser(description="Read-only 镜鉴/知识图谱 verification + migration dry-run")
    ap.add_argument("--url", help="DATABASE_URL (overrides env/.env)")
    ap.add_argument("--dry-run", action="store_true", help="run migration files in a rolled-back transaction")
    ap.add_argument("--files", nargs="*", default=["0064_*.sql", "0065_*.sql", "0066_*.sql"],
                    help="migration filename globs for --dry-run")
    args = ap.parse_args()

    url = load_url(args.url)
    if not url:
        print("ERROR: 未找到 DATABASE_URL。请 export DATABASE_URL=... 或用 --url 传入。", file=sys.stderr)
        sys.exit(2)
    try:
        import psycopg
    except ImportError:
        print("ERROR: 需要 psycopg。请运行: pip install \"psycopg[binary]\"", file=sys.stderr)
        sys.exit(2)

    with psycopg.connect(url, connect_timeout=15) as conn:
        with conn.cursor() as cur:
            counts(cur)
            connectivity(cur)
        if args.dry_run:
            dry_run(conn, args.files)
        conn.rollback()  # ensure nothing lingers


if __name__ == "__main__":
    main()
