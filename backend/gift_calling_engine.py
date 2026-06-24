#!/usr/bin/env python3
"""
Gift & Calling Engine — Spiritual Planet GCOS v1.0 (MVP3)
=========================================================

恩赐与呼召识别引擎：把"识别天然优势 / 属灵恩赐 / 属灵果子 / 使命负担 /
误用风险 / 服事匹配 / 成长计划"落成一个可计算、可复盘的闭环。

八个子 Agent（与产品设计一致）：
    1 Strength Profiler        天然优势画像
    2 Spiritual Gifts          属灵恩赐辨识
    3 Fruit Verification       属灵果子验证（防止只看"能力/恩赐"）
    4 Calling Pattern          使命负担模式（记录反复主题，非宣告呼召）
    5 Community Confirmation    共同体确认（生成反馈表 + 聚合已有反馈）
    6 Misuse Risk              恩赐误用风险（含福音重构 + 操练）
    7 Ministry Matching        服事岗位匹配（A/B/C/D 级 + 保护机制）
    8 Growth Path Planner      30/90/180 天成长计划
   (Orchestrator: assess() 顺序聚合，输出完整报告)

工程取向（与 disciple_engine / crisis_engine 一致）：
    - 确定性核心：纯函数 + 关键词启发式，零依赖可跑，永远返回完整报告。
    - AI 增强：复用 waiting_engine.call_ai_provider（OpenAI 兼容）。一次结构化 JSON
      调用产出全部维度/恩赐/果子/使命/风险/服事/计划；失败回退确定性结果。
    - 本模块不落库、不依赖 FastAPI（便于单测）；落库与回流由 routers/gift_calling.py 负责。

神学护栏（贯穿 AI 提示词与输出）：
    - 不宣告最终呼召，只给"可能倾向 / 可探索方向 / 需共同体确认"。
    - 恩赐分数不是属灵等级；身份根基在基督里，不在恩赐表现。
    - 一切导向：爱神爱人、建造教会、服事邻舍、荣耀基督、在真理中成长。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# 0. 输入字段（前端问卷 / 自由文本）。引擎把所有文本拼接后做关键词启发式。
# ─────────────────────────────────────────────────────────────────────────────

INPUT_FIELDS: List[Dict[str, str]] = [
    {"key": "experiences",  "zh": "长期经历 / 项目 / 服事记录"},
    {"key": "interests",    "zh": "长期反复关注的主题与问题"},
    {"key": "service",      "zh": "服事经历与果效"},
    {"key": "others_say",   "zh": "别人常请你帮助什么 / 他人反馈"},
    {"key": "burdens",      "zh": "你为谁、为什么愿意付代价"},
    {"key": "skills",       "zh": "后天技能 / 专业能力"},
    {"key": "struggles",    "zh": "压力下的反应 / 试探 / 软弱"},
    {"key": "faith_journey","zh": "信仰历程 / 灵修与教会生活"},
]
INPUT_KEYS = [f["key"] for f in INPUT_FIELDS]

CONFIDENCE_LEVELS = ("low", "medium", "high")
IDENTITY_REMINDER = (
    "你的身份不是「有恩赐的人」，而是「在基督里蒙爱的神儿女」。"
    "恩赐是为爱而赐、为建造教会而用、为荣耀基督而归还给神。"
)
BOUNDARY_NOTICE = (
    "本系统只提供属灵恩赐与优势的辅助辨识，不宣告你的最终呼召。"
    "最终方向需要圣经、祷告、教会共同体、牧者确认与长期忠心验证。"
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. 天然优势 — 10 维
# ─────────────────────────────────────────────────────────────────────────────

STRENGTHS: List[Dict[str, Any]] = [
    {"key": "cognitive",  "zh": "认知 / 系统思考",
     "kw": ["系统", "逻辑", "抽象", "结构", "整合", "分析", "概念", "模式", "框架", "system", "architecture"]},
    {"key": "expression", "zh": "表达 / 讲解",
     "kw": ["写作", "讲解", "讲道", "表达", "说服", "叙事", "文字", "演讲", "可视化", "课程"]},
    {"key": "relational", "zh": "关系 / 共情",
     "kw": ["倾听", "共情", "陪伴", "关心", "信任", "调解", "体谅", "关系", "安慰"]},
    {"key": "execution",  "zh": "执行 / 推进",
     "kw": ["计划", "推进", "落地", "项目", "执行", "解决问题", "复盘", "交付", "完成", "迭代"]},
    {"key": "creativity", "zh": "创造 / 设计",
     "kw": ["设计", "创作", "创意", "审美", "艺术", "产品", "发明", "世界观", "游戏", "内容"]},
    {"key": "leadership", "zh": "领导 / 组织",
     "kw": ["异象", "决策", "组织", "带领", "动员", "授权", "团队", "领袖", "影响力"]},
    {"key": "discernment","zh": "分辨 / 辨析",
     "kw": ["分辨", "辨析", "风险", "谬误", "判断", "护教", "世界观", "警觉", "识别", "批判"]},
    {"key": "learning",   "zh": "学习 / 跨学科",
     "kw": ["自学", "研究", "跨学科", "学习", "钻研", "迁移", "好奇", "阅读", "掌握"]},
    {"key": "technical",  "zh": "技术 / 工具",
     "kw": ["编程", "代码", "数据", "ai", "架构", "自动化", "工具", "知识图谱", "工程", "java", "python"]},
    {"key": "resilience", "zh": "韧性 / 坚持",
     "kw": ["坚持", "恢复", "承担", "压力", "不确定", "失败中", "长期", "毅力", "扛"]},
]
STRENGTH_KEYS = [s["key"] for s in STRENGTHS]
STRENGTH_ZH = {s["key"]: s["zh"] for s in STRENGTHS}
STRENGTH_COL = {k: f"{k}_score" for k in STRENGTH_KEYS}


# ─────────────────────────────────────────────────────────────────────────────
# 2. 属灵恩赐 — 15 类（参考 罗12 / 林前12 / 弗4 / 彼前4）
# ─────────────────────────────────────────────────────────────────────────────

GIFTS: List[Dict[str, Any]] = [
    {"key": "teaching",      "zh": "教导",
     "kw": ["教导", "讲解圣经", "课程", "查经", "结构化真理", "讲道", "释经", "主日学"]},
    {"key": "exhortation",   "zh": "劝勉",
     "kw": ["鼓励", "劝勉", "安慰", "提醒", "推动", "造就", "陪跑"]},
    {"key": "shepherding",   "zh": "牧养",
     "kw": ["牧养", "守望", "长期关心", "陪伴成长", "小组", "门徒", "看顾"]},
    {"key": "mercy",         "zh": "怜悯",
     "kw": ["怜悯", "软弱者", "受伤", "苦难", "照顾", "同情", "扶持"]},
    {"key": "giving",        "zh": "施予",
     "kw": ["奉献", "资源", "支持", "施予", "供应", "慷慨"]},
    {"key": "administration","zh": "治理",
     "kw": ["组织", "流程", "治理", "管理", "统筹", "事工运作", "秩序", "协调"]},
    {"key": "faith",         "zh": "信心",
     "kw": ["信心", "应许", "信靠神", "祷告蒙应允", "冒险信心", "凭信"]},
    {"key": "discernment",   "zh": "分辨诸灵",
     "kw": ["分辨", "假教导", "属灵危险", "动机", "时代精神", "护教", "异端", "谬误"]},
    {"key": "evangelism",    "zh": "传福音",
     "kw": ["传福音", "未信者", "福音", "布道", "带人信主", "外展", "慕道"]},
    {"key": "wisdom",        "zh": "智慧",
     "kw": ["智慧", "应用真理", "复杂处境", "辅导", "出主意", "落地建议"]},
    {"key": "knowledge",     "zh": "知识",
     "kw": ["神学", "研究", "归纳", "知识", "系统神学", "整理资料", "考据"]},
    {"key": "hospitality",   "zh": "接待",
     "kw": ["接待", "开放", "接纳", "招待", "安全空间", "款待"]},
    {"key": "mission",       "zh": "宣教",
     "kw": ["宣教", "跨文化", "未得之民", "差传", "边缘人群", "禾场"]},
    {"key": "pioneering",    "zh": "开拓",
     "kw": ["开拓", "开创", "新事工", "新平台", "新方法", "拓荒", "从0到1", "mvp"]},
    {"key": "worship",       "zh": "敬拜 / 艺术",
     "kw": ["敬拜", "音乐", "诗歌", "艺术", "视觉", "创作引导", "赞美"]},
]
GIFT_KEYS = [g["key"] for g in GIFTS]
GIFT_ZH = {g["key"]: g["zh"] for g in GIFTS}


# ─────────────────────────────────────────────────────────────────────────────
# 3. 圣灵果子 — 9（加 5:22-23）。pos/neg 关键词。
# ─────────────────────────────────────────────────────────────────────────────

FRUITS: List[Dict[str, Any]] = [
    {"key": "love",         "zh": "仁爱",
     "pos": ["爱人", "饶恕", "关心", "舍己", "体谅", "和好"], "neg": ["恨", "记仇", "冷漠", "嫉妒", "自私"]},
    {"key": "joy",          "zh": "喜乐",
     "pos": ["喜乐", "感恩", "在主里喜乐", "知足"], "neg": ["焦虑", "比较", "苦毒", "怨"]},
    {"key": "peace",        "zh": "和平",
     "pos": ["合一", "和好", "平安", "调解", "和睦"], "neg": ["争竞", "紧张", "冲突", "争吵", "分裂"]},
    {"key": "patience",     "zh": "忍耐",
     "pos": ["忍耐", "等候", "给时间", "持守", "宽容"], "neg": ["急躁", "受不了", "等不及", "暴躁"]},
    {"key": "kindness",     "zh": "恩慈",
     "pos": ["恩慈", "温柔待人", "体恤", "善待", "亲切"], "neg": ["尖锐", "刻薄", "伤人", "冷硬"]},
    {"key": "goodness",     "zh": "良善",
     "pos": ["正直", "诚实", "行在光中", "良善", "守正"], "neg": ["欺瞒", "暗昧", "动机不纯", "虚伪"]},
    {"key": "faithfulness", "zh": "信实",
     "pos": ["守约", "稳定", "可靠", "忠心", "尽责"], "neg": ["失信", "半途而废", "不可靠", "拖延"]},
    {"key": "gentleness",   "zh": "温柔",
     "pos": ["温柔", "不压迫", "柔和", "谦和", "留余地"], "neg": ["压迫", "强势", "咄咄逼人", "控制"]},
    {"key": "self_control", "zh": "节制",
     "pos": ["节制", "自律", "克制", "管住", "界限"], "neg": ["放纵", "冲动", "上瘾", "失控", "怒气"]},
]
FRUIT_KEYS = [f["key"] for f in FRUITS]
FRUIT_ZH = {f["key"]: f["zh"] for f in FRUITS}
FRUIT_COL = {k: f"{k}_score" for k in FRUIT_KEYS}


# ─────────────────────────────────────────────────────────────────────────────
# 4. 使命负担模式 — 12 类
# ─────────────────────────────────────────────────────────────────────────────

CALLINGS: List[Dict[str, Any]] = [
    {"key": "teaching_formation",     "zh": "教导建造型",
     "kw": ["教导", "课程", "查经", "主日学", "门训材料", "讲道", "建造信徒"]},
    {"key": "apologetics_discernment","zh": "护教学辨析型",
     "kw": ["护教", "哲学", "科学", "世界观", "ai", "辨析", "无神论", "怀疑", "理性"]},
    {"key": "pastoral_care",          "zh": "牧养关怀型",
     "kw": ["牧养", "陪伴", "关怀", "受伤", "困惑", "守望", "探访"]},
    {"key": "crisis_intervention",    "zh": "危机干预型",
     "kw": ["危机", "崩溃", "抑郁", "自杀", "创伤", "重大压力", "信仰崩塌"]},
    {"key": "mission_outreach",       "zh": "宣教拓展型",
     "kw": ["宣教", "未信者", "跨文化", "外展", "福音", "未得之民"]},
    {"key": "marketplace_discipleship","zh": "职场门训型",
     "kw": ["职场", "工作", "商业", "技术", "管理", "信仰整合", "门训职场"]},
    {"key": "creative_worship",       "zh": "创作敬拜型",
     "kw": ["音乐", "艺术", "视频", "游戏", "文学", "视觉", "敬拜", "创作"]},
    {"key": "system_building",        "zh": "系统建造型",
     "kw": ["平台", "工具", "知识图谱", "系统", "agent", "门训系统", "产品", "自动化"]},
    {"key": "children_youth",         "zh": "儿童青少年型",
     "kw": ["儿童", "青少年", "下一代", "青年", "校园", "品格教育"]},
    {"key": "church_governance",      "zh": "教会治理型",
     "kw": ["教会组织", "流程", "事工管理", "资源", "团队管理", "行政"]},
    {"key": "justice_mercy",          "zh": "公义怜悯型",
     "kw": ["贫穷", "边缘", "压迫", "弱势", "公义", "社会", "怜悯事工"]},
    {"key": "theology_research",      "zh": "神学研究型",
     "kw": ["圣经研究", "系统神学", "历史神学", "哲学神学", "教义", "研究转化"]},
]
CALLING_KEYS = [c["key"] for c in CALLINGS]
CALLING_ZH = {c["key"]: c["zh"] for c in CALLINGS}


# ─────────────────────────────────────────────────────────────────────────────
# 5. 误用风险 — 由高分恩赐/优势触发；含福音重构 + 操练
# ─────────────────────────────────────────────────────────────────────────────

RISKS: List[Dict[str, Any]] = [
    {"key": "pride", "zh": "知识骄傲",
     "triggers": ["teaching", "knowledge", "discernment", "cognitive"],
     "fruits": ["love", "gentleness"],
     "reframe": "在基督里你已被父神完全接纳，不需要用「正确」来证明价值。",
     "practice": "每次指出问题前，先真诚肯定对方一个合理的关切。"},
    {"key": "control", "zh": "控制欲",
     "triggers": ["leadership", "administration", "execution"],
     "fruits": ["patience", "gentleness"],
     "reframe": "神坐着为王，把你紧抓不放的主权交还给祂。",
     "practice": "在一件事上主动授权，并接受别人用不同方式完成。"},
    {"key": "criticism", "zh": "批判强于建造",
     "triggers": ["discernment", "knowledge"],
     "fruits": ["love", "kindness"],
     "reframe": "基督知道全部真理，却用恩典接近软弱的人；真理是为把人带向生命。",
     "practice": "每次辨析后，写下一句能造就对方、给人盼望的话。"},
    {"key": "comparison", "zh": "比较心",
     "triggers": ["leadership", "teaching", "expression"],
     "fruits": ["joy", "peace"],
     "reframe": "你的价值不在胜过别人，乃在天父称你为爱子/爱女。",
     "practice": "为一位同工的恩赐与果效真诚感恩并当面祝福。"},
    {"key": "people_pleasing", "zh": "讨好人",
     "triggers": ["mercy", "exhortation", "relational"],
     "fruits": ["faithfulness", "self_control"],
     "reframe": "你只需讨神喜悦；在祂里面你已被爱，不必靠取悦换取接纳。",
     "practice": "在合宜处温柔而诚实地说出一个真实但不讨好的看见。"},
    {"key": "boundary_blur", "zh": "边界混乱",
     "triggers": ["mercy", "hospitality"],
     "fruits": ["self_control", "peace"],
     "reframe": "唯有神是救主，你不必拯救每一个人；安息在祂的供应里。",
     "practice": "设定一个清晰的服事界限（时间/精力），并向人坦诚说明。"},
    {"key": "efficiency_idol", "zh": "效率偶像 / 技术救世主义",
     "triggers": ["technical", "execution", "administration"],
     "fruits": ["love", "patience"],
     "reframe": "神要的是你这个人，不是你产出的工；不能用模型代替爱。",
     "practice": "本周留一段不追求产出的安静祷告与陪伴时间。"},
    {"key": "instability", "zh": "虎头蛇尾 / 不受约束",
     "triggers": ["creativity", "pioneering"],
     "fruits": ["faithfulness", "self_control"],
     "reframe": "忠心于小事的，才被托付更大的；恩赐需在顺服与共同体中受约束。",
     "practice": "选一个已开始的项目，定一个可交付的小成果并完成它。"},
    {"key": "result_idol", "zh": "结果主义",
     "triggers": ["evangelism", "mission", "leadership"],
     "fruits": ["love", "patience"],
     "reframe": "人是神所爱的，不是你的项目或业绩；果效在乎神。",
     "practice": "把一个人当作完整的人去倾听，而不带任何转化目标。"},
]
RISK_KEYS = [r["key"] for r in RISKS]
RISK_ZH = {r["key"]: r["zh"] for r in RISKS}


# ─────────────────────────────────────────────────────────────────────────────
# 6. 服事岗位目录（匹配用）。required = 恩赐/优势键；fruits = 关键果子。
# ─────────────────────────────────────────────────────────────────────────────

MINISTRIES: List[Dict[str, Any]] = [
    {"key": "apologetics_course", "zh": "护教学课程开发",
     "gifts": ["teaching", "discernment", "knowledge"], "strengths": ["cognitive", "discernment", "technical"],
     "fruits": ["gentleness", "patience", "love"], "risks": ["pride", "criticism"],
     "safeguards": ["牧者/神学成熟者审核内容", "小组试讲并收集反馈"],
     "first_step": "准备一次 10 分钟护教学问答分享，在 2-3 人中试讲。"},
    {"key": "sunday_school_material", "zh": "主日学 / 门训材料设计",
     "gifts": ["teaching", "knowledge"], "strengths": ["cognitive", "expression"],
     "fruits": ["patience", "love"], "risks": ["pride"],
     "safeguards": ["先从材料辅助做起，不必马上主讲", "请老师审阅"],
     "first_step": "把一段经文做成一页结构化查经提纲。"},
    {"key": "ai_faith_tool", "zh": "AI 信仰教育工具开发",
     "gifts": ["teaching", "pioneering", "knowledge"], "strengths": ["technical", "cognitive", "creativity"],
     "fruits": ["love", "self_control"], "risks": ["efficiency_idol", "instability"],
     "safeguards": ["加入神学护栏，AI 不替代牧养", "牧者参与产品评审"],
     "first_step": "为一个真实属灵需求做一个最小可用原型并请人试用。"},
    {"key": "small_group_lead", "zh": "小组查经带领",
     "gifts": ["teaching", "shepherding", "exhortation"], "strengths": ["relational", "expression"],
     "fruits": ["love", "patience"], "risks": ["control", "pride"],
     "safeguards": ["与同工搭配带领", "定期向牧者复盘"],
     "first_step": "带一次小组查经，邀请一位成熟肢体观察反馈。"},
    {"key": "seeker_qa", "zh": "慕道班 / 线上信仰问答",
     "gifts": ["evangelism", "teaching", "discernment"], "strengths": ["expression", "relational"],
     "fruits": ["gentleness", "love"], "risks": ["result_idol", "criticism"],
     "safeguards": ["先倾听再回应", "避免赢得争论式表达"],
     "first_step": "回答 3 个慕道友常问的问题，每个先复述对方的真实顾虑。"},
    {"key": "pastoral_care", "zh": "关怀探访",
     "gifts": ["mercy", "shepherding"], "strengths": ["relational", "resilience"],
     "fruits": ["love", "patience"], "risks": ["boundary_blur", "people_pleasing"],
     "safeguards": ["明确服事界限", "重个案转介牧者/专业辅导"],
     "first_step": "本月固定关怀一位软弱中的肢体，记录界限与代祷。"},
    {"key": "crisis_companion", "zh": "危机陪伴",
     "gifts": ["mercy", "discernment", "faith"], "strengths": ["relational", "resilience"],
     "fruits": ["peace", "self_control", "love"], "risks": ["boundary_blur"],
     "safeguards": ["必须有牧者/专业辅导督导", "严重个案立即转介"],
     "first_step": "完成一次危机陪伴基础训练，明确转介红线。"},
    {"key": "content_writing", "zh": "文字 / 媒体事工",
     "gifts": ["teaching", "worship", "knowledge"], "strengths": ["expression", "creativity"],
     "fruits": ["faithfulness", "gentleness"], "risks": ["comparison", "instability"],
     "safeguards": ["内容受同工审阅", "建立稳定产出节奏"],
     "first_step": "写一篇 800 字短文并请 2 人反馈是否造就人。"},
    {"key": "worship_arts", "zh": "敬拜 / 艺术事工",
     "gifts": ["worship"], "strengths": ["creativity", "expression"],
     "fruits": ["gentleness", "faithfulness"], "risks": ["comparison", "instability"],
     "safeguards": ["以服事神而非表演为心志", "团队配搭"],
     "first_step": "在一次聚会中配搭服事，事后请团队反馈。"},
    {"key": "church_admin", "zh": "教会行政 / 流程管理",
     "gifts": ["administration"], "strengths": ["execution", "leadership"],
     "fruits": ["patience", "gentleness"], "risks": ["control", "efficiency_idol"],
     "safeguards": ["把人放在效率之上", "重大决定与团队商议"],
     "first_step": "优化一个具体事工流程，并征求受影响同工的意见。"},
    {"key": "marketplace_discipleship", "zh": "职场门训",
     "gifts": ["teaching", "exhortation", "wisdom"], "strengths": ["leadership", "relational"],
     "fruits": ["faithfulness", "love"], "risks": ["pride", "comparison"],
     "safeguards": ["从同侪同行做起", "牧者属灵遮盖"],
     "first_step": "约一位职场基督徒，每两周一次信仰与工作整合对谈。"},
    {"key": "mission_outreach", "zh": "宣教外展",
     "gifts": ["mission", "evangelism", "pioneering"], "strengths": ["resilience", "relational"],
     "fruits": ["love", "patience"], "risks": ["result_idol", "instability"],
     "safeguards": ["在差派机构/教会架构下行动", "长期委身而非短期热情"],
     "first_step": "参与一次外展，事后复盘是否真的把人带近神。"},
]
MINISTRY_KEYS = [m["key"] for m in MINISTRIES]
MINISTRY_ZH = {m["key"]: m["zh"] for m in MINISTRIES}

LEVEL_ORDER = {"A": 3, "B": 2, "C": 1, "D": 0}


# ─────────────────────────────────────────────────────────────────────────────
# 7. 启发式打分工具
# ─────────────────────────────────────────────────────────────────────────────

def _clamp(x: float, lo: int = 0, hi: int = 100) -> int:
    return int(max(lo, min(hi, round(x))))


def _blob(inputs: Dict[str, Any]) -> str:
    """把所有字符串输入拼接为单一文本（小写化以匹配英文关键词）。"""
    parts: List[str] = []
    for v in (inputs or {}).values():
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, (list, tuple)):
            parts.extend(str(x) for x in v)
    return "\n".join(parts).lower()


def _hits(text: str, kws: List[str]) -> List[str]:
    """返回命中的关键词列表（去重，保序）。"""
    seen: List[str] = []
    for k in kws:
        if k.lower() in text and k not in seen:
            seen.append(k)
    return seen


def _score_from_hits(n_hits: int, base: int = 30, step: int = 14, cap: int = 96) -> int:
    if n_hits <= 0:
        return base
    return _clamp(base + n_hits * step, base, cap)


def _avg(vals: List[float]) -> float:
    vals = [v for v in vals if isinstance(v, (int, float))]
    return (sum(vals) / len(vals)) if vals else 0.0


def _confidence(total_chars: int, signal: int) -> str:
    """资料越多、信号越强 → 置信度越高。"""
    if total_chars < 120 or signal <= 2:
        return "low"
    if total_chars < 600 or signal <= 6:
        return "medium"
    return "high"


# ─────────────────────────────────────────────────────────────────────────────
# 8. 各 Agent 的确定性核心
# ─────────────────────────────────────────────────────────────────────────────

def score_strengths(text: str) -> Dict[str, Any]:
    scores: Dict[str, int] = {}
    matched: Dict[str, List[str]] = {}
    for s in STRENGTHS:
        h = _hits(text, s["kw"])
        matched[s["key"]] = h
        scores[s["key"]] = _score_from_hits(len(h))
    ranked = sorted(STRENGTH_KEYS, key=lambda k: scores[k], reverse=True)
    core = [{
        "name": STRENGTH_ZH[k], "key": k, "score": scores[k],
        "evidence": matched[k][:4],
        "possible_use": _strength_use(k),
    } for k in ranked[:3] if scores[k] >= 45]
    secondary = [{"name": STRENGTH_ZH[k], "key": k, "score": scores[k]}
                 for k in ranked[3:6] if scores[k] >= 40]
    under = [{"name": STRENGTH_ZH[k], "key": k, "score": scores[k]}
             for k in ranked if scores[k] <= 32][:3]
    return {"scores": scores, "core_strengths": core,
            "secondary_strengths": secondary, "underdeveloped_areas": under,
            "_matched": matched}


_STRENGTH_USE = {
    "cognitive": ["课程设计", "知识图谱", "护教学系统"],
    "expression": ["教导", "写作事工", "讲道辅助"],
    "relational": ["小组牧养", "关怀陪伴", "接待"],
    "execution": ["项目统筹", "事工落地", "流程优化"],
    "creativity": ["内容创作", "敬拜艺术", "产品构想"],
    "leadership": ["小组带领", "事工组织", "团队动员"],
    "discernment": ["护教辨析", "属灵分辨", "内容把关"],
    "learning": ["神学研究", "跨学科整合", "资料建设"],
    "technical": ["AI 信仰工具", "平台搭建", "自动化服事"],
    "resilience": ["危机陪伴", "长期门训", "拓荒服事"],
}


def _strength_use(k: str) -> List[str]:
    return _STRENGTH_USE.get(k, [])


def score_gifts(text: str) -> Dict[str, Any]:
    scores: Dict[str, int] = {}
    matched: Dict[str, List[str]] = {}
    for g in GIFTS:
        h = _hits(text, g["kw"])
        matched[g["key"]] = h
        scores[g["key"]] = _score_from_hits(len(h), base=28, step=15)
    ranked = sorted(GIFT_KEYS, key=lambda k: scores[k], reverse=True)
    likely = [{
        "gift": GIFT_ZH[k], "key": k, "score": scores[k],
        "evidence": matched[k][:4],
        "maturity_warning": _gift_warning(k),
        "validation_task": _gift_validation(k),
    } for k in ranked[:3] if scores[k] >= 50]
    possible = [{"gift": GIFT_ZH[k], "key": k, "score": scores[k]}
                for k in ranked[3:6] if scores[k] >= 43]
    low = [{"gift": GIFT_ZH[k], "key": k, "score": scores[k]} for k in ranked if scores[k] < 40][:4]
    return {"scores": scores, "likely_gifts": likely, "possible_gifts": possible,
            "low_evidence_gifts": low,
            "needs_community_confirmation": [g["gift"] for g in likely],
            "_matched": matched}


_GIFT_WARNING = {
    "teaching": "需要仁爱与温柔承托，避免真理表达伤人。",
    "discernment": "避免论断，分辨须配上怜悯与建造。",
    "knowledge": "避免知识骄傲与过度复杂化。",
    "leadership": "避免控制与急躁，学习授权与忍耐。",
    "mercy": "注意边界，避免情绪耗竭与讨好。",
    "exhortation": "避免急于改变别人或把建议当神旨意。",
    "evangelism": "避免结果主义，把人当人而非项目。",
    "administration": "把人放在效率之上。",
    "pioneering": "避免不受约束与虎头蛇尾。",
}


def _gift_warning(k: str) -> str:
    return _GIFT_WARNING.get(k, "在共同体监督与属灵果子中持续验证。")


def _gift_validation(k: str) -> str:
    return f"在小范围服事中实践「{GIFT_ZH.get(k, k)}」3 次，并请 3 位成熟肢体反馈：是否清楚、是否有爱、是否造就人。"


def score_fruits(text: str) -> Dict[str, Any]:
    scores: Dict[str, int] = {}
    for f in FRUITS:
        pos = len(_hits(text, f["pos"]))
        neg = len(_hits(text, f["neg"]))
        scores[f["key"]] = _clamp(58 + pos * 10 - neg * 13, 5, 98)
    ranked = sorted(FRUIT_KEYS, key=lambda k: scores[k], reverse=True)
    supporting = [FRUIT_ZH[k] for k in ranked if scores[k] >= 65][:4]
    growth = [FRUIT_ZH[k] for k in ranked[::-1] if scores[k] <= 55][:3]
    red_flags = [f"{FRUIT_ZH[k]} 偏低，建议牧养关注" for k in FRUIT_KEYS if scores[k] <= 25]
    return {"scores": scores, "average_score": round(_avg(list(scores.values())), 2),
            "supporting_fruits": supporting, "growth_fruits": growth, "red_flags": red_flags}


def align_gift_fruit(top_gift_keys: List[str], fruit_scores: Dict[str, int]) -> List[Dict[str, Any]]:
    """恩赐 × 果子：高分恩赐若缺关键果子则标记风险与操练。"""
    need = {
        "teaching": ["love", "gentleness", "patience"],
        "discernment": ["love", "kindness"],
        "knowledge": ["love", "gentleness"],
        "leadership": ["patience", "gentleness"],
        "mercy": ["self_control", "peace"],
        "exhortation": ["patience", "gentleness"],
        "evangelism": ["love", "patience"],
        "administration": ["patience", "gentleness"],
        "pioneering": ["faithfulness", "self_control"],
        "shepherding": ["love", "patience"],
    }
    out: List[Dict[str, Any]] = []
    for gk in top_gift_keys:
        fruits = need.get(gk, ["love", "gentleness"])
        weak = [FRUIT_ZH[f] for f in fruits if fruit_scores.get(f, 50) < 55]
        risk = (f"「{GIFT_ZH.get(gk, gk)}」目前缺少 {('、'.join(weak))} 的承托，"
                "表达真理时可能伤人或显出能力而非爱。") if weak else \
               f"「{GIFT_ZH.get(gk, gk)}」已有较好的果子承托，可在共同体中继续操练。"
        out.append({
            "gift_or_strength": GIFT_ZH.get(gk, gk),
            "supporting_fruits": [FRUIT_ZH[f] for f in fruits],
            "current_risk": risk,
            "growth_practice": "每次服事前先问：我是为爱这个人，还是为证明自己？",
        })
    return out


def score_callings(text: str) -> Dict[str, Any]:
    scores: Dict[str, int] = {}
    matched: Dict[str, List[str]] = {}
    for c in CALLINGS:
        h = _hits(text, c["kw"])
        matched[c["key"]] = h
        scores[c["key"]] = _score_from_hits(len(h), base=25, step=16)
    ranked = sorted(CALLING_KEYS, key=lambda k: scores[k], reverse=True)
    primary = ranked[0] if scores[ranked[0]] >= 45 else None
    secondary = [CALLING_ZH[k] for k in ranked[1:4] if scores[k] >= 45]
    evidence = matched[primary][:5] if primary else []
    return {"scores": scores, "primary": primary,
            "primary_zh": CALLING_ZH.get(primary, "") if primary else "",
            "secondary": secondary, "evidence": evidence, "_matched": matched}


def build_mission_sentence(primary_zh: str, top_gift_zh: str, top_strength_zh: str) -> str:
    if not primary_zh:
        return "目前使命主题尚不明显，建议在祷告与小范围服事中继续观察反复出现的负担。"
    return (f"用「{top_strength_zh}」与「{top_gift_zh}」，"
            f"走向「{primary_zh}」的服事——帮助人更认识基督、被建造、活出使命。"
            "（此为可探索方向，需共同体与长期忠心验证。）")


def score_risks(strength_scores: Dict[str, int], gift_scores: Dict[str, int],
                fruit_scores: Dict[str, int]) -> Dict[str, Any]:
    combo = {**strength_scores, **gift_scores}
    fruit_avg = _avg(list(fruit_scores.values())) or 50.0
    profile: Dict[str, int] = {}
    detail: List[Dict[str, Any]] = []
    for r in RISKS:
        trig = [combo.get(t, 0) for t in r["triggers"] if t in combo]
        if not trig:
            profile[r["key"]] = 0
            continue
        trig_avg = _avg(trig)
        rel_fruits = _avg([fruit_scores.get(f, 50) for f in r["fruits"]]) or 50.0
        score = _clamp(trig_avg * 0.82 + (55 - rel_fruits) * 0.5)
        profile[r["key"]] = score
        detail.append({
            "risk": r["zh"], "key": r["key"], "score": score,
            "related": [GIFT_ZH.get(t) or STRENGTH_ZH.get(t) or t for t in r["triggers"] if t in combo],
            "gospel_reframe": r["reframe"], "practice": r["practice"],
            "fruits_needed": [FRUIT_ZH[f] for f in r["fruits"]],
        })
    detail.sort(key=lambda d: d["score"], reverse=True)
    top = detail[:3]
    overall = _clamp(_avg([d["score"] for d in top])) if top else 0
    disciplines = ["祷告省察", "牧者审核", "共同体反馈", "小范围试服事"]
    warnings = ["开始不愿听反馈", "只想扩大影响力", "表达越来越尖锐", "服事后人被消耗而非被造就"]
    return {"overall_risk_score": overall, "risk_profile": profile,
            "top_risks": top, "protective_disciplines": disciplines,
            "warning_signs": warnings}


def match_ministries(strength_scores: Dict[str, int], gift_scores: Dict[str, int],
                     fruit_scores: Dict[str, int], risk_profile: Dict[str, int]) -> Dict[str, Any]:
    fruit_avg = _avg(list(fruit_scores.values())) or 50.0
    results: List[Dict[str, Any]] = []
    for m in MINISTRIES:
        g = _avg([gift_scores.get(k, 0) for k in m["gifts"]])
        s = _avg([strength_scores.get(k, 0) for k in m["strengths"]])
        fit = 0.55 * g + 0.30 * s + 0.15 * fruit_avg
        # 风险惩罚：相关风险越高、果子越低，匹配分下降
        rel_risk = _avg([risk_profile.get(rk, 0) for rk in m["risks"]]) if m.get("risks") else 0
        score = _clamp(fit - rel_risk * 0.12)
        fruit_gap = [FRUIT_ZH[f] for f in m["fruits"] if fruit_scores.get(f, 50) < 50]
        # 等级：能力 + 果子成熟度 + 风险共同决定
        if score >= 78 and fruit_avg >= 55 and rel_risk < 70:
            level = "A"
        elif score >= 62:
            level = "B"
        elif score >= 48:
            level = "C"
        else:
            level = "D"
        results.append({
            "ministry": m["zh"], "key": m["key"], "level": level, "match_score": score,
            "matched_gifts": [GIFT_ZH[k] for k in m["gifts"]],
            "matched_strengths": [STRENGTH_ZH[k] for k in m["strengths"]],
            "fruit_requirements": [FRUIT_ZH[f] for f in m["fruits"]],
            "fruit_gap": fruit_gap,
            "risks": [RISK_ZH.get(rk, rk) for rk in m.get("risks", [])],
            "safeguards": m["safeguards"],
            "first_step": m["first_step"],
        })
    results.sort(key=lambda d: (LEVEL_ORDER[d["level"]], d["match_score"]), reverse=True)
    recommended = [r for r in results if r["level"] == "A"][:3]
    experimental = [r for r in results if r["level"] in ("B", "C")][:4]
    not_now = [{"ministry": r["ministry"], "reason": "当前能力/果子证据不足，建议先成长或辅助参与"}
               for r in results if r["level"] == "D"][:3]
    top = recommended[0] if recommended else (experimental[0] if experimental else results[0])
    return {"recommended_ministries": recommended, "experimental_ministries": experimental,
            "not_recommended_now": not_now,
            "top_ministry": top["ministry"], "top_match_score": top["match_score"],
            "safeguards": top["safeguards"]}


def build_growth_plan(top_strength_zh: str, top_gift_zh: str, top_risk: Optional[Dict[str, Any]],
                      top_ministry: str, growth_fruits: List[str]) -> Dict[str, Any]:
    risk_zh = top_risk["risk"] if top_risk else "属灵骄傲"
    risk_practice = top_risk["practice"] if top_risk else "每次服事前省察动机。"
    fruits = "、".join(growth_fruits) if growth_fruits else "温柔、忍耐"
    plan = {
        "30_days": {
            "theme": "认识恩赐与盲点（先验证，不扩大服事）",
            "biblical_formation": ["读罗马书12 / 林前12-13 / 加5，写下恩赐为爱与建造而设"],
            "prayer_practice": ["每日 10 分钟省察祷告：主啊，让我看见你给的恩赐，也看见需要悔改之处"],
            "character_practice": [f"操练 {fruits}", risk_practice],
            "ministry_experiment": [f"准备一次 10 分钟「{top_gift_zh}」相关分享，仅在 2-3 人中试做"],
            "feedback_loop": ["请 3 位成熟肢体反馈：是否清楚、是否有爱、是否帮助人更亲近神"],
            "risk_guard": [f"守望「{risk_zh}」：出现尖锐/不愿听反馈时停下祷告"],
            "deliverable": ["写一份《我的恩赐使用守则》"],
            "review_questions": ["这次服事我更爱神爱人了吗？", "我是否愿意接受纠正？"],
        },
        "90_days": {
            "theme": "稳定操练与小型服事（形成节奏）",
            "ministry_experiment": [f"在「{top_ministry}」方向做一个小型可交付成果"],
            "feedback_loop": ["邀请一位同工固定搭配并双周复盘"],
            "character_practice": [f"持续操练 {fruits}"],
            "risk_guard": [f"每月一次共同体反馈，专看「{risk_zh}」是否改善"],
            "deliverable": ["完成并交付一个小型服事成果"],
            "review_questions": ["我的服事是否使人被造就而非只被我的能力吸引？"],
        },
        "180_days": {
            "theme": "成熟化与共同体确认（进入稳定服事角色）",
            "ministry_experiment": [f"在牧者确认下进入「{top_ministry}」的稳定服事"],
            "feedback_loop": ["请牧者/小组长正式确认恩赐与服事方向"],
            "character_practice": ["把属灵果子操练固化为长期节奏"],
            "risk_guard": ["建立长期问责关系与督导"],
            "deliverable": ["一份半年复盘 + 下一阶段方向"],
            "review_questions": ["半年来我是否更像基督？", "是否有人因我的服事更亲近神？"],
        },
    }
    weekly = [
        {"day": "每日", "practice": "10 分钟省察祷告与读经"},
        {"day": "每周", "practice": "1 次小范围服事 + 1 次复盘"},
        {"day": "每月", "practice": "1 次共同体反馈"},
    ]
    indicators = ["更爱神更爱人", "更愿意听反馈与被纠正", "服事后人被造就", "恩赐使用更有温柔与忍耐"]
    return {"plan_json": plan, "weekly_rhythm": weekly,
            "success_indicators": indicators,
            "warning_signs": ["以成果衡量价值", "不愿接受反馈", "服事使人被消耗"],
            "current_phase": "30_days"}


# ── Agent 5: 共同体确认（反馈表 + 聚合） ────────────────────────────────────────

COMMUNITY_FORMS: Dict[str, List[str]] = {
    "pastor_leader": [
        "他/她是否清楚理解并表达圣经真理？",
        "他/她的服事是否造就人，而不是只展示能力？",
        "他/她是否愿意接受提醒和纠正？",
        "他/她是否在团队中谦卑配搭？",
        "他/她是否有稳定的属灵生命和教会生活？",
        "他/她是否有明显的爱心、温柔、忍耐？",
        "他/她最明显的恩赐是什么？目前最大的成长功课是什么？",
        "你是否建议他/她在此方向继续服事？为什么？",
    ],
    "coworker": [
        "一起服事时，他/她是否可靠、守约、完成承诺？",
        "他/她是否尊重同工与牧者的界限？",
        "冲突或压力中，他/她如何回应？",
        "他/她的恩赐在团队中如何配搭？",
        "你观察到他/她最需要成长的地方是什么？",
    ],
    "recipient": [
        "被他/她服事后，你是否更明白真理、更亲近神？",
        "你感受到的是关怀，还是只是完成任务？",
        "有没有哪里让你感到压力或困惑？",
        "你会愿意再次被他/她服事吗？为什么？",
    ],
}

# 共同体反馈来源权重（聚合用）
SOURCE_WEIGHT = {
    "pastor": 0.35, "elder": 0.35, "mentor": 0.30,
    "small_group_leader": 0.25, "coworker": 0.25,
    "recipient": 0.20, "family": 0.15, "friend": 0.15, "self": 0.05, "other": 0.10,
}


def summarize_community_feedback(feedbacks: List[Dict[str, Any]],
                                 self_scores: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """聚合共同体反馈（加权）。每条 feedback: {source_type, scores{1~5}, confirmed_gifts[], concern_areas[]}。"""
    if not feedbacks:
        return {"count": 0, "weighted_scores": {}, "confirmed_strengths": [],
                "confirmed_gifts": [], "areas_of_concern": [],
                "alignment_analysis": "暂无共同体反馈；建议邀请牧者、同工、被服事者各 1-2 位填写反馈表。"}
    agg: Dict[str, float] = {}
    wsum: Dict[str, float] = {}
    gifts: Dict[str, int] = {}
    concerns: Dict[str, int] = {}
    strengths: Dict[str, int] = {}
    for fb in feedbacks:
        w = SOURCE_WEIGHT.get(str(fb.get("source_type", "other")), 0.10)
        for k, v in (fb.get("scores") or {}).items():
            if isinstance(v, (int, float)):
                agg[k] = agg.get(k, 0.0) + v * w
                wsum[k] = wsum.get(k, 0.0) + w
        for g in (fb.get("confirmed_gifts") or []):
            gifts[str(g)] = gifts.get(str(g), 0) + 1
        for c in (fb.get("concern_areas") or []):
            concerns[str(c)] = concerns.get(str(c), 0) + 1
        for s in (fb.get("confirmed_strengths") or []):
            strengths[str(s)] = strengths.get(str(s), 0) + 1
    weighted = {k: round(agg[k] / wsum[k], 2) for k in agg if wsum.get(k)}
    top_gifts = sorted(gifts, key=gifts.get, reverse=True)[:5]
    analysis = "已有共同体反馈。"
    if self_scores and weighted:
        # 简单一致性提示
        analysis += "建议对照自评：自评明显高于他评处可能存在自我认知偏差；他评高于自评处可能是缺乏信心。"
    return {"count": len(feedbacks), "weighted_scores": weighted,
            "confirmed_strengths": sorted(strengths, key=strengths.get, reverse=True)[:5],
            "confirmed_gifts": top_gifts,
            "areas_of_concern": sorted(concerns, key=concerns.get, reverse=True)[:5],
            "alignment_analysis": analysis}


# ─────────────────────────────────────────────────────────────────────────────
# 9. 确定性总装：assess_fallback()
# ─────────────────────────────────────────────────────────────────────────────

def assess_fallback(inputs: Dict[str, Any],
                    feedbacks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    text = _blob(inputs)
    total_chars = len(re.sub(r"\s", "", text))

    st = score_strengths(text)
    gf = score_gifts(text)
    fr = score_fruits(text)
    ca = score_callings(text)

    top_strength = max(STRENGTH_KEYS, key=lambda k: st["scores"][k])
    top_gift = max(GIFT_KEYS, key=lambda k: gf["scores"][k])
    top_gift_keys = [g["key"] for g in gf["likely_gifts"]] or [top_gift]

    rk = score_risks(st["scores"], gf["scores"], fr["scores"])
    mm = match_ministries(st["scores"], gf["scores"], fr["scores"], rk["risk_profile"])
    top_risk = rk["top_risks"][0] if rk["top_risks"] else None
    plan = build_growth_plan(STRENGTH_ZH[top_strength], GIFT_ZH[top_gift], top_risk,
                             mm["top_ministry"], fr["growth_fruits"])

    mission = build_mission_sentence(ca["primary_zh"], GIFT_ZH[top_gift], STRENGTH_ZH[top_strength])
    crossroads = {
        "strengths": [STRENGTH_ZH[k] for k in sorted(STRENGTH_KEYS, key=lambda k: st["scores"][k], reverse=True)[:2]],
        "gifts": [GIFT_ZH[k] for k in top_gift_keys[:2]],
        "burdens": ca["secondary"][:2] + ([ca["primary_zh"]] if ca["primary_zh"] else []),
        "opportunities": [m["ministry"] for m in mm["recommended_ministries"][:2]],
    }

    signal = (len(st["core_strengths"]) + len(gf["likely_gifts"]) +
              (1 if ca["primary"] else 0) + len(rk["top_risks"]))
    conf = _confidence(total_chars, signal)

    return {
        "source": "heuristic",
        "confidence": conf,
        "strength_profile": {
            "scores": st["scores"],
            "core_strengths": st["core_strengths"],
            "secondary_strengths": st["secondary_strengths"],
            "underdeveloped_areas": st["underdeveloped_areas"],
            "skill_assets": _hits(text, STRENGTHS[8]["kw"]),  # 技术类作为技能资产证据
            "personality_tendencies": [],
            "summary": f"你的核心天然优势可能是「{STRENGTH_ZH[top_strength]}」，适合被训练为：" +
                       "、".join(_strength_use(top_strength)) + "。",
        },
        "spiritual_gifts": {
            "scores": gf["scores"],
            "likely_gifts": gf["likely_gifts"],
            "possible_gifts": gf["possible_gifts"],
            "low_evidence_gifts": gf["low_evidence_gifts"],
            "needs_community_confirmation": gf["needs_community_confirmation"],
            "summary": f"目前较明显的恩赐倾向可能是「{GIFT_ZH[top_gift]}」，"
                       "但需在教会共同体、小范围服事与属灵果子中继续验证。",
        },
        "fruit_scores": {
            "scores": fr["scores"],
            "average_score": fr["average_score"],
            "supporting_fruits": fr["supporting_fruits"],
            "growth_fruits": fr["growth_fruits"],
            "gift_fruit_alignment": align_gift_fruit(top_gift_keys, fr["scores"]),
            "red_flags": fr["red_flags"],
            "summary": "恩赐决定能做什么，果子决定是否成熟、安全、荣耀神地使用。",
        },
        "calling_patterns": {
            "scores": ca["scores"],
            "primary_pattern": ca["primary_zh"],
            "secondary_patterns": ca["secondary"],
            "evidence": ca["evidence"],
            "burden_groups": [],
            "burden_topics": ca["evidence"],
            "crossroads": crossroads,
            "possible_mission_sentence": mission,
            "validation_path": ["做 3 次相关小组分享", "请牧者反馈", "开发一个最小服事尝试"],
            "warnings": ["兴趣/能力/痛苦/机会都不自动等于呼召；需祷告、圣经、教会确认与长期忠心验证"],
            "summary": f"你反复出现的使命主题可能集中在「{ca['primary_zh'] or '尚不明显'}」。",
        },
        "community_confirmation": {
            "forms": COMMUNITY_FORMS,
            "recommended_reviewers": ["牧者/长老", "小组长/同工", "被服事者", "家人/亲近朋友"],
            **summarize_community_feedback(feedbacks or []),
        },
        "misuse_risks": {
            "overall_risk_score": rk["overall_risk_score"],
            "risk_profile": rk["risk_profile"],
            "top_risks": rk["top_risks"],
            "protective_disciplines": rk["protective_disciplines"],
            "community_safeguards": ["牧者审核", "同工搭配", "小范围试服事", "定期反馈"],
            "gospel_reframes": [r["gospel_reframe"] for r in rk["top_risks"]],
            "warning_signs": rk["warning_signs"],
            "summary": "这些风险不是否定你，而是保护你更安全、更有爱地服事。",
        },
        "ministry_matches": {
            "top_ministry": mm["top_ministry"],
            "top_match_score": mm["top_match_score"],
            "recommended_ministries": mm["recommended_ministries"],
            "experimental_ministries": mm["experimental_ministries"],
            "not_recommended_now": mm["not_recommended_now"],
            "safeguards": mm["safeguards"],
            "summary": f"当前最匹配的服事方向可能是「{mm['top_ministry']}」（需在监督下开始）。",
        },
        "growth_plan": {
            "plan_json": plan["plan_json"],
            "weekly_rhythm": plan["weekly_rhythm"],
            "success_indicators": plan["success_indicators"],
            "warning_signs": plan["warning_signs"],
            "current_phase": plan["current_phase"],
            "summary": "未来 30 天重点不是扩大服事，而是验证与扎根。",
        },
        "summary": f"核心优势「{STRENGTH_ZH[top_strength]}」+ 恩赐倾向「{GIFT_ZH[top_gift]}」"
                   f"+ 使命方向「{ca['primary_zh'] or '待辨识'}」；最匹配服事「{mm['top_ministry']}」。",
        "identity_reminder": IDENTITY_REMINDER,
        "boundary_notice": BOUNDARY_NOTICE,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 10. AI 增强
# ─────────────────────────────────────────────────────────────────────────────

GUARDRAIL_SYSTEM_PROMPT = (
    "你是「属灵星球 Gift & Calling OS」的恩赐与呼召辅助辨识 Agent。"
    "严守神学边界：(1) 不宣告最终呼召，只给「可能倾向/可探索方向/需共同体确认」；"
    "(2) 恩赐分数不是属灵等级，高分不代表更属灵；(3) 身份根基在基督里，不在恩赐表现；"
    "(4) 不鼓励属灵骄傲、比较、操控、越权服事；(5) 涉及自伤/严重抑郁/创伤/成瘾/精神危机，"
    "建议寻求可信赖牧者、专业辅导或当地紧急帮助，不替代牧养与医疗；"
    "(6) 区分天然优势/后天技能/属灵恩赐/属灵果子/使命负担/教会确认；"
    "(7) 语气温柔、诚实、具体、非定罪，避免「神一定呼召你做……」这类绝对化表达；"
    "(8) 一切导向爱神爱人、建造教会、服事邻舍、荣耀基督、在真理中成长。"
)

_JSON_SHAPE = (
    '{'
    '"confidence":"low|medium|high",'
    '"strength_profile":{"scores":{<10项0-100>},"core_strengths":[{"name":"","score":0,"evidence":[],"possible_use":[]}],"summary":""},'
    '"spiritual_gifts":{"scores":{<15项0-100>},"likely_gifts":[{"gift":"","score":0,"evidence":[],"maturity_warning":"","validation_task":""}],"summary":""},'
    '"fruit_scores":{"scores":{<9项0-100>},"gift_fruit_alignment":[{"gift_or_strength":"","supporting_fruits":[],"current_risk":"","growth_practice":""}],"summary":""},'
    '"calling_patterns":{"primary_pattern":"","secondary_patterns":[],"evidence":[],"possible_mission_sentence":"","validation_path":[],"summary":""},'
    '"misuse_risks":{"overall_risk_score":0,"top_risks":[{"risk":"","score":0,"gospel_reframe":"","practice":""}],"summary":""},'
    '"ministry_matches":{"top_ministry":"","recommended_ministries":[{"ministry":"","level":"A|B|C|D","match_score":0,"safeguards":[],"first_step":""}],"summary":""},'
    '"growth_plan":{"plan_json":{"30_days":{},"90_days":{},"180_days":{}},"success_indicators":[],"summary":""},'
    '"summary":""'
    '}'
)


def build_prompt(inputs: Dict[str, Any]) -> List[Dict[str, str]]:
    lines = []
    for f in INPUT_FIELDS:
        v = inputs.get(f["key"])
        if v:
            lines.append(f"【{f['zh']}】{v}")
    body = "\n".join(lines) or "（用户资料较少）"
    user = (
        "请根据以下用户资料，做恩赐与呼召的辅助辨识。\n\n"
        f"{body}\n\n"
        "要求：分数 0~100；只给可探索方向并标注需共同体确认；恩赐务必配上属灵果子的承托与误用风险；"
        "服事推荐给出 A/B/C/D 级与保护机制与第一步；成长计划给 30/90/180 天。\n"
        f"严格只输出如下 JSON，不要任何额外文字：\n{_JSON_SHAPE}"
    )
    return [{"role": "system", "content": GUARDRAIL_SYSTEM_PROMPT},
            {"role": "user", "content": user}]


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


def _call_ai(messages: List[Dict[str, str]], settings: Any) -> Optional[Dict[str, Any]]:
    """复用 waiting_engine 的 OpenAI 兼容 Provider；返回解析后的 dict 或 None。"""
    try:
        try:
            from backend.waiting_engine import call_ai_provider
        except Exception:
            from waiting_engine import call_ai_provider  # type: ignore
        raw = call_ai_provider(messages, settings=settings)
        if isinstance(raw, dict):
            # 有些 provider 已返回 dict；否则其可能含 answer 文本
            if any(k in raw for k in ("strength_profile", "spiritual_gifts", "fruit_scores")):
                return raw
            for v in raw.values():
                if isinstance(v, str):
                    got = _extract_json(v)
                    if got:
                        return got
            return raw
        if isinstance(raw, str):
            return _extract_json(raw)
    except Exception:
        return None
    return None


def _merge_scores(base: Dict[str, int], ai: Any, keys: List[str]) -> Dict[str, int]:
    out = dict(base)
    if isinstance(ai, dict):
        for k in keys:
            v = ai.get(k)
            if isinstance(v, (int, float)):
                out[k] = _clamp(float(v))
    return out


def _take(ai_sec: Any, key: str, default: Any) -> Any:
    """AI 段里取非空值，否则用 default。"""
    if isinstance(ai_sec, dict):
        v = ai_sec.get(key)
        if v not in (None, "", [], {}):
            return v
    return default


def assess(inputs: Dict[str, Any], feedbacks: Optional[List[Dict[str, Any]]] = None,
           settings: Any = None, use_ai: bool = True) -> Dict[str, Any]:
    """主入口（Orchestrator）：确定性核心 + AI 增强合并。永远返回完整报告。"""
    fb = assess_fallback(inputs, feedbacks=feedbacks)
    if not use_ai:
        return fb

    ai = _call_ai(build_prompt(inputs), settings)
    if not ai:
        return fb

    out = json.loads(json.dumps(fb))  # deep copy

    if ai.get("confidence") in CONFIDENCE_LEVELS:
        out["confidence"] = ai["confidence"]

    # 优势
    sp = ai.get("strength_profile")
    out["strength_profile"]["scores"] = _merge_scores(out["strength_profile"]["scores"],
                                                      (sp or {}).get("scores"), STRENGTH_KEYS)
    out["strength_profile"]["core_strengths"] = _take(sp, "core_strengths", out["strength_profile"]["core_strengths"])
    out["strength_profile"]["summary"] = _take(sp, "summary", out["strength_profile"]["summary"])

    # 恩赐
    sg = ai.get("spiritual_gifts")
    out["spiritual_gifts"]["scores"] = _merge_scores(out["spiritual_gifts"]["scores"],
                                                    (sg or {}).get("scores"), GIFT_KEYS)
    out["spiritual_gifts"]["likely_gifts"] = _take(sg, "likely_gifts", out["spiritual_gifts"]["likely_gifts"])
    out["spiritual_gifts"]["summary"] = _take(sg, "summary", out["spiritual_gifts"]["summary"])

    # 果子
    fs = ai.get("fruit_scores")
    out["fruit_scores"]["scores"] = _merge_scores(out["fruit_scores"]["scores"],
                                                 (fs or {}).get("scores"), FRUIT_KEYS)
    out["fruit_scores"]["average_score"] = round(_avg(list(out["fruit_scores"]["scores"].values())), 2)
    out["fruit_scores"]["gift_fruit_alignment"] = _take(fs, "gift_fruit_alignment",
                                                        out["fruit_scores"]["gift_fruit_alignment"])
    out["fruit_scores"]["summary"] = _take(fs, "summary", out["fruit_scores"]["summary"])

    # 使命
    cp = ai.get("calling_patterns")
    out["calling_patterns"]["primary_pattern"] = _take(cp, "primary_pattern", out["calling_patterns"]["primary_pattern"])
    out["calling_patterns"]["secondary_patterns"] = _take(cp, "secondary_patterns", out["calling_patterns"]["secondary_patterns"])
    out["calling_patterns"]["possible_mission_sentence"] = _take(cp, "possible_mission_sentence",
                                                                out["calling_patterns"]["possible_mission_sentence"])
    out["calling_patterns"]["validation_path"] = _take(cp, "validation_path", out["calling_patterns"]["validation_path"])
    out["calling_patterns"]["summary"] = _take(cp, "summary", out["calling_patterns"]["summary"])

    # 风险
    mr = ai.get("misuse_risks")
    if isinstance(mr, dict) and isinstance(mr.get("overall_risk_score"), (int, float)):
        out["misuse_risks"]["overall_risk_score"] = _clamp(float(mr["overall_risk_score"]))
    out["misuse_risks"]["top_risks"] = _take(mr, "top_risks", out["misuse_risks"]["top_risks"])
    out["misuse_risks"]["summary"] = _take(mr, "summary", out["misuse_risks"]["summary"])

    # 服事
    mm = ai.get("ministry_matches")
    out["ministry_matches"]["top_ministry"] = _take(mm, "top_ministry", out["ministry_matches"]["top_ministry"])
    out["ministry_matches"]["recommended_ministries"] = _take(mm, "recommended_ministries",
                                                             out["ministry_matches"]["recommended_ministries"])
    out["ministry_matches"]["summary"] = _take(mm, "summary", out["ministry_matches"]["summary"])

    # 成长计划
    gp = ai.get("growth_plan")
    out["growth_plan"]["plan_json"] = _take(gp, "plan_json", out["growth_plan"]["plan_json"])
    out["growth_plan"]["success_indicators"] = _take(gp, "success_indicators", out["growth_plan"]["success_indicators"])
    out["growth_plan"]["summary"] = _take(gp, "summary", out["growth_plan"]["summary"])

    out["summary"] = _take(ai, "summary", out["summary"])
    out["source"] = "ai"
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 11. meta / empty —— 给前端渲染
# ─────────────────────────────────────────────────────────────────────────────

def meta() -> Dict[str, Any]:
    return {
        "version": "gcos1.0",
        "input_fields": INPUT_FIELDS,
        "strengths": [{"key": s["key"], "zh": s["zh"]} for s in STRENGTHS],
        "gifts": [{"key": g["key"], "zh": g["zh"]} for g in GIFTS],
        "fruits": [{"key": f["key"], "zh": f["zh"]} for f in FRUITS],
        "callings": [{"key": c["key"], "zh": c["zh"]} for c in CALLINGS],
        "risks": [{"key": r["key"], "zh": r["zh"]} for r in RISKS],
        "ministries": [{"key": m["key"], "zh": m["zh"]} for m in MINISTRIES],
        "community_forms": COMMUNITY_FORMS,
        "identity_reminder": IDENTITY_REMINDER,
        "boundary_notice": BOUNDARY_NOTICE,
    }


def empty_profile() -> Dict[str, Any]:
    return {
        "has_assessment": False,
        "strength_profile": {"scores": {k: 0 for k in STRENGTH_KEYS}, "core_strengths": []},
        "spiritual_gifts": {"scores": {k: 0 for k in GIFT_KEYS}, "likely_gifts": []},
        "fruit_scores": {"scores": {k: 50 for k in FRUIT_KEYS}, "average_score": 50.0},
        "calling_patterns": {"primary_pattern": "", "secondary_patterns": []},
        "misuse_risks": {"overall_risk_score": 0, "top_risks": []},
        "ministry_matches": {"top_ministry": "", "recommended_ministries": []},
        "growth_plan": {"plan_json": {}, "current_phase": "30_days"},
        "identity_reminder": IDENTITY_REMINDER,
        "boundary_notice": BOUNDARY_NOTICE,
        "updated_at": None,
    }
