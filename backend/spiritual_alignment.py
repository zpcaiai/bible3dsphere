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
            "tips": [
                "今天开始工作前，用1-2分钟安静祷告：'主，这份工作是你托付的，求你赐我智慧和专注，让我在每个细节中荣耀你。无论结果如何，我将荣耀归给你。'",
                "当遇到压力或人际摩擦时，在心里默祷：'主，求你让我的回应反映基督的温柔与诚实。'然后做出一个小而具体的善意行动。",
                "今天下班前，用30秒回顾：我今天在工作中有没有一个时刻是真正为神而做的？将那个时刻感谢神，作为明天的动力。"
            ]
        },
        "学习": {
            "keywords": ["学习", "读书", "考试", "论文", "研究", "课程", "培训", "study", "read", "exam", "paper", "research", "course"],
            "principle": "你要尽心、尽性、尽力爱耶和华你的神",
            "scripture": "申6:5",
            "alignment_score": 75,
            "assessment": "学习是装备自己更好地服事神和人的途径，当以敬畏神的心追求知识。",
            "tips": [
                "学习前祷告：'主，你是一切知识的源头。求你开我的悟性，让我所学能更好地服事你和他人。赐我专注与毅力，使这学习成为爱你的方式之一。'",
                "学完一个段落后停一下，问自己：'这知识如何帮助我更认识神、更爱人？'写下一句话，将所学与信仰连接。",
                "当学习困难时，不要立刻放弃，先祷告：'主，求你赐我突破的力量。'然后把问题拆小，每完成一步就感谢神的帮助。"
            ]
        },
        "休息": {
            "keywords": ["休息", "睡觉", "午休", "假期", "放松", "rest", "sleep", "vacation", "relax"],
            "principle": "你们要安息，要知道我是神",
            "scripture": "诗46:10",
            "alignment_score": 80,
            "assessment": "休息是神的恩赐和命令，为恢复体力更好地服事。但要避免以休息为借口逃避责任。",
            "tips": [
                "休息前感恩祷告：'主，感谢你赐我安息的权利。求你在我休息时更新我的力量，让这休息不只是身体的恢复，更是灵魂在你里面的安静。'",
                "在休息中刻意放慢：选一段诗篇（如诗23篇），读一遍，让神的话语在心里留驻，而非立刻拿起手机填满每一个空白。",
                "休息结束前，用1分钟问自己：'神在这段安静中对我说了什么？'哪怕只是一个感受，也将它写下或对神说出。"
            ]
        },
        "运动": {
            "keywords": ["运动", "跑步", "健身", "游泳", "打球", "exercise", "run", "gym", "swim", "sport"],
            "principle": "身子是圣灵的殿",
            "scripture": "林前6:19",
            "alignment_score": 75,
            "assessment": "照顾身体是管家的责任，但不可将身体崇拜取代对神的敬拜。",
            "tips": [
                "运动开始时祷告：'主，感谢你赐给我这个身体。这次运动是对你托付的管家职分的回应，不是为了骄傲，而是为了更有力量服事你和家人。'",
                "运动中若感到疲惫，默念：'我靠着那加给我力量的，凡事都能做。'（腓4:13）让每一步都成为对神话语的实践。",
                "运动后检视心态：我今天运动的动机是荣耀神还是取悦自己？若发现有偶像化倾向，对神说：'主，帮我将焦点从外表转向内在的圣洁。'"
            ]
        },
        "娱乐": {
            "keywords": ["娱乐", "游戏", "追剧", "看电影", "刷视频", "短视频", "game", "movie", "video", "tv", "show"],
            "principle": "凡事我都可行，但不都有益处",
            "scripture": "林前6:12",
            "alignment_score": 45,
            "assessment": "娱乐需要谨慎分辨，避免沉迷和消耗时间，选择能滋养心灵的内容。",
            "tips": [
                "娱乐前祷告：'主，我需要放松，求你帮我分辨什么是滋养灵魂的，什么是消耗生命的。给我智慧设定界限，让我娱乐之后仍能离你更近。'",
                "实践具体界限：设置计时器（如30分钟），时间到时停下来做一个深呼吸，问：'我刚才的时间是建造了我还是消耗了我？'然后决定是否继续。",
                "本周用一次娱乐时间替换为属灵滋养：听一首敬拜诗歌、读一篇见证、或与信仰朋友通话10分钟，感受不同的满足感。"
            ]
        },
        "社交": {
            "keywords": ["社交", "聚会", "吃饭", "聊天", "约会", "朋友", "party", "dinner", "chat", "friend", "date"],
            "principle": "你们要彼此相爱，像我爱你们一样",
            "scripture": "约15:12",
            "alignment_score": 65,
            "assessment": "社交是神所设立的关系，当以爱心和诚实待人，避免无益的交往。",
            "tips": [
                "社交前祷告：'主，让我今天遇见的每一个人都感受到你的爱通过我流淌。给我敏锐的心，知道什么时候倾听、什么时候鼓励、什么时候分享信仰。'",
                "在交往中实践一个小小的见证：诚实地说一句真话、主动关心一个需要的人、或在合适的时机自然地说'我会为你祷告'并真正去做。",
                "社交结束后问自己：'今天的交往有没有使我或他人离神更近？'若有遗憾，对神认罪并求调整；若有果效，感谢神并记录下来。"
            ]
        },
        "消费": {
            "keywords": ["购物", "消费", "买", "花钱", "网购", "shopping", "buy", "spend", "purchase", "order"],
            "principle": "你们要谨慎自守，免去一切的贪婪",
            "scripture": "路12:15",
            "alignment_score": 50,
            "assessment": "消费需要节制和管家意识，避免贪婪和浪费，优先考虑神的国和义。",
            "tips": [
                "消费前停3秒祷告：'主，这是需要还是欲望？是托付的管家行为还是短暂的满足？求你给我辨别的智慧，让我的金钱用法反映我的信仰价值观。'",
                "建立一个实践：每次消费前在心里快速问三个问题——这是必需的吗？这会荣耀神吗？我是否已经考虑过奉献比例？让消费成为信仰的训练场。",
                "本月从消费中拨出一笔小额（哪怕50元）用于奉献或帮助有需要的人，让每一次花钱都与神国的价值观连接。"
            ]
        },
        "饮食": {
            "keywords": ["吃饭", "吃", "做饭", "外卖", "餐厅", "eat", "food", "cook", "meal", "restaurant"],
            "principle": "所以，你们或吃或喝，无论做什么，都要为荣耀神而行",
            "scripture": "林前10:31",
            "alignment_score": 70,
            "assessment": "饮食是神的恩赐，当以感恩的心领受，避免暴饮暴食和拜偶像。",
            "tips": [
                "饭前用真实的感恩祷告，不只是惯例：'主，感谢你预备这食物，感谢种植、烹调、运输这食物的每一双手。让这食物成为我服事你的力量，而非贪欲的满足。'",
                "饮食中练习节制：吃到七八分饱就停下来，感谢神的供应已经足够。若有暴食冲动，对神说：'主，我里面有什么空洞在用食物填补？求你用你的爱来填满。'",
                "本周一次，邀请一个独居或孤单的人一起吃饭，让餐桌成为神爱流动的地方，让饮食不只滋养身体也滋养关系。"
            ]
        },
        "家务": {
            "keywords": ["家务", "打扫", "洗碗", "洗衣", "整理", "清洁", "housework", "clean", "wash"],
            "principle": "要殷勤不可懒惰",
            "scripture": "罗12:11",
            "alignment_score": 75,
            "assessment": "家务是管家职分的具体体现，当以喜乐的心服事家人。",
            "tips": [
                "开始家务前祷告：'主，这些琐事是我对家人爱的表达，也是对你托付的回应。求你让我的心不焦躁、不抱怨，在平凡中找到服事的喜悦和你同在的平安。'",
                "做家务时把它变成默想的时间：选一节经文（如'凡你手所当做的事要尽力去做'），在重复的动作中反复默念，让劳动成为心灵操练。",
                "家务完成后，看着整洁的环境，对神说一句感谢：'主，感谢你让我有能力、有家人可以服事。'让感恩成为结束日常劳动的方式。"
            ]
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
        ("以祷告开始", ["祷告", "祈求", "pray"], "继续保持以祷告开始的习惯，并加深它：不只是请求，也倾听神在这件事上对你说的话，用1-2分钟在安静中等候神的引导。", 10),
        ("以感恩的心", ["感恩", "感谢", "thank"], "感恩是抵挡抱怨和焦虑的武器。在这件事结束后，写下三件具体感谢神的事，让感恩不只是开始时的态度，也成为全程的底色。", 10),
        ("以服事的心", ["服事", "帮助", "serve", "help"], "服事的心是宝贵的恩赐，但也需要被滋养。今天服事后，回到神面前休息一会儿，告诉祂你的感受和疲惫，让服事从与神的亲密关系中涌流，而非耗尽自己。", 10),
        ("忠心完成", ["忠心", "尽力", "diligent", "faithful"], "忠心是神所看重的品格。当这件事完成时，不论结果大小，对神说：'主，我尽了我所能，将结果交托给你。'让忠心成为你与神之间的信任关系的操练。", 10),
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
                    alignment_actions=[
                        "主啊，感谢你赐我渴慕亲近你的心。求你在这操练中更新我，使我不只有行为的形式，更有与你同在的喜悦。愿我每次祷告、读经、敬拜都成为真实的相交，而非宗教习惯。",
                        "立下具体计划：固定时间、固定地点，将这操练记入日程。若有一天缺失，不要自责，轻柔地回到神面前，从感恩开始重新起步。",
                        "本周邀请一位弟兄姊妹一同参与，或分享你在这操练中经历的一句话，让你的生命成为他人的激励。"
                    ],
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
            alignment_actions=[
                "在开始之前，安静2分钟祷告：'主，求你用你的光照我，让我看清这件事背后的动机是出于爱、责任还是恐惧。若符合你的心意，求你赐力量；若不符合，求你关门并给我平安。'",
                "做一个简单的动机检视：拿纸写下'我为什么要做这件事？'列出三个理由，诚实地问：哪一条最接近荣耀神和服事人？让最纯正的动机成为行动的驱动力。",
                "本周找一位你信任的属灵同伴或牧者，用10分钟分享这件事，听取他们从信仰角度的观察。有时候，神的声音通过身边人的智慧最清晰地传递。"
            ],
            category="需进一步分辨"
        )


# 便捷函数
spiritual_alignment_engine = SpiritualAlignmentEngine()


def assess_spiritual_alignment(task: str) -> dict:
    """便捷函数：评估属灵对齐"""
    return spiritual_alignment_engine.assess(task).to_dict()
