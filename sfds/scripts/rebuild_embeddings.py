#!/usr/bin/env python3
"""
Rebuild Script — Regenerate all pgvector embeddings.

Use when: switching embedding model or re-indexing after data changes.
Run: python scripts/rebuild_embeddings.py
"""

import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def rebuild() -> None:
    from dotenv import load_dotenv
    load_dotenv()

    import asyncpg
    from openai import AsyncOpenAI

    pg_url  = os.getenv("POSTGRES_URL", "")
    api_key = os.getenv("OPENAI_API_KEY", "")
    model   = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    pool   = await asyncpg.create_pool(pg_url)
    client = AsyncOpenAI(api_key=api_key)

    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, principle_en FROM spiritual_principles")

    print(f"Rebuilding embeddings for {len(rows)} principles using {model}...")

    for row in rows:
        resp = await client.embeddings.create(input=row["principle_en"], model=model)
        embedding = resp.data[0].embedding

        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE spiritual_principles SET embedding = $1::vector WHERE id = $2",
                embedding, row["id"],
            )
        print(f"  ✓ {row['id']}")

    await pool.close()
    print(f"\n✓ Rebuilt {len(rows)} embeddings.")


if __name__ == "__main__":
    asyncio.run(rebuild())
