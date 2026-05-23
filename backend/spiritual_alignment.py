"""
属灵对齐评估引擎 (Spiritual Alignment Engine)
基于圣经原则评判行为是否与神的道对齐
"""

import json
import re
from dataclasses import dataclass, field, asdict
from typing import List


@dataclass
class SpiritualAlignmentResult:
    """属灵对齐评估结果"""
    aligned: bool = True
    alignment_score: int = 50
    assessment: str = ""
    scripture_reference: str = ""
    principle: str = ""
    misalignment_areas: List[str] = field(default_factory=list)
    alignment_actions: List[str] = field(default_factory=list)
    category: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class SpiritualAlignmentEngine:
    """
    属灵对齐评估引擎
    基于圣经原则评判行为是否与神的道对齐
    """

    HIGH_ALIGNMENT_KEYWORDS = [
        "祷告", "读经", "灵修", "敬拜", "赞美", "感恩",
        "服事", "奉献", "探访", "安慰", "帮助", "分享",
        "传福音", "见证", "赦免", "饶恕", "悔改", "认罪",
        "施舍", "济贫", "代祷", "禁食", "默想", "祷告会",
        "教会", "小组", "团契", "主日学", "洗礼", "圣餐",
        "祈祷", "圣经", "神的话", "主的话", "晨更", "晚祷",
        "pray", "prayer", "bible", "scripture", "worship", "praise",
        "thanksgiving", "gratitude", "serve", "service", "give",
        "evangelize", "testify", "forgive", "repent", "confess", "fast",
        "meditate", "church", "fellowship", "baptism", "communion",
        "devotion", "spiritual", "ministry"
    ]

    LOW_ALIGNMENT_KEYWORDS = [
        "撒谎", "欺骗", "诈骗", "偷窃", "贪污", "受贿",
        "淫乱", "色情", "赌博", "酗酒", "吸毒",
        "咒骂", "亵渎", "毁谤", "论断", "嫉妒", "纷争",
        "仇恨", "报复", "暴力", "虐待", "杀人", "自杀",
        "怠惰", "懒惰", "逃避", "推脱", "抱怨", "埋怨",
        "攀比", "炫耀", "骄傲", "狂妄", "贪婪", "吝啬",
        "看黄", "手淫", "嫖娼", "出轨", "包养", "小三",
        "lie", "cheat", "deceive", "steal", "corrupt", "bribe",
        "adultery", "porn", "gamble", "drunk", "drug", "curse",
        "blasphemy", "slander", "gossip", "judge", "envy", "strife",
        "hate", "revenge", "violence", "abuse", "kill", "suicide",
        "lazy", "avoid", "complain", "greedy"
    ]

    NEUTRAL_CATEGORIES = {
        "工作": {
            "keywords": ["工作", "上班", "加班", "项目", "报告", "会议", "邮件", "客户", "同事", "work", "job", "project", "report", "meeting"],
            "principle": "无论做什么，都要从心里做，像是给主做的，不是给人做的",
            "scripture": "西3:23",
            "alignment_score": 70,
            "assessment": "工作是神所托付的管家职分，当以忠心和卓越态度对待。",
            "tips": ["以祷告开始工作", "在工作中见证基督的品格", "将工作视为服事神的机会"]
        },
        "学习": {
            "keywords": ["学习", "读书", "考试", "论文", "研究", "课程", "培训", "study", "read", "exam", "paper", "research", "course"],
            "principle": "你要尽心、尽性、尽力爱耶和华你的神",
            "scripture": "申6:5",
            "alignment_score": 75,
            "assessment": "学习是装备自己更好地服事神和人的途径，当以敬畏神的心追求知识。",
            "tips": ["为学习祷告求智慧", "将所学用于建造神国", "在学习中荣耀神"]
        },
        "休息": {
            "keywords": ["休息", "睡觉", "午休", "假期", "放松", "rest", "sleep", "vacation", "relax"],
            "principle": "你们要安息，要知道我是神",
            "scripture": "诗46:10",
            "alignment_score": 80,
            "assessment": "休息是神的恩赐和命令，为恢复体力更好地服事。但要避免以休息为借口逃避责任。",
            "tips": ["在休息中默想神的话语", "感恩神的供应", "为恢复后的服事做准备"]
        },
        "运动": {
            "keywords": ["运动", "跑步", "健身", "游泳", "打球", "exercise", "run", "gym", "swim", "sport"],
            "principle": "身子是圣灵的殿",
            "scripture": "林前6:19",
            "alignment_score": 75,
            "assessment": "照顾身体是管家的责任，但不可将身体崇拜取代对神的敬拜。",
            "tips": ["在运动中信靠神的供应", "将健康视为服事的工具", "避免偶像化的身材追求"]
        },
        "娱乐": {
            "keywords": ["娱乐", "游戏", "追剧", "看电影", "刷视频", "短视频", "game", "movie", "video", "tv", "show"],
            "principle": "凡事我都可行，但不都有益处",
            "scripture": "林前6:12",
            "alignment_score": 45,
            "assessment": "娱乐需要谨慎分辨，避免沉迷和消耗时间，选择能滋养心灵的内容。",
            "tips": ["设定娱乐时间界限", "选择有建造性的内容", "避免使人远离神的娱乐"]
        },
        "社交": {
            "keywords": ["社交", "聚会", "吃饭", "聊天", "约会", "朋友", "party", "dinner", "chat", "friend", "date"],
            "principle": "你们要彼此相爱，像我爱你们一样",
            "scripture": "约15:12",
            "alignment_score": 65,
            "assessment": "社交是神所设立的关系，当以爱心和诚实待人，避免无益的交往。",
            "tips": ["在社交中见证基督", "选择能彼此建造的友谊", "避免使人跌倒的场合"]
        },
        "消费": {
            "keywords": ["购物", "消费", "买", "花钱", "网购", "shopping", "buy", "spend", "purchase", "order"],
            "principle": "你们要谨慎自守，免去一切的贪婪",
            "scripture": "路12:15",
            "alignment_score": 50,
            "assessment": "消费需要节制和管家意识，避免贪婪和浪费，优先考虑神的国和义。",
            "tips": ["消费前祷告寻求智慧", "分辨需要与欲望", "将部分资源用于奉献"]
        },
        "饮食": {
            "keywords": ["吃饭", "吃", "做饭", "外卖", "餐厅", "eat", "food", "cook", "meal", "restaurant"],
            "principle": "所以，你们或吃或喝，无论做什么，都要为荣耀神而行",
            "scripture": "林前10:31",
            "alignment_score": 70,
            "assessment": "饮食是神的恩赐，当以感恩的心领受，避免暴饮暴食和拜偶像。",
            "tips": ["饭前感恩祷告", "节制饮食", "与他人分享食物"]
        },
        "家务": {
            "keywords": ["家务", "打扫", "洗碗", "洗衣", "整理", "清洁", "housework", "clean", "wash"],
            "principle": "要殷勤不可懒惰",
            "scripture": "罗12:11",
            "alignment_score": 75,
            "assessment": "家务是管家职分的具体体现，当以喜乐的心服事家人。",
            "tips": ["以服事神的心做家务", "为家人的益处而做", "在工作中默想神的恩典"]
        }
    }

    NEGATIVE_SIGNALS = [
        ("拖延逃避", ["拖延", "推迟", "明天再说", "procrastinate", "later", "明天"], "逃避责任", "将任务交托给神，依靠祂的力量开始"),
        ("过度沉迷", ["通宵", "熬夜", "binge", "一直", "不停", "all night"], "缺乏节制", "设定健康的界限，避免过度消耗"),
        ("心志抱怨", ["不想", "被迫", "烦", "讨厌", "hate", "forced"], "心志不对", "调整心态，将其视为服事神的机会"),
        ("动机不纯", ["赚钱", "发财", "暴富", "rich", "money", "wealth", "profit"], "动机不纯", "检视动机，确保是为了荣耀神而非满足私欲"),
        ("逃避现实", ["逃避", "躲", "不想面对", "avoid", "hide", "escape"], "逃避现实", "勇敢面对，相信神与你同在"),
    ]

    POSITIVE_SIGNALS = [
        ("以祷告开始", ["祷告", "祈求", "pray"], "以祷告开始", 10),
        ("以感恩的心", ["感恩", "感谢", "thank"], "以感恩的心去做", 10),
        ("以服事的心", ["服事", "帮助", "serve", "help"], "以服事的心去做", 10),
        ("忠心完成", ["忠心", "尽力", "diligent", "faithful"], "忠心完成托付", 10),
    ]

    def assess(self, task: str) -> SpiritualAlignmentResult:
        """评估行为与神的道的对齐程度"""
        task_lower = task.lower()

        # 1. 检查高对齐关键词
        for kw in self.HIGH_ALIGNMENT_KEYWORDS:
            if kw.lower() in task_lower:
                score = 85 + min(task_lower.count(kw.lower()) * 3, 15)
                return SpiritualAlignmentResult(
                    aligned=True,
                    alignment_score=min(score, 100),
                    assessment=f"'{task}' 是直接与神相交或服事神的行为，与神的道高度对齐。",
                    scripture_reference="太22:37-39",
                    principle="你要尽心、尽性、尽意爱主你的神，又要爱人如己。",
                    misalignment_areas=[],
                    alignment_actions=["持续持守这美好的习惯", "在其中经历与神更深的相交", "邀请他人一同参与"],
                    category="敬虔操练"
                )

        # 2. 检查低对齐关键词
        for kw in self.LOW_ALIGNMENT_KEYWORDS:
            if kw.lower() in task_lower:
                return SpiritualAlignmentResult(
                    aligned=False,
                    alignment_score=15,
                    assessment=f"'{task}' 明显偏离神的道，需要立即悔改和调整。",
                    scripture_reference="加5:19-21",
                    principle="情欲的事都是显而易见的...行这样事的人必不能承受神的国。",
                    misalignment_areas=["与神的关系破裂", "圣洁生活的亏欠", "可能伤害自己和他人"],
                    alignment_actions=["立即悔改并认罪", "寻求教会领袖或肢体的帮助", "建立问责机制", "以敬虔的操练替代这行为"],
                    category="需要悔改"
                )

        # 3. 中性行为分类匹配
        best_match = None
        best_score = 0
        for category, config in self.NEUTRAL_CATEGORIES.items():
            score = sum(1 for kw in config["keywords"] if kw.lower() in task_lower)
            if score > best_score:
                best_score = score
                best_match = (category, config)

        if best_match and best_score > 0:
            category, config = best_match
            base_score = config["alignment_score"]
            misalignment_areas = []
            alignment_actions = config["tips"].copy()

            for area, keywords, misalignment, action in self.NEGATIVE_SIGNALS:
                if any(kw in task_lower for kw in keywords):
                    misalignment_areas.append(misalignment)
                    alignment_actions.append(action)
                    base_score -= 15

            for area, keywords, action, bonus in self.POSITIVE_SIGNALS:
                if any(kw in task_lower for kw in keywords):
                    alignment_actions.append(action)
                    base_score += bonus

            base_score = max(10, min(95, base_score))
            aligned = base_score >= 50

            return SpiritualAlignmentResult(
                aligned=aligned,
                alignment_score=base_score,
                assessment=f"'{task}' 属于{category}类行为。{config['assessment']}",
                scripture_reference=config["scripture"],
                principle=config["principle"],
                misalignment_areas=misalignment_areas,
                alignment_actions=alignment_actions,
                category=category
            )

        # 4. 默认评估
        return SpiritualAlignmentResult(
            aligned=True,
            alignment_score=60,
            assessment=f"'{task}' 需要更多情境信息才能精确评估。建议以祷告求神鉴察这行为的动机和方式。",
            scripture_reference="箴3:5-6",
            principle="你要专心仰赖耶和华，不可倚靠自己的聪明。",
            misalignment_areas=[],
            alignment_actions=["为此行为祷告寻求神的引导", "检视内心的动机", "咨询属灵导师或牧师的意见"],
            category="需进一步分辨"
        )


# 便捷函数
spiritual_alignment_engine = SpiritualAlignmentEngine()


def assess_spiritual_alignment(task: str) -> dict:
    """便捷函数：评估属灵对齐"""
    return spiritual_alignment_engine.assess(task).to_dict()
