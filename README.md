---
license: apache-2.0
title: 属灵星球 - Bible 3D Sphere
sdk: docker
emoji: 📖
colorFrom: indigo
colorTo: purple
pinned: false
app_port: 7860
---

# Bible 3D Sphere

> **Architecture note (2026-06):** The React/Vite frontend has been extracted to an
> independent repository **bible3dsphereWeb** (deployed at [holiness.uk](https://holiness.uk) via Vercel).
> This repository is now a **pure Python API backend** deployed on Hugging Face Spaces at
> `stephenzao-biblesphere.hf.space`. All `/api/*` endpoints remain unchanged.

## Overview

This project builds a Chinese CUV Bible verse vector index and uses Neuronpedia emotion-feature descriptions to retrieve semantically resonant verses.

## Current Architecture

### Verse Layer

Each verse record is stored with:

- `id`
- `content`
- `context_weight`
- `book_name`
- `chapter`
- `verse`
- `formatted_text`
- `row_id`

Recommended input template for embeddings:

```text
[卷名] [章:节] [经文内容]
```

Example:

```text
马太福音 9:36 他看见许多的人，就怜悯他们；因为他们困苦流离，如同羊没有牧人一般。
```

### Embedding Model

- Provider: `SiliconFlow`
- Model: `BAAI/bge-m3`
- Dense vector retrieval is enabled now
- Default retrieval uses normalized dense vectors and inner-product search

### Technical Highlights

- Total CUV verse count: about `31,102`
- Dense vector dimension: typically `1024`
- Dense vector memory footprint:

```text
31102 × 1024 × 4 bytes ≈ 127 MB
```

- This is small enough to keep in memory comfortably
- All verse vectors are `L2` normalized
- Query vectors are also `L2` normalized
- With `FAISS IndexFlatIP`, the inner product equals cosine similarity

Scoring formula:

```text
Score = v_CUV_verse · v_emotion
```

This is the core of emotion resonance retrieval.

### Files

- `vectorize_bible_siliconflow.py`
  - Builds verse embeddings from CSV
  - Writes FAISS index, metadata, and config

- `search_bible_index.py`
  - Loads index and metadata
  - Embeds a query with SiliconFlow
  - Runs dense retrieval
  - Supports hybrid lexical boosting

- `fetch_neuronpedia_emotion_features.py`
  - Fetches Neuronpedia emotion-related features
  - Can optionally embed feature descriptions with SiliconFlow

## Hybrid Retrieval Direction

`BGE-M3` also supports multi-granularity retrieval ideas beyond dense vectors.

For theology-heavy Chinese retrieval, some terms may deserve explicit lexical emphasis, for example:

- `中保`
- `挽回祭`
- `赎罪`
- `恩慈`
- `怜悯`
- `救赎`

The current implementation adds a lightweight lexical score on top of dense retrieval so that exact theological terms can be boosted without replacing the dense semantic pipeline.

## Expected CSV Columns

Input CSV should contain at least:

- `book_name`
- `chapter`
- `verse`
- `content`

Optional:

- `book_abbrev`

## Retrieval Flow

1. Build verse vectors from the Chinese CUV corpus
2. Normalize vectors with `L2`
3. Encode emotion query text or Neuronpedia-derived seed text
4. Search by inner product
5. Optionally add lexical weighting for theology-sensitive terms
6. Return ranked verses with scores and metadata

---

## 3D Emotion Sphere — Full Stack Run Guide

### Prerequisites

```bash
python3.11 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt

# Optional: install rerank dependencies only when you plan to enable rerank
./.venv/bin/python -m pip install -r requirements-rerank.txt

# Frontend lives in the separate bible3dsphereWeb repo
# (no Node deps needed in this backend repo)
```

### Python setup commands

```bash
python3.11 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
```

If you only want the Python environment refreshed inside an existing `.venv`:

```bash
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
```

Optional rerank dependencies:

```bash
./.venv/bin/python -m pip install -r requirements-rerank.txt
```

### Copy-paste run commands

```bash
# 1) Build single-language CUV vectors
./.venv/bin/python vectorize_bible_siliconflow.py

# 2) Upload single-language vectors to Qdrant
./.venv/bin/python qdrant_bible_index.py

# 3) Build bilingual CUV/ESV vectors
./.venv/bin/python vectorize_bible_bilingual.py

# 4) Upload bilingual vectors to Qdrant
./.venv/bin/python qdrant_bible_bilingual.py

# 5) Fetch Neuronpedia emotion features
./.venv/bin/python fetch_neuronpedia_emotion_features.py

# 6) Build feature-to-verse matches
./.venv/bin/python batch_search_emotion_exemplars.py

# 7) Analyze match outputs
./.venv/bin/python analyze_emotion_matches.py

# 8) Build 3D emotion sphere layout
./.venv/bin/python build_emotion_sphere_layout.py

# 9) Start local API server
./.venv/bin/python emotion_api_server.py

# 10) Run CLI query
./.venv/bin/python query_emotion_verses.py "我感到极度孤独" --guidance
```

### Unified retrieval pipeline

The individual scripts above can also be run through one workflow CLI:

```bash
# Build local CUV FAISS artifacts
./.venv/bin/python scripts/retrieval_pipeline.py build-cuv

# Build sphere layout from emotion features
./.venv/bin/python scripts/retrieval_pipeline.py build-layout

# Run retrieval quality evaluation
./.venv/bin/python scripts/retrieval_pipeline.py evaluate

# Write a reproducibility manifest for generated artifacts
./.venv/bin/python scripts/retrieval_pipeline.py manifest

# Optional: sync latest eval/manifest JSON into PostgreSQL/Neon
./.venv/bin/python scripts/sync_observability_to_db.py
```

For a local rebuild pass:

```bash
./.venv/bin/python scripts/retrieval_pipeline.py full-local
```

Remote Qdrant and provider-backed steps require the relevant environment
variables from `.env.example`, including `SILICONFLOW_API_KEY`,
`QDRANT_URL`, and `QDRANT_API_KEY`.

### Step 1 — Generate 3D layout

```bash
./.venv/bin/python build_emotion_sphere_layout.py
# Outputs: emotion_sphere_layout.json, emotion_sphere_layout.csv
```

### Step 2 — Start the Python API server

```bash
./.venv/bin/python emotion_api_server.py
# Listens on http://127.0.0.1:8787
```

API endpoints:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/layout` | 3D emotion point coordinates + metadata |
| GET | `/api/history` | Past query history |
| GET | `/api/feature?key=layer:id` | Feature detail + verse matches |
| POST | `/api/query` | Natural language → emotions → verses |
| POST | `/api/guidance` | Natural language → psychological assessment + spiritual guidance |

`/api/query` body:
```json
{
  "query": "我感到很孤独和迷失",
  "topFeatures": 5,
  "topVerses": 5,
  "languageFilter": "both",
  "includeGuidance": true,
  "enableRerank": false,
  "rerankCandidates": 20,
  "rerankWeight": 0.7
}
```

`/api/guidance` body:
```json
{ "query": "我感到很孤独和迷失" }
```

Guidance response shape:
```json
{
  "core_emotions": ["孤独", "迷失"],
  "psychological_assessment": "...",
  "coping_suggestions": ["建议1", "建议2"],
  "spiritual_guidance": "...",
  "core_need": "..."
}
```

### Step 3 — Start the frontend (independent repo)

The frontend is now developed and deployed from the **bible3dsphereWeb** repository.
Clone that repo and follow its README to run the Vite dev server locally.
Point `VITE_API_BASE` at `http://localhost:7860` for local backend development.

### Docker deployment (pure API)

The frontend has moved to **bible3dsphereWeb** (Vercel, holiness.uk). This repo
deploys as a single-stage Python API image on Hugging Face Spaces.

Current deploy layout:

- `backend/main.py`: FastAPI entry point
- `backend/vector_search.py`: backend query exports
- `Dockerfile`: single-stage Python 3.11 image (no Node build step)

Build and run locally with Docker:

```bash
docker build -t bible-emotion-sphere .
docker run --rm -p 7860:7860 bible-emotion-sphere
```

Then verify the API root:

```bash
curl http://127.0.0.1:7860/
# {"service":"biblesphere-api","status":"ok","frontend":"https://holiness.uk","docs":"/docs"}
```

Notes:

- The frontend (holiness.uk) calls this API at `https://stephenzao-biblesphere.hf.space/api/*`
- rerank is disabled by default and does not require model downloads in the deploy image
- **Persistent statistics** — survives service restarts via local JSON or HF Hub API storage

### CLI usage

```bash
# Basic query
./.venv/bin/python query_emotion_verses.py "我感到极度孤独"

# With psychological + spiritual guidance
./.venv/bin/python query_emotion_verses.py "我感到极度孤独" --guidance

# With optional rerank enabled (requires requirements-rerank.txt to be installed)
./.venv/bin/python query_emotion_verses.py "我感到极度孤独" --enable-rerank --rerank-candidates 20 --rerank-weight 0.7

# Export to JSON/Markdown/CSV
./.venv/bin/python query_emotion_verses.py "恩典与饶恕" --guidance --export --slug my-query
```

#### Visit Statistics

The application tracks page views and unique visitors with persistent storage:

**Features:**

- **Total Page Views** — incremented on every page load
- **Unique Visitors** — tracked via browser-generated visitor ID (stored in localStorage)
- **Persistent Storage** — survives service restarts via:
  - Local JSON file (`visit_stats.json`)
  - Hugging Face Hub API (when `HF_TOKEN` is configured for HF Spaces)

**API Endpoints:**

```bash
# Get current statistics
GET /api/stats
# Returns: { "page_views": 1234, "unique_visitors": 567 }

# Track a visit (called automatically on page load)
POST /api/stats/track
Body: { "visitorId": "uuid-generated-by-frontend" }
# Returns: { "page_views": 1235, "unique_visitors": 567 }
```

**UI Display:**

- Topbar compact view: 👁 1234
- Hero section: inline stats badges
- Stats card: animated gradient cards with live pulse indicator

**HF Spaces Persistence:**
Set the `HF_TOKEN` environment variable in your Space settings. When present, statistics will be backed up to the Hugging Face Hub via API calls, ensuring data survives container rebuilds.

### Frontend architecture

The React/Vite PWA frontend is maintained in the separate **bible3dsphereWeb** repository
and deployed to [holiness.uk](https://holiness.uk) via Vercel. It communicates with this API
at `https://stephenzao-biblesphere.hf.space/api/*`.
