"""dating_priority router — extracted from main.py (deps injected at init)."""
from __future__ import annotations

import json
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()

# Dependencies injected from main at startup:
_get_db = None
_release_db = None

def init_dating_priority_router(**deps):
    globals().update(deps)

class DatingPrioritySubmitRequest(BaseModel):
    visitor_id: str = Field(min_length=1, max_length=255)
    perspective: str = Field(pattern='^(dx|zm)$')
    focus_order: list = Field(default=[])
    block_order: list = Field(default=[])


@router.post('/api/dating-priority/submit')
def submit_dating_priority(payload: DatingPrioritySubmitRequest) -> dict:
    """Save a user's dating priority ranking."""
    print(f'[dating] submit visitor={payload.visitor_id[:8]}... persp={payload.perspective} focus={len(payload.focus_order)} block={len(payload.block_order)}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO dating_priority_submissions (visitor_id, perspective, focus_order, block_order)
                VALUES (%s, %s, %s, %s)
            ''', (payload.visitor_id, payload.perspective,
                  json.dumps(payload.focus_order), json.dumps(payload.block_order)))
            conn.commit()
        return {'ok': True}
    finally:
        _release_db(conn)


@router.get('/api/dating-priority/stats')
def get_dating_priority_stats(perspective: str = Query(pattern='^(dx|zm)$')) -> dict:
    """Get aggregated statistics for dating priority rankings.
    Returns average rank position for each option across all submissions.
    """
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT focus_order, block_order FROM dating_priority_submissions
                WHERE perspective = %s
            ''', (perspective,))
            rows = cur.fetchall()

        total = len(rows)
        if total == 0:
            return {'ok': True, 'total': 0, 'focus_stats': [], 'block_stats': []}

        # Aggregate: for each item, collect all rank positions assigned by users
        focus_ranks = {}  # item -> list of rank positions (1-indexed)
        block_ranks = {}

        for row in rows:
            focus_list = row[0] if isinstance(row[0], list) else json.loads(row[0]) if row[0] else []
            block_list = row[1] if isinstance(row[1], list) else json.loads(row[1]) if row[1] else []

            for rank, item in enumerate(focus_list, 1):
                if item not in focus_ranks:
                    focus_ranks[item] = []
                focus_ranks[item].append(rank)

            for rank, item in enumerate(block_list, 1):
                if item not in block_ranks:
                    block_ranks[item] = []
                block_ranks[item].append(rank)

        # Calculate stats: avg rank, selection count
        def calc_stats(ranks_dict):
            stats = []
            for item, ranks in ranks_dict.items():
                avg_rank = sum(ranks) / len(ranks)
                stats.append({
                    'item': item,
                    'avg_rank': round(avg_rank, 2),
                    'times_selected': len(ranks),
                    'selection_rate': round(len(ranks) / total * 100, 1),
                })
            stats.sort(key=lambda x: x['avg_rank'])
            return stats

        return {
            'ok': True,
            'total': total,
            'focus_stats': calc_stats(focus_ranks),
            'block_stats': calc_stats(block_ranks),
        }
    finally:
        _release_db(conn)


# ============================================================
# 人格塑造、习惯养成、行为追踪系统 API (从emotion-sphere移植)
# ============================================================
