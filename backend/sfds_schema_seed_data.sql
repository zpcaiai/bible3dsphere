-- ============================================================================
-- SFDS Schema (Part 3/3) - Seed Data & Example Dataset
-- ============================================================================

-- ============================================================================
-- 30 SPIRITUAL PRINCIPLES SEED DATA
-- ============================================================================

INSERT INTO sfds_spiritual_principles (
    principle_text, principle_summary, scripture_reference, scripture_text,
    category, subcategory, applicable_contexts, applicable_emotions, search_keywords
) VALUES 
-- 1-5: Discernment Principles
('凡事察验，善美的要持守', '测试一切事物，持守善良美好的', '帖撒罗尼迦前书 5:21', '但要凡事察验，善美的要持守', 'discernment', 'testing', ARRAY['career', 'relationship', 'ministry'], ARRAY['confusion', 'doubt', 'uncertainty'], ARRAY['察验', '测试', '分辨', '验证', '确认']),
('你要保守你心，胜过保守一切，因为一生的果效是由心发出', '用心守护内心，因为生命走向由心决定', '箴言 4:23', '你要保守你心，胜过保守一切，因为一生的果效是由心发出', 'discernment', 'heart_guarding', ARRAY['temptation', 'relationship', 'calling'], ARRAY['desire', 'lust', 'temptation'], ARRAY['保守', '守护', '内心', '心', '动机']),
('不要效法这个世界，只要心意更新而变化，叫你们察验何为神的善良、纯全、可喜悦的旨意', '不被世界同化，而是心意更新，明白神纯全的旨意', '罗马书 12:2', '不要效法这个世界，只要心意更新而变化', 'discernment', 'worldly_values', ARRAY['career', 'calling', 'ministry'], ARRAY['confusion', 'pressure'], ARRAY['效法', '世界', '更新', '变化', '旨意']),
('凭果子认出他们来', '通过结果和行为来识别真伪', '马太福音 7:20', '所以，凭著他们的果子就可以认出他们来', 'discernment', 'fruit', ARRAY['relationship', 'ministry', 'calling'], ARRAY['doubt', 'suspicion', 'confusion'], ARRAY['果子', '结果', '行为', '识别', '判断']),
('有两三个人奉我的名聚会，那里就有我在他们中间', '在群体智慧和属灵遮盖中确认决定', '马太福音 18:20', '因为无论在哪里，有两三个人奉我的名聚会，那里就有我在他们中间', 'discernment', 'confirmation', ARRAY['career', 'relationship', 'ministry', 'calling'], ARRAY['uncertainty', 'doubt', 'loneliness'], ARRAY['印证', '遮盖', '群体', '智慧', '同行']),

-- 6-10: Truth & Integrity Principles
('真理必叫你们得以自由', '真理带来真正的自由，而非舒适或方便', '约翰福音 8:32', '你们必晓得真理，真理必叫你们得以自由', 'truth', 'freedom', ARRAY['relationship', 'temptation', 'calling'], ARRAY['shame', 'guilt', 'fear', 'desire'], ARRAY['真理', '自由', '释放', '诚实', '真相']),
('是，就说是；不是，就说不是', '诚实面对自己和他人，不模棱两可', '马太福音 5:37', '你们的话，是，就说是；不是，就说不是', 'truth', 'honesty', ARRAY['relationship', 'career', 'other'], ARRAY['confusion', 'doubt', 'pressure'], ARRAY['诚实', '坦诚', '直接', '清楚', '是']),
('你们要弃绝谎言，各人与邻舍说实话', '在关系和沟通中持守真实', '以弗所书 4:25', '所以你们要弃绝谎言，各人与邻舍说实话', 'truth', 'integrity', ARRAY['relationship', 'ministry'], ARRAY['guilt', 'shame', 'fear'], ARRAY['诚实', '真实', '诚信', '谎言', '说话']),
('不可偷盗，不可欺骗，也不可彼此说谎', '以诚实作为行事为人的基础', '利未记 19:11', '不可偷盗，不可欺骗，也不可彼此说谎', 'truth', 'honesty', ARRAY['career', 'financial', 'relationship'], ARRAY['desire', 'greed', 'temptation'], ARRAY['诚实', '偷盗', '欺骗', '撒谎', '真实']),
('惟独我的仆人迦勒，因他另有一个心志，专一跟从我', '专一跟从，不被外界声音左右', '民数记 14:24', '惟独我的仆人迦勒，因他另有一个心志，专一跟从我', 'truth', 'commitment', ARRAY['calling', 'ministry', 'temptation'], ARRAY['doubt', 'confusion', 'pressure'], ARRAY['专一', '心志', '跟从', '忠诚', '专心']),

-- 11-15: Love & Others Principles
('我若能说万人的方言，并天使的话语，却没有爱，我就成了鸣的锣、响的钹一般', '爱比恩赐、成功更重要', '哥林多前书 13:1-3', '我若能说万人的方言，并天使的话语，却没有爱，我就成了鸣的锣、响的钹一般', 'love', 'priority', ARRAY['career', 'ministry', 'relationship', 'calling'], ARRAY['ambition', 'pride', 'desire'], ARRAY['爱', '优先', '恩赐', '成功', '重要']),
('爱人如己', '将他人益处置于自己之上', '马太福音 22:39', '要爱人如己', 'love', 'others_first', ARRAY['relationship', 'career', 'ministry'], ARRAY['anger', 'resentment', 'frustration'], ARRAY['爱', '他人', '自己', '如己', '对待']),
('不求自己的益处，反倒求别人的益处', '舍己爱人，放下自我中心', '腓立比书 2:4', '各人不要单顾自己的事，也要顾别人的事', 'love', 'selflessness', ARRAY['relationship', 'family', 'ministry'], ARRAY['pride', 'selfishness', 'resentment'], ARRAY['益处', '别人', '自己', '顾念', '舍己']),
('倘若这人与那人有嫌隙，总要彼此包容，彼此饶恕', '以饶恕和包容维系关系', '歌罗西书 3:13', '倘若这人与那人有嫌隙，总要彼此包容，彼此饶恕', 'love', 'forgiveness', ARRAY['relationship', 'family'], ARRAY['anger', 'bitterness', 'resentment', 'hurt'], ARRAY['饶恕', '包容', '原谅', '嫌隙', '和好']),
('你们愿意人怎样待你们，你们也要怎样待人', '以对待他人的方式定义自己的品格', '路加福音 6:31', '你们愿意人怎样待你们，你们也要怎样待人', 'love', 'golden_rule', ARRAY['relationship', 'career', 'ministry'], ARRAY['resentment', 'anger', 'frustration'], ARRAY['待人', '对待', '愿意', '黄金法则', '人际']),

-- 16-20: Humility & Character Principles
('凡自高的，必降为卑；自卑的，必升为高', '神阻挡骄傲的人，赐恩给谦卑的人', '马太福音 23:12', '凡自高的，必降为卑；自卑的，必升为高', 'humility', 'pride_warning', ARRAY['career', 'ministry', 'relationship'], ARRAY['pride', 'arrogance', 'ambition'], ARRAY['谦卑', '骄傲', '自高', '自卑', '升高']),
('看别人比自己强', '以谦卑的态度看待他人', '腓立比书 2:3', '只要存心谦卑，各人看别人比自己强', 'humility', 'others_value', ARRAY['relationship', 'ministry', 'career'], ARRAY['pride', 'contempt', 'judgment'], ARRAY['别人', '自己', '强', '谦卑', '存心']),
('虚心的人有福了，因为天国是他们的', '承认自己的贫乏和需要', '马太福音 5:3', '虚心的人有福了，因为天国是他们的', 'humility', 'poverty_of_spirit', ARRAY['calling', 'temptation', 'ministry'], ARRAY['pride', 'arrogance'], ARRAY['虚心', '有福', '天国', '贫穷', '灵']),
('你们年幼的，也要顺服年长的。就是你们众人也都要以谦卑束腰', '以顺服和谦卑为品格装束', '彼得前书 5:5', '就是你们众人也都要以谦卑束腰', 'humility', 'submission', ARRAY['ministry', 'career', 'relationship'], ARRAY['pride', 'rebellion', 'defiance'], ARRAY['顺服', '谦卑', '束腰', '年幼', '年长']),
('神赐恩给谦卑的人', '谦卑是领受恩典的管道', '雅各书 4:6', '但他赐更多的恩典，所以经上说：神阻挡骄傲的人，赐恩给谦卑的人', 'humility', 'grace_reception', ARRAY['calling', 'ministry', 'temptation'], ARRAY['pride', 'self_reliance'], ARRAY['恩典', '谦卑', '阻挡', '骄傲', '赐给']),

-- 21-25: Fear & Courage Principles
('不要恐惧，因为我与你同在；不要惊惶，因为我是你的神', '神的同在胜过一切恐惧', '以赛亚书 41:10', '你不要害怕，因为我与你同在；不要惊惶，因为我是你的神', 'faith', 'courage', ARRAY['career', 'relationship', 'health', 'financial'], ARRAY['fear', 'anxiety', 'panic', 'dread'], ARRAY['恐惧', '害怕', '同在', '神', '同在']),
('我留下平安给你们，我将我的平安赐给你们。我所赐的，不像世人所赐的', '基督赐的平安超越环境', '约翰福音 14:27', '我留下平安给你们，我将我的平安赐给你们', 'peace', 'christian_peace', ARRAY['career', 'relationship', 'health', 'ministry'], ARRAY['anxiety', 'stress', 'worry', 'fear'], ARRAY['平安', '留下', '赐给', '世人', '不一样']),
('应当一无挂虑，只要凡事借着祷告、祈求和感谢，将你们所要的告诉神', '以祷告代替忧虑', '腓立比书 4:6', '应当一无挂虑，只要凡事借着祷告、祈求和感谢', 'peace', 'prayer_over_anxiety', ARRAY['career', 'financial', 'health', 'relationship'], ARRAY['anxiety', 'worry', 'stress', 'fear'], ARRAY['挂虑', '祷告', '祈求', '感谢', '忧虑']),
('神所赐出人意外的平安，必在基督耶稣里保守你们的心怀意念', '神的平安保守心思意念', '腓立比书 4:7', '神所赐出人意外的平安，必在基督耶稣里保守你们的心怀意念', 'peace', 'guard_mind', ARRAY['career', 'relationship', 'temptation'], ARRAY['anxiety', 'confusion', 'doubt'], ARRAY['平安', '意外', '保守', '心怀', '意念']),
('你们这小群，不要惧怕，因为你们的父乐意把国赐给你们', '天父乐意赐福，不要惧怕匮乏', '路加福音 12:32', '你们这小群，不要惧怕，因为你们的父乐意把国赐给你们', 'faith', 'provision', ARRAY['financial', 'career', 'calling'], ARRAY['fear', 'anxiety', 'worry', 'doubt'], ARRAY['小群', '不要', '惧怕', '父', '乐意']),

-- 26-30: Patience & Resistance Principles
('患难生忍耐，忍耐生老练，老练生盼望', '忍耐是品格成长的路径', '罗马书 5:3-4', '患难生忍耐，忍耐生老练，老练生盼望', 'patience', 'growth_process', ARRAY['career', 'relationship', 'calling', 'ministry'], ARRAY['frustration', 'impatience', 'discouragement'], ARRAY['患难', '忍耐', '老练', '盼望', '品格']),
('你们所受的试探，无非是人所能受的。神是信实的，必不叫你们受试探过于所能受的', '神知道我们的限度，试探有出路', '哥林多前书 10:13', '你们所受的试探，无非是人所能受的', 'resistance', 'temptation_escape', ARRAY['temptation', 'relationship', 'ministry'], ARRAY['temptation', 'desire', 'lust', 'pressure'], ARRAY['试探', '受试探', '信实', '过于', '所能']),
('务要谨守，警醒。因为你们的仇敌魔鬼，如同吼叫的狮子，遍地游行，寻找可吞吃的人', '保持警醒，抵挡试探', '彼得前书 5:8', '务要谨守，警醒。因为你们的仇敌魔鬼，如同吼叫的狮子', 'resistance', 'vigilance', ARRAY['temptation', 'relationship', 'career'], ARRAY['temptation', 'desire', 'lust', 'greed'], ARRAY['谨守', '警醒', '仇敌', '魔鬼', '狮子']),
('你们要顺服神。务要抵挡魔鬼，魔鬼就必离开你们逃跑了', '主动抵挡，魔鬼必逃跑', '雅各书 4:7', '你们要顺服神。务要抵挡魔鬼，魔鬼就必离开你们逃跑了', 'resistance', 'active_resistance', ARRAY['temptation', 'relationship', 'ministry'], ARRAY['temptation', 'desire', 'fear', 'pressure'], ARRAY['抵挡', '魔鬼', '逃跑', '离开', '顺服']),
('不可为恶所胜，反要以善胜恶', '以善胜恶，不以恶报恶', '罗马书 12:21', '你不可为恶所胜，反要以善胜恶', 'character', 'overcome_evil', ARRAY['relationship', 'career', 'ministry'], ARRAY['anger', 'resentment', 'hurt', 'revenge'], ARRAY['善', '恶', '胜', '以善', '恶胜']);

-- ============================================================================
-- EXAMPLE USER DATASET
-- ============================================================================

-- Create example user
INSERT INTO sfds_users (
    id, email, nickname, spiritual_maturity_score, personality_type, 
    decision_style, created_at, last_login_at
) VALUES (
    '11111111-1111-1111-1111-111111111111',
    'demo@sfds.example',
    'Demo User',
    6,
    'ambivert',
    'analytical',
    NOW() - INTERVAL '90 days',
    NOW() - INTERVAL '2 days'
) ON CONFLICT (email) DO NOTHING;

-- ============================================================================
-- EXAMPLE DECISIONS WITH FULL ANALYSIS
-- ============================================================================

-- Example Decision 1: Career decision with fear-driven motivation
INSERT INTO sfds_decision_events (
    id, user_id, title, description, category, urgency_level, importance_level,
    reversibility, deadline_date, processing_status, outcome_status, 
    final_decision, created_at, updated_at, analyzed_at, decided_at
) VALUES (
    'd1111111-1111-1111-1111-111111111111',
    '11111111-1111-1111-1111-111111111111',
    '是否应该接受新的工作机会',
    '收到一份薪资更高但压力更大的工作邀请。目前在现岗位已3年，工作稳定但发展空间有限。担心改变带来的不确定性，也害怕无法胜任新职责，但同时又渴望更高的收入和职业成长。',
    'career',
    4, 5,
    false,
    NOW() - INTERVAL '45 days',
    'reviewed',
    'implemented',
    '决定接受新工作，但设定了3个月的试用期评估',
    NOW() - INTERVAL '60 days',
    NOW() - INTERVAL '30 days',
    NOW() - INTERVAL '58 days',
    NOW() - INTERVAL '45 days'
) ON CONFLICT DO NOTHING;

-- State snapshot for decision 1
INSERT INTO sfds_state_snapshots (
    decision_id, stress_level, anxiety_level, fatigue_level, 
    spiritual_dryness_level, emotional_stability_level,
    overall_wellbeing_score, decision_readiness_score,
    sleep_quality, physical_health, relational_harmony, financial_pressure,
    user_notes, recorded_at
) VALUES (
    'd1111111-1111-1111-1111-111111111111',
    7, 8, 6, 4, 4,
    5, 5,
    5, 6, 7, 8,
    '最近因为工作的事情睡得不太好，总是反复思考。',
    NOW() - INTERVAL '60 days'
);

-- Emotions for decision 1
INSERT INTO sfds_emotion_logs (decision_id, emotion_type, intensity, trigger_description, trigger_category, recorded_at, duration_minutes) VALUES
('d1111111-1111-1111-1111-111111111111', 'anxiety', 8, '想到要面对新环境和不确定的未来', 'circumstantial', NOW() - INTERVAL '60 days', 120),
('d1111111-1111-1111-1111-111111111111', 'fear', 7, '担心无法胜任新职责，害怕失败', 'internal', NOW() - INTERVAL '60 days', 90),
('d1111111-1111-1111-1111-111111111111', 'desire', 6, '对更高薪资和职业发展的渴望', 'internal', NOW() - INTERVAL '59 days', 60),
('d1111111-1111-1111-1111-111111111111', 'confusion', 5, '不确定哪个选择更符合神的旨意', 'spiritual', NOW() - INTERVAL '58 days', 180);

-- Motive analysis for decision 1
INSERT INTO sfds_motive_analyses (
    decision_id, fear_driven_score, pride_driven_score, love_driven_score, 
    desire_driven_score, duty_driven_score, ambition_driven_score,
    primary_motive, secondary_motive, confidence_score, 
    analysis_algorithm, sentiment_score, created_at
) VALUES (
    'd1111111-1111-1111-1111-111111111111',
    0.65, 0.20, 0.15, 0.60, 0.10, 0.55,
    'fear', 'desire',
    0.72,
    'v1.0-rule-based',
    -0.15,
    NOW() - INTERVAL '58 days'
);

-- Discernment result for decision 1
INSERT INTO sfds_discernment_results (
    decision_id, primary_source, secondary_source, source_confidence,
    biblical_alignment_score, long_term_fruit_prediction, explanation_text,
    alternative_explanations, has_spiritual_warning, has_psychological_warning,
    warning_details, created_at
) VALUES (
    'd1111111-1111-1111-1111-111111111111',
    'fear_response',
    'worldly_value',
    0.68,
    0.42,
    -0.25,
    '决策明显受恐惧和物质欲望驱动。焦虑水平高（8/10），主要担忧是「无法胜任」和「失败」，这是典型的恐惧反应。同时，薪资驱动的动机表明世俗价值观的影响。虽然并非错误的决定，但动机需要审视。',
    ARRAY['这可能是神预备的成长机会，恐惧可能正是需要跨越的', '物质增益本身不一定是错的，但要检视是否信靠神的供应'],
    true, true,
    '{"spiritual": "高焦虑下的决策容易受恐惧支配，缺乏属灵确据", "psychological": "疲劳和精神压力可能影响判断力"}'::jsonb,
    NOW() - INTERVAL '58 days'
);

-- Guidance for decision 1
INSERT INTO sfds_guidance_outputs (
    decision_id, structured_advice, summary_advice, primary_risks, risk_severity,
    alternative_interpretations, blind_spots, recommended_actions, immediate_actions,
    long_term_actions, priority_level, suggested_timeline, follow_up_questions,
    guidance_version, used_llm, created_at
) VALUES (
    'd1111111-1111-1111-1111-111111111111',
    '基于当前状态分析，您的决策明显受恐惧（0.65）和欲望（0.60）驱动。虽然这是正常的职业选择，但在高焦虑状态下（8/10）做出的决定可能不够全面。建议：1）先处理焦虑，2）与属灵同伴讨论，3）考虑试用期条款。',
    '在高焦虑中做重大职业变动需谨慎',
    ARRAY['恐惧驱动的决定往往过度保守或过度激进', '疲劳状态下判断力下降', '可能忽视其他更重要因素（如家庭、健康）'],
    'medium',
    ARRAY['这可能是神的带领，恐惧只是需要跨越的信心考验', '新环境反而带来突破和成长'],
    ARRAY['可能低估了适应能力', '可能高估了薪资的重要性', '可能忽略了祷告中的平安信号'],
    ARRAY['与2-3位属灵同伴深入讨论', '向新雇主争取3-6个月试用期', '制定压力管理和界限设定计划', '保持与现雇主良好关系'],
    ARRAY['暂停48小时，记录祷告感受', '列出最坏的后果，评估是否可承受', '背诵以赛亚书41:10对抗恐惧'],
    ARRAY['3个月后评估身心状态', '建立新的支持系统和界限', '持续灵修保持与神的连结'],
    'high',
    '建议等待24-48小时再做最终决定',
    ARRAY['如果完全不怕，你会怎么选择？', '这个新工作如何帮助你服事他人？', '5年后回头看，这个决定会如何？'],
    'v1.0',
    false,
    NOW() - INTERVAL '58 days'
);

-- Decision-Principles links for decision 1
INSERT INTO sfds_decision_principles (decision_id, principle_id, relationship_type, relevance_score, application_notes) 
SELECT 'd1111111-1111-1111-1111-111111111111', id, 'supporting', 0.85, '需要察验这个工作机会是否来自神'
FROM sfds_spiritual_principles WHERE principle_text LIKE '%察验%';

INSERT INTO sfds_decision_principles (decision_id, principle_id, relationship_type, relevance_score, application_notes)
SELECT 'd1111111-1111-1111-1111-111111111111', id, 'supporting', 0.80, '恐惧是主要动机，需要面对'
FROM sfds_spiritual_principles WHERE principle_text LIKE '%恐惧%';

-- Review for decision 1
INSERT INTO sfds_decision_reviews (
    decision_id, user_id, outcome_description, outcome_category,
    peace_level, regret_level, satisfaction_level,
    followed_guidance, guidance_accuracy, character_growth,
    spiritual_lessons, what_went_well, what_could_improve,
    review_date, days_since_decision, would_decide_differently
) VALUES (
    'd1111111-1111-1111-1111-111111111111',
    '11111111-1111-1111-1111-111111111111',
    '已经在新岗位工作3个月。适应比预期快，薪资确实有帮助，但压力也很大。庆幸当时要了试用期条款。',
    'mixed',
    2, 3, 7,
    true, 7,
    '学会了在高压力下依靠神，也学会了设界限。',
    '恐惧虽然是动机，但神的恩典够我用。重要的是在高压力中保持与神的关系。',
    ARRAY['适应了比预期快', '试用期条款给了安全感', '薪资确实缓解了财务压力'],
    ARRAY['应该更早开始新工作的灵修习惯', '应该更主动建立同事关系'],
    NOW() - INTERVAL '15 days',
    45,
    false
);

-- ============================================================================
-- Example Decision 2: Relationship decision with love-driven motivation
-- ============================================================================

INSERT INTO sfds_decision_events (
    id, user_id, title, description, category, urgency_level, importance_level,
    reversibility, processing_status, outcome_status, 
    created_at, analyzed_at
) VALUES (
    'd2222222-2222-2222-2222-222222222222',
    '11111111-1111-1111-1111-111111111111',
    '是否应该饶恕曾经伤害我的朋友',
    '一位多年的朋友在我困难时没有提供帮助，甚至说了一些伤人的话。现在对方表达了歉意，但我内心仍有挣扎，不确定是否应该完全饶恕并恢复关系。这让我很困扰，因为不想带着苦毒，但又害怕再次受伤。',
    'relationship',
    2, 5,
    true,
    'guided',
    'ongoing',
    NOW() - INTERVAL '14 days',
    NOW() - INTERVAL '12 days'
) ON CONFLICT DO NOTHING;

-- State snapshot for decision 2
INSERT INTO sfds_state_snapshots (
    decision_id, stress_level, anxiety_level, fatigue_level, 
    spiritual_dryness_level, emotional_stability_level,
    overall_wellbeing_score, decision_readiness_score,
    user_notes, recorded_at
) VALUES (
    'd2222222-2222-2222-2222-222222222222',
    4, 3, 5, 3, 7,
    6, 8,
    '最近灵修比较稳定，感觉比较平静。',
    NOW() - INTERVAL '14 days'
);

-- Emotions for decision 2
INSERT INTO sfds_emotion_logs (decision_id, emotion_type, intensity, trigger_description, trigger_category, recorded_at) VALUES
('d2222222-2222-2222-2222-222222222222', 'hurt', 7, '回忆被背叛的经历', 'relational', NOW() - INTERVAL '14 days'),
('d2222222-2222-2222-2222-222222222222', 'confusion', 5, '不确定饶恕的界限和程度', 'spiritual', NOW() - INTERVAL '14 days'),
('d2222222-2222-2222-2222-222222222222', 'peace', 6, '想到饶恕带来的释放', 'spiritual', NOW() - INTERVAL '13 days'),
('d2222222-2222-2222-2222-222222222222', 'fear', 4, '担心再次受伤或被利用', 'relational', NOW() - INTERVAL '13 days'),
('d2222222-2222-2222-2222-222222222222', 'love', 7, '想到多年的友谊和对方的改变', 'relational', NOW() - INTERVAL '12 days');

-- Motive analysis for decision 2
INSERT INTO sfds_motive_analyses (
    decision_id, fear_driven_score, pride_driven_score, love_driven_score, 
    desire_driven_score, primary_motive, secondary_motive, confidence_score,
    created_at
) VALUES (
    'd2222222-2222-2222-2222-222222222222',
    0.25, 0.15, 0.75, 0.30,
    'love', 'duty',
    0.78,
    NOW() - INTERVAL '12 days'
);

-- Discernment result for decision 2
INSERT INTO sfds_discernment_results (
    decision_id, primary_source, secondary_source, source_confidence,
    biblical_alignment_score, long_term_fruit_prediction, explanation_text,
    has_spiritual_warning, created_at
) VALUES (
    'd2222222-2222-2222-2222-222222222222',
    'holy_spirit',
    'conscience',
    0.75,
    0.85,
    0.70,
    '决策由爱和渴望和解驱动，与圣灵的果子一致。情绪稳定性高（7/10），灵性状况良好，支持这个方向。虽然不是无条件的信任恢复，但饶恕的方向是正确的。',
    false,
    NOW() - INTERVAL '12 days'
);

-- ============================================================================
-- Example Spiritual Metrics (Time-series data)
-- ============================================================================

INSERT INTO sfds_spiritual_metrics (
    user_id, metric_date, metric_period,
    prayer_consistency, scripture_engagement, community_connection,
    humility_score, patience_score, love_score, peace_score,
    emotional_regulation, stress_resilience, spiritual_vitality,
    overall_spiritual_health, daily_reflection, recorded_via
) VALUES
('11111111-1111-1111-1111-111111111111', CURRENT_DATE - 7, 'daily', 7, 6, 5, 6, 5, 7, 6, 6, 5, 6, 6, '这周比较忙碌，但尽量保持了灵修', 'manual'),
('11111111-1111-1111-1111-111111111111', CURRENT_DATE - 6, 'daily', 8, 7, 6, 7, 6, 8, 7, 7, 6, 7, 7, '今天小组聚会很受鼓励', 'checkin'),
('11111111-1111-1111-1111-111111111111', CURRENT_DATE - 5, 'daily', 6, 8, 5, 6, 5, 7, 6, 6, 5, 6, 6, '读了诗篇，很得安慰', 'journal'),
('11111111-1111-1111-1111-111111111111', CURRENT_DATE - 4, 'daily', 7, 7, 7, 7, 6, 8, 7, 7, 6, 7, 7, '帮助了一位弟兄，心里很有喜乐', 'manual'),
('11111111-1111-1111-1111-111111111111', CURRENT_DATE - 3, 'daily', 5, 6, 8, 6, 5, 7, 6, 5, 5, 6, 5, '工作压力比较大，灵修时间被压缩', 'checkin'),
('11111111-1111-1111-1111-111111111111', CURRENT_DATE - 2, 'daily', 6, 7, 6, 7, 6, 8, 7, 6, 6, 7, 6, '做了新的职业决定，有些紧张但平安', 'decision_review'),
('11111111-1111-1111-1111-111111111111', CURRENT_DATE - 1, 'daily', 8, 8, 7, 7, 7, 8, 8, 7, 7, 7, 7, '周末休息得很好，灵修时间充足', 'manual');

-- ============================================================================
-- Example User Pattern
-- ============================================================================

INSERT INTO sfds_user_patterns (
    user_id, pattern_type, pattern_name, pattern_description,
    first_observed_at, last_observed_at, occurrence_count, confidence_score,
    related_decision_ids, pattern_data, is_active, is_addressed
) VALUES (
    '11111111-1111-1111-1111-111111111111',
    'decision_bias',
    '高压下倾向于风险规避',
    '在压力水平≥7时，用户倾向于选择更安全但可能限制成长的选项。这种恐惧驱动的模式在过去3个职业相关决策中重复出现。',
    NOW() - INTERVAL '90 days',
    NOW() - INTERVAL '60 days',
    3,
    0.72,
    ARRAY['d1111111-1111-1111-1111-111111111111'::UUID],
    '{"trigger": "high_stress", "threshold": 7, "pattern": "risk_aversion", "category": "career"}'::jsonb,
    true,
    false
);

-- Update principle reference counts
UPDATE sfds_spiritual_principles p
SET reference_count = subquery.count,
    last_referenced_at = NOW()
FROM (
    SELECT principle_id, COUNT(*) as count
    FROM sfds_decision_principles
    GROUP BY principle_id
) subquery
WHERE p.id = subquery.principle_id;
