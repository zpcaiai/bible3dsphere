'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  ArrowLeft, AlertTriangle, Sparkles, BookOpen,
  GitBranch, Clock, Compass, HelpCircle, Activity,
  ChevronRight, Info
} from 'lucide-react';
import { Button } from '@/app/components/Button';
import { Card } from '@/app/components/Card';
import type { FormationOutput, StructuralInsight, TemporalInsight, AlignmentInsight, InterventionInsight } from '@/lib/types';

// ── Mock V2 data (replace with real API call) ─────────────────────────────────
const mockV2: FormationOutput = {
  pipeline_id:   'mock-pipeline-001',
  generated_at:  new Date().toISOString(),
  user_id:       'user1',
  decision_id:   'decision1',
  '1_structural': {
    summary: '模式识别：fear → control → overwork → burnout → spiritual dryness',
    patterns: ['fear → control → overwork → burnout → spiritual dryness', 'pride → comparison → anxiety → performance addiction → emptiness'],
    cycles_detected: true,
    cycle_labels: ['fear → control → overwork → burnout → spiritual dryness'],
    interventions: [
      { break_at: 'control_impulse', suggestion: '注意到控制冲动的时刻，在行动之前停下来。如果放手，感觉会怎样？', scripture: 'Matthew 6:25-27', category: 'fear' },
      { break_at: 'comparison', suggestion: '比较衡量的是错误的东西。没有人看见的时候，你真正在乎的是什么？', scripture: 'Galatians 6:4', category: 'pride' },
    ],
    reflective_questions: [
      '如果你停止试图控制这件事，你最害怕会发生什么？',
      '如果没有人知道这个决定的结果，你还会做出同样的选择吗？',
    ],
  },
  '2_temporal': {
    trend: 'declining',
    season: 'dry',
    season_narrative: '你目前似乎正处于一个属灵干旱的季节 — 平静度低，焦虑度高。这本身不是失败，而是一个需要滋养的季节。',
    trend_narrative: '过去两周的属灵稳定性整体呈下降趋势。',
    detected_patterns: [
      { type: 'burnout', description: '压力持续高企，随后出现断崖式下降', confidence: 0.72 },
      { type: 'cycle', description: '焦虑模式每约10天重复出现一次', confidence: 0.58 },
    ],
    intervention_window: true,
    data_points_available: 12,
  },
  '3_alignment': {
    trend_narrative: '整体属灵对齐度在过去的观察期内有所下降。在下降阶段做出的决定往往更多反映焦虑而非信心。',
    alignment_declining: true,
  },
  '4_intervention': {
    suggestion: '目前有多个压力信号同时出现。如果可行，可以考虑给自己24–72小时再做决定。\n\n模式反思：注意到控制冲动的时刻，在行动之前停下来。 (Matthew 6:25-27)',
    reflective_questions: [
      '如果你停止试图控制这件事，你最害怕会发生什么？',
      '如果没有人知道这个决定的结果，你还会做出同样的选择吗？',
      '这个决定的动机是恐惧还是爱？',
    ],
    is_high_risk_window: true,
    pause_recommended: true,
  },
  reflective_questions: [
    '如果你停止试图控制这件事，你最害怕会发生什么？',
    '如果没有人知道这个决定的结果，你还会做出同样的选择吗？',
    '这个决定的动机是恐惧还是爱？',
  ],
  is_high_risk_window: true,
  pause_recommended: true,
  disclaimer: '本系统提供结构化反思，而非属灵权威。它是一面镜子，不是判决。所有洞见都是概率性的。人的自由意志、恩典和奥秘永远超越任何模型所能捕捉的。',
  pipeline_meta: {
    layers_run: [
      { layer: 'state_snapshot', success: true, duration_ms: 0.1 },
      { layer: 'semantic_retrieval', success: true, duration_ms: 12.4 },
      { layer: 'graph_query', success: true, duration_ms: 8.2 },
      { layer: 'timeseries_query', success: true, duration_ms: 15.6 },
      { layer: 'llm_discernment', success: true, duration_ms: 45.3 },
    ],
  },
};

// ── Season labels ─────────────────────────────────────────────────────────────
const seasonLabels: Record<string, string> = {
  dry: '干旱季节', stable: '稳定期', growing: '成长期',
  confused: '迷茫期', restoring: '恢复期',
};
const trendLabels: Record<string, string> = {
  improving: '上升 ↑', declining: '下降 ↓',
  stable: '稳定 →', volatile: '波动 ↕', unknown: '未知',
};
const trendColor: Record<string, string> = {
  improving: 'text-sfds-accent-teal', declining: 'text-sfds-accent-warm',
  stable: 'text-sfds-text-secondary', volatile: 'text-amber-500', unknown: 'text-sfds-text-muted',
};

// ── Tab definitions ───────────────────────────────────────────────────────────
const tabs = ['overview', 'structural', 'temporal', 'reflection'] as const;
type Tab = typeof tabs[number];
const tabLabels: Record<Tab, string> = {
  overview: '概览', structural: '结构', temporal: '时间', reflection: '反思',
};

// ── Sub-components ────────────────────────────────────────────────────────────

function RiskBanner({ paused }: { paused: boolean }) {
  if (!paused) return null;
  return (
    <div className="mb-4 flex items-start gap-3 p-4 rounded-lg bg-sfds-accent-warm-light border border-sfds-accent-warm/30">
      <AlertTriangle className="w-5 h-5 text-sfds-accent-warm flex-shrink-0 mt-0.5" />
      <div>
        <p className="font-medium text-sfds-text-primary text-sm">多重信号叠加 · 建议暂缓</p>
        <p className="text-xs text-sfds-text-secondary mt-1">
          当前检测到多个压力指标同时升高。如果可行，给自己24–72小时再做决定可能是值得的。
        </p>
      </div>
    </div>
  );
}

function InsightPill({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-sfds-bg-secondary ${color ?? 'text-sfds-text-secondary'}`}>
      {label}: {value}
    </span>
  );
}

function CycleBadge({ detected }: { detected: boolean }) {
  if (!detected) return null;
  return (
    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-sfds-accent-warm-light text-sfds-accent-warm">
      ⚠ 检测到循环模式
    </span>
  );
}

function ReflectiveCard({ question }: { question: string }) {
  return (
    <div className="p-4 rounded-lg border border-sfds-border bg-gradient-to-br from-sfds-bg-secondary to-sfds-bg-card">
      <div className="flex items-start gap-3">
        <HelpCircle className="w-4 h-4 text-sfds-accent-teal flex-shrink-0 mt-0.5" />
        <p className="text-sm text-sfds-text-primary leading-relaxed italic">{question}</p>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function AnalysisPage() {
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const data = mockV2;

  const structural: StructuralInsight   = data['1_structural'];
  const temporal:   TemporalInsight     = data['2_temporal'];
  const alignment:  AlignmentInsight    = data['3_alignment'];
  const intervention: InterventionInsight = data['4_intervention'];

  return (
    <main className="min-h-screen pb-24">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-sfds-bg-card/80 backdrop-blur-md border-b border-sfds-border">
        <div className="max-w-3xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link href="/">
              <Button variant="ghost" size="sm" className="p-2">
                <ArrowLeft className="w-5 h-5" />
              </Button>
            </Link>
            <div className="flex-1">
              <h1 className="text-lg font-semibold text-sfds-text-primary">形成性辨识 V2</h1>
              <p className="text-xs text-sfds-text-muted">镜子，不是裁判 · 意识 · 反思 · 自由意志</p>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-4 py-6">
        {/* Risk banner */}
        <RiskBanner paused={data.pause_recommended} />

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-sfds-bg-secondary p-1 rounded-lg">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-2 px-2 rounded-md text-xs font-medium transition-colors ${
                activeTab === tab
                  ? 'bg-sfds-bg-card text-sfds-text-primary shadow-sm'
                  : 'text-sfds-text-muted hover:text-sfds-text-secondary'
              }`}
            >
              {tabLabels[tab]}
            </button>
          ))}
        </div>

        {/* ── 概览 ── */}
        {activeTab === 'overview' && (
          <div className="animate-fade-in space-y-4">
            {/* Quick pills */}
            <div className="flex flex-wrap gap-2 mb-2">
              <InsightPill
                label="趋势"
                value={trendLabels[temporal.trend] ?? temporal.trend}
                color={trendColor[temporal.trend]}
              />
              <InsightPill label="季节" value={seasonLabels[temporal.season] ?? temporal.season} />
              <CycleBadge detected={structural.cycles_detected} />
            </div>

            {/* Alignment card */}
            <Card>
              <div className="flex items-start gap-3">
                <Compass className="w-5 h-5 text-sfds-accent-teal flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-medium text-sfds-text-primary mb-1 text-sm">属灵对齐</h3>
                  <p className="text-sm text-sfds-text-secondary leading-relaxed">{alignment.trend_narrative}</p>
                </div>
              </div>
            </Card>

            {/* Intervention card */}
            <Card>
              <div className="flex items-start gap-3">
                <Sparkles className="w-5 h-5 text-sfds-accent-sage flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-medium text-sfds-text-primary mb-2 text-sm">当前提示</h3>
                  {intervention.suggestion.split('\n\n').map((para, i) => (
                    <p key={i} className="text-sm text-sfds-text-secondary leading-relaxed mb-2">{para}</p>
                  ))}
                </div>
              </div>
            </Card>

            {/* First reflective question */}
            {data.reflective_questions[0] && (
              <div>
                <p className="text-xs font-medium text-sfds-text-muted mb-2 uppercase tracking-wide">反思邀请</p>
                <ReflectiveCard question={data.reflective_questions[0]} />
              </div>
            )}

            {/* Disclaimer */}
            <div className="flex items-start gap-2 p-3 rounded-lg bg-sfds-bg-secondary">
              <Info className="w-3.5 h-3.5 text-sfds-text-muted flex-shrink-0 mt-0.5" />
              <p className="text-xs text-sfds-text-muted leading-relaxed">{data.disclaimer}</p>
            </div>
          </div>
        )}

        {/* ── 结构（WHY） ── */}
        {activeTab === 'structural' && (
          <div className="animate-fade-in space-y-4">
            <div className="flex items-center gap-2 mb-1">
              <GitBranch className="w-4 h-4 text-sfds-accent-teal" />
              <h2 className="text-sm font-semibold text-sfds-text-primary">结构分析 · 为什么会这样？</h2>
            </div>
            <p className="text-xs text-sfds-text-muted mb-3">
              以下模式来自对22种常见人类形成循环的比对。它们是镜子，不是诊断。
            </p>

            {/* Pattern chains */}
            {structural.patterns.map((pattern, i) => (
              <Card key={i} className="mb-2">
                <p className="text-xs font-mono text-sfds-accent-teal leading-relaxed">{pattern}</p>
              </Card>
            ))}

            {/* Cycle warning */}
            {structural.cycles_detected && structural.cycle_labels.length > 0 && (
              <div className="p-3 rounded-lg bg-sfds-accent-warm-light border border-sfds-accent-warm/20">
                <p className="text-xs font-medium text-sfds-accent-warm mb-1">可能存在循环模式</p>
                {structural.cycle_labels.map((lbl, i) => (
                  <p key={i} className="text-xs text-sfds-text-secondary">{lbl}</p>
                ))}
              </div>
            )}

            {/* Intervention points */}
            {structural.interventions.length > 0 && (
              <div>
                <p className="text-xs font-medium text-sfds-text-muted uppercase tracking-wide mb-2">高杠杆反思点</p>
                {structural.interventions.map((iv, i) => (
                  <Card key={i} className="mb-3">
                    <div className="flex items-start gap-2 mb-2">
                      <ChevronRight className="w-4 h-4 text-sfds-accent-teal flex-shrink-0 mt-0.5" />
                      <span className="text-xs font-medium text-sfds-text-primary uppercase tracking-wide">{iv.break_at.replace(/_/g, ' ')}</span>
                    </div>
                    <p className="text-sm text-sfds-text-secondary leading-relaxed mb-1">{iv.suggestion}</p>
                    {iv.scripture && (
                      <p className="text-xs text-sfds-text-muted">{iv.scripture}</p>
                    )}
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── 时间（WHEN） ── */}
        {activeTab === 'temporal' && (
          <div className="animate-fade-in space-y-4">
            <div className="flex items-center gap-2 mb-1">
              <Clock className="w-4 h-4 text-sfds-accent-teal" />
              <h2 className="text-sm font-semibold text-sfds-text-primary">时间分析 · 这是什么时候开始的？</h2>
            </div>

            {/* Season + trend */}
            <div className="grid grid-cols-2 gap-3">
              <Card>
                <p className="text-xs text-sfds-text-muted mb-1">属灵季节</p>
                <p className="text-lg font-semibold text-sfds-text-primary">{seasonLabels[temporal.season] ?? temporal.season}</p>
                <p className="text-xs text-sfds-text-secondary mt-1 leading-relaxed">{temporal.season_narrative}</p>
              </Card>
              <Card>
                <p className="text-xs text-sfds-text-muted mb-1">整体趋势</p>
                <p className={`text-lg font-semibold ${trendColor[temporal.trend]}`}>{trendLabels[temporal.trend] ?? temporal.trend}</p>
                <p className="text-xs text-sfds-text-secondary mt-1 leading-relaxed">{temporal.trend_narrative}</p>
              </Card>
            </div>

            {/* Detected temporal patterns */}
            {temporal.detected_patterns.length > 0 && (
              <div>
                <p className="text-xs font-medium text-sfds-text-muted uppercase tracking-wide mb-2">检测到的时间模式</p>
                {temporal.detected_patterns.map((p, i) => (
                  <Card key={i} className="mb-2">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start gap-2">
                        <Activity className="w-4 h-4 text-sfds-accent-warm flex-shrink-0 mt-0.5" />
                        <div>
                          <p className="text-xs font-medium text-sfds-text-primary capitalize">{p.type}</p>
                          <p className="text-xs text-sfds-text-secondary mt-0.5">{p.description}</p>
                        </div>
                      </div>
                      <span className="text-xs text-sfds-text-muted whitespace-nowrap">
                        {Math.round(p.confidence * 100)}% 置信度
                      </span>
                    </div>
                  </Card>
                ))}
              </div>
            )}

            {/* Intervention window */}
            {temporal.intervention_window && (
              <div className="p-3 rounded-lg bg-sfds-accent-warm-light border border-sfds-accent-warm/20">
                <p className="text-xs font-medium text-sfds-accent-warm">当前处于干预窗口期</p>
                <p className="text-xs text-sfds-text-secondary mt-1">
                  这是一个特别需要审慎的时期。在此期间做出的决定可能更多受情绪驱动而非价值观驱动。
                </p>
              </div>
            )}

            <p className="text-xs text-sfds-text-muted text-center">
              基于 {temporal.data_points_available} 个数据点 · 数据越多，洞见越准确
            </p>
          </div>
        )}

        {/* ── 反思（Reflection） ── */}
        {activeTab === 'reflection' && (
          <div className="animate-fade-in space-y-4">
            <div className="flex items-center gap-2 mb-1">
              <HelpCircle className="w-4 h-4 text-sfds-accent-teal" />
              <h2 className="text-sm font-semibold text-sfds-text-primary">反思邀请</h2>
            </div>
            <p className="text-xs text-sfds-text-muted mb-3 leading-relaxed">
              以下问题来自与你当前处境最相关的形成模式。它们没有正确答案。
              它们是镜子——你自己的回应才是最重要的。
            </p>

            <div className="space-y-3">
              {data.reflective_questions.map((q, i) => (
                <ReflectiveCard key={i} question={q} />
              ))}
            </div>

            {/* Structural reflective questions */}
            {structural.reflective_questions.filter(q => !data.reflective_questions.includes(q)).map((q, i) => (
              <ReflectiveCard key={`s-${i}`} question={q} />
            ))}

            {/* Disclaimer */}
            <div className="mt-6 p-4 rounded-lg bg-gradient-to-br from-sfds-bg-secondary to-sfds-bg-card border border-sfds-border">
              <div className="flex items-start gap-2">
                <BookOpen className="w-4 h-4 text-sfds-text-muted flex-shrink-0 mt-0.5" />
                <p className="text-xs text-sfds-text-muted leading-relaxed">{data.disclaimer}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
