"""Versioned lexicons and taxonomies.

Kept separate from the skill modules so that prompt/taxonomy/schema versioning
required by the engineering acceptance criteria has a single home.
"""

from __future__ import annotations

from .models import ClaimType, PrideSignal, QuestionStage

TAXONOMY_VERSION = "0.1.0"

# --- skill 02: claim typing ------------------------------------------------

CLAIM_MARKERS: dict[ClaimType, tuple[str, ...]] = {
    ClaimType.SALVATION: (
        "财富自由", "就能实现", "任何人都能", "彻底解决", "从此不再",
        "拯救", "救赎", "唯一出路", "终极答案", "改变命运", "得自由",
    ),
    ClaimType.CAUSAL: (
        "因为", "所以", "导致", "才会", "只要", "就能", "就会", "之所以",
    ),
    ClaimType.MORAL: (
        "应该", "不该", "错的", "对的", "罪", "可耻", "懒", "不配", "活该",
    ),
    ClaimType.IDENTITY: (
        "我是", "他是", "你就是", "本质上", "这种人", "失败者", "赢家",
    ),
    ClaimType.ANTHROPOLOGICAL: (
        "人本来", "人性", "每个人都", "人天生", "人只要",
    ),
    ClaimType.ENEMY: (
        "他们", "那些人", "敌人", "既得利益", "阻碍你的", "拖后腿",
    ),
    ClaimType.ACTION_CALL: (
        "复制", "立刻", "马上", "报名", "跟我", "照做", "执行", "现在就",
    ),
    ClaimType.EMOTIONAL: (
        "我觉得", "我担心", "我害怕", "我焦虑", "让我", "我常常", "我总是",
    ),
    ClaimType.FACTUAL: (
        "数据", "统计", "研究", "报告", "年", "%", "百分",
    ),
}

RHETORIC_MARKERS: tuple[str, ...] = (
    "永远", "绝对", "百分之百", "从来没有", "所有人", "任何人", "一定",
    "毫无例外", "根本不可能",
)

VERIFIABLE_MARKERS: tuple[str, ...] = ("数据", "统计", "研究", "报告", "记录", "财报")

# --- skill 04: pride signal taxonomy ---------------------------------------

PRIDE_MARKERS: dict[PrideSignal, tuple[str, ...]] = {
    PrideSignal.EPISTEMIC_SUPERIORITY: (
        "我最清楚", "只有我懂", "你们不懂", "醒醒吧", "看不透", "认知不够",
    ),
    PrideSignal.MORAL_SELF_RIGHTEOUSNESS: (
        "我从不", "我问心无愧", "我比他们干净", "我是好人", "我没有错",
    ),
    PrideSignal.ACHIEVEMENT_JUSTIFICATION: (
        "努力", "执行力", "财富自由", "成功", "复制我", "我做到了", "身价",
    ),
    PrideSignal.AUTONOMY_ABSOLUTISM: (
        "我的人生我做主", "谁也管不了", "只听自己", "不需要任何人",
    ),
    PrideSignal.CONTROL_SOVEREIGNTY: (
        "必须掌控", "不能失控", "一切尽在掌握", "我安排好", "不允许意外",
    ),
    PrideSignal.STATUS_GLORY: (
        "粉丝", "流量", "被看见", "被羡慕", "影响力", "关注", "追随",
    ),
    PrideSignal.TRIBAL_SUPERIORITY: (
        "我们这类人", "我们圈子", "外面那些", "他们那种",
    ),
    PrideSignal.VICTIMHOOD_INNOCENCE: (
        "我才是受害者", "都是他们害的", "我什么都没做错", "凭什么怪我",
    ),
    PrideSignal.SPIRITUAL_PRIDE: (
        "神告诉我", "属灵", "我读经", "我更敬虔", "恩赐", "领受",
    ),
    PrideSignal.CONTEMPT_FOR_WEAKNESS: (
        "穷是因为", "失败者", "没执行力", "懒", "废物", "弱者", "活该",
    ),
    PrideSignal.RESENTFUL_JUDGMENT: (
        "就该被", "报应", "让他们看看", "自作自受",
    ),
    PrideSignal.MESSIANIC_SELF_IMAGE: (
        "我来拯救", "跟着我就能", "只有我们能改变", "唯一希望",
    ),
}

PRIDE_ALTERNATIVES: dict[PrideSignal, tuple[str, ...]] = {
    PrideSignal.EPISTEMIC_SUPERIORITY: (
        "可能只是对某一领域确有专长的直白表达",
        "可能是在特定语境下的反讽或修辞",
    ),
    PrideSignal.MORAL_SELF_RIGHTEOUSNESS: (
        "可能是在被指控后的正当自辩",
        "可能是良心确实清白的事实陈述",
    ),
    PrideSignal.ACHIEVEMENT_JUSTIFICATION: (
        "可能是对勤奋这一受造之善的正当肯定",
        "可能是营销话术，不代表其真实自我认知",
    ),
    PrideSignal.AUTONOMY_ABSOLUTISM: (
        "可能是从控制型关系中挣脱的健康边界",
        "可能是对具体越界行为的回应",
    ),
    PrideSignal.CONTROL_SOVEREIGNTY: (
        "可能是尽责的计划能力而非控制欲",
        "可能来自过往创伤形成的安全策略",
    ),
    PrideSignal.STATUS_GLORY: (
        "可能只是职业属性所需的公开曝光",
        "可能是被认可这一正当需要的自然表达",
    ),
    PrideSignal.TRIBAL_SUPERIORITY: (
        "可能是正常的归属感表达",
        "可能是在群体被攻击时的防御",
    ),
    PrideSignal.VICTIMHOOD_INNOCENCE: (
        "可能确实是真实受害经历的陈述",
        "可能是长期不被相信之后的强调",
    ),
    PrideSignal.SPIRITUAL_PRIDE: (
        "可能是真实的属灵经历表达",
        "可能只是该群体的惯用语言",
    ),
    PrideSignal.CONTEMPT_FOR_WEAKNESS: (
        "可能是对特定行为而非对人的批评",
        "可能是激励式语言的粗糙表达",
    ),
    PrideSignal.RESENTFUL_JUDGMENT: (
        "可能是对不义的正当愤怒",
        "可能是尚未处理的伤害反应",
    ),
    PrideSignal.MESSIANIC_SELF_IMAGE: (
        "可能是使命感的夸张表达",
        "可能是商业叙事而非自我神化",
    ),
}

PRIDE_QUESTIONS: dict[PrideSignal, str] = {
    PrideSignal.EPISTEMIC_SUPERIORITY: "什么样的证据会让你认为自己在这件事上看错了？",
    PrideSignal.MORAL_SELF_RIGHTEOUSNESS: "如果同样的标准用在你身上，你会怎样被衡量？",
    PrideSignal.ACHIEVEMENT_JUSTIFICATION: "如果这些成就明天全部失去，你还剩下什么？",
    PrideSignal.AUTONOMY_ABSOLUTISM: "有没有哪一次，听从别人反而让你受益？",
    PrideSignal.CONTROL_SOVEREIGNTY: "当事情脱离掌控时，你最害怕会发生什么？",
    PrideSignal.STATUS_GLORY: "如果没有人看见你做的这件事，你还愿意做吗？",
    PrideSignal.TRIBAL_SUPERIORITY: "你所属群体里，有没有你不愿承认的问题？",
    PrideSignal.VICTIMHOOD_INNOCENCE: "在这件事里，有没有哪怕一小部分是你可以负责的？",
    PrideSignal.SPIRITUAL_PRIDE: "你的属灵经历，是让你更容易还是更难与软弱的人同行？",
    PrideSignal.CONTEMPT_FOR_WEAKNESS: "如果你在对方的处境里，你确定自己会做得更好吗？",
    PrideSignal.RESENTFUL_JUDGMENT: "定罪对方之后，你心里得到了什么？",
    PrideSignal.MESSIANIC_SELF_IMAGE: "如果这件事没有你也能成，你会有什么感受？",
}

# --- skill 05: desire chains ------------------------------------------------

DESIRE_TEMPLATES: dict[PrideSignal, dict[str, str]] = {
    PrideSignal.ACHIEVEMENT_JUSTIFICATION: {
        "good_desire": "希望自己的劳动有意义、被承认",
        "absolutized_desire": "必须靠成就证明自己配活着",
        "functional_savior": "成功与财富",
        "demanded_sacrifice": "安息、关系与诚实面对失败",
        "enslaving_fruit": "持续焦虑、与他人比较、无法停下",
        "loss_reaction": "一旦失败便觉得自身价值崩塌",
        "reanchoring_in_christ": "价值不是靠业绩挣得，而是在基督里被赐予；工作因此可以尽力也可以放手",
    },
    PrideSignal.STATUS_GLORY: {
        "good_desire": "希望被看见、被认可",
        "absolutized_desire": "必须人人肯定我",
        "functional_savior": "流量与地位",
        "demanded_sacrifice": "真实与安息",
        "enslaving_fruit": "焦虑和比较",
        "loss_reaction": "无人关注时感到自己不存在",
        "reanchoring_in_christ": "在基督里已被那位最重要的看见与接纳，公开的注视因此不再是生死攸关",
    },
    PrideSignal.CONTROL_SOVEREIGNTY: {
        "good_desire": "希望所爱的人和事得到保护",
        "absolutized_desire": "必须掌控一切结果",
        "functional_savior": "掌控感与确定性",
        "demanded_sacrifice": "信任、脆弱与依靠他人",
        "enslaving_fruit": "长期紧绷、易怒、无法休息",
        "loss_reaction": "计划被打乱时感到恐慌或愤怒",
        "reanchoring_in_christ": "神的护理比我的掌控更可靠；负责任与放手可以并存",
    },
    PrideSignal.SPIRITUAL_PRIDE: {
        "good_desire": "渴望亲近神、讨神喜悦",
        "absolutized_desire": "必须表现得够属灵才能被神接纳",
        "functional_savior": "属灵表现与自我省察",
        "demanded_sacrifice": "安息、喜乐与坦然无惧",
        "enslaving_fruit": "反复认罪却始终不得确据",
        "loss_reaction": "一有软弱就怀疑神不再赦免",
        "reanchoring_in_christ": "被接纳不靠认罪的彻底程度，而靠基督一次成全的赎罪；悔改是回到已有的接纳里",
    },
    PrideSignal.MORAL_SELF_RIGHTEOUSNESS: {
        "good_desire": "渴望正直、渴望自己是好的",
        "absolutized_desire": "必须证明自己没有错",
        "functional_savior": "道德记录",
        "demanded_sacrifice": "承认过错的自由",
        "enslaving_fruit": "防御、难以道歉、对他人苛刻",
        "loss_reaction": "被指出错误时强烈反弹",
        "reanchoring_in_christ": "在基督里可以承认全部真相而不被定罪，因为定罪已由祂承担",
    },
    PrideSignal.VICTIMHOOD_INNOCENCE: {
        "good_desire": "渴望自己受的伤被看见、被承认",
        "absolutized_desire": "必须在一切事上都是无辜的",
        "functional_savior": "受害者身份",
        "demanded_sacrifice": "自身能动性与成长空间",
        "enslaving_fruit": "苦毒、停滞、关系反复破裂",
        "loss_reaction": "被要求负责时感到再次被伤害",
        "reanchoring_in_christ": "基督既完全看见伤害，也赐下不靠自证无辜的新身份",
    },
}

DEFAULT_DESIRE_CHAIN: dict[str, str] = {
    "good_desire": "渴望安全、意义与被接纳",
    "absolutized_desire": "把某一项好东西当作不可失去的前提",
    "functional_savior": "尚未确定",
    "demanded_sacrifice": "尚未确定",
    "enslaving_fruit": "尚未确定",
    "loss_reaction": "尚未确定",
    "reanchoring_in_christ": "需要更多自我报告才能指出正当需要如何在基督里被重新安置",
}

STRUCTURAL_MARKERS: tuple[str, ...] = (
    "失业", "贫困", "housing", "房价", "裁员", "歧视", "医疗", "债务",
    "原生家庭", "创伤", "霸凌", "压迫", "体制", "系统性",
)

# --- skill 06: question templates -------------------------------------------

STAGE_TEMPLATES: dict[QuestionStage, tuple[str, str]] = {
    QuestionStage.CLARIFY: (
        "当你说“{topic}”的时候，具体指的是什么？",
        "澄清用词，避免在误解的定义上争论",
    ),
    QuestionStage.ASSUMPTION: (
        "这个判断成立，需要先假定哪些事情是真的？",
        "让隐含前提浮出水面",
    ),
    QuestionStage.EVIDENCE: (
        "什么样的证据会让你改变现在的看法？",
        "检验此判断是否可证伪",
    ),
    QuestionStage.COUNTEREXAMPLE: (
        "有没有你认识的人，情况正好相反？",
        "以反例检验普遍化的强度",
    ),
    QuestionStage.CONSEQUENCE: (
        "如果长期照这个信念生活，十年后会结出什么样的果子？",
        "从结果回看信念",
    ),
    QuestionStage.HEART: (
        "在这件事里，你最想得到什么，又最怕失去什么？",
        "从观点层进入心的层面",
    ),
    QuestionStage.WORSHIP: (
        "有没有什么东西，正在承担只有神才承担得起的重量？",
        "辨识功能性救主",
    ),
    QuestionStage.LAW: (
        "如果这个标准同样用在你自己身上，你会怎样？",
        "律法的镜照作用",
    ),
    QuestionStage.GOSPEL: (
        "如果你的价值不是靠赢得，而是在基督里领受的，什么会改变？",
        "把重量从自我表现转移到基督",
    ),
    QuestionStage.RESPONSE: (
        "这一周有没有一件真实的小事，可以作为回应而不是表演？",
        "落到具体、非表演性的回应",
    ),
}

CONSENT_REQUIRED_STAGES: frozenset[QuestionStage] = frozenset(
    {QuestionStage.GOSPEL, QuestionStage.WORSHIP}
)

LAW_PRESSURE_STAGES: frozenset[QuestionStage] = frozenset(
    {QuestionStage.LAW, QuestionStage.WORSHIP}
)

# --- skill 09: safety patterns ----------------------------------------------

CRISIS_MARKERS: tuple[str, ...] = (
    "自杀", "不想活", "结束生命", "自残", "割腕", "轻生", "活不下去", "想死",
)

HARM_TO_OTHERS_MARKERS: tuple[str, ...] = ("杀了他", "报复他们", "让他们付出代价", "伤害他")

ABUSE_MARKERS: tuple[str, ...] = (
    "家暴", "殴打", "性侵", "猥亵", "控制我", "威胁我", "不让我出门", "虐待",
)

DELUSION_MARKERS: tuple[str, ...] = (
    "神直接告诉我", "我领受了新启示", "只有我被拣选", "他们都在监视我", "被鬼附",
)

SCRUPULOSITY_MARKERS: tuple[str, ...] = (
    "反复检查", "认罪几个小时", "还是担心神不会赦免", "不断认罪", "是不是骄傲",
    "得罪神", "不敢有自信", "总觉得自己有罪",
)

MINOR_MARKERS: tuple[str, ...] = ("未成年", "小学生", "初中生", "我今年13", "我今年14")

MEDICALIZATION_MARKERS: tuple[str, ...] = ("抑郁症", "焦虑症", "双相", "精神分裂", "吃药")

CONDEMNATION_MARKERS: tuple[str, ...] = (
    "被鬼附", "被神咒诅", "神已经定他的罪", "他一定下地狱", "他没得救",
)

DEEPER_SIN_REQUEST_MARKERS: tuple[str, ...] = (
    "继续深挖", "还有哪些隐藏的罪", "把我所有的罪", "更多的罪",
)

SUPPORT_GUIDANCE: dict[str, tuple[str, ...]] = {
    "crisis": (
        "这类情况需要现实中的即时支持，请联系当地的紧急服务或危机热线。",
        "同时告诉一位你信任的人，不要独自承受。",
    ),
    "abuse": (
        "安全优先：请考虑联系当地的保护机构或可信任的第三方。",
        "这类情况需要有资质的专业人员介入，而不是仅靠属灵分析。",
    ),
    "mental_health": (
        "反复的自责与不安可能既是属灵问题也是身心健康问题，建议同时寻求合格的心理或医疗专业人员。",
        "也建议找一位稳妥的牧者同行，而不是独自反复自我审查。",
    ),
    "delusion": (
        "这类确定性很强的属灵经历，建议在信任的群体和牧者面前一起察验。",
    ),
}

# --- skill 07: gospel bridge -------------------------------------------------

SCRIPTURE_ANCHORS: dict[str, tuple[str, ...]] = {
    "achievement": ("以弗所书 2:8-9", "腓立比书 3:7-9"),
    "status": ("加拉太书 1:10", "约翰福音 12:43"),
    "control": ("马太福音 6:25-34", "彼得前书 5:6-7"),
    "scrupulosity": ("罗马书 8:1", "希伯来书 10:14", "约翰一书 1:9"),
    "self_righteousness": ("路加福音 18:9-14", "罗马书 3:23-24"),
    "victimhood": ("罗马书 12:19", "以弗所书 4:32"),
    "default": ("罗马书 5:8", "哥林多后书 5:21"),
}

PRIDE_TO_ANCHOR: dict[PrideSignal, str] = {
    PrideSignal.ACHIEVEMENT_JUSTIFICATION: "achievement",
    PrideSignal.CONTEMPT_FOR_WEAKNESS: "achievement",
    PrideSignal.STATUS_GLORY: "status",
    PrideSignal.CONTROL_SOVEREIGNTY: "control",
    PrideSignal.SPIRITUAL_PRIDE: "scrupulosity",
    PrideSignal.MORAL_SELF_RIGHTEOUSNESS: "self_righteousness",
    PrideSignal.VICTIMHOOD_INNOCENCE: "victimhood",
}
