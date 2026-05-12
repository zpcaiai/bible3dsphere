'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/app/components/Button';
import { Card } from '@/app/components/Card';
import { Slider } from '@/app/components/Slider';

const categories = [
  { value: 'career', label: '职业/工作', emoji: '💼' },
  { value: 'relationship', label: '人际关系', emoji: '💕' },
  { value: 'temptation', label: '试探/诱惑', emoji: '⚠️' },
  { value: 'calling', label: '呼召/使命', emoji: '🎯' },
  { value: 'financial', label: '财务/金钱', emoji: '💰' },
  { value: 'health', label: '健康/身体', emoji: '🏥' },
  { value: 'ministry', label: '事工/服事', emoji: '⛪' },
  { value: 'other', label: '其他', emoji: '📝' },
];

const emotions = [
  { type: 'joy', label: '喜乐' }, { type: 'peace', label: '平安' },
  { type: 'love', label: '爱' }, { type: 'gratitude', label: '感恩' },
  { type: 'hope', label: '盼望' }, { type: 'confidence', label: '自信' },
  { type: 'sadness', label: '悲伤' }, { type: 'fear', label: '恐惧' },
  { type: 'anxiety', label: '焦虑' }, { type: 'anger', label: '愤怒' },
  { type: 'confusion', label: '困惑' }, { type: 'guilt', label: '内疚' },
];

export default function NewDecision() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    title: '', category: '', urgency: 3, importance: 3,
    selectedEmotions: [] as string[],
    stateSnapshot: { stress_level: 5, anxiety_level: 5, fatigue_level: 5, spiritual_dryness: 5, emotional_stability: 5 },
  });

  const handleSubmit = () => router.push('/decision/123/analysis');

  return (
    <main className="min-h-screen pb-32">
      <header className="sticky top-0 z-50 bg-sfds-bg-card/80 backdrop-blur-md border-b border-sfds-border">
        <div className="max-w-3xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link href="/"><Button variant="ghost" size="sm" className="p-2"><ArrowLeft className="w-5 h-5" /></Button></Link>
            <div className="flex-1">
              <div className="flex gap-1 mb-2">
                {[1, 2, 3, 4].map(s => <div key={s} className={`h-1 flex-1 rounded-full ${s <= step ? 'bg-sfds-accent-teal' : 'bg-sfds-border'}`} />)}
              </div>
              <p className="text-xs text-sfds-text-muted">步骤 {step} / 4</p>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-4 py-6">
        {step === 1 && (
          <div className="animate-fade-in space-y-5">
            <div>
              <h2 className="text-xl font-medium text-sfds-text-primary mb-2">描述您的情况</h2>
              <p className="text-sfds-text-secondary">没有"正确"或"错误"的描述方式</p>
            </div>
            <input type="text" value={formData.title} onChange={(e) => setFormData({ ...formData, title: e.target.value })} placeholder="这个决定是关于什么的？" className="w-full px-4 py-3 rounded-lg border border-sfds-border bg-sfds-bg-card text-sfds-text-primary placeholder:text-sfds-text-muted focus-ring" />
            <div className="grid grid-cols-2 gap-2">
              {categories.map((cat) => (
                <button key={cat.value} onClick={() => setFormData({ ...formData, category: cat.value })} className={`p-3 rounded-lg border text-left transition-colors ${formData.category === cat.value ? 'border-sfds-accent-teal bg-sfds-accent-teal-light text-sfds-accent-teal' : 'border-sfds-border bg-sfds-bg-card text-sfds-text-secondary'}`}>
                  <span className="mr-2">{cat.emoji}</span>{cat.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="animate-fade-in">
            <h2 className="text-xl font-medium text-sfds-text-primary mb-4">当下的情绪</h2>
            <div className="grid grid-cols-3 gap-2 mb-4">
              {emotions.map((emotion) => (
                <button key={emotion.type} onClick={() => setFormData(prev => ({ ...prev, selectedEmotions: prev.selectedEmotions.includes(emotion.type) ? prev.selectedEmotions.filter(e => e !== emotion.type) : prev.selectedEmotions.length >= 3 ? prev.selectedEmotions : [...prev.selectedEmotions, emotion.type] }))} className={`p-3 rounded-lg border text-sm transition-colors ${formData.selectedEmotions.includes(emotion.type) ? 'border-sfds-accent-teal bg-sfds-accent-teal text-white' : 'border-sfds-border bg-sfds-bg-card text-sfds-text-secondary'}`}>
                  {emotion.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="animate-fade-in">
            <h2 className="text-xl font-medium text-sfds-text-primary mb-4">此刻的状态</h2>
            <Card>
              <Slider label="压力水平" value={formData.stateSnapshot.stress_level} onChange={(v) => setFormData({ ...formData, stateSnapshot: { ...formData.stateSnapshot, stress_level: v } })} lowLabel="轻松" highLabel="压力很大" />
              <Slider label="焦虑水平" value={formData.stateSnapshot.anxiety_level} onChange={(v) => setFormData({ ...formData, stateSnapshot: { ...formData.stateSnapshot, anxiety_level: v } })} lowLabel="平静" highLabel="焦虑很高" />
              <Slider label="疲劳程度" value={formData.stateSnapshot.fatigue_level} onChange={(v) => setFormData({ ...formData, stateSnapshot: { ...formData.stateSnapshot, fatigue_level: v } })} lowLabel="精力充沛" highLabel="非常疲惫" />
              <Slider label="灵性状态" value={formData.stateSnapshot.spiritual_dryness} onChange={(v) => setFormData({ ...formData, stateSnapshot: { ...formData.stateSnapshot, spiritual_dryness: v } })} lowLabel="与神亲近" highLabel="灵性干涸" inverse />
              <Slider label="情绪稳定" value={formData.stateSnapshot.emotional_stability} onChange={(v) => setFormData({ ...formData, stateSnapshot: { ...formData.stateSnapshot, emotional_stability: v } })} lowLabel="波动很大" highLabel="非常稳定" />
            </Card>
          </div>
        )}

        {step === 4 && (
          <div className="animate-fade-in">
            <h2 className="text-xl font-medium text-sfds-text-primary mb-4">准备开始辨识</h2>
            <Card className="mb-4"><p className="text-sfds-text-primary font-medium">{formData.title}</p><p className="text-sm text-sfds-text-muted">{categories.find(c => c.value === formData.category)?.label}</p></Card>
          </div>
        )}
      </div>

      <div className="fixed bottom-0 left-0 right-0 bg-sfds-bg-card border-t border-sfds-border p-4">
        <div className="max-w-3xl mx-auto">
          {step < 4 ? (
            <Button onClick={() => setStep(step + 1)} disabled={!formData.title || !formData.category} className="w-full">继续</Button>
          ) : (
            <Button onClick={handleSubmit} className="w-full">开始辨识</Button>
          )}
        </div>
      </div>
    </main>
  );
}
