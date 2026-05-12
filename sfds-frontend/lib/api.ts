// API Client for SFDS Backend

import { 
  DecisionEvent, 
  DecisionCategory, 
  StateSnapshot, 
  EmotionLog, 
  SpiritualPrinciple,
  ReviewLog,
  FormationOutput,
  FormationPattern,
  V2DiscernmentRequest,
  TimelineRecord,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/sfds';

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }

  return response.json();
}

// Decision APIs
export async function createDecision(data: {
  title: string;
  description: string;
  category: DecisionCategory;
  urgency: number;
  importance: number;
  state_snapshot: StateSnapshot;
  emotion_logs: EmotionLog[];
}) {
  return fetchApi<{ id: string; status: string; message: string }>('/decisions', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getDecision(id: string): Promise<DecisionEvent> {
  return fetchApi<DecisionEvent>(`/decisions/${id}`);
}

export async function listDecisions(): Promise<DecisionEvent[]> {
  return fetchApi<DecisionEvent[]>('/decisions');
}

// Analysis APIs
export async function quickAnalyze(
  state: StateSnapshot, 
  emotions: EmotionLog[]
) {
  return fetchApi('/quick-discern', {
    method: 'POST',
    body: JSON.stringify({ state_snapshot: state, emotion_logs: emotions }),
  });
}

export async function deepAnalyze(data: {
  title: string;
  description: string;
  category: DecisionCategory;
  urgency: number;
  importance: number;
  state_snapshot: StateSnapshot;
  emotion_logs: EmotionLog[];
}) {
  return fetchApi('/reflective-discern', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// Principle APIs
export async function getPrinciples(category?: string): Promise<SpiritualPrinciple[]> {
  const query = category ? `?category=${category}` : '';
  return fetchApi<SpiritualPrinciple[]>(`/principles${query}`);
}

export async function searchPrinciples(query: string): Promise<SpiritualPrinciple[]> {
  return fetchApi<SpiritualPrinciple[]>('/principles/search', {
    method: 'POST',
    body: JSON.stringify({ query }),
  });
}

// Review APIs
export async function submitReview(decisionId: string, review: {
  outcome_description: string;
  peace_level: number;
  regret_level: number;
  lessons_learned?: string;
  character_impact?: string;
}) {
  return fetchApi<{ id: string; message: string }>(`/decisions/${decisionId}/review`, {
    method: 'POST',
    body: JSON.stringify(review),
  });
}

// Journal APIs (mock for now, would connect to backend)
export async function getJournalEntries(): Promise<any[]> {
  // Mock data - would be fetched from backend
  return [
    {
      id: '1',
      date: new Date().toISOString().split('T')[0],
      type: 'daily',
      content: '今天的灵修让我对即将到来的决定有了更清晰的认识...',
      emotions: ['peace', 'gratitude'],
    },
  ];
}

export async function createJournalEntry(entry: {
  content: string;
  emotions: string[];
  type: 'daily' | 'decision_review';
}) {
  // Mock - would POST to backend
  return { id: Date.now().toString(), ...entry };
}

// ─────────────────────────────────────────────────────────────
// V2 Formation Pipeline APIs
// ─────────────────────────────────────────────────────────────

export async function v2Discern(data: V2DiscernmentRequest): Promise<FormationOutput> {
  return fetchApi<FormationOutput>('/v2/discern', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function recordTimeline(record: TimelineRecord): Promise<{ recorded: boolean; message: string }> {
  return fetchApi('/v2/timeline/record', {
    method: 'POST',
    body: JSON.stringify(record),
  });
}

export async function recordEmotion(data: {
  user_id: string;
  emotion_type: string;
  intensity: number;
  trigger?: string;
  decision_id?: string;
}): Promise<{ recorded: boolean }> {
  return fetchApi('/v2/emotions/record', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getTemporalAnalysis(userId: string, days = 90) {
  return fetchApi(`/v2/timeline/${encodeURIComponent(userId)}?days=${days}`);
}

export async function getGraphPatterns(category?: string): Promise<{ total: number; patterns: FormationPattern[] }> {
  const query = category ? `?category=${encodeURIComponent(category)}` : '';
  return fetchApi<{ total: number; patterns: FormationPattern[] }>(`/v2/graph/patterns${query}`);
}
