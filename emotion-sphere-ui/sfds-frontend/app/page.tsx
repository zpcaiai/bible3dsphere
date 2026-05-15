'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  Plus, 
  BookOpen, 
  Clock, 
  ChevronRight,
  Heart,
  Sparkles,
  TrendingUp,
  Shield,
  ArrowRight
} from 'lucide-react';
import { Button } from './components/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './components/Card';
import { DecisionEvent } from '@/lib/types';

// Mock data for demonstration
const mockDecisions: DecisionEvent[] = [
  {
    id: '1',
    user_id: 'user1',
    title: '是否应该接受新的工作机会',
    description: '收到了一份新工作的offer，薪资更高但需要 relocation',
    category: 'career',
    urgency_level: 3,
    importance_level: 4,
    state_snapshot: {
      stress_level: 6,
      anxiety_level: 5,
      fatigue_level: 5,
      spiritual_dryness: 4,
      emotional_stability: 5,
    },
    emotion_logs: [],
    created_at: '2026-05-08T10:00:00Z',
    status: 'analyzing',
  },
  {
    id: '2',
    user_id: 'user1',
    title: '饶恕曾经伤害我的朋友',
    description: '一年前发生的一件事，心里还有疙瘩',
    category: 'relationship',
    urgency_level: 2,
    importance_level: 5,
    state_snapshot: {
      stress_level: 4,
      anxiety_level: 3,
      fatigue_level: 4,
      spiritual_dryness: 3,
      emotional_stability: 6,
    },
    emotion_logs: [],
    created_at: '2026-05-05T14:30:00Z',
    status: 'guided',
  },
];

const mockEmotionalState = {
  stress: 5,
  anxiety: 4,
  peace: 6,
  joy: 5,
  fatigue: 6,
  spiritualVitality: 5,
};

export default function Dashboard() {
  const [decisions, setDecisions] = useState<DecisionEvent[]>(mockDecisions);
  const [isLoading, setIsLoading] = useState(false);

  const categoryLabels: Record<string, string> = {
    career: '职业',
    relationship: '关系',
    calling: '呼召',
    temptation: '试探',
    financial: '财务',
    health: '健康',
    ministry: '事工',
    other: '其他',
  };

  const getWellbeingScore = () => {
    const { stress, anxiety, peace, joy, spiritualVitality } = mockEmotionalState;
    return Math.round((peace + joy + spiritualVitality - stress - anxiety + 15) / 3);
  };

  const getWellbeingStatus = (score: number) => {
    if (score >= 7) return { text: '状态良好', color: 'text-sfds-accent-teal', bg: 'bg-sfds-accent-teal/10' };
    if (score >= 5) return { text: '状态平稳', color: 'text-sfds-accent-sage', bg: 'bg-sfds-accent-sage/10' };
    return { text: '需要关注', color: 'text-sfds-accent-warm', bg: 'bg-sfds-accent-warm/10' };
  };

  const wellbeing = getWellbeingStatus(getWellbeingScore());

  return (
    <main className="min-h-screen pb-24">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-sfds-bg-card/80 backdrop-blur-md border-b border-sfds-border">
        <div className="max-w-3xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-sfds-accent-teal to-sfds-accent-sage flex items-center justify-center">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-sfds-text-primary">灵性决策陪伴</h1>
                <p className="text-xs text-sfds-text-muted">Reflective Decision Support</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-4 py-6">
        {/* Welcome */}
        <div className="mb-8 animate-fade-in">
          <h2 className="text-2xl font-medium text-sfds-text-primary mb-2">
            欢迎回来
          </h2>
          <p className="text-sfds-text-secondary">
            在这里，我们陪伴您分辨内心的声音，而非替您做决定
          </p>
        </div>

        {/* Current State Card */}
        <Card variant="gentle" className="mb-6 animate-fade-in">
          <div className="flex justify-between items-start mb-5">
            <div>
              <h3 className="text-lg font-medium text-sfds-text-primary flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-sfds-accent-teal" />
                今日状态
              </h3>
              <p className="text-sm text-sfds-text-secondary mt-1">
                觉察当下的自己，是分辨的第一步
              </p>
            </div>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${wellbeing.bg} ${wellbeing.color}`}>
              {wellbeing.text}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-4 mb-5">
            <StateIndicator label="压力" value={mockEmotionalState.stress} inverse />
            <StateIndicator label="焦虑" value={mockEmotionalState.anxiety} inverse />
            <StateIndicator label="平安" value={mockEmotionalState.peace} />
            <StateIndicator label="喜乐" value={mockEmotionalState.joy} />
            <StateIndicator label="疲劳" value={mockEmotionalState.fatigue} inverse />
            <StateIndicator label="灵性活力" value={mockEmotionalState.spiritualVitality} />
          </div>

          <div className="bg-sfds-bg-secondary rounded-lg p-4">
            <p className="text-sm text-sfds-text-secondary">
              <span className="font-medium">💭 温柔的提醒：</span>
              {mockEmotionalState.stress > 6 || mockEmotionalState.anxiety > 6
                ? '您现在的压力/焦虑水平较高，如果要做重要决定，或许可以先花一些时间照顾自己的情绪。'
                : mockEmotionalState.spiritualVitality < 4
                ? '灵性的干涸是真实的。在这个季节，或许重建与神的关系比做任何决定都更重要。'
                : '您的状态看起来相对平稳。这是一个适合思考和分辨的时机。'}
            </p>
          </div>
        </Card>

        {/* Quick Action */}
        <Link href="/decision/new" className="block mb-8">
          <Button 
            variant="primary" 
            size="lg" 
            className="w-full shadow-lg shadow-sfds-accent-teal/20"
          >
            <Plus className="w-5 h-5" />
            记录一个新的决定
          </Button>
        </Link>

        {/* Recent Decisions */}
        <div className="mb-8">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-sfds-text-primary flex items-center gap-2">
              <Clock className="w-5 h-5 text-sfds-text-muted" />
              最近的决定
            </h3>
            <Link href="/decisions">
              <Button variant="ghost" size="sm">
                查看全部
                <ChevronRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>

          {decisions.length === 0 ? (
            <Card className="text-center py-12">
              <div className="text-4xl mb-3">🌱</div>
              <p className="text-sfds-text-muted">还没有记录的决定</p>
              <p className="text-sm text-sfds-text-muted mt-1">
                每一个重要的决定都值得被温柔地对待
              </p>
            </Card>
          ) : (
            <div className="space-y-3">
              {decisions.map((decision) => (
                <Link key={decision.id} href={`/decision/${decision.id}`}>
                  <Card className="hover:shadow-sfds-hover transition-shadow cursor-pointer">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="px-2 py-0.5 bg-sfds-bg-secondary rounded text-xs text-sfds-text-muted">
                            {categoryLabels[decision.category] || decision.category}
                          </span>
                          <span className="text-xs text-sfds-text-muted">
                            {new Date(decision.created_at).toLocaleDateString('zh-CN')}
                          </span>
                        </div>
                        <h4 className="font-medium text-sfds-text-primary mb-1">
                          {decision.title}
                        </h4>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                          decision.status === 'analyzing' 
                            ? 'bg-sfds-accent-warm/10 text-sfds-accent-warm'
                            : decision.status === 'guided'
                            ? 'bg-sfds-accent-teal/10 text-sfds-accent-teal'
                            : 'bg-sfds-bg-secondary text-sfds-text-muted'
                        }`}>
                          {decision.status === 'analyzing' && '分析中'}
                          {decision.status === 'guided' && '已有指导'}
                          {decision.status === 'decided' && '已决定'}
                          {decision.status === 'reviewed' && '已回顾'}
                        </span>
                      </div>
                      <ChevronRight className="w-5 h-5 text-sfds-text-muted flex-shrink-0" />
                    </div>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Spiritual Trend Chart Placeholder */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-sfds-text-muted" />
              灵性成长轨迹
            </CardTitle>
            <CardDescription>
              属灵生命的成长，往往是在我们未曾察觉的时候悄然发生
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-40 bg-sfds-bg-secondary rounded-lg flex items-center justify-center">
              <div className="text-center">
                <div className="text-4xl mb-2">📈</div>
                <p className="text-sm text-sfds-text-muted">灵性健康趋势图表将在这里显示</p>
                <p className="text-xs text-sfds-text-muted mt-1">
                  记录更多日常状态后，您将看到自己的成长轨迹
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Daily Reflection Prompt */}
        <div className="bg-gradient-to-br from-sfds-accent-warm-light to-sfds-bg-secondary rounded-sfds p-6 mb-8">
          <p className="text-lg font-medium text-sfds-text-primary mb-3 italic">
            "今天的我，比昨天更靠近神一些了吗？"
          </p>
          <Link href="/journal">
            <Button variant="gentle">
              <BookOpen className="w-4 h-4" />
              写下今日反思
            </Button>
          </Link>
        </div>
      </div>

      {/* Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 bg-sfds-bg-card border-t border-sfds-border pb-safe">
        <div className="max-w-3xl mx-auto px-4 py-2">
          <div className="flex justify-around items-center">
            <NavItem href="/" icon={<Heart className="w-5 h-5" />} label="首页" active />
            <NavItem href="/decision/new" icon={<Plus className="w-5 h-5" />} label="新决定" />
            <NavItem href="/journal" icon={<BookOpen className="w-5 h-5" />} label="日记" />
            <NavItem href="/decisions" icon={<Clock className="w-5 h-5" />} label="历史" />
          </div>
        </div>
      </nav>
    </main>
  );
}

function StateIndicator({ 
  label, 
  value, 
  inverse 
}: { 
  label: string; 
  value: number; 
  inverse?: boolean;
}) {
  const getColor = (val: number) => {
    if (inverse) {
      if (val <= 3) return '#5a9a8f';
      if (val <= 6) return '#8fa872';
      return '#c4a77d';
    }
    if (val >= 7) return '#5a9a8f';
    if (val >= 5) return '#8fa872';
    return '#c4a77d';
  };

  const color = getColor(value);

  return (
    <div className="text-center">
      <div 
        className="text-xl font-semibold mb-1"
        style={{ color }}
      >
        {value}
      </div>
      <div className="text-xs text-sfds-text-muted">{label}</div>
      <div className="h-1 bg-sfds-border rounded-full mt-2 overflow-hidden">
        <div 
          className="h-full rounded-full transition-all duration-300"
          style={{ 
            width: `${value * 10}%`,
            backgroundColor: color,
          }}
        />
      </div>
    </div>
  );
}

function NavItem({ 
  href, 
  icon, 
  label, 
  active 
}: { 
  href: string; 
  icon: React.ReactNode; 
  label: string; 
  active?: boolean;
}) {
  return (
    <Link 
      href={href}
      className={`flex flex-col items-center gap-1 px-3 py-2 rounded-lg transition-colors ${
        active 
          ? 'text-sfds-accent-teal' 
          : 'text-sfds-text-muted hover:text-sfds-text-primary'
      }`}
    >
      {icon}
      <span className="text-xs">{label}</span>
    </Link>
  );
}
