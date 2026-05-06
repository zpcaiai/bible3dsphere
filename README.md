---
license: apache-2.0
title: 情感星球 - Bible 3D Sphere
sdk: docker
emoji: 📖
colorFrom: indigo
colorTo: purple
---

# Bible 3D Sphere

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

# Node deps (inside emotion-sphere-ui/)
(cd emotion-sphere-ui && npm install)
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

### Step 3 — Start the Vite frontend

```bash
(cd emotion-sphere-ui && npm run dev)
# Opens http://localhost:5173
```

### PWA mobile preview

```bash
(cd emotion-sphere-ui && npm run build)
(cd emotion-sphere-ui && npm run preview:mobile)
```

Then open `http://<your-computer-lan-ip>:4173` on your phone.

Important notes:

- Local network preview works for layout and interaction testing.
- Real PWA installation on mobile usually requires an `HTTPS` origin.
- For iPhone or Android install testing, deploy the frontend behind `HTTPS` or use a trusted tunnel / reverse proxy.
- Once served over `HTTPS`, the app can be added to the home screen and opened in standalone mode like a native app.

### Unified Docker deployment

The project now includes a deployable `backend/` FastAPI app plus a root-level `Dockerfile`.

Current deploy layout:

- `emotion-sphere-ui/`: React + Vite frontend
- `backend/main.py`: FastAPI entry point
- `backend/vector_search.py`: backend query exports
- `Dockerfile`: multi-stage build for frontend + backend

Build and run locally with Docker:

```bash
docker build -t bible-emotion-sphere .
docker run --rm -p 7860:7860 bible-emotion-sphere
```

Then open:

```text
http://127.0.0.1:7860
```

In this mode:

- React static assets are served by FastAPI
- frontend requests use same-origin `/api`
- the whole app can be deployed behind one HTTPS domain for PWA installation
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

### Visit Statistics

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

```
emotion-sphere-ui/src/
├── main.jsx                 # React entry
├── App.jsx                  # Shell: query form, guidance panel, verse sidebar
├── EmotionSphereScene.jsx   # R3F: InstancedMesh, KMeans clusters, 3D popover, LOD
├── store.js                 # Zustand global state
├── api.js                   # fetch wrappers for all API endpoints
└── styles.css               # Glassmorphism dark UI
```

Key frontend features:
- **InstancedMesh** — all 171 points rendered as a single draw call
- **KMeans clustering** (k=7) run client-side on UMAP coordinates; each cluster gets a distinct color
- **LOD**: far → cluster labels, mid → partial labels, near → all point labels
- **3D glassmorphism verse popover** — appears anchored to the selected point in world space
- **Psychological + spiritual guidance panel** — right sidebar, rendered after query
- **Bloom post-processing** via `@react-three/postprocessing`
- **Visit Statistics** — persistent page views & unique visitor tracking with beautiful animated UI cards
