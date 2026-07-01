"""
expansion_content.py — 内容与神学扩充：推荐书目 + 圣诗目录（content-theology-expansion 批次）

作为数据来源的真理表（single source of truth）。路由从此模块读取，无需 DB 即可服务；
用户的收藏/书签走 `resource_bookmarks`（迁移 0141）。
continent 对应属灵星球「大陆」：A 认识神 / B 回到福音 / C 心的争战 / D 与神同行 /
E 等候与受苦 / F 分辨与呼召 / G 门徒与群体 / H 华人本土灵修。
public_domain=True 者可考虑收录全文；False 者宜用授权节选/导读。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

CONTINENTS: Dict[str, str] = {
    "A": "认识神 · 神论与敬拜",
    "B": "回到福音 · 恩典/身份/联合",
    "C": "心的争战 · 情感与内在",
    "D": "与神同行 · 操练与祷告",
    "E": "等候与受苦 · 哀歌",
    "F": "分辨与呼召",
    "G": "门徒与群体",
    "H": "华人本土灵修",
}

# priority: 3=填补空白/极高契合, 2=强化, 1=锦上添花
BOOKS: List[Dict[str, Any]] = [
    # A 认识神
    {"slug": "packer-knowing-god", "zh": "认识神", "en": "Knowing God", "author": "巴刻 J.I. Packer",
     "tradition": "改革宗福音派", "continent": "A", "public_domain": False, "priority": 3,
     "blurb": "认识神本身，而非只认识关于神的知识；属性化为敬拜。"},
    {"slug": "tozer-pursuit", "zh": "渴慕神", "en": "The Pursuit of God", "author": "陶恕 A.W. Tozer",
     "tradition": "敬虔/奋兴", "continent": "A", "public_domain": False, "priority": 3,
     "blurb": "对神的圣洁饥渴；追求祂自己过于祂的恩赐。"},
    {"slug": "tozer-holy", "zh": "认识至圣者", "en": "The Knowledge of the Holy", "author": "陶恕 A.W. Tozer",
     "tradition": "敬虔", "continent": "A", "public_domain": False, "priority": 3,
     "blurb": "逐一默想神的属性——你如何想神，是你最重要的事。"},
    {"slug": "reeves-trinity", "zh": "活在三一神的爱中", "en": "Delighting in the Trinity", "author": "麦克·里夫斯 Michael Reeves",
     "tradition": "改革宗", "continent": "A", "public_domain": False, "priority": 2,
     "blurb": "神本是父子灵的爱之团契——补三一空白。"},
    {"slug": "piper-desiring-god", "zh": "渴慕神（基督徒享乐主义）", "en": "Desiring God", "author": "约翰·派博 John Piper",
     "tradition": "改革宗", "continent": "A", "public_domain": False, "priority": 3,
     "blurb": "神在我们最以祂为乐时最得荣耀。"},

    # B 回到福音
    {"slug": "augustine-confessions", "zh": "忏悔录", "en": "Confessions", "author": "奥古斯丁 Augustine",
     "tradition": "教父/古典", "continent": "B", "public_domain": True, "priority": 3,
     "blurb": "失序之爱；心不安直到安息于你——偶像循环的神学根。"},
    {"slug": "ortlund-gentle-lowly", "zh": "温柔谦卑", "en": "Gentle and Lowly", "author": "Dane Ortlund",
     "tradition": "改革宗/清教徒", "continent": "B", "public_domain": False, "priority": 3,
     "blurb": "基督对罪人与受苦者的慈心——托底『不定罪』。"},
    {"slug": "ferguson-whole-christ", "zh": "全备的基督", "en": "The Whole Christ", "author": "辛克莱·傅格森 Sinclair Ferguson",
     "tradition": "改革宗", "continent": "B", "public_domain": False, "priority": 3,
     "blurb": "律法主义/反律法主义/得救确据——对接属灵低潮诊断。"},
    {"slug": "wilbourne-union", "zh": "与基督联合", "en": "Union with Christ", "author": "Rankin Wilbourne",
     "tradition": "改革宗", "continent": "B", "public_domain": False, "priority": 2,
     "blurb": "『在基督里』是身份与成圣的枢纽。"},
    {"slug": "thompson-soul-of-shame", "zh": "灵魂的羞耻", "en": "The Soul of Shame", "author": "汤普森 Curt Thompson",
     "tradition": "整合（神学+神经科学）", "continent": "B", "public_domain": False, "priority": 2,
     "blurb": "羞耻的神经科学 + 恩典——契合心理×属灵融合。"},
    {"slug": "bridges-discipline-grace", "zh": "恩典的操练", "en": "The Discipline of Grace", "author": "傑瑞·布里吉斯 Jerry Bridges",
     "tradition": "改革宗福音派", "continent": "B", "public_domain": False, "priority": 2,
     "blurb": "每天向自己传讲福音。"},

    # C 心的争战
    {"slug": "edwards-affections", "zh": "宗教情感真伪辨", "en": "Religious Affections", "author": "爱德华兹 Jonathan Edwards",
     "tradition": "清教徒/改革宗", "continent": "C", "public_domain": True, "priority": 3,
     "blurb": "真假属灵情感的分辨——情绪球的神学底座。"},
    {"slug": "flavel-keeping-heart", "zh": "守护你的心", "en": "Keeping the Heart", "author": "约翰·傅拉维 John Flavel",
     "tradition": "清教徒", "continent": "C", "public_domain": True, "priority": 2,
     "blurb": "竭力保守己心（箴4:23）——与『今日心镜』同魂。"},
    {"slug": "burroughs-contentment", "zh": "基督徒知足的秘诀", "en": "The Rare Jewel of Christian Contentment", "author": "伯罗斯 Jeremiah Burroughs",
     "tradition": "清教徒", "continent": "C", "public_domain": True, "priority": 3,
     "blurb": "知足是学来的——对治焦虑/掌控偶像。"},
    {"slug": "watson-repentance", "zh": "悔改的教义", "en": "The Doctrine of Repentance", "author": "汤姆·华森 Thomas Watson",
     "tradition": "清教徒", "continent": "C", "public_domain": True, "priority": 1,
     "blurb": "真悔改的六要素。"},

    # D 与神同行
    {"slug": "willard-renovation", "zh": "心灵的重塑", "en": "Renovation of the Heart", "author": "达拉斯·魏乐德 Dallas Willard",
     "tradition": "灵修神学", "continent": "D", "public_domain": False, "priority": 3,
     "blurb": "全人塑造（心思/意志/身体/社会/灵魂）——Formation OS 级框架。"},
    {"slug": "foster-celebration", "zh": "属灵操练礼赞", "en": "Celebration of Discipline", "author": "傅士德 Richard Foster",
     "tradition": "灵修神学", "continent": "D", "public_domain": False, "priority": 2,
     "blurb": "操练的经典分类（内在/外在/团体）。"},
    {"slug": "smith-you-are-what-you-love", "zh": "你的爱决定你是谁", "en": "You Are What You Love", "author": "James K.A. Smith",
     "tradition": "改革宗/文化神学", "continent": "D", "public_domain": False, "priority": 3,
     "blurb": "文化礼仪塑造欲望——喂养 habit/cultural 引擎。"},
    {"slug": "warren-liturgy-ordinary", "zh": "平凡日子的属灵操练", "en": "Liturgy of the Ordinary", "author": "华伦 Tish Harrison Warren",
     "tradition": "圣公会", "continent": "D", "public_domain": False, "priority": 1,
     "blurb": "日常琐事即塑造。"},
    {"slug": "scazzero-eh-spirituality", "zh": "情商与灵命", "en": "Emotionally Healthy Spirituality", "author": "彼得·斯卡吉罗 Peter Scazzero",
     "tradition": "福音派", "continent": "D", "public_domain": False, "priority": 3,
     "blurb": "情感不成熟＝属灵不成熟——本产品论题的正主。"},
    {"slug": "valley-of-vision", "zh": "幽谷之光（清教徒祷文）", "en": "The Valley of Vision", "author": "Arthur Bennett 编",
     "tradition": "清教徒", "continent": "D", "public_domain": False, "priority": 3,
     "blurb": "清教徒祷告文选——祷告规则/清晨甘露祷文库。"},
    {"slug": "keller-prayer", "zh": "祷告：与神亲密", "en": "Prayer", "author": "提摩太·凯勒 Timothy Keller",
     "tradition": "改革宗", "continent": "D", "public_domain": False, "priority": 2,
     "blurb": "敬畏与亲密并重的祷告神学。"},
    {"slug": "comer-hurry", "zh": "毫不留情地除掉匆忙", "en": "The Ruthless Elimination of Hurry", "author": "约翰·马克·科默 John Mark Comer",
     "tradition": "福音派", "continent": "D", "public_domain": False, "priority": 1,
     "blurb": "以耶稣的节奏对治匆忙——安息主线。"},

    # E 等候与受苦
    {"slug": "vroegop-dark-clouds", "zh": "黑云背后是深恩", "en": "Dark Clouds, Deep Mercy", "author": "Mark Vroegop",
     "tradition": "改革宗", "continent": "E", "public_domain": False, "priority": 3,
     "blurb": "哀歌四步：转向→倾诉→祈求→信靠——补哀歌模板空白。"},
    {"slug": "keller-suffering", "zh": "行过苦难", "en": "Walking with God through Pain and Suffering", "author": "提摩太·凯勒 Timothy Keller",
     "tradition": "改革宗", "continent": "E", "public_domain": False, "priority": 3,
     "blurb": "苦难的多种『炉』与福音回应——扩展受苦引擎。"},
    {"slug": "lewis-grief-observed", "zh": "卿卿如晤", "en": "A Grief Observed", "author": "C.S. 路易斯 C.S. Lewis",
     "tradition": "福音派/古典", "continent": "E", "public_domain": False, "priority": 2,
     "blurb": "诚实的哀恸；危机后牧养。"},
    {"slug": "john-cross-dark-night", "zh": "心灵的黑夜", "en": "Dark Night of the Soul", "author": "十字架约翰 John of the Cross",
     "tradition": "天主教默观", "continent": "E", "public_domain": True, "priority": 2,
     "blurb": "属灵枯竭中的净化——对接属灵低潮/枯竭。"},

    # F 分辨与呼召
    {"slug": "ignatius-exercises", "zh": "神操（诸灵分辨）", "en": "The Spiritual Exercises", "author": "罗耀拉的依纳爵 Ignatius of Loyola",
     "tradition": "天主教/依纳爵", "continent": "F", "public_domain": True, "priority": 3,
     "blurb": "安慰/枯竭分辨规则——给决策引擎加经典轴线。"},
    {"slug": "guinness-the-call", "zh": "一生的呼召", "en": "The Call", "author": "奥斯·葛尼斯 Os Guinness",
     "tradition": "福音派", "continent": "F", "public_domain": False, "priority": 2,
     "blurb": "首要呼召（归向神）vs 次要呼召（职业）。"},
    {"slug": "palmer-let-life-speak", "zh": "倾听生命的声音", "en": "Let Your Life Speak", "author": "帕克·帕尔默 Parker Palmer",
     "tradition": "贵格会", "continent": "F", "public_domain": False, "priority": 1,
     "blurb": "召命是让生命发声，而非勉强。"},

    # G 门徒与群体
    {"slug": "bonhoeffer-cost", "zh": "作门徒的代价", "en": "The Cost of Discipleship", "author": "潘霍华 Dietrich Bonhoeffer",
     "tradition": "信义宗", "continent": "G", "public_domain": False, "priority": 3,
     "blurb": "廉价恩典 vs 重价恩典。"},
    {"slug": "bonhoeffer-life-together", "zh": "团契生活", "en": "Life Together", "author": "潘霍华 Dietrich Bonhoeffer",
     "tradition": "信义宗", "continent": "G", "public_domain": False, "priority": 3,
     "blurb": "基督里团契的神学与操练——accountability 的底座。"},

    # H 华人本土灵修（附教义提示）
    {"slug": "nee-normal-christian-life", "zh": "正常的基督徒生活", "en": "The Normal Christian Life", "author": "倪柝声 Watchman Nee",
     "tradition": "华人（地方教会，需分辨）", "continent": "H", "public_domain": False, "priority": 3,
     "blurb": "因信与基督同死同活——与基督联合的华人表达。⚠部分体系有争议，宜取灵修经典段落。"},
    {"slug": "wang-mingdao", "zh": "王明道文集/见证", "en": "Wang Mingdao — Writings", "author": "王明道 Wang Mingdao",
     "tradition": "华人", "continent": "H", "public_domain": False, "priority": 2,
     "blurb": "重生、真实、受苦中的忠贞——华人受苦见证。"},
    {"slug": "stephen-tong", "zh": "唐崇荣归正讲道选", "en": "Stephen Tong — Reformed Sermons", "author": "唐崇荣 Stephen Tong",
     "tradition": "华人改革宗", "continent": "H", "public_domain": False, "priority": 2,
     "blurb": "归正神学的华人系统表达——教义/世界观。"},
    {"slug": "john-sung", "zh": "宋尚节日记/讲道", "en": "John Sung — Diaries", "author": "宋尚节 John Sung",
     "tradition": "华人奋兴", "continent": "H", "public_domain": False, "priority": 1,
     "blurb": "认罪、复兴、布道的火。"},
]

# 圣诗扩充（现有 9 首之外）
HYMNS: List[Dict[str, Any]] = [
    {"slug": "be-thou-my-vision", "zh": "成为我异象", "en": "Be Thou My Vision", "era": "古典", "theme": "认识神/献身"},
    {"slug": "come-thou-fount", "zh": "我灵镇静", "en": "Come Thou Fount of Every Blessing", "era": "古典", "theme": "恩典"},
    {"slug": "great-is-thy-faithfulness", "zh": "你信实何广大", "en": "Great Is Thy Faithfulness", "era": "古典", "theme": "信实/等候"},
    {"slug": "and-can-it-be", "zh": "何等奇妙", "en": "And Can It Be", "era": "古典", "theme": "福音/称义"},
    {"slug": "rock-of-ages", "zh": "万古磐石", "en": "Rock of Ages", "era": "古典", "theme": "福音/避难所"},
    {"slug": "o-sacred-head", "zh": "宝血的头曾受伤", "en": "O Sacred Head Now Wounded", "era": "古典", "theme": "十架/受苦"},
    {"slug": "turn-your-eyes", "zh": "定睛在耶稣", "en": "Turn Your Eyes Upon Jesus", "era": "古典", "theme": "仰望/认识神"},
    {"slug": "his-eye-sparrow", "zh": "祂看顾麻雀", "en": "His Eye Is on the Sparrow", "era": "古典", "theme": "护理/安慰"},
    {"slug": "in-christ-alone", "zh": "唯独基督", "en": "In Christ Alone", "era": "现代", "theme": "与基督联合"},
    {"slug": "yet-not-i", "zh": "不再是我", "en": "Yet Not I but Through Christ in Me", "era": "现代", "theme": "在基督里/身份"},
    {"slug": "he-will-hold-me-fast", "zh": "祂必保守我", "en": "He Will Hold Me Fast", "era": "现代", "theme": "得救的稳固/坚忍"},
    {"slug": "zh-most-beautiful-blessing", "zh": "这一生最美的祝福", "en": "The Most Beautiful Blessing", "era": "华语现代", "theme": "跟随/献身"},
    {"slug": "zh-who-holds-tomorrow", "zh": "我知谁掌管明天", "en": "I Know Who Holds Tomorrow", "era": "华语", "theme": "护理/等候"},
]


def list_books(continent: Optional[str] = None, min_priority: int = 0) -> List[Dict[str, Any]]:
    out = [b for b in BOOKS if (continent is None or b["continent"] == continent) and b["priority"] >= min_priority]
    return sorted(out, key=lambda b: (-b["priority"], b["continent"], b["slug"]))


def list_hymns() -> List[Dict[str, Any]]:
    return list(HYMNS)


def meta() -> Dict[str, Any]:
    return {
        "continents": CONTINENTS,
        "book_count": len(BOOKS),
        "hymn_count": len(HYMNS),
        "note": "public_domain=True 者可考虑收录全文；False 者宜用授权节选/导读。华人条目附教义分辨提示。",
    }
