"""
SFDS Vector Search Module
Handles embedding generation and similarity search using pgvector and OpenAI
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import asyncpg
from openai import AsyncOpenAI

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
EMBEDDING_TIMEOUT = 20.0      # per-request timeout (s)
EMBEDDING_MAX_RETRIES = 2     # small retry so a single hiccup doesn't abort the search


@dataclass
class PrincipleResult:
    """Result from vector search for spiritual principles"""
    id: str
    principle_text: str
    scripture_reference: str
    category: str
    relevance_score: float
    similarity: float


async def generate_embedding(text: str) -> List[float]:
    """Generate embedding for text using OpenAI API.

    Adds a per-request timeout and a small retry with backoff so a single
    transient hiccup (timeout / 429 / 5xx) does not abort the whole search.
    """
    last_exc: Optional[Exception] = None
    for attempt in range(EMBEDDING_MAX_RETRIES + 1):
        try:
            response = await openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text,
                dimensions=EMBEDDING_DIMENSIONS,
                timeout=EMBEDDING_TIMEOUT,
            )
            return response.data[0].embedding
        except Exception as e:
            last_exc = e
            print(f"[VectorSearch] embedding attempt {attempt + 1}/"
                  f"{EMBEDDING_MAX_RETRIES + 1} failed: {e}")
            if attempt < EMBEDDING_MAX_RETRIES:
                await asyncio.sleep(0.5 * (attempt + 1))
    print(f"[VectorSearch] Error generating embedding after retries: {last_exc}")
    raise last_exc


async def search_spiritual_principles(
    pool: asyncpg.Pool,
    query_text: str,
    top_k: int = 5,
    category_filter: Optional[str] = None
) -> List[PrincipleResult]:
    """
    Search spiritual principles using vector similarity
    
    Args:
        pool: Database connection pool
        query_text: Text to search for
        top_k: Number of results to return
        category_filter: Optional category to filter by
        
    Returns:
        List of PrincipleResult objects sorted by relevance
    """
    # Generate embedding for query
    query_embedding = await generate_embedding(query_text)
    
    async with pool.acquire() as conn:
        # Build query with optional category filter
        if category_filter:
            rows = await conn.fetch(
                """
                SELECT 
                    id,
                    principle_text,
                    scripture_reference,
                    category,
                    1 - (embedding <=> $1::vector) as similarity
                FROM sfds_spiritual_principles
                WHERE is_active = true AND category = $3
                ORDER BY embedding <=> $1::vector
                LIMIT $2
                """,
                query_embedding,
                top_k,
                category_filter
            )
        else:
            rows = await conn.fetch(
                """
                SELECT 
                    id,
                    principle_text,
                    scripture_reference,
                    category,
                    1 - (embedding <=> $1::vector) as similarity
                FROM sfds_spiritual_principles
                WHERE is_active = true
                ORDER BY embedding <=> $1::vector
                LIMIT $2
                """,
                query_embedding,
                top_k
            )
        
        results = []
        for row in rows:
            results.append(PrincipleResult(
                id=str(row['id']),
                principle_text=row['principle_text'],
                scripture_reference=row['scripture_reference'] or "",
                category=row['category'],
                relevance_score=row['similarity'],
                similarity=row['similarity']
            ))
        
        return results


async def search_principles_for_decision(
    pool: asyncpg.Pool,
    decision_title: str,
    decision_description: str,
    emotions: List[Dict[str, Any]],
    top_k: int = 5
) -> List[PrincipleResult]:
    """
    Search principles specifically tailored for a decision context
    
    Combines decision text with emotional context for better relevance
    """
    # Build rich context query
    emotion_text = " ".join([
        f"{e.get('emotion_type', '')} ({e.get('intensity', 5)}/10 intensity)"
        for e in emotions
    ])
    
    query = f"""
    Decision: {decision_title}
    Context: {decision_description}
    Emotional state: {emotion_text}
    
    What spiritual principles should guide this decision?
    """
    
    return await search_spiritual_principles(pool, query, top_k)


async def embed_and_store_principle(
    pool: asyncpg.Pool,
    principle_text: str,
    scripture_reference: str,
    category: str,
    principle_id: Optional[str] = None
) -> str:
    """
    Generate embedding and store/update a spiritual principle
    
    Returns:
        The principle ID
    """
    # Generate embedding
    embedding = await generate_embedding(principle_text)
    
    async with pool.acquire() as conn:
        if principle_id:
            # Update existing
            await conn.execute(
                """
                UPDATE sfds_spiritual_principles
                SET 
                    principle_text = $1,
                    scripture_reference = $2,
                    category = $3,
                    embedding = $4::vector,
                    updated_at = NOW()
                WHERE id = $5
                """,
                principle_text,
                scripture_reference,
                category,
                embedding,
                principle_id
            )
            return principle_id
        else:
            # Insert new
            new_id = await conn.fetchval(
                """
                INSERT INTO sfds_spiritual_principles
                (principle_text, scripture_reference, category, embedding, is_active)
                VALUES ($1, $2, $3, $4::vector, true)
                RETURNING id
                """,
                principle_text,
                scripture_reference,
                category,
                embedding
            )
            return str(new_id)


async def seed_spiritual_principles(pool: asyncpg.Pool):
    """Seed database with initial spiritual principles and embeddings"""
    
    principles = [
        # Discernment
        {"text": "凡事察验，善美的要持守", "scripture": "帖撒罗尼迦前书 5:21", "category": "discernment"},
        {"text": "不要轻信所有的灵，总要试验那些灵是否出于神", "scripture": "约翰一书 4:1", "category": "discernment"},
        {"text": "凭果子认出他们来", "scripture": "马太福音 7:20", "category": "discernment"},
        
        # Heart Guarding
        {"text": "你要保守你心，胜过保守一切，因为一生的果效是由心发出", "scripture": "箴言 4:23", "category": "heart"},
        {"text": "人心比万物都诡诈，坏到极处，谁能识透呢", "scripture": "耶利米书 17:9", "category": "heart"},
        
        # Fear and Anxiety
        {"text": "不要恐惧，因为我与你同在；不要惊惶，因为我是你的神", "scripture": "以赛亚书 41:10", "category": "fear"},
        {"text": "应当一无挂虑，只要凡事借着祷告、祈求和感谢，将你们所要的告诉神", "scripture": "腓立比书 4:6", "category": "anxiety"},
        {"text": "你们这小群，不要惧怕，因为你们的父乐意把国赐给你们", "scripture": "路加福音 12:32", "category": "fear"},
        {"text": "应当悔改归正，使你们的罪得以涂抹", "scripture": "使徒行传 3:19", "category": "peace"},
        
        # Humility
        {"text": "看别人比自己强", "scripture": "腓立比书 2:3", "category": "humility"},
        {"text": "谦卑的人有福了，因为他们必承受地土", "scripture": "马太福音 5:5", "category": "humility"},
        {"text": "谦卑在智慧以先", "scripture": "箴言 11:2", "category": "humility"},
        {"text": "凡自高的必降为卑，自卑的必升为高", "scripture": "路加福音 14:11", "category": "humility"},
        
        # Love
        {"text": "爱是恒久忍耐，又有恩慈；爱是不嫉妒，爱是不自夸", "scripture": "哥林多前书 13:4", "category": "love"},
        {"text": "爱比成功更高", "scripture": "哥林多前书 13:1-3", "category": "love"},
        {"text": "我们爱，因为神先爱我们", "scripture": "约翰一书 4:19", "category": "love"},
        
        # Truth
        {"text": "真理必叫你们得以自由", "scripture": "约翰福音 8:32", "category": "truth"},
        {"text": "真理比舒适更重要", "scripture": "约翰福音 8:32", "category": "truth"},
        {"text": "喜爱真理，不喜爱不义", "scripture": "帖撒罗尼迦后书 2:10", "category": "truth"},
        
        # Rest
        {"text": "安息是属灵操练", "scripture": "马可福音 6:31", "category": "rest"},
        {"text": "你们得救在乎归回安息，得力在乎平静安稳", "scripture": "以赛亚书 30:15", "category": "rest"},
        {"text": "不可为明天忧虑，因为明天自有明天的忧虑", "scripture": "马太福音 6:34", "category": "rest"},
        
        # Patience
        {"text": "患难生忍耐，忍耐生老练", "scripture": "罗马书 5:3-4", "category": "patience"},
        {"text": "慢慢动怒的人，大有聪明", "scripture": "箴言 14:29", "category": "patience"},
        
        # Obedience
        {"text": "顺服神，不顺从人", "scripture": "使徒行传 5:29", "category": "obedience"},
        {"text": "有了我的命令又遵守的，这人就是爱我的", "scripture": "约翰福音 14:21", "category": "obedience"},
        
        # Sacrifice
        {"text": "愿意受苦而不愿犯罪", "scripture": "希伯来书 11:25", "category": "sacrifice"},
        {"text": "若有人要跟从我，就当舍己，天天背起他的十字架", "scripture": "路加福音 9:23", "category": "sacrifice"},
        
        # Victory
        {"text": "不可为恶所胜，反要以善胜恶", "scripture": "罗马书 12:21", "category": "victory"},
        {"text": "靠着爱我们的主，在这一切事上我们已经得胜有余了", "scripture": "罗马书 8:37", "category": "victory"},
        
        # Peace
        {"text": "我留下平安给你们，我将我的平安赐给你们", "scripture": "约翰福音 14:27", "category": "peace"},
        {"text": "在压力中保持平安", "scripture": "约翰福音 14:27", "category": "peace"},
        
        # Faith
        {"text": "信就是所望之事的实底，是未见之事的确据", "scripture": "希伯来书 11:1", "category": "faith"},
        {"text": "义人必因信得生", "scripture": "哈巴谷书 2:4", "category": "faith"},
        
        # Wisdom
        {"text": "你们中间若有缺少智慧的，应当求那厚赐与众人、也不斥责人的神", "scripture": "雅各书 1:5", "category": "wisdom"},
        {"text": "敬畏耶和华是知识的开端", "scripture": "箴言 1:7", "category": "wisdom"},
    ]
    
    print(f"[VectorSearch] Seeding {len(principles)} spiritual principles...")
    
    for i, p in enumerate(principles):
        try:
            await embed_and_store_principle(
                pool,
                p["text"],
                p["scripture"],
                p["category"]
            )
            print(f"[VectorSearch] Seeded principle {i+1}/{len(principles)}: {p['text'][:30]}...")
        except Exception as e:
            print(f"[VectorSearch] Error seeding principle {i+1}: {e}")
    
    print("[VectorSearch] Seeding complete!")


# Legacy exports for backward compatibility
from query_emotion_verses import assess_psychological_state, query_emotion_verses

__all__ = [
    'generate_embedding',
    'search_spiritual_principles',
    'search_principles_for_decision',
    'embed_and_store_principle',
    'seed_spiritual_principles',
    'PrincipleResult',
    'assess_psychological_state',
    'query_emotion_verses',
]
