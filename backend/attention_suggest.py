"""Deterministic suggestions for Attention Stewardship.

No model calls live here. The copy stays gentle because this module can touch
sensitive struggles such as anxiety, comparison, lust, and fatigue.
"""
from __future__ import annotations

from typing import Iterable

ATTENTION_PULLS = {
    "anxiety",
    "comparison",
    "lust",
    "greed",
    "boredom",
    "escape",
    "control",
    "fomo",
    "fatigue",
    "algorithm",
    "consumerism",
    "people_pleasing",
    "vanity",
    "curiosity_without_purpose",
}

SCRIPTURES = {
    "proverbs_4_23": {
        "reference": "箴言 4:23",
        "text": "你要保守你心，胜过保守一切，因为一生的果效是由心发出。",
    },
    "psalm_46_10": {
        "reference": "诗篇 46:10",
        "text": "你们要休息，要知道我是神。",
    },
    "philippians_4_6_7": {
        "reference": "腓立比书 4:6-7",
        "text": "应当一无挂虑，只要凡事借着祷告、祈求和感谢，将你们所要的告诉神。",
    },
    "galatians_1_10": {
        "reference": "加拉太书 1:10",
        "text": "我现在是要得人的心呢，还是要得神的心呢？",
    },
    "psalm_139_14": {
        "reference": "诗篇 139:14",
        "text": "我要称谢你，因我受造奇妙可畏。",
    },
    "1_corinthians_6_12": {
        "reference": "哥林多前书 6:12",
        "text": "凡事我都可行，但无论哪一件，我总不受它的辖制。",
    },
    "matthew_6_21": {
        "reference": "马太福音 6:21",
        "text": "因为你的财宝在哪里，你的心也在那里。",
    },
    "matthew_11_28": {
        "reference": "马太福音 11:28",
        "text": "凡劳苦担重担的人可以到我这里来，我就使你们得安息。",
    },
}


def clean_pulls(values: Iterable[str] | None) -> list[str]:
    if not values:
        return []
    return [str(v) for v in values if str(v) in ATTENTION_PULLS]


def build_attention_suggestion(
    primary_offering: str = "",
    main_risk: str = "",
    risk_pulls: Iterable[str] | None = None,
) -> dict:
    pulls = set(clean_pulls(risk_pulls))
    offering = (primary_offering or "今天你所托付的一件事").strip()
    risk = (main_risk or "无目的的信息牵引").strip()

    suggestion = {
        "suggestedDigitalBoundary": "今天只在固定时间处理资讯和消息，其他时间先回到眼前被托付的事。",
        "suggestedTimeBoundary": "今天信息摄入控制在 30 分钟以内。",
        "suggestedSpiritualBoundary": "想分心时，先停下 30 秒，把心带回神面前。",
        "suggestedScripture": SCRIPTURES["proverbs_4_23"],
        "suggestedPrayer": (
            f"主啊，求你帮助我今天把最好的注意力献给「{offering}」。"
            f"当我的心被「{risk}」牵引时，求你温柔提醒我归回你面前，"
            "不是被焦虑或欲望驱赶，而是忠心回应你今天的托付。"
        ),
    }

    if "fomo" in pulls:
        suggestion.update({
            "suggestedDigitalBoundary": "上午不看相关资讯，下午固定 30 分钟集中处理。",
            "suggestedTimeBoundary": "今天信息摄入控制在 30 分钟以内。",
            "suggestedSpiritualBoundary": "想刷资讯前，先写下「我真正害怕错过什么？」并交托给神。",
            "suggestedScripture": SCRIPTURES["psalm_46_10"],
            "suggestedPrayer": "主啊，求你救我脱离被时代焦虑驱赶的心，帮助我今天不是追逐更多信息，而是忠心完成你托付的一件事。",
        })
    elif "anxiety" in pulls:
        suggestion.update({
            "suggestedDigitalBoundary": "把焦虑来源的信息查看限制在一个固定窗口，不让它全天占据你的心。",
            "suggestedTimeBoundary": "今天焦虑来源的信息查看不超过 30 分钟。",
            "suggestedSpiritualBoundary": "焦虑升起时，先做 1 分钟交托祷告，再决定是否需要行动。",
            "suggestedScripture": SCRIPTURES["philippians_4_6_7"],
            "suggestedPrayer": "主啊，我把今天真实的挂虑带到你面前。求你赐我够用的平安，使我先信靠你，再处理眼前的责任。",
        })
    elif "comparison" in pulls:
        suggestion.update({
            "suggestedDigitalBoundary": "今天减少社交媒体浏览，避免让别人的片段定义你的价值。",
            "suggestedTimeBoundary": "今天社交媒体集中在一个短窗口内处理。",
            "suggestedSpiritualBoundary": "想比较时，先写下 3 个感恩，并提醒自己是在神面前被认识的人。",
            "suggestedScripture": SCRIPTURES["galatians_1_10"],
            "suggestedPrayer": "主啊，求你把我的心从比较中带出来，使我不靠人的评价确认自己，而是在你里面安稳地忠心。",
        })
    elif "lust" in pulls:
        suggestion.update({
            "suggestedDigitalBoundary": "避免独处疲惫时打开高风险 App 或网站，必要时把设备放到公共空间。",
            "suggestedTimeBoundary": "今晚给屏幕使用设定清楚结束时间，保留安静和休息。",
            "suggestedSpiritualBoundary": "受试探时立即离开场景，并联系可信任的守望伙伴；这不是羞辱，而是选择自由。",
            "suggestedScripture": SCRIPTURES["1_corinthians_6_12"],
            "suggestedPrayer": "主啊，求你在试探临近时给我一条出路，也给我诚实求助的勇气。愿我的身体、眼目和心都重新归给你。",
        })
    elif "greed" in pulls or "consumerism" in pulls:
        suggestion.update({
            "suggestedDigitalBoundary": "购物或投资冲动前等待 24 小时，不在情绪高点做决定。",
            "suggestedTimeBoundary": "今天不反复查看购物、投资或价格信息。",
            "suggestedSpiritualBoundary": "写下真实需要，并做知足祷告，把安全感交还给神。",
            "suggestedScripture": SCRIPTURES["matthew_6_21"],
            "suggestedPrayer": "主啊，求你帮助我分辨真实需要和被牵引的欲望，使我的财宝和心都重新归向你。",
        })
    elif "fatigue" in pulls:
        suggestion.update({
            "suggestedDigitalBoundary": "晚上 9 点后减少屏幕使用，把身体带入安息。",
            "suggestedTimeBoundary": "今天保留一段不被消息打断的恢复时间。",
            "suggestedSpiritualBoundary": "承认自己有限，选择安息，把未完成的事交托给神。",
            "suggestedScripture": SCRIPTURES["matthew_11_28"],
            "suggestedPrayer": "主啊，我承认自己不是机器。求你教我在有限中信靠，在安息中重新领受力量。",
        })

    return suggestion
