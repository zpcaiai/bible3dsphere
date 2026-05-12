// SFDS Type Definitions

export type DecisionCategory = 
  | 'career' 
  | 'relationship' 
  | 'temptation' 
  | 'calling' 
  | 'financial' 
  | 'health' 
  | 'ministry' 
  | 'other';

export type EmotionType = 
  | 'fear' 
  | 'anxiety' 
  | 'anger' 
  | 'joy' 
  | 'peace' 
  | 'love' 
  | 'sadness' 
  | 'confusion' 
  | 'hope' 
  | 'doubt' 
  | 'desire' 
  | 'lust';

export type MotiveType = 
  | 'fear' 
  | 'pride' 
  | 'love' 
  | 'desire' 
  | 'duty' 
  | 'ambition';

export type DiscernmentSource = 
  | 'holy_spirit'
  | 'conscience'
  | 'fear_response'
  | 'pride_response'
  | 'trauma_response'
  | 'worldly_value'
  | 'flesh_desire'
  | 'uncertain';

export interface StateSnapshot {
  stress_level: number;
  anxiety_level: number;
  fatigue_level: number;
  spiritual_dryness: number;
  emotional_stability: number;
}

export interface EmotionLog {
  emotion_type: string;
  intensity: number;
  trigger?: string;
}

export interface MotiveAnalysis {
  fear_driven_score: number;
  pride_driven_score: number;
  love_driven_score: number;
  desire_driven_score: number;
  dominant_motive: MotiveType;
  secondary_motive?: MotiveType;
  analysis_notes?: string;
}

export interface DiscernmentResult {
  primary_source: DiscernmentSource;
  secondary_source?: DiscernmentSource;
  source_confidence: number;
  biblical_alignment_score?: number;
  long_term_fruit_prediction?: number;
  explanation: string;
  alternative_explanations: string[];
}

export interface SpiritualPrinciple {
  id: string;
  principle_text: string;
  scripture_reference?: string;
  category: string;
  relevance_score: number;
}

export interface GuidanceOutput {
  structured_advice: string;
  summary_advice?: string;
  primary_risks: string[];
  risk_severity: 'low' | 'medium' | 'high' | 'critical';
  alternative_interpretations: string[];
  blind_spots?: string[];
  recommended_actions: string[];
  immediate_actions?: string[];
  long_term_actions?: string[];
  priority: 'low' | 'medium' | 'high' | 'urgent';
  suggested_timeline?: string;
  recommended_scriptures?: string[];
  follow_up_questions?: string[];
}

export interface DecisionEvent {
  id: string;
  user_id: string;
  title: string;
  description: string;
  category: DecisionCategory;
  urgency_level: number;
  importance_level: number;
  state_snapshot: StateSnapshot;
  emotion_logs: EmotionLog[];
  motive_analysis?: MotiveAnalysis;
  discernment_result?: DiscernmentResult;
  guidance?: GuidanceOutput;
  created_at: string;
  status: 'analyzing' | 'guided' | 'decided' | 'reviewed';
}

export interface ReviewLog {
  id: string;
  decision_id: string;
  outcome_description: string;
  peace_level: number;
  regret_level: number;
  lessons_learned?: string;
  character_impact?: string;
  created_at: string;
}

export interface JournalEntry {
  id: string;
  date: string;
  type: 'daily' | 'decision_review';
  content: string;
  emotions: string[];
  decision_id?: string;
  decision_title?: string;
  outcome?: 'positive' | 'negative' | 'mixed' | 'ongoing';
}

// ─────────────────────────────────────────────────────────────
// V2 Formation Pipeline types
// ─────────────────────────────────────────────────────────────

export type TrendDirection = 'improving' | 'declining' | 'stable' | 'volatile' | 'unknown';
export type SpiritualSeason = 'dry' | 'stable' | 'growing' | 'confused' | 'restoring';
export type PatternCategory = 'fear' | 'pride' | 'shame' | 'desire' | 'relational' | 'spiritual' | 'growth';

export interface FormationIntervention {
  break_at:   string;
  suggestion: string;
  scripture?: string;
  category?:  string;
}

export interface FormationPattern {
  id:                   string;
  category:             PatternCategory;
  label:                string;
  chain:                string[];
  intervention:         FormationIntervention;
  reflective_question?: string;
}

export interface DetectedTemporalPattern {
  type:        string;
  description: string;
  confidence:  number;
}

// Pillar 1 — WHY (Neo4j structural)
export interface StructuralInsight {
  summary:              string;
  patterns:             string[];
  cycles_detected:      boolean;
  cycle_labels:         string[];
  interventions:        FormationIntervention[];
  reflective_questions: string[];
}

// Pillar 2 — WHEN (TimescaleDB temporal)
export interface TemporalInsight {
  trend:                    TrendDirection;
  season:                   SpiritualSeason;
  season_narrative:         string;
  trend_narrative:          string;
  detected_patterns:        DetectedTemporalPattern[];
  intervention_window:      boolean;
  data_points_available:    number;
}

// Pillar 3 — WHERE (spiritual alignment)
export interface AlignmentInsight {
  trend_narrative:    string;
  alignment_declining: boolean;
}

// Pillar 4 — NOW (intervention)
export interface InterventionInsight {
  suggestion:           string;
  reflective_questions: string[];
  is_high_risk_window:  boolean;
  pause_recommended:    boolean;
}

export interface PipelineLayerMeta {
  layer:       string;
  success:     boolean;
  error?:      string | null;
  duration_ms: number;
}

export interface FormationOutput {
  pipeline_id:          string;
  generated_at:         string;
  user_id:              string;
  decision_id:          string;
  '1_structural':       StructuralInsight;
  '2_temporal':         TemporalInsight;
  '3_alignment':        AlignmentInsight;
  '4_intervention':     InterventionInsight;
  reflective_questions: string[];
  v1_analysis?:         Record<string, unknown>;
  is_high_risk_window:  boolean;
  pause_recommended:    boolean;
  disclaimer:           string;
  pipeline_meta: {
    layers_run: PipelineLayerMeta[];
  };
}

export interface V2DiscernmentRequest {
  title:               string;
  description?:        string;
  category:            DecisionCategory;
  urgency?:            number;
  importance?:         number;
  snapshot: {
    anxiety_level:       number;
    peace_level:         number;
    clarity_level:       number;
    spiritual_dryness:   number;
    emotional_stability: number;
    decision_confidence: number;
    stress_level?:       number;
    fatigue_level?:      number;
  };
  emotion_logs?:        EmotionLog[];
  motive_analysis?:     Partial<MotiveAnalysis>;
  past_behavior_types?: string[];
  user_id?:             string;
}

export interface TimelineRecord {
  user_id:             string;
  anxiety_level:       number;
  peace_level:         number;
  clarity_level:       number;
  spiritual_dryness:   number;
  emotional_stability: number;
  decision_confidence: number;
  source_type?:        string;
  source_id?:          string;
  notes?:              string;
}
