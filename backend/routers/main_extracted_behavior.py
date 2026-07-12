"""行为调节系统 /api/behavior/* — 从 main.py 逐字搬移（路径不变，无 prefix）。

对 main.py 内部辅助（_get_db、_release_db、_get_session_user）通过
init_main_extracted_behavior() 在 include_router 之前注入。

说明：原 main.py 的 behavior_regulate 里 ``uuid.uuid4()`` 引用的 ``uuid`` 在模块级
并未 import（NameError 被日志 try/except 吞掉，行为历史落库从未生效）。本模块补上
``import uuid``，使落库按原始意图工作；见 REFACTOR_PLAN.md。
"""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter()

# ── main.py 注入的依赖（导入期为 None，仅在请求期被调用）──
_get_db = None
_release_db = None
_get_session_user = None


def init_main_extracted_behavior(*, get_db, release_db, get_session_user) -> None:
    global _get_db, _release_db, _get_session_user
    _get_db = get_db
    _release_db = release_db
    _get_session_user = get_session_user


class BehaviorRegulateRequest(BaseModel):
    task: str = Field(min_length=1, max_length=500)
    energy_level: int = Field(default=3, ge=1, le=5)
    motivation: int = Field(default=5, ge=1, le=10)


# ── 行为调节系统 API ─────────────────────────────────────────

@router.post('/api/behavior/regulate')
def behavior_regulate(payload: BehaviorRegulateRequest, request: Request):
    """
    行为调节引擎 - 动态行为工程学
    基于当前能量和动机水平，推荐最小可执行动作
    """
    try:
        from backend.habit_behavior_engine import regulate_behavior
        result = regulate_behavior(payload.task, payload.energy_level)
        
        # 记录到行为历史 (异步记录，不阻塞响应)
        user = _get_session_user(request)
        if user:
            conn = None
            try:
                conn = _get_db()
                with conn.cursor() as cur:
                    cur.execute(
                        '''INSERT INTO sfds_behavior_history 
                           (user_id, session_id, task, energy_level, motivation, tier_executed,
                            min_executable_action, task_downgrade, emotional_compensation, continuity_advice, spiritual_alignment)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                        (user['id'], str(uuid.uuid4()), payload.task, payload.energy_level, 
                         getattr(payload, 'motivation', 5), result.get('selected_tier', 'Yellow'),
                         result.get('min_executable_action', ''), result.get('task_downgrade', ''),
                         result.get('emotional_compensation', ''), result.get('continuity_advice', ''),
                         json.dumps(result.get('spiritual_alignment', {}), ensure_ascii=False))
                    )
                    conn.commit()
            except Exception as log_exc:
                print(f'[behavior_regulate] Log error: {log_exc}', flush=True)
            finally:
                if conn is not None:
                    _release_db(conn)
        
        return result
    except Exception as exc:
        print(f'[behavior_regulate] Failed: {exc}', flush=True)
        tier = "Red" if payload.energy_level <= 2 else ("Yellow" if payload.energy_level <= 3 else "Green")
        return {
            "degraded": True,
            "selected_tier": tier,
            "min_executable_action": f"尝试{payload.task}的最小版本" if tier == "Red" else f"开始{payload.task}",
            "emotional_compensation": "系统智能降级，保持连续性",
            "continuity_advice": "任何微小启动都算成功",
            "spiritual_alignment": {
                "aligned": True,
                "alignment_score": 50,
                "assessment": "系统降级运行，属灵对齐评估暂不可用",
                "scripture_reference": "箴3:5-6",
                "principle": "你要专心仰赖耶和华，不可倚靠自己的聪明",
                "misalignment_areas": [],
                "alignment_actions": ["稍后重试", "检查后端服务日志"],
                "category": "系统降级"
            }
        }


@router.get('/api/behavior/history')
def get_behavior_history(user_id: str = None, limit: int = Query(default=30, ge=1, le=200), request: Request = None):
    """获取用户的行为调节历史"""
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    target_user_id = user_id or str(user['id'])
    
    # 只能查询自己的数据
    if str(target_user_id) != str(user['id']):
        raise HTTPException(status_code=403, detail='只能查看自己的数据')
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT id, task, energy_level, motivation, tier_executed,
                          min_executable_action, was_completed, completion_percentage,
                          executed_at, system_energy_state, spiritual_alignment
                   FROM sfds_behavior_history 
                   WHERE user_id = %s
                   ORDER BY executed_at DESC
                   LIMIT %s''',
                (target_user_id, limit)
            )
            rows = cur.fetchall()
            
            def _parse_json_safe(val):
                if not val:
                    return None
                try:
                    return json.loads(val)
                except Exception:
                    return None

            items = [{
                'id': str(r[0]),
                'task': r[1],
                'energy_level': r[2],
                'motivation': r[3],
                'tier_executed': r[4],
                'min_executable_action': r[5],
                'was_completed': r[6],
                'completion_percentage': r[7],
                'executed_at': r[8].isoformat() if r[8] else None,
                'system_energy_state': r[9],
                'spiritual_alignment': _parse_json_safe(r[10]),
                'source': 'behavior'
            } for r in rows]

            # Also pull habit execution logs and merge
            try:
                cur.execute(
                    '''SELECT hel.id, hsm.habit_name, hel.energy_level_at_execution,
                              hel.selected_tier, hel.was_completed, hel.completion_percentage,
                              hel.mood_before, hel.mood_after, hel.tokens_earned, hel.executed_at
                       FROM habit_execution_logs hel
                       LEFT JOIN habit_state_machines hsm ON hsm.id::text = hel.habit_id
                       WHERE hel.user_id = %s
                       ORDER BY hel.executed_at DESC
                       LIMIT %s''',
                    (target_user_id, limit)
                )
                habit_rows = cur.fetchall()
                for hr in habit_rows:
                    items.append({
                        'id': 'h_' + str(hr[0]),
                        'task': hr[1] or '习惯执行',
                        'energy_level': hr[2],
                        'motivation': None,
                        'tier_executed': hr[3],
                        'min_executable_action': None,
                        'was_completed': hr[4],
                        'completion_percentage': hr[5],
                        'executed_at': hr[9].isoformat() if hr[9] else None,
                        'system_energy_state': None,
                        'spiritual_alignment': None,
                        'mood_before': hr[6],
                        'mood_after': hr[7],
                        'tokens_earned': hr[8],
                        'source': 'habit'
                    })
            except Exception as habit_exc:
                print(f'[behavior_history] habit log merge failed: {habit_exc}', flush=True)

            # Sort merged list by executed_at descending
            items.sort(key=lambda x: x['executed_at'] or '', reverse=True)
            items = items[:limit]

        return {'items': items, 'count': len(items)}
    finally:
        _release_db(conn)


@router.get('/api/behavior/stats')
def get_behavior_stats(user_id: str = None, request: Request = None):
    """获取用户的行为调节统计"""
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    target_user_id = user_id or str(user['id'])
    
    if str(target_user_id) != str(user['id']):
        raise HTTPException(status_code=403, detail='只能查看自己的数据')
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # 总体统计
            cur.execute(
                '''SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN was_completed THEN 1 ELSE 0 END) as completed,
                    AVG(completion_percentage) as avg_completion,
                    AVG(energy_level) as avg_energy
                   FROM sfds_behavior_history 
                   WHERE user_id = %s''',
                (target_user_id,)
            )
            row = cur.fetchone()
            
            total_regulations = row[0] or 0
            completed_regulations = row[1] or 0
            avg_completion_percentage = round(row[2] or 0, 1)
            avg_energy_level = round(row[3] or 3, 1)
            
            # 层级分布
            cur.execute(
                '''SELECT tier_executed, COUNT(*) 
                   FROM sfds_behavior_history 
                   WHERE user_id = %s
                   GROUP BY tier_executed''',
                (target_user_id,)
            )
            tier_distribution = {r[0]: r[1] for r in cur.fetchall()}
            
            # 最近7天统计
            cur.execute(
                '''SELECT COUNT(*) 
                   FROM sfds_behavior_history 
                   WHERE user_id = %s AND executed_at > NOW() - INTERVAL '7 days' ''',
                (target_user_id,)
            )
            last_7_days = cur.fetchone()[0] or 0

            # 计算Red电路占比（反映疲劳趋势）
            red_count = tier_distribution.get('Red', 0)
            red_tier_ratio = round((red_count / total_regulations * 100), 1) if total_regulations > 0 else 0

            # 最近30天能量趋势（判断疲劳累积）
            cur.execute(
                '''SELECT AVG(energy_level) as avg_energy_30d,
                       COUNT(CASE WHEN energy_level <= 2 THEN 1 END) as low_energy_count
                   FROM sfds_behavior_history 
                   WHERE user_id = %s AND executed_at > NOW() - INTERVAL '30 days' ''',
                (target_user_id,)
            )
            trend_row = cur.fetchone()
            avg_energy_30d = round(trend_row[0] or 3, 1) if trend_row else 3
            low_energy_count_30d = trend_row[1] or 0 if trend_row else 0

            # 最近习惯执行统计（关联sfds_formation_metrics中的数据）
            cur.execute(
                '''SELECT COUNT(*), AVG(energy_level_at_execution)
                   FROM habit_execution_logs 
                   WHERE user_id = %s AND executed_at > NOW() - INTERVAL '7 days' ''',
                (target_user_id,)
            )
            habit_row = cur.fetchone()
            recent_habit_executions = habit_row[0] or 0
            avg_habit_energy = round(habit_row[1] or 3, 1) if habit_row else 3

        return {
            'total_regulations': total_regulations,
            'completed_regulations': completed_regulations,
            'completion_rate': round((completed_regulations / total_regulations * 100), 1) if total_regulations > 0 else 0,
            'avg_completion_percentage': avg_completion_percentage,
            'avg_energy_level': avg_energy_level,
            'tier_distribution': tier_distribution,
            'last_7_days_regulations': last_7_days,
            # 新增决策相关字段
            'red_tier_ratio': red_tier_ratio,
            'fatigue_trend': 'high' if red_tier_ratio > 30 or avg_energy_30d < 2.5 else 'moderate' if red_tier_ratio > 15 else 'normal',
            'avg_energy_30d': avg_energy_30d,
            'low_energy_episodes_30d': low_energy_count_30d,
            'recent_habit_executions_7d': recent_habit_executions,
            'avg_habit_energy_7d': avg_habit_energy,
            'behavior_consistency_score': round((last_7_days / 7) * 10, 1)  # 每日平均执行次数 × 10
        }
    finally:
        _release_db(conn)


