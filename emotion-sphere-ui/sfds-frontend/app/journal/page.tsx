'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Plus, BookOpen } from 'lucide-react';
import { Button } from '@/app/components/Button';
import { Card } from '@/app/components/Card';

const prompts = [
  '今天的我，比昨天更靠近神一些了吗？',
  '此刻，什么占据了我的心？',
  '我是否带着平安，还是带着焦虑做决定？',
  '这个决定的动机是恐惧还是爱？',
  '如果神亲自问我，我会怎么回答？',
];

const mockEntries = [
  { id: '1', date: '2026-05-08', content: '今天的灵修让我对即将到来的决定有了更清晰的认识...', emotions: ['peace', 'gratitude'], type: 'daily' },
  { id: '2', date: '2026-05-06', content: '关于工作offer的纠结，我一直在害怕失败...', emotions: ['fear', 'confusion'], type: 'decision_review' },
];

export default function Journal() {
  const [showNewEntry, setShowNewEntry] = useState(false);
  const [selectedPrompt, setSelectedPrompt] = useState('');
  const [content, setContent] = useState('');

  return (
    <main className="min-h-screen pb-24">
      <header className="sticky top-0 z-50 bg-sfds-bg-card/80 backdrop-blur-md border-b border-sfds-border">
        <div className="max-w-3xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link href="/"><Button variant="ghost" size="sm" className="p-2"><ArrowLeft className="w-5 h-5" /></Button></Link>
            <div className="flex-1"><h1 className="text-lg font-semibold text-sfds-text-primary">反思日记</h1></div>
          </div>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-4 py-6">
        {!showNewEntry ? (
          <>
            <Button onClick={() => setShowNewEntry(true)} className="w-full mb-6"><Plus className="w-4 h-4" /> 新建日记</Button>
            
            <h2 className="text-lg font-medium text-sfds-text-primary mb-4 flex items-center gap-2"><BookOpen className="w-5 h-5" /> 历史记录</h2>
            {mockEntries.map((entry) => (
              <Card key={entry.id} className="mb-3">
                <p className="text-xs text-sfds-text-muted mb-2">{entry.date} · {entry.type === 'daily' ? '日常' : '决策反思'}</p>
                <p className="text-sfds-text-primary line-clamp-3">{entry.content}</p>
                <div className="flex gap-2 mt-3">
                  {entry.emotions.map((e) => <span key={e} className="px-2 py-0.5 bg-sfds-bg-secondary rounded text-xs text-sfds-text-muted">{e}</span>)}
                </div>
              </Card>
            ))}

            <div className="mt-8 bg-gradient-to-br from-sfds-accent-warm-light to-sfds-bg-secondary rounded-sfds p-5">
              <p className="text-sm text-sfds-text-secondary mb-4">📝 <strong>反思提示</strong></p>
              <div className="space-y-2">
                {prompts.map((p) => <button key={p} onClick={() => { setSelectedPrompt(p); setShowNewEntry(true); }} className="block w-full text-left p-3 bg-sfds-bg-card rounded-lg text-sm text-sfds-text-secondary hover:bg-sfds-accent-teal-light transition-colors">{p}</button>)}
              </div>
            </div>
          </>
        ) : (
          <div className="animate-fade-in">
            <h2 className="text-xl font-medium text-sfds-text-primary mb-4">新的反思</h2>
            {selectedPrompt && <p className="text-sfds-text-secondary mb-4 italic">{selectedPrompt}</p>}
            <textarea value={content} onChange={(e) => setContent(e.target.value)} placeholder="写下您的想法..." rows={10} className="w-full px-4 py-3 rounded-lg border border-sfds-border bg-sfds-bg-card text-sfds-text-primary placeholder:text-sfds-text-muted focus-ring resize-none mb-4" />
            <div className="flex gap-3">
              <Button variant="secondary" onClick={() => setShowNewEntry(false)} className="flex-1">取消</Button>
              <Button onClick={() => setShowNewEntry(false)} className="flex-1">保存</Button>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
