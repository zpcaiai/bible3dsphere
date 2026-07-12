"""习惯养成状态机 /api/habits/* 与路线规划 /api/route — 从 main.py 逐字搬移（路径不变，无 prefix）。

对 main.py 内部辅助（_get_db、_release_db、_get_session_user、settings）通过
init_main_extracted_habits() 在 include_router 之前注入，本模块与 main 无 import 期耦合。
"""
from __future__ import annotations

import json
import os
from typing import List

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()

# ── main.py 注入的依赖（导入期为 None，仅在请求期被调用）──
_get_db = None
_release_db = None
_get_session_user = None
settings = None


def init_main_extracted_habits(*, get_db, release_db, get_session_user, settings_obj) -> None:
    global _get_db, _release_db, _get_session_user, settings
    _get_db = get_db
    _release_db = release_db
    _get_session_user = get_session_user
    settings = settings_obj


class HabitCreateRequest(BaseModel):
    habit_name: str = Field(min_length=1, max_length=200)
    anchor: str = Field(default='', max_length=200)
    energy_level: int = Field(default=3, ge=1, le=5)


class HabitExecuteRequest(BaseModel):
    habit_id: str = Field(min_length=1)
    energy_level: int = Field(default=3, ge=1, le=5)


class HabitLogRequest(BaseModel):
    habit_id: str = Field(min_length=1)
    tier_executed: str = Field(default='Yellow')
    was_completed: bool = Field(default=False)
    completion_percentage: int = Field(default=0, ge=0, le=100)
    mood_before: int = Field(default=5, ge=1, le=10)
    mood_after: int = Field(default=5, ge=1, le=10)


class FormationToHabitsRequest(BaseModel):
    """从人格塑造计划批量创建习惯的请求"""
    user_id: str = Field(min_length=1)
    plan_items: List[str] = Field(min_length=1, max_length=10)
    plan_type: str = Field(default='short', pattern='^(short|mid)$')


# ── 习惯养成状态机 API ───────────────────────────────────────

@router.post('/api/habits/create')
def create_habit_endpoint(payload: HabitCreateRequest, request: Request):
    """
    创建习惯状态机 - 三层动态电路保护
    """
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    user_id = str(user['id'])
    
    try:
        from backend.habit_behavior_engine import create_habit as _create_habit_fn
        result = _create_habit_fn(payload.habit_name, payload.anchor, payload.energy_level)
        
        # 保存到数据库
        conn = _get_db()
        try:
            with conn.cursor() as cur:
                fsm_config = result.get('habit_config', {})
                cur.execute(
                    '''INSERT INTO habit_state_machines 
                       (user_id, habit_name, deterministic_anchor, 
                        tier_green_config, tier_yellow_config, tier_red_config,
                        token_green_yield, token_yellow_yield, token_red_yield)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                       RETURNING id''',
                    (user_id, payload.habit_name, fsm_config.get('deterministic_anchor', ''),
                     json.dumps(fsm_config.get('tier_configs', {}).get('green', {})),
                     json.dumps(fsm_config.get('tier_configs', {}).get('yellow', {})),
                     json.dumps(fsm_config.get('tier_configs', {}).get('red', {})),
                     10, 5, 1)
                )
                row = cur.fetchone()
                conn.commit()
                result['saved_habit_id'] = str(row[0])
        finally:
            _release_db(conn)
        
        return result
        
    except Exception as exc:
        import traceback
        print(f'[habits_create] Failed: {exc}\n{traceback.format_exc()}', flush=True)
        raise HTTPException(status_code=500, detail='internal error')


@router.get('/api/habits')
def list_habits(request: Request):
    """获取用户的习惯列表"""
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    user_id = str(user['id'])
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT id, habit_name, deterministic_anchor, is_active,
                          current_streak_days, total_executions, last_execution_at,
                          tier_green_config, tier_yellow_config, tier_red_config
                   FROM habit_state_machines 
                   WHERE user_id = %s AND is_active = TRUE
                   ORDER BY created_at DESC''',
                (user_id,)
            )
            rows = cur.fetchall()
            
            items = [{
                'id': str(r[0]),
                'habit_name': r[1],
                'anchor': r[2],
                'is_active': r[3],
                'current_streak': r[4],
                'total_executions': r[5],
                'last_execution': r[6].isoformat() if r[6] else None,
                'tier_configs': {
                    'green': r[7] if isinstance(r[7], dict) else {},
                    'yellow': r[8] if isinstance(r[8], dict) else {},
                    'red': r[9] if isinstance(r[9], dict) else {}
                }
            } for r in rows]
            
            return {'items': items, 'total': len(items)}
    except Exception as exc:
        import traceback
        print(f'[list_habits] ERROR user_id={user_id}: {exc}\n{traceback.format_exc()}', flush=True)
        raise HTTPException(status_code=500, detail='internal error')
    finally:
        _release_db(conn)


@router.post('/api/habits/{habit_id}/execute')
def execute_habit(habit_id: str, payload: HabitExecuteRequest, request: Request):
    """
    执行习惯状态机 - 根据当前能量动态选择层级
    """
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    user_id = str(user['id'])
    
    conn = _get_db()
    try:
        # 获取习惯配置
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT habit_name, deterministic_anchor,
                          tier_green_config, tier_yellow_config, tier_red_config
                   FROM habit_state_machines 
                   WHERE id = %s AND user_id = %s''',
                (habit_id, user_id)
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail='习惯未找到')
            
            habit_config = {
                'habit_name': row[0],
                'deterministic_anchor': row[1],
                'tier_configs': {
                    'green': row[2] if isinstance(row[2], dict) else {},
                    'yellow': row[3] if isinstance(row[3], dict) else {},
                    'red': row[4] if isinstance(row[4], dict) else {}
                }
            }
        
        # 执行状态机
        from backend.habit_behavior_engine import habit_fsm
        execution = habit_fsm.execute_habit(habit_config, payload.energy_level)
        
        return execution.to_dict()
        
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        print(f'[execute_habit] ERROR habit_id={habit_id} user_id={user_id}: {exc}\n{traceback.format_exc()}', flush=True)
        raise HTTPException(status_code=500, detail='internal error')
    finally:
        _release_db(conn)


@router.post('/api/habits/{habit_id}/log')
def log_habit_execution(habit_id: str, payload: HabitLogRequest, request: Request):
    """
    记录习惯执行结果，更新代币和连胜
    """
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    user_id = str(user['id'])
    
    # 代币计算
    tier_tokens = {'Green': 10, 'Yellow': 5, 'Red': 1}
    tokens_earned = tier_tokens.get(payload.tier_executed, 5)
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # 校验 habit 归属，防止越权写入他人 habit (IDOR)
            cur.execute(
                'SELECT 1 FROM habit_state_machines WHERE id = %s AND user_id = %s',
                (habit_id, user_id)
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail='习惯不存在或无权访问')
            # 记录执行日志
            cur.execute(
                '''INSERT INTO habit_execution_logs 
                   (user_id, habit_id, energy_level_at_execution, selected_tier,
                    tokens_earned, was_completed, completion_percentage,
                    circuit_breaker_triggered, mood_before, mood_after)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id''',
                (user_id, habit_id, 3, payload.tier_executed,
                 tokens_earned, payload.was_completed, payload.completion_percentage,
                 payload.tier_executed == 'Red',
                 payload.mood_before, payload.mood_after)
            )
            log_id = cur.fetchone()[0]
            
            # 更新习惯统计
            if payload.was_completed:
                cur.execute(
                    '''UPDATE habit_state_machines 
                       SET total_executions = total_executions + 1,
                           last_execution_at = NOW(),
                           current_streak_days = CASE 
                               WHEN last_execution_at >= CURRENT_DATE - INTERVAL '1 day' 
                               THEN current_streak_days + 1 
                               ELSE 1 
                           END
                       WHERE id = %s AND user_id = %s''',
                    (habit_id, user_id)
                )
            
            # 更新代币账本
            cur.execute(
                '''INSERT INTO user_token_ledgers (user_id, current_balance, lifetime_earned)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (user_id) 
                   DO UPDATE SET 
                       current_balance = user_token_ledgers.current_balance + %s,
                       lifetime_earned = user_token_ledgers.lifetime_earned + %s,
                       last_updated = NOW()''',
                (user_id, tokens_earned, tokens_earned, tokens_earned, tokens_earned)
            )
            
            # 记录代币交易
            cur.execute(
                '''INSERT INTO token_transactions 
                   (user_id, transaction_type, amount, balance_after, habit_id, habit_log_id, description)
                   VALUES (%s, %s, %s, 
                       (SELECT current_balance FROM user_token_ledgers WHERE user_id = %s),
                       %s, %s, %s)''',
                (user_id, 'earn', tokens_earned, user_id, 
                 habit_id, log_id, f'{payload.tier_executed} tier execution')
            )
            
            conn.commit()
            
            return {
                'ok': True,
                'log_id': str(log_id),
                'tokens_earned': tokens_earned,
                'circuit_breaker_triggered': payload.tier_executed == 'Red',
                'anti_guilt_message': '系统已切换至保护模式。连胜保持。核心控制回路完整性100%。' 
                    if payload.tier_executed == 'Red' else None
            }
            
    finally:
        _release_db(conn)


class HabitNoteRequest(BaseModel):
    note: str = Field(default='', max_length=2000)


@router.post('/api/habits/{habit_id}/note')
def save_habit_note(habit_id: str, payload: HabitNoteRequest, request: Request):
    """Persist today's per-habit note WITHOUT counting a habit execution."""
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    user_id = str(user['id'])
    note = (payload.note or '')[:2000]
    today = __import__('datetime').date.today()
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO habit_daily_notes (user_id, habit_id, note_date, note, updated_at)
                   VALUES (%s, %s, %s, %s, NOW())
                   ON CONFLICT (user_id, habit_id, note_date)
                   DO UPDATE SET note = EXCLUDED.note, updated_at = NOW()""",
                (user_id, habit_id, today, note),
            )
            conn.commit()
        return {'ok': True}
    finally:
        _release_db(conn)


def _catmull_rom_chain(pts, samples_per_seg: int = 14):
    """Smooth curve through ``pts`` ([[lng,lat],...]) via Catmull-Rom — gives a
    natural sailing arc instead of a straight line. Endpoints duplicated."""
    if len(pts) < 2:
        return list(pts)
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s_i in range(samples_per_seg):
            t = s_i / samples_per_seg
            t2 = t * t
            t3 = t2 * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t +
                       (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                       (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t +
                       (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                       (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append([round(x, 5), round(y, 5)])
    out.append([round(pts[-1][0], 5), round(pts[-1][1], 5)])
    return out


def _sea_route(clean):
    """Realistic sea route along shipping lanes (searoute if installed),
    otherwise a smooth Catmull-Rom sailing arc through the ports. Never a
    straight line."""
    # Prefer real maritime routing if the optional `searoute` package is present.
    try:
        import searoute as _sr  # optional; add `searoute` to requirements to enable
        full = []
        for i in range(len(clean) - 1):
            o = clean[i]
            d = clean[i + 1]
            route = _sr.searoute(o, d)
            coords = route['geometry']['coordinates']
            if i > 0 and coords:
                coords = coords[1:]
            full.extend([[round(float(c[0]), 5), round(float(c[1]), 5)] for c in coords])
        if len(full) >= 2:
            return full
    except Exception as exc:
        print(f'[route] searoute unavailable, using sailing arc: {exc}', flush=True)
    return _catmull_rom_chain(clean)


class RouteRequest(BaseModel):
    coordinates: list = Field(default_factory=list)  # [[lng,lat], ...] in order
    profile: str = Field(default='foot-walking', max_length=24)


@router.post('/api/route')
def plan_route(payload: RouteRequest):
    """Walking-route proxy (OpenRouteService) with DB cache.

    Returns {ok, geometry:[[lng,lat],...]} for land journeys. On any failure
    (no API key, sea legs ORS can't route, distance limits, timeout) returns
    {ok: false} so clients fall back to a straight line.
    """
    coords = payload.coordinates or []
    # Validate / sanitise: 2..50 numeric [lng,lat] pairs.
    clean = []
    for c in coords[:50]:
        try:
            lng = float(c[0]); lat = float(c[1])
        except Exception:
            continue
        if -180 <= lng <= 180 and -90 <= lat <= 90:
            clean.append([round(lng, 5), round(lat, 5)])
    if len(clean) < 2:
        return {'ok': False, 'reason': 'need>=2 coords'}
    profile = payload.profile if payload.profile in (
        'foot-walking', 'foot-hiking', 'driving-car', 'sea') else 'foot-walking'

    import hashlib
    key = hashlib.sha1(
        (profile + '|' + ';'.join(f'{a},{b}' for a, b in clean)).encode()
    ).hexdigest()

    # 1) cache lookup
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute('SELECT geometry FROM route_cache WHERE cache_key=%s', (key,))
                row = cur.fetchone()
                if row and row[0]:
                    geom = row[0] if isinstance(row[0], list) else json.loads(row[0])
                    return {'ok': True, 'geometry': geom, 'cached': True}
            except Exception:
                conn.rollback()
    finally:
        _release_db(conn)

    # 2) sea legs → maritime/sailing route (no API key needed)
    if profile == 'sea':
        geom = _sea_route(clean)
        conn = _get_db()
        try:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        'INSERT INTO route_cache (cache_key, geometry) VALUES (%s, %s) '
                        'ON CONFLICT (cache_key) DO NOTHING',
                        (key, json.dumps(geom)),
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()
        finally:
            _release_db(conn)
        return {'ok': True, 'geometry': geom}

    # 3) call OpenRouteService
    ors_key = os.environ.get('ORS_API_KEY', '') or getattr(settings, 'ors_api_key', '') or ''
    if not ors_key or ors_key.startswith('your_'):
        return {'ok': False, 'reason': 'no_key'}
    try:
        url = f'https://api.openrouteservice.org/v2/directions/{profile}/geojson'
        with httpx.Client(timeout=20) as client:
            resp = client.post(url, headers={
                'Authorization': ors_key,
                'Content-Type': 'application/json',
            }, json={'coordinates': clean})
        if resp.status_code >= 400:
            return {'ok': False, 'reason': f'ors {resp.status_code}'}
        data = resp.json()
        geom = data['features'][0]['geometry']['coordinates']
        geom = [[round(float(p[0]), 5), round(float(p[1]), 5)] for p in geom]
    except Exception as exc:
        print(f'[route] ORS failed: {exc}', flush=True)
        return {'ok': False, 'reason': 'ors_error'}

    # 3) store in cache (best-effort)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    'INSERT INTO route_cache (cache_key, geometry) VALUES (%s, %s) '
                    'ON CONFLICT (cache_key) DO NOTHING',
                    (key, json.dumps(geom)),
                )
                conn.commit()
            except Exception:
                conn.rollback()
    finally:
        _release_db(conn)

    return {'ok': True, 'geometry': geom}


@router.get('/api/habits/today')
def habits_today(request: Request):
    """Per-habit today state: done (from execution logs) + note (from daily notes)."""
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    user_id = str(user['id'])
    today = __import__('datetime').date.today()
    conn = _get_db()
    try:
        merged: dict = {}
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """SELECT habit_id, BOOL_OR(was_completed)
                       FROM habit_execution_logs
                       WHERE user_id = %s AND executed_at::date = %s
                       GROUP BY habit_id""",
                    (user_id, today),
                )
                for r in cur.fetchall():
                    merged.setdefault(str(r[0]), {})['done'] = bool(r[1])
            except Exception:
                conn.rollback()
            try:
                cur.execute(
                    "SELECT habit_id, note FROM habit_daily_notes WHERE user_id = %s AND note_date = %s",
                    (user_id, today),
                )
                for r in cur.fetchall():
                    merged.setdefault(str(r[0]), {})['note'] = r[1] or ''
            except Exception:
                conn.rollback()
        items = [
            {'habit_id': k, 'done': v.get('done', False), 'note': v.get('note', '')}
            for k, v in merged.items()
        ]
        return {'items': items}
    finally:
        _release_db(conn)


@router.get('/api/habits/dashboard')
def habits_dashboard(request: Request):
    """习惯系统仪表盘"""
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    user_id = str(user['id'])
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # Try view first, fall back to direct query if view doesn't exist
            try:
                cur.execute(
                    '''SELECT active_habits, today_executions, max_current_streak,
                              token_balance, last_habit_name, circuit_breaker_count
                       FROM user_habit_dashboard 
                       WHERE user_id = %s''',
                    (user_id,)
                )
                row = cur.fetchone()
            except Exception as view_exc:
                print(f'[habits_dashboard] view query failed, using direct query: {view_exc}', flush=True)
                conn.rollback()
                cur.execute(
                    '''SELECT
                           COUNT(DISTINCT id) FILTER (WHERE is_active) AS active_habits,
                           0 AS today_executions,
                           COALESCE(MAX(current_streak_days), 0) AS max_current_streak,
                           0 AS token_balance,
                           NULL AS last_habit_name,
                           0 AS circuit_breaker_count
                       FROM habit_state_machines
                       WHERE user_id = %s''',
                    (user_id,)
                )
                row = cur.fetchone()
            
            if not row:
                return {
                    'active_habits': 0,
                    'today_executions': 0,
                    'current_streak': 0,
                    'token_balance': 0,
                    'circuit_breaker_count': 0
                }
            
            return {
                'active_habits': row[0] or 0,
                'today_executions': row[1] or 0,
                'current_streak': row[2] or 0,
                'token_balance': row[3] or 0,
                'last_habit_name': row[4],
                'circuit_breaker_count': row[5] or 0
            }
    except Exception as exc:
        import traceback
        print(f'[habits_dashboard] ERROR user_id={user_id}: {exc}\n{traceback.format_exc()}', flush=True)
        raise HTTPException(status_code=500, detail='internal error')
    finally:
        _release_db(conn)


@router.post('/api/habits/create-from-formation')
def create_habits_from_formation(payload: FormationToHabitsRequest, request: Request):
    """
    从人格塑造计划批量创建习惯
    将反思问卷生成的灵修计划自动同步为习惯状态机
    """
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    user_id = str(user['id'])
    
    # 验证用户只能为自己创建习惯
    if user_id != payload.user_id:
        raise HTTPException(status_code=403, detail='只能为自己的账户创建习惯')
    
    created_count = 0
    created_habits = []
    
    try:
        from backend.habit_behavior_engine import create_habit as _create_habit_fn
        
        conn = _get_db()
        try:
            for item in payload.plan_items:
                # 生成习惯名称（从计划文本中提取关键词）
                habit_name = item[:50] if len(item) <= 50 else item[:47] + '...'
                
                # 根据计划类型设置不同的默认能量等级
                default_energy = 3 if payload.plan_type == 'short' else 4
                
                # 调用引擎创建习惯配置
                result = _create_habit_fn(habit_name, '', default_energy)
                
                # 保存到数据库
                with conn.cursor() as cur:
                    fsm_config = result.get('habit_config', {})
                    cur.execute(
                        '''INSERT INTO habit_state_machines 
                           (user_id, habit_name, deterministic_anchor, 
                            tier_green_config, tier_yellow_config, tier_red_config,
                            token_green_yield, token_yellow_yield, token_red_yield,
                            source_type, source_ref)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           RETURNING id''',
                        (
                            user_id, 
                            habit_name, 
                            result.get('deterministic_anchor', ''),
                            json.dumps(fsm_config.get('Green', {})),
                            json.dumps(fsm_config.get('Yellow', {})),
                            json.dumps(fsm_config.get('Red', {})),
                            result.get('token_yield', 5),
                            max(3, result.get('token_yield', 5) - 1),
                            1,  # Red tier minimum yield
                            'formation_plan',  # 标记来源
                            payload.plan_type  # short or mid
                        )
                    )
                    row = cur.fetchone()
                    created_id = str(row[0])
                    created_count += 1
                    created_habits.append({
                        'id': created_id,
                        'name': habit_name,
                        'tier': result.get('selected_tier', 'Yellow')
                    })
            
            conn.commit()
            
        finally:
            _release_db(conn)
        
        return {
            'ok': True,
            'created_count': created_count,
            'habits': created_habits,
            'plan_type': payload.plan_type,
            'message': f'成功创建 {created_count} 个来自人格塑造计划的习惯'
        }
        
    except Exception as exc:
        import traceback
        print(f'[create_habits_from_formation] ERROR user_id={user_id}: {exc}\n{traceback.format_exc()}', flush=True)
        raise HTTPException(status_code=500, detail='internal error')


