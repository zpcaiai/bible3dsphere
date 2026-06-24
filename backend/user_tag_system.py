"""
用户个人信息标签系统 (User Tag System)

从用户的情绪输入、决策选择、MVFE 分析结果中自动提取个人标签
支持标签的增删改查、权重计算、时间衰减
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
from enum import Enum
import uuid


class TagSource(Enum):
    """标签来源类型"""
    EMOTION = "emotion"           # 从情绪输入提取
    DECISION = "decision"         # 从决策类别/描述提取
    MVFE_ANALYSIS = "mvfe"        # 从 MVFE 分析结果提取
    ATTENTION = "attention"       # 从注意力焦点提取
    FORMATION = "formation"       # 从形成分析提取
    MANUAL = "manual"             # 用户手动添加
    SYSTEM = "system"             # 系统推断


class TagCategory(Enum):
    """标签分类"""
    EMOTION_TYPE = "emotion_type"     # 情绪类型标签（焦虑、喜悦等）
    LIFE_DOMAIN = "life_domain"       # 生活领域（工作、关系、健康等）
    BEHAVIOR_PATTERN = "behavior"     # 行为模式（逃避、完美主义等）
    VALUE_PRIORITY = "value"          # 价值观/优先级
    RELATIONSHIP = "relationship"     # 关系标签（家庭、朋友、同事等）
    SPIRITUAL_STATE = "spiritual"     # 灵性状态
    COGNITIVE_STYLE = "cognitive"     # 认知风格
    DECISION_STYLE = "decision"       # 决策风格


@dataclass
class UserTag:
    """用户标签数据模型"""
    id: str
    user_id: str
    tag_name: str
    tag_category: str
    source: str
    confidence: float           # 置信度 0-1
    weight: float                 # 权重，随时间衰减
    first_seen_at: str
    last_seen_at: str
    occurrence_count: int         # 出现次数
    context_snapshot: Dict[str, Any]  # 标签产生的上下文
    related_emotions: List[str]   # 相关情绪
    related_decisions: List[str]  # 相关决策ID
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TagExtractor:
    """标签提取引擎 - 从各种输入中自动提取用户标签"""
    
    # 预定义标签词典
    TAG_PATTERNS = {
        TagCategory.EMOTION_TYPE: {
            '焦虑': ['焦虑', '紧张', '担忧', '不安', 'stress', 'anxiety', 'worried'],
            '抑郁': ['抑郁', '悲伤', '沮丧', '低落', 'depressed', 'sad', 'down'],
            '愤怒': ['愤怒', '生气', '恼火', '暴躁', 'angry', 'mad', 'frustrated'],
            '恐惧': ['恐惧', '害怕', '恐慌', 'fear', 'afraid', 'scared', 'panic'],
            '喜悦': ['喜悦', '开心', '高兴', '快乐', 'joy', 'happy', 'glad'],
            '平静': ['平静', '安宁', 'peace', 'calm', 'peaceful', 'tranquil'],
            '孤独': ['孤独', '寂寞', 'lonely', 'alone', 'isolated'],
            '羞愧': ['羞愧', '羞耻', 'shame', 'ashamed', 'embarrassed'],
            '内疚': ['内疚', '自责', 'guilt', 'guilty', 'remorse'],
            '感恩': ['感恩', '感谢', '感激', 'gratitude', 'thankful', 'grateful'],
            '盼望': ['盼望', '希望', '期待', 'hope', 'hopeful', 'expecting'],
            '迷茫': ['迷茫', '困惑', 'confused', 'confusion', 'uncertain'],
        },
        TagCategory.LIFE_DOMAIN: {
            '工作': ['工作', '职场', '事业', 'job', 'work', 'career', 'profession'],
            '家庭': ['家庭', '家人', '夫妻', '亲子', 'family', 'home', 'household'],
            '关系': ['关系', '友谊', '社交', 'relationship', 'friendship', 'social'],
            '健康': ['健康', '身体', '生病', 'health', 'wellness', 'sick'],
            '财务': ['财务', '金钱', '经济', 'financial', 'money', 'economy'],
            '信仰': ['信仰', '灵修', '神', 'faith', 'spiritual', 'prayer', 'god'],
            '学习': ['学习', '考试', '学业', 'study', 'education', 'exam'],
            '娱乐': ['娱乐', '休息', '爱好', 'entertainment', 'hobby', 'recreation'],
        },
        TagCategory.BEHAVIOR_PATTERN: {
            '逃避型': ['逃避', '躲', '回避', 'avoid', 'avoidance', 'escape'],
            '完美主义': ['完美', '挑剔', '苛刻', 'perfect', 'perfectionist'],
            '拖延': ['拖延', '推迟', 'procrastinate', 'delay', 'put off'],
            '冲动': ['冲动', '鲁莽', 'impulsive', 'rash', 'impulse'],
            '控制欲': ['控制', '掌控', 'control', 'dominant', 'controlling'],
            '讨好型': ['讨好', '取悦', '迎合', 'please', 'people-pleaser'],
            '自我批评': ['自我批评', '自责', 'self-criticism', 'self-blame'],
            '过度思考': ['想太多', '反复思考', 'overthink', 'ruminate'],
            '寻求认可': ['认可', '肯定', 'approval', 'validation', 'seeking'],
            '边界模糊': ['边界', '界限', 'boundary', 'blurred', 'unclear'],
        },
        TagCategory.VALUE_PRIORITY: {
            '安全感': ['安全', '稳定', 'security', 'safety', 'stability'],
            '自由': ['自由', '自主', 'freedom', 'autonomy', 'liberty'],
            '成就': ['成就', '成功', 'achievement', 'success', 'accomplishment'],
            '被爱': ['被爱', '接纳', 'love', 'acceptance', 'belonging'],
            '尊重': ['尊重', '尊严', 'respect', 'dignity', 'honor'],
            '真实': ['真实', '诚实', 'authentic', 'truth', 'honesty'],
            '和谐': ['和谐', '和睦', 'harmony', 'peace', 'balance'],
            '成长': ['成长', '进步', 'growth', 'progress', 'development'],
        },
        TagCategory.RELATIONSHIP: {
            '亲密关系': ['亲密', '伴侣', 'spouse', 'partner', 'intimate'],
            '亲子关系': ['孩子', '父母', 'parent', 'child', 'parenting'],
            '职场关系': ['同事', '上司', '下属', 'colleague', 'boss', 'workplace'],
            '友谊': ['朋友', '友情', 'friend', 'friendship', 'buddy'],
            '原生家庭': ['原生家庭', '父母', 'family-of-origin', 'parents'],
            '权威关系': ['权威', '老师', '权威', 'authority', 'teacher', 'mentor'],
        },
        TagCategory.SPIRITUAL_STATE: {
            '灵性干枯': ['干枯', '远离神', 'dry', 'distant', 'spiritual-dryness'],
            '被弃感': ['被弃', '离弃', 'forsaken', 'abandoned', 'god-forsaken'],
            '怀疑': ['怀疑', '不信', 'doubt', 'unbelief', 'skepticism'],
            '认罪': ['认罪', '悔改', 'repent', 'confession', 'sin-acknowledgment'],
            '感恩灵修': ['感恩', '赞美', 'gratitude', 'praise', 'thanksgiving'],
            '寻求引导': ['引导', '旨意', 'guidance', 'will-of-god', 'direction'],
        },
        TagCategory.COGNITIVE_STYLE: {
            '全或无': ['全或无', '黑白', 'all-or-nothing', 'black-white', 'binary'],
            '灾难化': ['灾难', '最糟', 'catastrophize', 'worst-case', 'disaster'],
            '读心术': ['读心', '知道', 'mind-reading', 'assume', 'knowing'],
            '个人化': ['个人化', '针对我', 'personalize', 'about-me', 'targeted'],
            '过度概括': ['总是', '从不', 'overgeneralize', 'always', 'never'],
            '负面过滤': ['负面', '只看', 'negative-filter', 'focus-negative'],
        },
        TagCategory.DECISION_STYLE: {
            '快速决策': ['快速', '立即', 'quick', 'fast', 'immediate'],
            '拖延决策': ['拖延', '推迟', 'delay', 'procrastinate', 'put-off'],
            '寻求共识': ['共识', '商量', 'consensus', 'discuss', 'together'],
            '独自决定': ['独自', '自己', 'alone', 'independent', 'self'],
            '避免冲突': ['避免', '冲突', 'avoid-conflict', 'keep-peace', 'harmony'],
            '风险偏好': ['风险', '冒险', 'risk', 'adventure', 'daring'],
            '保守谨慎': ['保守', '谨慎', 'conservative', 'cautious', 'careful'],
        },
    }
    
    def __init__(self):
        self.tag_patterns = self.TAG_PATTERNS
    
    def extract_from_text(self, text: str, source: TagSource = TagSource.SYSTEM) -> List[Dict[str, Any]]:
        """从文本中提取标签"""
        if not text:
            return []
        
        text_lower = text.lower()
        extracted_tags = []
        
        for category, tags in self.tag_patterns.items():
            for tag_name, keywords in tags.items():
                # 计算匹配分数
                match_score = 0
                matched_keywords = []
                
                for keyword in keywords:
                    if keyword in text or keyword in text_lower:
                        match_score += 1
                        matched_keywords.append(keyword)
                
                if match_score > 0:
                    confidence = min(0.5 + (match_score * 0.15), 0.95)
                    extracted_tags.append({
                        'tag_name': tag_name,
                        'tag_category': category.value,
                        'source': source.value,
                        'confidence': round(confidence, 2),
                        'matched_keywords': matched_keywords,
                        'extraction_method': 'pattern_match'
                    })
        
        # 按置信度排序
        extracted_tags.sort(key=lambda x: x['confidence'], reverse=True)
        return extracted_tags
    
    def extract_from_emotion(self, emotion_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从情绪分析结果中提取标签"""
        tags = []
        
        primary_emotion = emotion_data.get('primary_emotion', '')
        secondary_emotions = emotion_data.get('secondary_emotions', [])
        intensity = emotion_data.get('intensity', 0.5)
        uncertainty = emotion_data.get('uncertainty', 0.5)
        
        # 主要情绪标签
        if primary_emotion:
            tags.append({
                'tag_name': primary_emotion,
                'tag_category': TagCategory.EMOTION_TYPE.value,
                'source': TagSource.EMOTION.value,
                'confidence': round(0.7 + (intensity * 0.25), 2),
                'context': {'intensity': intensity, 'role': 'primary'}
            })
        
        # 次要情绪标签
        for emotion in secondary_emotions[:2]:
            tags.append({
                'tag_name': emotion,
                'tag_category': TagCategory.EMOTION_TYPE.value,
                'source': TagSource.EMOTION.value,
                'confidence': round(0.5 + (intensity * 0.2), 2),
                'context': {'intensity': intensity * 0.7, 'role': 'secondary'}
            })
        
        # 不确定性标签
        if uncertainty > 0.6:
            tags.append({
                'tag_name': '迷茫',
                'tag_category': TagCategory.EMOTION_TYPE.value,
                'source': TagSource.EMOTION.value,
                'confidence': round(uncertainty, 2),
                'context': {'uncertainty': uncertainty}
            })
        
        # 从触发器文本提取
        trigger = emotion_data.get('trigger', '')
        if trigger:
            trigger_tags = self.extract_from_text(trigger, TagSource.EMOTION)
            tags.extend(trigger_tags)
        
        return tags
    
    def extract_from_decision(self, decision_data: Dict[str, Any], 
                              description: str = "") -> List[Dict[str, Any]]:
        """从决策数据中提取标签"""
        tags = []
        
        # 决策类型标签
        decision_type = decision_data.get('type')
        if decision_type == 'avoidance':
            tags.append({
                'tag_name': '逃避型',
                'tag_category': TagCategory.BEHAVIOR_PATTERN.value,
                'source': TagSource.DECISION.value,
                'confidence': 0.75,
                'context': {'decision_type': decision_type}
            })
        elif decision_type == 'approach':
            tags.append({
                'tag_name': '主动型',
                'tag_category': TagCategory.BEHAVIOR_PATTERN.value,
                'source': TagSource.DECISION.value,
                'confidence': 0.75,
                'context': {'decision_type': decision_type}
            })
        
        # 决策驱动因素标签
        drivers = decision_data.get('drivers', {})
        if drivers.get('fear', 0) > 0.6:
            tags.append({
                'tag_name': '恐惧驱动',
                'tag_category': TagCategory.BEHAVIOR_PATTERN.value,
                'source': TagSource.DECISION.value,
                'confidence': round(drivers['fear'], 2),
                'context': {'fear_driver': drivers['fear']}
            })
        if drivers.get('ego', 0) > 0.6:
            tags.append({
                'tag_name': '自我中心',
                'tag_category': TagCategory.BEHAVIOR_PATTERN.value,
                'source': TagSource.DECISION.value,
                'confidence': round(drivers['ego'], 2),
                'context': {'ego_driver': drivers['ego']}
            })
        if drivers.get('love', 0) > 0.6:
            tags.append({
                'tag_name': '爱驱动',
                'tag_category': TagCategory.VALUE_PRIORITY.value,
                'source': TagSource.DECISION.value,
                'confidence': round(drivers['love'], 2),
                'context': {'love_driver': drivers['love']}
            })
        
        # 从决策描述提取
        if description:
            desc_tags = self.extract_from_text(description, TagSource.DECISION)
            tags.extend(desc_tags)
        
        return tags
    
    def extract_from_attention(self, attention_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从注意力分析中提取标签"""
        tags = []
        
        focus = attention_data.get('focus', '')
        fixation_score = attention_data.get('fixation_score', 0)
        
        # 注意力焦点标签
        if focus:
            focus_tags = self.extract_from_text(focus, TagSource.ATTENTION)
            for tag in focus_tags:
                tag['confidence'] = round(0.5 + (fixation_score * 0.4), 2)
                tag['context'] = {'focus': focus, 'fixation': fixation_score}
            tags.extend(focus_tags)
        
        # 过度专注标签
        if fixation_score > 0.7:
            tags.append({
                'tag_name': '过度专注',
                'tag_category': TagCategory.BEHAVIOR_PATTERN.value,
                'source': TagSource.ATTENTION.value,
                'confidence': round(fixation_score, 2),
                'context': {'fixation_score': fixation_score}
            })
        
        return tags
    
    def extract_from_formation(self, formation_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从形成分析中提取标签"""
        tags = []
        
        dominant_loop = formation_data.get('dominant_loop', '')
        trajectory_direction = formation_data.get('trajectory_direction', '')
        
        # 主导回路标签
        if dominant_loop:
            loop_name = dominant_loop.replace('_', ' ')
            tags.append({
                'tag_name': loop_name,
                'tag_category': TagCategory.BEHAVIOR_PATTERN.value,
                'source': TagSource.FORMATION.value,
                'confidence': 0.75,
                'context': {'loop_type': dominant_loop}
            })
        
        # 轨迹方向标签
        if trajectory_direction:
            direction_mapping = {
                'stabilizing': '趋于稳定',
                'fragmenting': '趋于破碎',
                'improving_clarity': '清晰度提升',
                'increasing_volatility': '波动性增加',
                'cyclical': '循环反复'
            }
            direction_cn = direction_mapping.get(trajectory_direction, trajectory_direction)
            tags.append({
                'tag_name': direction_cn,
                'tag_category': TagCategory.BEHAVIOR_PATTERN.value,
                'source': TagSource.FORMATION.value,
                'confidence': 0.7,
                'context': {'trajectory': trajectory_direction}
            })
        
        return tags
    
    def extract_from_mvfe_result(self, mvfe_result: Dict[str, Any], 
                                  input_text: str = "") -> List[Dict[str, Any]]:
        """从完整的 MVFE 分析结果中提取所有标签"""
        all_tags = []
        
        # 从情绪提取
        emotion = mvfe_result.get('emotion', {})
        if emotion:
            all_tags.extend(self.extract_from_emotion(emotion))
        
        # 从决策提取
        decision = mvfe_result.get('decision', {})
        if decision:
            all_tags.extend(self.extract_from_decision(decision, input_text))
        
        # 从注意力提取
        attention = mvfe_result.get('attention', {})
        if attention:
            all_tags.extend(self.extract_from_attention(attention))
        
        # 从形成分析提取
        formation = mvfe_result.get('formation', {})
        if formation:
            all_tags.extend(self.extract_from_formation(formation))
        
        # 从原始输入文本提取
        if input_text:
            text_tags = self.extract_from_text(input_text, TagSource.MVFE_ANALYSIS)
            # 去重：如果与已有标签重复，提升置信度
            existing_names = {t['tag_name'] for t in all_tags}
            for tag in text_tags:
                if tag['tag_name'] not in existing_names:
                    all_tags.append(tag)
        
        return all_tags


class UserTagStore:
    """用户标签存储管理"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self._init_table()
    
    def _init_table(self):
        """初始化标签表"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_personal_tags (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id TEXT NOT NULL,
                        tag_name TEXT NOT NULL,
                        tag_category TEXT NOT NULL,
                        source TEXT NOT NULL,
                        confidence REAL DEFAULT 0.5,
                        weight REAL DEFAULT 1.0,
                        first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        occurrence_count INTEGER DEFAULT 1,
                        context_snapshot JSONB DEFAULT '{}',
                        related_emotions JSONB DEFAULT '[]',
                        related_decisions JSONB DEFAULT '[]',
                        is_active BOOLEAN DEFAULT TRUE,
                        UNIQUE(user_id, tag_name)
                    )
                """)
                # 创建索引
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_tags_user_id 
                    ON user_personal_tags(user_id)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_tags_category 
                    ON user_personal_tags(tag_category)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_tags_weight 
                    ON user_personal_tags(weight DESC)
                """)
                conn.commit()
                print('[tags] user_personal_tags table initialized', flush=True)
        finally:
            self.db_pool.putconn(conn)
    
    def add_or_update_tags(self, user_id: str, tags: List[Dict[str, Any]], 
                          decision_id: Optional[str] = None) -> List[str]:
        """添加或更新标签，返回标签ID列表"""
        if not tags:
            return []
        
        conn = self.db_pool.getconn()
        tag_ids = []
        
        try:
            with conn.cursor() as cur:
                for tag in tags:
                    tag_name = tag['tag_name']
                    tag_category = tag.get('tag_category', 'unknown')
                    source = tag.get('source', 'system')
                    confidence = tag.get('confidence', 0.5)
                    context = tag.get('context', {})
                    related_emotions = tag.get('related_emotions', [])
                    
                    # 检查是否已存在
                    cur.execute("""
                        SELECT id, occurrence_count, weight FROM user_personal_tags
                        WHERE user_id = %s AND tag_name = %s
                    """, (user_id, tag_name))
                    
                    result = cur.fetchone()
                    
                    if result:
                        # 更新现有标签
                        tag_id, count, old_weight = result
                        new_count = count + 1
                        # 权重递增算法：每次出现增加 0.1，上限 5.0
                        new_weight = min(old_weight + 0.1, 5.0)
                        
                        cur.execute("""
                            UPDATE user_personal_tags
                            SET last_seen_at = NOW(),
                                occurrence_count = %s,
                                weight = %s,
                                confidence = GREATEST(confidence, %s),
                                context_snapshot = context_snapshot || %s::jsonb
                            WHERE id = %s
                            RETURNING id
                        """, (new_count, new_weight, confidence, 
                              json.dumps(context), tag_id))
                        
                        # 如果有决策ID，添加到相关决策列表
                        if decision_id:
                            cur.execute("""
                                UPDATE user_personal_tags
                                SET related_decisions = (
                                    SELECT jsonb_agg(DISTINCT elem)
                                    FROM (
                                        SELECT jsonb_array_elements(related_decisions) as elem
                                        UNION SELECT %s::jsonb
                                    ) sub
                                )
                                WHERE id = %s
                            """, (json.dumps([decision_id]), tag_id))
                        
                        tag_ids.append(tag_id)
                    else:
                        # 创建新标签
                        cur.execute("""
                            INSERT INTO user_personal_tags
                            (user_id, tag_name, tag_category, source, confidence, weight,
                             context_snapshot, related_emotions)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id
                        """, (user_id, tag_name, tag_category, source, confidence, 1.0,
                              json.dumps(context), json.dumps(related_emotions)))
                        
                        tag_id = cur.fetchone()[0]
                        tag_ids.append(tag_id)
                
                conn.commit()
        finally:
            self.db_pool.putconn(conn)
        
        return tag_ids
    
    def get_user_tags(self, user_id: str, category: Optional[str] = None,
                     limit: int = 50, active_only: bool = True) -> List[Dict[str, Any]]:
        """获取用户的标签列表"""
        conn = self.db_pool.getconn()
        
        try:
            with conn.cursor() as cur:
                query = """
                    SELECT id, tag_name, tag_category, source, confidence, weight,
                           first_seen_at, last_seen_at, occurrence_count,
                           context_snapshot, related_emotions, related_decisions
                    FROM user_personal_tags
                    WHERE user_id = %s
                """
                params = [user_id]
                
                if active_only:
                    query += " AND is_active = TRUE"
                
                if category:
                    query += " AND tag_category = %s"
                    params.append(category)
                
                query += " ORDER BY weight DESC, occurrence_count DESC LIMIT %s"
                params.append(limit)
                
                cur.execute(query, params)
                
                columns = [desc[0] for desc in cur.description]
                tags = []
                for row in cur.fetchall():
                    tag_dict = dict(zip(columns, row))
                    # 解析 JSONB 字段
                    for field in ['context_snapshot', 'related_emotions', 'related_decisions']:
                        if tag_dict.get(field):
                            try:
                                tag_dict[field] = json.loads(tag_dict[field])
                            except Exception:
                                pass
                    tags.append(tag_dict)
                
                return tags
        finally:
            self.db_pool.putconn(conn)
    
    def get_tag_insights(self, user_id: str) -> Dict[str, Any]:
        """获取用户标签洞察统计"""
        conn = self.db_pool.getconn()
        
        try:
            with conn.cursor() as cur:
                # 总体统计
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_tags,
                        COUNT(DISTINCT tag_category) as categories,
                        AVG(weight) as avg_weight,
                        MAX(last_seen_at) as latest_activity
                    FROM user_personal_tags
                    WHERE user_id = %s AND is_active = TRUE
                """, (user_id,))
                
                stats = cur.fetchone()
                
                # 分类统计
                cur.execute("""
                    SELECT tag_category, COUNT(*) as count, AVG(weight) as avg_weight
                    FROM user_personal_tags
                    WHERE user_id = %s AND is_active = TRUE
                    GROUP BY tag_category
                    ORDER BY count DESC
                """, (user_id,))
                
                category_stats = [
                    {'category': row[0], 'count': row[1], 'avg_weight': round(row[2], 2)}
                    for row in cur.fetchall()
                ]
                
                # 最近活跃标签
                cur.execute("""
                    SELECT tag_name, tag_category, weight, last_seen_at
                    FROM user_personal_tags
                    WHERE user_id = %s AND is_active = TRUE
                    ORDER BY last_seen_at DESC
                    LIMIT 10
                """, (user_id,))
                
                recent_tags = [
                    {'name': row[0], 'category': row[1], 'weight': row[2], 'last_seen': row[3]}
                    for row in cur.fetchall()
                ]
                
                return {
                    'total_tags': stats[0] or 0,
                    'total_categories': stats[1] or 0,
                    'average_weight': round(stats[2] or 0, 2),
                    'latest_activity': stats[3],
                    'category_distribution': category_stats,
                    'recently_active': recent_tags
                }
        finally:
            self.db_pool.putconn(conn)
    
    def deactivate_tag(self, user_id: str, tag_name: str) -> bool:
        """停用标签（用户选择不显示）"""
        conn = self.db_pool.getconn()
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE user_personal_tags
                    SET is_active = FALSE
                    WHERE user_id = %s AND tag_name = %s
                    RETURNING id
                """, (user_id, tag_name))
                
                result = cur.fetchone()
                conn.commit()
                return result is not None
        finally:
            self.db_pool.putconn(conn)
    
    def apply_time_decay(self, decay_days: int = 30):
        """应用时间衰减（可定期调用）"""
        conn = self.db_pool.getconn()
        
        try:
            with conn.cursor() as cur:
                # 长时间未出现的标签权重衰减
                cur.execute("""
                    UPDATE user_personal_tags
                    SET weight = weight * 0.95
                    WHERE last_seen_at < NOW() - INTERVAL '%s days'
                    AND weight > 0.5
                """, (decay_days,))
                
                # 极低权重的标签标记为不活跃
                cur.execute("""
                    UPDATE user_personal_tags
                    SET is_active = FALSE
                    WHERE weight < 0.3
                """)
                
                conn.commit()
        finally:
            self.db_pool.putconn(conn)


# 全局实例
tag_extractor = TagExtractor()


def init_tag_store(db_pool):
    """初始化标签存储（在应用启动时调用）"""
    global _tag_store
    _tag_store = UserTagStore(db_pool)
    print('[tags] UserTagStore initialized', flush=True)
    return _tag_store


def get_tag_store() -> Optional[UserTagStore]:
    """获取标签存储实例"""
    global _tag_store
    return _tag_store


_tag_store: Optional[UserTagStore] = None
