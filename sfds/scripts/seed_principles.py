#!/usr/bin/env python3
"""
Seed Script — Spiritual Principles (pgvector)

Generates embeddings for all principles and stores in Postgres.
Run: python scripts/seed_principles.py
"""

import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SEED_PRINCIPLES = [
    {
        "principle_en": "Humility opens the path to truth that pride keeps closed.",
        "principle_zh": "谦卑打开骄傲关闭的真理之路。",
        "category":     "humility",
        "source_ref":   "Proverbs 11:2",
    },
    {
        "principle_en": "Fear-driven control produces the exhaustion it was meant to prevent.",
        "principle_zh": "恐惧驱动的控制产生了它本想预防的精疲力竭。",
        "category":     "fear",
        "source_ref":   "Matthew 6:27",
    },
    {
        "principle_en": "Rest is not weakness — it interrupts the burnout loop.",
        "principle_zh": "休息不是软弱——它打断了精疲力竭的循环。",
        "category":     "resilience",
        "source_ref":   "Psalm 23:2",
    },
    {
        "principle_en": "Truth-facing reduces the structural power of shame.",
        "principle_zh": "面对真相降低了羞耻的结构性力量。",
        "category":     "truth",
        "source_ref":   "John 8:32",
    },
    {
        "principle_en": "The pattern that repeats most insistently may point to the deepest unmet need.",
        "principle_zh": "重复最执着的模式可能指向最深的未满足需求。",
        "category":     "formation",
        "source_ref":   "",
    },
    {
        "principle_en": "Compassion for others grows most easily from honest self-awareness.",
        "principle_zh": "对他人的同情最容易从诚实的自我意识中生长。",
        "category":     "compassion",
        "source_ref":   "",
    },
    {
        "principle_en": "Comparison is a loop, not a destination — it rarely arrives where it promises.",
        "principle_zh": "比较是一个循环，不是目的地——它很少到达它承诺的地方。",
        "category":     "pride",
        "source_ref":   "Galatians 6:4",
    },
    {
        "principle_en": "Resilience is built in small recoveries, not large dramatic victories.",
        "principle_zh": "韧性在小的恢复中建立，而不是在大的戏剧性胜利中。",
        "category":     "resilience",
        "source_ref":   "",
    },
]


async def seed() -> None:
    from dotenv import load_dotenv
    load_dotenv()

    import asyncpg
    from openai import AsyncOpenAI

    pg_url = os.getenv("POSTGRES_URL", "")
    api_key = os.getenv("OPENAI_API_KEY", "")

    pool   = await asyncpg.create_pool(pg_url)
    client = AsyncOpenAI(api_key=api_key)

    print(f"Seeding {len(SEED_PRINCIPLES)} principles...")

    for p in SEED_PRINCIPLES:
        resp = await client.embeddings.create(
            input=p["principle_en"],
            model="text-embedding-3-small",
        )
        embedding = resp.data[0].embedding

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO spiritual_principles
                    (principle_en, principle_zh, category, source_ref, embedding)
                VALUES ($1, $2, $3, $4, $5::vector)
                ON CONFLICT DO NOTHING
                """,
                p["principle_en"], p["principle_zh"],
                p["category"], p["source_ref"], embedding,
            )
        print(f"  ✓ {p['category']}: {p['principle_en'][:50]}...")

    await pool.close()
    print(f"\n✓ Seeded {len(SEED_PRINCIPLES)} principles.")


if __name__ == "__main__":
    asyncio.run(seed())
