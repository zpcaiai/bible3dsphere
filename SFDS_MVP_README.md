# SFDS-MVP: Spiritual Formation & Discernment System

A production-ready MVP of a reflective decision support system that helps users in spiritual decision-making through structured self-examination, emotional awareness, motive analysis, and alignment with spiritual principles.

## System Overview

The SFDS (Spiritual Formation & Discernment System) acts as a "spiritual mirror" rather than an oracle. It provides reflective, non-authoritative guidance that emphasizes:
- **Humility** - Acknowledging uncertainty in discernment
- **User Autonomy** - The user retains full decision-making authority
- **Non-judgmental Tone** - Avoiding moralistic or guilt-inducing language
- **Probabilistic Analysis** - Presenting possibilities, not certainties

## Architecture

### Backend (FastAPI + PostgreSQL + pgvector)

```
backend/
├── decision_support.py       # Main API router and endpoints
├── discernment_engine.py     # Core discernment logic module
├── vector_search.py          # OpenAI embeddings + pgvector search
├── sfds_schema_core.sql      # Database schema
└── main.py                   # FastAPI app integration point
```

### Frontend (Next.js + TailwindCSS)

```
sfds-frontend/
├── app/
│   ├── components/           # Reusable UI components
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   └── Slider.tsx
│   ├── decision/
│   │   ├── new/page.tsx      # Decision input form
│   │   └── [id]/analysis/page.tsx  # Analysis results
│   ├── journal/page.tsx      # Reflection journal
│   ├── page.tsx              # Dashboard
│   ├── layout.tsx            # Root layout
│   └── globals.css           # Tailwind + custom styles
├── lib/
│   ├── types.ts              # TypeScript definitions
│   └── api.ts                # API client
├── package.json
├── tailwind.config.js
└── next.config.js
```

## Core Components

### 1. DiscernmentEngine Module
The heart of the system that implements reflective, probabilistic motive classification:

**Key Features:**
- Source type classification (Holy Spirit, fear, pride, trauma, worldly, etc.)
- Confidence levels (low/medium/high)
- Risk assessment
- Alternative explanations
- Humility statements
- Next step recommendations

**Source Types:**
- `holy_spirit` - Alignment with spiritual values
- `conscience` - Inner moral compass
- `fear` - Fear-driven responses
- `pride` - Pride/ego-driven motives
- `trauma` - Past wound influence
- `worldly` - Worldly value systems
- `flesh` - Base desires
- `uncertain` - Unable to classify

### 2. Vector Search with OpenAI + pgvector
Uses OpenAI's `text-embedding-3-small` model (1536 dimensions) for semantic similarity search:

```python
# Generate embeddings
embedding = await generate_embedding("decision context text")

# Search principles with cosine similarity
results = await search_spiritual_principles(pool, query_text, top_k=5)
```

### 3. Database Schema
PostgreSQL with pgvector extension for vector storage:

**Key Tables:**
- `sfds_users` - User profiles
- `sfds_decision_events` - Decision records
- `sfds_state_snapshots` - Emotional/mental state at decision time
- `sfds_emotion_logs` - Detailed emotion tracking
- `sfds_spiritual_principles` - Vector-embedded principles
- `sfds_discernment_results` - Analysis outputs
- `sfds_guidance_outputs` - Structured guidance
- `sfds_decision_reviews` - Outcome reflections

### 4. API Endpoints

```
POST /api/sfds/decisions          # Create new decision
GET  /api/sfds/decisions          # List user decisions
GET  /api/sfds/decisions/{id}     # Get decision details
POST /api/sfds/quick-discern      # Quick analysis (no DB)
POST /api/sfds/reflective-discern # Deep discernment
GET  /api/sfds/principles         # List principles
POST /api/sfds/principles/search  # Vector search
POST /api/sfds/decisions/{id}/review  # Submit review
```

## Frontend Pages

### Dashboard (`/`)
- Current emotional state overview
- Recent decisions list
- Spiritual trend chart placeholder
- Daily reflection prompt

### Decision Input (`/decision/new`)
4-step form:
1. Describe situation (title, category, urgency/importance)
2. Select emotions (max 3)
3. State snapshot (5 sliders)
4. Review and submit

### Analysis Results (`/decision/[id]/analysis`)
Tabbed interface:
- **Overview** - Summary of discernment result
- **Motives** - Breakdown of motive scores
- **Principles** - Relevant spiritual principles
- **Guidance** - Recommended actions and risks

### Reflection Journal (`/journal`)
- List of past entries
- New entry creation with prompts
- Emotion tagging

## Design Principles

### Visual Design
- **Calm Color Palette:**
  - Primary: `#5a9a8f` (teal)
  - Secondary: `#8fa872` (sage)
  - Accent: `#c4a77d` (warm)
  - Background: `#faf9f7` (warm white)
  
- **Typography:** System fonts for familiarity
- **Spacing:** Generous whitespace for breathing room
- **Animations:** Subtle fade-ins, gentle hover states

### UX Principles
1. **No Perfectionism** - Emphasize progress over perfection
2. **Gentle Warnings** - Never guilt-inducing
3. **Reflection Prompts** - Guide self-examination
4. **Uncertainty** - Always qualify analysis results
5. **User Control** - Clear emphasis on user autonomy

## Setup Instructions

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ with pgvector extension
- OpenAI API key

### Backend Setup

```bash
# 1. Install dependencies
cd backend
pip install -r requirements.txt

# 2. Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost/sfds"
export OPENAI_API_KEY="sk-..."

# 3. Run database migrations
psql -d sfds -f sfds_schema_core.sql

# 4. Seed spiritual principles with embeddings
python -c "
import asyncio
import asyncpg
from vector_search import seed_spiritual_principles

async def main():
    pool = await asyncpg.create_pool('postgresql://user:pass@localhost/sfds')
    await seed_spiritual_principles(pool)
    await pool.close()

asyncio.run(main())
"

# 5. Start the server
python -m uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd sfds-frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

### Environment Variables

**Backend:**
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/sfds
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
SECRET_KEY=your-jwt-secret
```

**Frontend:**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api/sfds
```

## Spiritual Principles Database

30+ principles with embeddings across categories:
- Discernment (凡事察验)
- Heart Guarding (保守你心)
- Fear/Anxiety (不要恐惧)
- Humility (看别人比自己强)
- Love (爱是恒久忍耐)
- Truth (真理必叫你们得以自由)
- Rest (安息是属灵操练)
- Patience (患难生忍耐)
- Obedience (顺服神)
- Sacrifice (愿意受苦)
- Victory (以善胜恶)
- Peace (留下平安)
- Faith (信是所望之事的实底)
- Wisdom (敬畏耶和华)

## Key Features

### 1. Reflective Discernment
- Probabilistic source classification
- Multiple alternative explanations
- Humility statements
- Risk assessment

### 2. Vector-Based Principle Retrieval
- Semantic search using OpenAI embeddings
- Context-aware relevance scoring
- Cosine similarity with pgvector

### 3. Emotional Awareness
- 16 emotion types tracked
- State snapshot (stress, anxiety, fatigue, etc.)
- Emotion-intensity correlation with motives

### 4. Non-Authoritative Output
- "Possible" rather than "is"
- "May" rather than "will"
- "Consider" rather than "should"
- User autonomy always emphasized

## API Response Example

```json
{
  "motive_analysis": {
    "fear_driven_score": 0.65,
    "pride_driven_score": 0.30,
    "love_driven_score": 0.45,
    "desire_driven_score": 0.40,
    "dominant_motive": "fear",
    "analysis_notes": "Decision appears significantly fear-driven"
  },
  "discernment": {
    "primary_source": "fear_response",
    "secondary_source": "conscience",
    "source_confidence": 0.70,
    "explanation": "This decision appears influenced by fear responses...",
    "alternative_explanations": [
      "This may be the Spirit guiding you into a new season",
      "Your inner wisdom may be protecting you from rushing"
    ],
    "risk_assessment": {
      "level": "moderate",
      "primary_concerns": ["Fear-based decisions often over-defend"]
    }
  },
  "guidance": {
    "structured_advice": "Given your current emotional state...",
    "immediate_actions": ["Share concerns with trusted friend"],
    "long_term_actions": ["Build stable emotional support system"],
    "follow_up_questions": ["What if this fear is actually wisdom?"]
  }
}
```

## Production Considerations

### Security
- JWT-based authentication
- Input validation with Pydantic
- SQL injection prevention via parameterized queries
- CORS configuration

### Performance
- Async database operations
- Connection pooling
- Vector search index optimization
- Frontend code splitting

### Monitoring
- API request logging
- Discernment accuracy tracking (via reviews)
- Error handling and alerting

## Future Enhancements

1. **LLM Integration** - GPT-4 for nuanced guidance generation
2. **Pattern Recognition** - Long-term user pattern analysis
3. **Community Features** - Anonymized collective insights
4. **Mobile App** - React Native or Flutter
5. **Offline Support** - PWA with service workers

## License

MIT License - Feel free to use and adapt for your own spiritual formation tools.

## Acknowledgments

This system is inspired by Ignatian discernment principles, combining ancient spiritual wisdom with modern AI technology to create a tool that respects both the mystery of spiritual formation and the value of self-reflection.

---

**Remember:** This system is a mirror, not a compass. The true guidance comes from within, as you learn to recognize the voice that speaks in stillness.
