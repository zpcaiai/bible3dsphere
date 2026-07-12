"""千人千面每日灵修 /api/daily-devotion-personal — 从 main.py 逐字搬移（路径不变，无 prefix）。

对 main.py 内部辅助（_get_session_user、is_english）通过 init_main_extracted_devotion()
在 include_router 之前注入。

注意（与 main.py 原状一致的既有行为）：路由内 ``with get_db() as (conn, cur)`` 中的
``get_db`` 在原 main.py 里就是未定义名字（NameError 被外层 except 吞掉，
formation 分数始终走默认值兜底）。逐字搬移保留该行为，未做修复；见 REFACTOR_PLAN.md。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()

# ── main.py 注入的依赖（导入期为 None，仅在请求期被调用）──
_get_session_user = None
is_english = None


def init_main_extracted_devotion(*, get_session_user, is_english_fn) -> None:
    global _get_session_user, is_english
    _get_session_user = get_session_user
    is_english = is_english_fn


# ─────────────────────────────────────────────────────────────────────────────
# 千人千面每日灵修 — Personalized Daily Devotion
# ─────────────────────────────────────────────────────────────────────────────
import datetime as _dt

# In-memory daily devotion cache: {email+date → result}
_devotion_cache: dict = {}

_DIM_THEMES = {
    'humility': {
        'label': '谦卑',
        'verse': '腓立比书2:3',
        'text': '凡事不可结党，不可贪图虚浮的荣耀；只要存心谦卑，各人看别人比自己强。',
        'theme': '谦卑服事',
    },
    'fear_tendency': {
        'label': '信靠超越恐惧',
        'verse': '以赛亚书41:10',
        'text': '你不要害怕，因为我与你同在；你不要惊惶，因为我是你的神。我必坚固你，我必帮助你，我必用我公义的右手扶持你。',
        'theme': '信靠代替恐惧',
    },
    'pride_tendency': {
        'label': '柔和谦卑',
        'verse': '雅各书4:6',
        'text': '「神阻挡骄傲的人，赐恩给谦卑的人。」',
        'theme': '降服胜过骄傲',
    },
    'emotional_stability': {
        'label': '心灵平静',
        'verse': '约翰福音14:27',
        'text': '我留下平安给你们，我将我的平安赐给你们。我所赐的不像世人所赐的。你们心里不要忧愁，也不要胆怯。',
        'theme': '神赐平安',
    },
    'truth_alignment': {
        'label': '行在真道中',
        'verse': '约翰福音8:32',
        'text': '你们必晓得真理，真理必叫你们得以自由。',
        'theme': '活在真理里',
    },
    'relational_health': {
        'label': '爱的相交',
        'verse': '约翰一书4:7',
        'text': '亲爱的弟兄啊，我们应当彼此相爱，因为爱是从神来的。凡有爱心的，都是由神而生，并且认识神。',
        'theme': '彼此相爱',
    },
    'resilience': {
        'label': '在苦难中得胜',
        'verse': '罗马书8:28',
        'text': '我们晓得万事都互相效力，叫爱神的人得益处，就是按他旨意被召的人。',
        'theme': '苦难中有盼望',
    },
    'spiritual_clarity': {
        'label': '灵命清醒',
        'verse': '歌罗西书3:16',
        'text': '当用各样的智慧，把基督的道理丰丰富富地存在心里，用诗章、颂词、灵歌彼此教导，互相劝戒，心被恩感，歌颂神。',
        'theme': '以基督为中心',
    },
}

_GROWTH_STAGES = {
    'blind_spot': ('🌱', '盲点期', '今日愿意放开自我防御，以温柔接受真理。'),
    'growing':    ('🌿', '成长期', '今日操练所知，让知识变成生命的果实。'),
    'stable':     ('🌳', '稳定期', '今日分享所得，以服事他人巩固自己的成长。'),
}


@router.get('/api/daily-devotion-personal')
def get_daily_devotion_personal(request: Request) -> dict:
    """
    千人千面每日灵修 — 根据用户灵命状态（formation）生成个性化灵修内容。
    每日缓存一次，保证不重复调用LLM。
    """
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')

    email = user.get('email', '')
    today = str(_dt.date.today())
    cache_key = f"{email}:{today}:{'en' if is_english() else 'zh'}"

    if cache_key in _devotion_cache:
        return _devotion_cache[cache_key]

    # ── 1. 获取 formation 数据（从 SFDS 快照） ──
    formation_scores: dict = {}
    try:
        with get_db() as (conn, cur):
            cur.execute(
                """SELECT dimension_key, score FROM sfds_formation_snapshots
                   WHERE email=%s ORDER BY created_at DESC LIMIT 24""",
                (email,)
            )
            rows = cur.fetchall()
            for dim, score in rows:
                if dim not in formation_scores:
                    formation_scores[dim] = float(score)
    except Exception:
        pass

    # Fallback defaults if no data
    if not formation_scores:
        formation_scores = {
            'humility': 0.5, 'fear_tendency': 0.5, 'pride_tendency': 0.5,
            'emotional_stability': 0.5, 'truth_alignment': 0.5,
            'relational_health': 0.5, 'resilience': 0.5, 'spiritual_clarity': 0.5,
        }

    # ── 2. 选出今日聚焦维度（最需成长的） ──
    # For inverse dims (fear, pride), high score = needs attention
    inverse_dims = {'fear_tendency', 'pride_tendency'}
    focus_scores = {}
    for dim, score in formation_scores.items():
        if dim in inverse_dims:
            focus_scores[dim] = score  # high = needs more attention
        else:
            focus_scores[dim] = 1.0 - score  # low = needs more growth

    # Pick the dimension most needing attention (deterministic but rotates by day-of-year)
    doy = _dt.date.today().timetuple().tm_yday
    sorted_dims = sorted(focus_scores.items(), key=lambda x: (-x[1], x[0]))
    # Rotate through top-3 by day
    top3 = [d for d, _ in sorted_dims[:3]]
    focus_dim = top3[doy % len(top3)]

    theme_data = _DIM_THEMES.get(focus_dim, _DIM_THEMES['humility'])

    # ── 3. 确定成长阶段 ──
    raw_score = formation_scores.get(focus_dim, 0.5)
    if focus_dim in inverse_dims:
        normalized = raw_score
    else:
        normalized = raw_score

    if normalized < 0.35:
        stage_key = 'blind_spot'
    elif normalized < 0.65:
        stage_key = 'growing'
    else:
        stage_key = 'stable'
    stage_icon, stage_label, stage_action = _GROWTH_STAGES[stage_key]

    # ── 4. 生成个性化灵修文 ──
    devotion_text = ''
    prayer_text = ''
    try:
        from query_emotion_verses import _call_llm_with_fallback
        nickname = user.get('nickname') or user.get('name') or '弟兄姐妹'

        system_prompt = (
            "你是一位温柔、敬虔的基督徒属灵导师。请根据用户当前的灵命聚焦维度，"
            "写一段120-180字的每日灵修文。\n"
            "要求：\n"
            "- 从圣经经文切入，自然联系今日主题\n"
            "- 用温柔、鼓励的语气，不说教，不批评\n"
            "- 结尾给出一个今日具体的可行操练（一句话）\n"
            "- 直接输出正文，不要标题"
        )
        user_msg = (
            f"用户昵称：{nickname}\n"
            f"今日聚焦：{theme_data['theme']}（{theme_data['label']}）\n"
            f"经文：{theme_data['verse']}——「{theme_data['text']}」\n"
            f"成长阶段：{stage_label} {stage_icon}"
        )
        devotion_text = _call_llm_with_fallback(
            system_prompt=system_prompt,
            user_message=user_msg,
            max_tokens=350,
            temperature=0.75,
            tag="personal-devotion",
        )

        # Short prayer
        prayer_system = "你是祷告代写者，请根据今日灵修主题写一段50-80字的祷告文，用第一人称，以「奉主耶稣基督的名祷告，阿们。」结束。"
        prayer_text = _call_llm_with_fallback(
            system_prompt=prayer_system,
            user_message=f"今日主题：{theme_data['theme']}\n经文：{theme_data['verse']}",
            max_tokens=200,
            temperature=0.7,
            tag="personal-prayer",
        )
    except Exception as e:
        devotion_text = f"「{theme_data['text']}」\n\n今日愿你在{theme_data['theme']}上经历神的恩典。{stage_action}"
        prayer_text = f"主啊，今日我将{theme_data['label']}这一功课交托给你。帮助我在今天的生活中活出你的话语。奉主耶稣基督的名祷告，阿们。"

    result = {
        'focus_dim': focus_dim,
        'focus_label': theme_data['label'],
        'theme': theme_data['theme'],
        'verse_ref': theme_data['verse'],
        'verse_text': theme_data['text'],
        'stage': stage_key,
        'stage_icon': stage_icon,
        'stage_label': stage_label,
        'stage_action': stage_action,
        'devotion_text': devotion_text,
        'prayer_text': prayer_text,
        'date': today,
    }
    _devotion_cache[cache_key] = result
    return result


