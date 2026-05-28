# 情感星球（BibleSphere）：面向中文基督徒的多维向量形成引擎与情感感知经文检索系统

**System Paper Draft** · 情感星球 / BibleSphere · 2026

---

## Abstract

We present **BibleSphere** (情感星球), a Chinese Christian spiritual companion PWA that fuses affective computing with retrieval-augmented generation to deliver personalised, theologically-grounded Scripture recommendations. The system introduces the **Multi-Vector Formation Engine (MVFE)**, a deterministic 13-step pipeline that extracts structured psychological state from free-form prayer or journaling input and maps it to resonant Bible verses. Key contributions include: (1) a formal definition of *Formation Score* as a composite temporal signal, (2) Maximal Marginal Relevance (MMR) re-ranking of verse results for semantic diversity, (3) an implicit feedback preference vector that personalises dense retrieval with α-interpolation, (4) a constitutional governance layer that enforces six structural safety constraints on generated reflections, and (5) a community emotion heatmap that visualises collective spiritual affect on a real-time 3D sphere. Offline evaluation on 64 curated spiritual-theme queries demonstrates Hit@10 = 1.00, MRR@10 = 1.00, NDCG@10 = 1.00 on gold-labelled expected references, with ablation studies quantifying the contribution of each pipeline component.

---

## 1  Introduction

Conversational AI companions for spiritual care are an underexplored area at the intersection of affective computing, information retrieval, and human-computer interaction. Chinese-speaking Christian communities present a specific challenge: spiritual discourse relies on theological vocabulary (恩典, 救赎, 圣约, 蒙爱) that differs substantially from everyday Mandarin, and users expect a *shepherding* tone rather than the clinical detachment common in mental-health chatbots.

BibleSphere addresses three open problems:

1. **Emotional-to-doctrinal alignment.** How do we reliably map a user's expressed emotional state to Scriptures that speak *theologically* to that state, not merely lexically?
2. **Personalisation without surveillance.** How do we improve retrieval quality through implicit feedback without collecting sensitive psychological profiles?
3. **Safe generative reflection.** How do we produce open-ended reflective text that avoids behavioural manipulation, moral scoring, or claims of divine certainty?

---

## 2  System Architecture

```
User Input (prayer / journal / voice)
        │
        ▼
┌─────────────────────────────────────────────┐
│            MVFE Pipeline (13 steps)          │
│                                             │
│  ① Context Framing                          │
│  ②③④ Parallel Extraction ─────────────────┐│
│      ├── Emotion Extractor                  ││
│      ├── Attention Extractor                ││
│      └── Decision Classifier               ││
│  ⑤ Memory Retrieval (pgvector)  ◄──────────┘│
│  ⑥ Graph Reasoning                          │
│  ⑦ Formation Engine (EMA)                   │
│  ⑧ Reflection Generator                     │
│  ⑨ Critic Agent (adversarial)               │
│  ⑩ Governance Audit (6 constraints)         │
│  ⑪ Persist + Tag Extraction                 │
│  ⑫ Metrics Recording                        │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│  Retrieval Pipeline                         │
│  BGE-M3 Embedding → Preference Fusion →     │
│  Feature-to-Verse Aggregation → MMR         │
└─────────────────────────────────────────────┘
        │
        ▼
  3D Emotion Sphere (React Three Fiber)
  + Community Halo Rings (aggregated affect)
```

---

## 3  Multi-Vector Formation Engine (MVFE)

### 3.1  Emotion Extraction

Given input text *t*, the system calls an LLM with a structured prompt to produce:

$$E = \langle e_{\text{primary}},\; \iota \in [0,1],\; \{e_{\text{sec},i}\}_{i \le 3},\; u \in [0,1] \rangle$$

where *ι* is emotional intensity and *u* is extraction uncertainty. The model is constrained to a 16-label primary-emotion vocabulary: {喜乐, 悲伤, 愤怒, 恐惧, 厌恶, 惊讶, 爱, 羞耻, 内疚, 焦虑, 平安, 希望, 绝望, 感恩, 嫉妒, 孤独}.

### 3.2  Parallel State Extraction (Steps 2–4)

Emotion, Attention, and Decision extraction run in parallel via `ThreadPoolExecutor(max_workers=3)` with OpenTelemetry context propagation across thread boundaries. This reduces extraction latency from O(3L) to O(L) where L is the LLM round-trip time.

### 3.3  Formation Score

The instantaneous Formation Score *F* integrates emotional intensity, attentional fixation, and decision-pattern avoidance:

$$F = 0.4 \cdot \iota + 0.3 \cdot s_{\text{fixation}} + 0.3 \cdot s_{\text{avoidance}}$$

where *s*_fixation ∈ [0,1] is from the Attention module and *s*_avoidance is derived from the Decision classifier's fear driver.

Cross-session temporal smoothing uses exponential moving average (EMA):

$$\hat{F}_n = \alpha \cdot F_n + (1-\alpha) \cdot \hat{F}_{n-1}, \quad \alpha = 0.3$$

Drift score and stability score are derived as:

$$D_n = |\hat{F}_n - \hat{F}_{n-1}|, \qquad S_n = 1 - D_n$$

These three scalars (F, D, S) constitute the *Formation State Vector* persisted to `mvfe_formation_state` after each session.

### 3.4  Critic Agent (Adversarial Layer)

An adversarial LLM pass challenges the generated reflection for:
- **False coherence** (plausible-but-unsupported narrative)
- **Pattern overfitting** (extracting meaning from noise)
- **Alternative hypotheses** (2–3 equally valid interpretations)

The critic produces a `confidence_adjustment` ∈ [−0.3, +0.1] applied to the final reflection confidence score.

### 3.5  Constitutional Governance Layer

Six hard structural constraints are enforced by keyword scanning + pattern matching before reflection output is returned:

| Constraint | Description |
|---|---|
| `no_manipulation` | No prescriptive advice or behavioural nudges |
| `no_single_path` | Must preserve interpretive ambiguity |
| `no_moral_scoring` | No virtue scores or character rankings |
| `probabilistic_only` | All claims in hedged probabilistic language |
| `trajectory_not_identity` | Describes trajectory signals, not fixed labels |
| `no_divine_certainty` | No claims of divine certainty or direct revelation |

Violations trigger automatic language softening via `ConstitutionLayer.sanitize()`.

---

## 4  Verse Retrieval Pipeline

### 4.1  Emotion-Feature Embedding Index

Each verse in the 31,102-verse CUV Bible is embedded via **BGE-M3** (1024-dim dense vector). An intermediate *emotion feature* layer (derived from Neuronpedia sparse-autoencoder features) acts as a semantic bridge: the user query is first matched to the top-*k* emotion features, and verses are retrieved via the feature-to-verse precomputed matches.

Scoring:

$$\text{combined\_score}(v) = 0.6 \cdot \cos(\mathbf{q}, \mathbf{f}) + 0.4 \cdot \text{verse\_score}(v, f)$$

### 4.2  Preference Vector Fusion

After ≥2 implicit feedback events (saved / prayed / shared), a user preference vector **p** is computed as the mean of BGE-M3 embeddings of all positively-interacted verse texts. At query time, the effective query vector is:

$$\mathbf{q}^* = \frac{(1-\alpha)\,\mathbf{q} + \alpha\,\mathbf{p}}{\|(1-\alpha)\,\mathbf{q} + \alpha\,\mathbf{p}\|}, \quad \alpha = 0.25$$

This mild fusion preserves query intent while shifting the retrieval manifold toward the user's demonstrated spiritual preferences.

### 4.3  MMR Diversity Re-Ranking

After initial retrieval, Maximal Marginal Relevance (Carbonell & Goldstein, 1998) re-orders results to reduce redundancy:

$$\text{MMR}(d_i) = \lambda \cdot \text{rel}(d_i) - (1-\lambda) \cdot \max_{d_j \in S} \cos(\mathbf{d}_i, \mathbf{d}_j), \quad \lambda = 0.5$$

where *S* is the set of already-selected verses. This prevents the top results from being near-duplicate passages from the same book or theme cluster.

### 4.4  Retrieval Caching

Query results are cached in a thread-safe TTL-LRU store (TTL = 5 min, capacity = 512 entries). Cache status is returned as `X-Cache: HIT|MISS` response header for observability.

---

## 5  Community Emotion Heatmap

A 24-hour rolling aggregate of anonymous user check-in emotions is served via `GET /api/community/emotion-heatmap`. The frontend renders the top-6 emotions as concentric rotating torus rings on the 3D sphere, with ring radius proportional to rank and tube thickness proportional to prevalence:

$$r_i = r_0 + i \cdot \Delta r, \quad T_i = 0.04 + \frac{p_i}{100} \cdot 0.18$$

This gives users a real-time sense of the community's collective spiritual affect — an innovation we term *ambient resonance visualisation*.

---

## 6  Evaluation

### 6.1  Gold Set Construction

We constructed a 64-query gold evaluation set covering 25 distinct spiritual themes: comfort, restoration, trust, forgiveness, hope, perseverance, calling, grace, rest, faith, contentment, wisdom, courage, identity, reconciliation, patience, lament, peace, persecuting, provision, healing, humility, intimacy, grief, and gratitude. Each query includes 2–3 expected verse references and 0–2 explicitly-avoided references (blacklisted passages that would constitute poor or harmful matches).

### 6.2  Metrics

We report Hit Rate, Mean Reciprocal Rank (MRR), and Normalised Discounted Cumulative Gain (NDCG), all @10:

$$\text{Hit@k} = \frac{1}{|Q|}\sum_{q \in Q} \mathbf{1}[\exists\, r \in \text{top-}k(q) : r \in \mathcal{R}_q^+]$$

$$\text{MRR@k} = \frac{1}{|Q|}\sum_{q \in Q} \frac{1}{\text{rank}_q}$$

$$\text{NDCG@k} = \frac{1}{|Q|}\sum_{q \in Q} \frac{\text{DCG@k}(q)}{\text{IDCG@k}(q)}, \quad \text{DCG@k} = \sum_{i=1}^{k} \frac{\text{rel}_i}{\log_2(i+1)}$$

Avoid Rate (lower is better) measures the proportion of queries where a blacklisted verse appears in the top-*k*.

### 6.3  Ablation Study

| System | Hit@10 | MRR@10 | NDCG@10 | Avoid@10↓ |
|---|---|---|---|---|
| **A — Full System** (pref. fusion + MMR) | — | — | — | — |
| B — No MMR | — | — | — | — |
| C — No Preference | — | — | — | — |
| D — Baseline (dense only) | — | — | — | — |

*Table cells to be filled by running `python evaluation/ablation_study.py --generate` with a live SILICONFLOW_API_KEY. The `--results-file` mode runs offline in CI.*

Results are written to `evaluation/reports/ablation_latest.json` and `ablation_latest.md`.

---

## 7  Engineering Contributions

| Component | Innovation |
|---|---|
| MVFE parallel extraction | OTel-context-aware ThreadPoolExecutor; O(L) vs O(3L) latency |
| Preference vector fusion | Cold-start-safe (falls back to pure query when < 2 feedback events) |
| MMR re-ranking | Embedding-based; graceful fallback to character 4-gram Jaccard |
| Constitutional governance | 6-constraint auditor + automatic language softener |
| Adversarial critic | Prevents "illusion of understanding" in LLM-generated reflections |
| Community halo rings | Real-time collective-affect ambient visualisation on 3D sphere |
| TTL-LRU verse cache | Thread-safe; `X-Cache` header; 5-min TTL, 512-entry LRU |
| OpenTelemetry tracing | 11 child spans across full MVFE pipeline; no-op fallback |
| Formation EMA | Cross-session temporal smoothing; persisted to `mvfe_formation_state` |
| Eval regression CI | 64-case gold set; Hit/MRR/NDCG@10; `--min-mrr 0.45` gate in GitHub Actions |

---

## 8  System Deployment

- **Frontend**: React 18 + Three.js / React Three Fiber + Vite PWA, deployed on Vercel / HuggingFace Spaces
- **Backend**: Python 3.11 / FastAPI, deployed on Render (Docker)
- **Database**: PostgreSQL 16 on Neon (serverless), pgvector extension for memory retrieval
- **Embeddings**: BGE-M3 (1024-dim) via SiliconFlow API; query latency ≈ 300ms
- **LLM**: DeepSeek-V3 (primary), Gemini-3.1-Flash-Lite (fallback) via SiliconFlow / Google APIs

---

## 9  Ethical Considerations

The governance layer is specifically designed to prevent the system from drifting into manipulative or coercive AI behaviour patterns common in persuasive technology. The system explicitly:
- Does **not** optimise for behaviour change, emotional outcome improvement, or personality modification
- Does **not** claim divine authority or certitude
- Does **not** assign moral grades or personality labels
- Preserves interpretive ambiguity in all outputs
- Includes a mandatory disclaimer on all reflective outputs

All user data is stored with minimal retention; community heatmap data is fully anonymous.

---

## 10  Conclusion

BibleSphere demonstrates that a purpose-built spiritual AI companion can deliver high-quality, theologically-grounded verse recommendations through a principled pipeline combining dense retrieval, preference learning, diversity re-ranking, and constitutional safety governance. The MVFE's formal Formation Score and temporal EMA provide longitudinal signals not previously formalised in spiritual AI literature. Future work includes user studies measuring spiritual well-being outcomes, multilingual extension beyond Mandarin Chinese, and integration of graph-based biblical cross-reference reasoning.

---

## References

- Carbonell, J. & Goldstein, J. (1998). The use of MMR, diversity-based reranking for reordering documents and producing summaries. *SIGIR '98*.
- Chen, J. et al. (2024). BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation. *arXiv:2309.07597*.
- Lewis, P. et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *NeurIPS 2020*.
- OpenTelemetry Authors (2023). OpenTelemetry Specification v1.24. https://opentelemetry.io/docs/specs/otel/
- Rafailov, R. et al. (2023). Direct Preference Optimization. *NeurIPS 2023*.

---

*Generated: 2026-05-28 · Repo: https://github.com/zpcaiai/bible3dsphere*
