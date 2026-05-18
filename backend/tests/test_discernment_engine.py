#!/usr/bin/env python3
"""
Test and demo for Discernment Engine

This script demonstrates how the discernment engine acts as a 
"spiritual mirror" rather than an oracle.
"""

from datetime import datetime
from discernment_engine import (
    DiscernmentEngine,
    DecisionEvent,
    EmotionalState,
    MotiveProfile,
    SpiritualPrinciple,
    format_result,
)


def demo_fear_based_decision():
    """Example: Career decision driven by fear."""
    print("=" * 60)
    print("示例 1: 职业决策 - 恐惧驱动")
    print("=" * 60)
    
    engine = DiscernmentEngine()
    
    decision = DecisionEvent(
        id="dec-001",
        user_id="user-001",
        title="是否应该接受新的工作机会",
        description="收到一份薪资更高但压力更大的工作邀请。目前在现岗位已3年，比较稳定。担心改变带来的不确定性，也担心错过成长机会。",
        category="career",
        urgency_level=4,
        importance_level=5,
        created_at=datetime.utcnow(),
    )
    
    emotional_state = EmotionalState(
        emotions=[
            {"type": "anxiety", "intensity": 8, "trigger": "新环境担忧"},
            {"type": "fear", "intensity": 7, "trigger": "能力怀疑"},
            {"type": "desire", "intensity": 6, "trigger": "薪资吸引"},
        ],
        stress_level=7,
        anxiety_level=8,
        fatigue_level=6,
        spiritual_dryness=4,
        emotional_stability=4,
    )
    
    motive_profile = MotiveProfile(
        fear_driven_score=0.65,
        pride_driven_score=0.20,
        love_driven_score=0.15,
        desire_driven_score=0.60,
        duty_driven_score=0.10,
        ambition_driven_score=0.55,
    )
    
    principles = [
        SpiritualPrinciple(
            id="p1",
            principle_text="不要恐惧，因为我与你同在",
            scripture_reference="以赛亚书 41:10",
            category="faith",
            relevance_score=0.85,
        ),
        SpiritualPrinciple(
            id="p2",
            principle_text="凡事察验，善美的要持守",
            scripture_reference="帖撒罗尼迦前书 5:21",
            category="discernment",
            relevance_score=0.75,
        ),
    ]
    
    result = engine.discern(decision, emotional_state, motive_profile, principles)
    output = format_result(result)
    
    print(f"\n📊 来源分类: {output['source']['primary']['name']} (置信度: {output['source']['confidence']})")
    print(f"\n💭 分析说明:\n{output['explanation']}")
    print("\n🔄 替代解释:")
    for i, alt in enumerate(output['alternatives'], 1):
        print(f"  {i}. {alt}")
    print(f"\n🙏 谦卑声明:\n{output['humility']}")
    print(f"\n⚠️  风险评估: {output['risk']['level']}")
    for factor in output['risk']['factors']:
        print(f"  • {factor['factor']}: {factor['message']}")
    print("\n📋 建议反思:")
    for ref in output['next_steps']['reflections']:
        print(f"  • {ref}")
    print("\n❓ 反思问题:")
    for q in output['next_steps']['questions']:
        print(f"  • {q}")
    print(f"\n⏰ 时间建议: {output['next_steps']['timeline']}")
    print("\n📖 相关原则:")
    for p in output['principles']:
        print(f"  • {p['text']} ({p['scripture']})")
    print(f"\n⚖️  {output['disclaimer']}")


def demo_love_based_decision():
    """Example: Relationship decision driven by love."""
    print("\n" + "=" * 60)
    print("示例 2: 关系决策 - 爱与饶恕")
    print("=" * 60)
    
    engine = DiscernmentEngine()
    
    decision = DecisionEvent(
        id="dec-002",
        user_id="user-001",
        title="是否应该饶恕曾经伤害我的朋友",
        description="一位多年的朋友在我困难时没有提供帮助，甚至说了伤人的话。现在对方表达了歉意，但我内心仍有挣扎。",
        category="relationship",
        urgency_level=2,
        importance_level=5,
        created_at=datetime.utcnow(),
    )
    
    emotional_state = EmotionalState(
        emotions=[
            {"type": "hurt", "intensity": 7, "trigger": "回忆被伤害"},
            {"type": "love", "intensity": 7, "trigger": "多年友谊"},
            {"type": "peace", "intensity": 6, "trigger": "想到饶恕"},
        ],
        stress_level=4,
        anxiety_level=3,
        fatigue_level=5,
        spiritual_dryness=3,
        emotional_stability=7,
    )
    
    motive_profile = MotiveProfile(
        fear_driven_score=0.25,
        pride_driven_score=0.15,
        love_driven_score=0.75,
        desire_driven_score=0.30,
    )
    
    principles = [
        SpiritualPrinciple(
            id="p3",
            principle_text="总要彼此包容，彼此饶恕",
            scripture_reference="歌罗西书 3:13",
            category="love",
            relevance_score=0.90,
        ),
        SpiritualPrinciple(
            id="p4",
            principle_text="看别人比自己强",
            scripture_reference="腓立比书 2:3",
            category="humility",
            relevance_score=0.70,
        ),
    ]
    
    result = engine.discern(decision, emotional_state, motive_profile, principles)
    output = format_result(result)
    
    print(f"\n📊 来源分类: {output['source']['primary']['name']} (置信度: {output['source']['confidence']})")
    print(f"\n💭 分析说明:\n{output['explanation']}")
    print(f"\n⚠️  风险评估: {output['risk']['level']}")
    print("\n📋 建议反思:")
    for ref in output['next_steps']['reflections'][:2]:
        print(f"  • {ref}")


def demo_uncertain_decision():
    """Example: Unclear decision."""
    print("\n" + "=" * 60)
    print("示例 3: 模糊不清 - 方向不明")
    print("=" * 60)
    
    engine = DiscernmentEngine()
    
    decision = DecisionEvent(
        id="dec-003",
        user_id="user-001",
        title="是否应该搬去另一个城市",
        description="有机会搬到新的城市，有一些吸引力，但也有很多不确定。没有特别强烈的感动，也没有特别的抵触。",
        category="other",
        urgency_level=3,
        importance_level=4,
        created_at=datetime.utcnow(),
    )
    
    emotional_state = EmotionalState(
        emotions=[
            {"type": "confusion", "intensity": 5, "trigger": "方向不明"},
            {"type": "curiosity", "intensity": 4, "trigger": "新机会"},
        ],
        stress_level=4,
        anxiety_level=4,
        fatigue_level=5,
        spiritual_dryness=5,
        emotional_stability=5,
    )
    
    motive_profile = MotiveProfile(
        fear_driven_score=0.30,
        pride_driven_score=0.25,
        love_driven_score=0.30,
        desire_driven_score=0.35,
    )
    
    principles = [
        SpiritualPrinciple(
            id="p5",
            principle_text="不要效法这个世界，只要心意更新而变化",
            scripture_reference="罗马书 12:2",
            category="discernment",
            relevance_score=0.60,
        ),
    ]
    
    result = engine.discern(decision, emotional_state, motive_profile, principles)
    output = format_result(result)
    
    print(f"\n📊 来源分类: {output['source']['primary']['name']}")
    print(f"\n💭 分析说明:\n{output['explanation']}")
    print(f"\n🙏 谦卑声明:\n{output['humility']}")
    print(f"\n⏰ 时间建议: {output['next_steps']['timeline']}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  辨识引擎 (Discernment Engine) 演示")
    print('  作为"灵性镜子"，而非"神谕"')
    print("=" * 60)
    
    demo_fear_based_decision()
    demo_love_based_decision()
    demo_uncertain_decision()
    
    print("\n" + "=" * 60)
    print("  演示完成")
    print("=" * 60)
