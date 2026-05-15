import { useState, useEffect, useCallback } from 'react'
import { API_BASE } from './api'

const MVFE_BASE = API_BASE + '/mvfe'

const EMOTION_NAMES = {
  anxiety:'焦虑', peace:'平静', hope:'盼望', sadness:'悲伤',
  anger:'愤怒', fear:'恐惧', joy:'喜乐', love:'爱',
  shame:'羞耻', guilt:'内疚', disgust:'厌恶', surprise:'惊讶',
  gratitude:'感恩', envy:'嫉妒', loneliness:'孤独', unknown:'未知',
}
const FOCUS_NAMES = {
  work:'工作', career:'职业', relationship:'关系', self:'自我', future:'未来',
  money:'金钱', finance:'财务', health:'健康', family:'家庭', past:'过去',
  spirituality:'灵性', identity:'身份', other:'其他', unknown:'未知',
}
const C = {
  anxiety:'#ffa94d', peace:'#4facfe', hope:'#51cf66', sadness:'#748ffc',
  anger:'#ff6b6b', fear:'#da77f2', joy:'#ffd43b', love:'#ff8787',
  shame:'#9775fa', guilt:'#63e6be', disgust:'#8ce99a', surprise:'#74c0fc',
  gratitude:'#ffec99', envy:'#ffa8a8', loneliness:'#bac8ff', unknown:'#868e96',
}

const QUICK = [
  {t:'最近工作压力很大，总是担心做不好，想逃避...',e:'\ud83d\ude30',l:'焦虑逃避'},
  {t:'今天内心很平静，和家人一起很感恩...',e:'\ud83d\ude0c',l:'平静感恩'},
  {t:'感觉被忽视了，有点生气又不知道怎么表达...',e:'\ud83d\ude24',l:'被忽视'},
  {t:'对未来充满期待，想尝试新的事情...',e:'\u2728',l:'充满期待'},
  {t:'一直在同一件事上反复纠结，走不出来...',e:'\ud83d\udd04',l:'反复纠结'},
]

export default function MVFEPage({ user, onBack }) {
  const [inputText, setInputText] = useState('')
  const [processing, setProcessing] = useState(false)
  const [lastResult, setLastResult] = useState(null)
  const [dashboardData, setDashboardData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeView, setActiveView] = useState('dashboard')
  const [error, setError] = useState('')
  const userId = String(user?.id || user?.email || 'default_user')

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const r = await fetch(MVFE_BASE + '/dashboard/state?user_id=' + userId + '&hours=168')
      if (r.ok) setDashboardData(await r.json())
    } catch(e){}
    setLoading(false)
  }, [userId])

  useEffect(() => { loadData() }, [loadData])

  async function handleProcess(text) {
    const t = text || inputText
    if (!t.trim()) return
    setProcessing(true); setError('')
    const payload = {text:t, user_id:userId}
    console.log('[mvfe] POST /process payload=', payload)
    try {
      const r = await fetch(MVFE_BASE + '/process', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify(payload)
      })
      const respText = await r.text()
      console.log('[mvfe] POST /process status=', r.status, 'body=', respText.slice(0,500))
      if (!r.ok) {
        let msg = '请求失败'
        try {
          const j = JSON.parse(respText)
          if (Array.isArray(j.detail)) {
            msg = j.detail.map(e => `${e.loc?.join('.') || ''}: ${e.msg}`).join('; ')
          } else if (typeof j.detail === 'string') {
            msg = j.detail
          } else if (j.detail) {
            msg = JSON.stringify(j.detail)
          } else if (j.error) {
            msg = j.error
          }
        } catch {}
        throw new Error(msg)
      }
      const d = JSON.parse(respText)
      setLastResult(d); setInputText(''); setActiveView('dashboard'); await loadData()
    } catch(err) { setError(err.message) }
    finally { setProcessing(false) }
  }

  const d = dashboardData || {}
  const hasData = (d.data_points || 0) > 0
  const latest = hasData ? (d.formation_curve||[])[d.formation_curve.length-1] : null

  return (
    <div style={s.page}>
      <div style={s.header}>
        <button onClick={onBack} style={s.back}>&larr;</button>
        <div style={{flex:1}}>
          <div style={s.title}>灵镜观心</div>
          <div style={s.subtitle}>
            <span>🧬 HIDOS 人格形成动态观测仪</span>
            {d.is_mock && <span style={{color:'#ffa94d',marginLeft:8}}>⚡ 预览数据</span>}
          </div>
        </div>
        <button onClick={()=>setActiveView(activeView==='dashboard'?'input':'dashboard')} style={s.btnPrimary}>
          {activeView==='dashboard'?'📝 记录心声':'📊 返回仪表盘'}
        </button>
      </div>

      {activeView==='input' && (
        <div style={{flex:1,overflow:'auto',padding:16}}>
          <div style={s.desc}>描述此刻的内心状态、正在思考的事情、或面临的选择。<br/>系统将自动提取情绪、注意力、决策驱动，并计算你的人格塑造轨迹。</div>
          <div style={{display:'flex',flexWrap:'wrap',gap:8,marginBottom:14}}>
            {QUICK.map((q,i)=> (
              <button key={i} onClick={()=>{setInputText(q.t);handleProcess(q.t)}} style={s.chip}>{q.e} {q.l}</button>
            ))}
          </div>
          <textarea value={inputText} onChange={e=>setInputText(e.target.value)} placeholder="或者，在这里自由写下你的感受..."
            style={s.textarea} />
          <button onClick={()=>handleProcess()} disabled={processing||!inputText.trim()} style={s.analyzeBtn(processing)}>
            {processing?'⏳ 分析中...':'🔬 灵镜分析'}
          </button>
          {error && <div style={s.errorBox}>{error}</div>}
        </div>
      )}

      {activeView==='dashboard' && (
        <div style={{flex:1,overflow:'auto'}}>
          {loading ? (
            <div style={s.center}><div style={{fontSize:36,marginBottom:14}}>🧬</div><div style={{fontSize:14}}>正在加载人格动态数据...</div></div>
          ) : !hasData && !lastResult ? (
            <div style={s.center}><div style={{fontSize:48,marginBottom:14}}>🔮</div><div style={{fontSize:16,fontWeight:600}}>暂无观心记录</div><div style={{fontSize:13,color:'rgba(255,255,255,0.25)',marginTop:8}}>点击右上角“记录心声”，开启第一次人格观测</div></div>
          ) : (
            <div style={{padding:12,display:'flex',flexDirection:'column',gap:12}}>
              <div style={s.grid4}>
                <Kpi icon="🎭" label="情绪" v={EMOTION_NAMES[lastResult?.emotion?.primary_emotion]||lastResult?.emotion?.primary_emotion||'—'}
                  sub={(lastResult?.emotion?.secondary_emotions||[]).slice(0,2).map(e=>EMOTION_NAMES[e]||e).join('， ')||''} color={C[lastResult?.emotion?.primary_emotion]||'#868e96'} />
                <Kpi icon="👁" label="注意力" v={FOCUS_NAMES[lastResult?.attention?.focus]||lastResult?.attention?.focus||'—'}
                  sub={'固化 '+((lastResult?.attention?.fixation_score||0)*100).toFixed(0)+'%'} color="#4facfe" />
                <Kpi icon="⚖️" label="决策" v={lastResult?.decision?.type==='approach'?'趋近':'回避'}
                  sub={'恐惧 '+((lastResult?.decision?.drivers?.fear||0)*100).toFixed(0)+'%'} color={lastResult?.decision?.type==='approach'?'#51cf66':'#ff6b6b'} />
                <Kpi icon="🧬" label="形成度" v={latest?(latest.formation_score*100).toFixed(0)+'%':'—'}
                  sub={'漂移 '+((latest?.drift_score||0)*100).toFixed(0)+'%'} color="#ffa94d" />
              </div>
              <div style={s.grid2}>
                <Card t="形成度仪表盘" i="🧭"><Gauge score={latest?.formation_score||0} drift={latest?.drift_score||0} stab={lastResult?.formation?.stability_score||0}/></Card>
                <Card t="决策驱动因素" i="🔥"><Drivers d={lastResult?.decision?.drivers||{fear:0,ego:0,love:0}}/></Card>
              </div>
              <div style={s.grid2}>
                <Card t="情绪时间线" i="📈"><EmoChart data={d.emotion_series||[]}/></Card>
                <Card t="注意力分配" i="🎯"><AttBars data={d.attention_map||(lastResult?.attention?{[FOCUS_NAMES[lastResult.attention.focus]||lastResult.attention.focus]:lastResult.attention.fixation_score}:{})}/></Card>
              </div>
              <Card t="实时因果链" i="🔗"><Chain r={lastResult}/></Card>
              <div style={s.grid2}>
                <Card t="灵镜洞察" i="💡"><Insight r={lastResult}/></Card>
                <Card t="形成回路检测" i="🔄"><LoopCard g={lastResult?.graph_insight}/></Card>
              </div>
              <Card t="决策模式流" i="⚖️"><DecFlow data={d.decision_flow||[]}/></Card>
              <div style={{fontSize:9,color:'rgba(255,255,255,0.15)',textAlign:'center',padding:8,lineHeight:1.6}}>本仪表盘仅展示观测性模式，不构成心理诊断、人格评估或行为处方。</div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function Card({t,i,children}){
  return <div style={s.card}><div style={{display:'flex',alignItems:'center',gap:6,marginBottom:10}}><span style={{fontSize:14}}>{i}</span><span style={{fontSize:12,fontWeight:700,color:'rgba(255,255,255,0.85)'}}>{t}</span></div><div>{children}</div></div>
}
function Kpi({icon,label,v,sub,color}){
  return <div style={s.kpi}><div style={{fontSize:20,marginBottom:4}}>{icon}</div><div style={{fontSize:10,color:'rgba(255,255,255,0.35)',marginBottom:2}}>{label}</div><div style={{fontSize:14,fontWeight:700,color}}>{v}</div>{sub&&<div style={{fontSize:9,color:'rgba(255,255,255,0.3)',marginTop:2}}>{sub}</div>}</div>
}
function Gauge({score,drift,stab}){
  const pct=Math.max(0,Math.min(1,score))*100, dpct=Math.max(0,Math.min(1,drift))*100
  const r=42,cx=56,cy=56,circ=2*Math.PI*r,off=circ*(1-pct/100)
  return <div style={{display:'flex',alignItems:'center',gap:14}}>
    <svg viewBox="0 0 112 80" style={{width:110,flexShrink:0}}>
      <path d={"M "+(cx-r)+" "+cy+" A "+r+" "+r+" 0 1 1 "+(cx+r)+" "+cy} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" strokeLinecap="round"/>
      <path d={"M "+(cx-r)+" "+cy+" A "+r+" "+r+" 0 1 1 "+(cx+r)+" "+cy} fill="none" stroke="#4facfe" strokeWidth="8" strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={off}/>
      <text x={cx} y={cy+5} fill="#fff" fontSize="16" fontWeight="700" textAnchor="middle">{pct.toFixed(0)}</text>
      <text x={cx} y={cy+18} fill="rgba(255,255,255,0.3)" fontSize="7" textAnchor="middle">形成度</text>
    </svg>
    <div style={{flex:1,display:'flex',flexDirection:'column',gap:6}}>
      <Bar l="形成度" v={pct} c="#4facfe"/>
      <Bar l="漂移信号" v={dpct} c={dpct>30?'#ff6b6b':'#ffa94d'}/>
      <Bar l="稳定性" v={(stab*100).toFixed(0)} c="#51cf66"/>
    </div>
  </div>
}
function Bar({l,v,c}){
  return <div><div style={{display:'flex',justifyContent:'space-between',marginBottom:3}}><span style={{fontSize:10,color:'rgba(255,255,255,0.4)'}}>{l}</span><span style={{fontSize:10,color:c,fontWeight:600}}>{v}%</span></div><div style={{height:5,borderRadius:3,background:'rgba(255,255,255,0.05)',overflow:'hidden'}}><div style={{width:Math.min(100,Math.max(0,v))+'%',height:'100%',borderRadius:3,background:c,transition:'width 0.8s ease'}}/></div></div>
}
function Drivers({d}){
  const items=[{k:'fear',l:'恐惧驱动',c:'#ff6b6b',e:'\ud83d\ude28'},{k:'ego',l:'自我驱动',c:'#ffa94d',e:'\ud83e\udd9a'},{k:'love',l:'关系驱动',c:'#ff8787',e:'\u2764\uFE0F'}]
  return <div style={{display:'flex',flexDirection:'column',gap:10}}>{items.map(({k,l,c,e})=>{
    const v=(d[k]||0)*100
    return <div key={k} style={{display:'flex',alignItems:'center',gap:8}}><span style={{fontSize:14,width:20,textAlign:'center'}}>{e}</span><div style={{flex:1}}><div style={{display:'flex',justifyContent:'space-between',marginBottom:3}}><span style={{fontSize:11,color:'rgba(255,255,255,0.6)'}}>{l}</span><span style={{fontSize:11,color:c,fontWeight:600}}>{v.toFixed(0)}%</span></div><div style={{height:8,borderRadius:4,background:'rgba(255,255,255,0.05)',overflow:'hidden'}}><div style={{width:v.toFixed(0)+'%',height:'100%',borderRadius:4,background:c,opacity:0.85,transition:'width 0.8s ease'}}/></div></div></div>
  })}</div>
}
function EmoChart({data}){
  if(!data||data.length<2) return <div style={s.noData}>暂无历史数据</div>
  const w=280,h=100,pl=10,pr=10,pt=8,pb=18,cw=w-pl-pr,ch=h-pt-pb,n=data.length
  const x=i=>pl+(i/(n-1))*cw, y=v=>pt+(1-v)*ch
  return <svg viewBox={"0 0 "+w+" "+h} style={{width:'100%',height:'auto'}}>
    {[0,0.5,1].map(t=><line key={t} x1={pl} y1={y(t)} x2={w-pr} y2={y(t)} stroke="rgba(255,255,255,0.05)" strokeWidth="1" strokeDasharray="2,2"/>)}
    {data.map((d,i)=><g key={i}><circle cx={x(i)} cy={y(d.intensity||0.5)} r="4" fill={C[d.primary_emotion]||'#868e96'} opacity="0.9"/><circle cx={x(i)} cy={y(d.intensity||0.5)} r="7" fill="none" stroke={C[d.primary_emotion]||'#868e96'} opacity="0.25" strokeWidth="1"/></g>)}
    {data.slice(0,n-1).map((d,i)=><line key={i} x1={x(i)} y1={y(d.intensity||0.5)} x2={x(i+1)} y2={y(data[i+1].intensity||0.5)} stroke="rgba(255,255,255,0.1)" strokeWidth="1.5"/>)}
    <text x={pl} y={h-4} fill="rgba(255,255,255,0.2)" fontSize="7" textAnchor="start">{data[0].timestamp?new Date(data[0].timestamp).toLocaleDateString('zh-CN',{month:'short',day:'numeric'}):''}</text>
    <text x={w-pr} y={h-4} fill="rgba(255,255,255,0.2)" fontSize="7" textAnchor="end">{data[n-1].timestamp?new Date(data[n-1].timestamp).toLocaleDateString('zh-CN',{month:'short',day:'numeric'}):''}</text>
  </svg>
}
function AttBars({data}){
  const e=Object.entries(data).sort((a,b)=>b[1]-a[1])
  if(e.length===0) return <div style={s.noData}>暂无数据</div>
  const mx=Math.max(...e.map(x=>x[1]),0.01)
  return <div style={{display:'flex',flexDirection:'column',gap:8}}>{e.slice(0,5).map(([focus,val])=>{
    const pct=(val/mx)*100, c=val>0.3?'#ff6b6b':val>0.15?'#ffa94d':'#4facfe'
    const label=FOCUS_NAMES[focus]||focus
    return <div key={focus}><div style={{display:'flex',justifyContent:'space-between',marginBottom:2}}><span style={{fontSize:11,color:'rgba(255,255,255,0.6)'}}>{label}</span><span style={{fontSize:11,color:c,fontWeight:600}}>{(val*100).toFixed(0)}%</span></div><div style={{height:5,borderRadius:3,background:'rgba(255,255,255,0.04)',overflow:'hidden'}}><div style={{width:pct+'%',height:'100%',borderRadius:3,background:c,opacity:0.8,transition:'width 0.6s'}}/></div></div>
  })}</div>
}
function Chain({r}){
  if(!r) return <div style={s.noData}>提交分析后显示实时因果链</div>
  const em=r.emotion||{}, at=r.attention||{}, de=r.decision||{}, fo=r.formation||{}
  const nodes=[
    {l:EMOTION_NAMES[em.primary_emotion]||em.primary_emotion||'情绪',v:((em.intensity||0)*100).toFixed(0)+'%',c:C[em.primary_emotion]||'#ffa94d',s:(em.secondary_emotions||[]).slice(0,2).map(e=>EMOTION_NAMES[e]||e).join('， ')||''},
    {l:FOCUS_NAMES[at.focus]||at.focus||'注意力',v:((at.fixation_score||0)*100).toFixed(0)+'% 固化',c:'#4facfe',s:'漂移 '+((at.drift_risk||0)*100).toFixed(0)+'%'},
    {l:de.type==='approach'?'趋近':'回避',v:'恐惧 '+((de.drivers?.fear||0)*100).toFixed(0)+'%',c:de.type==='approach'?'#51cf66':'#ff6b6b',s:'自我 '+((de.drivers?.ego||0)*100).toFixed(0)+'%'},
    {l:'形成',v:((fo.formation_score||0)*100).toFixed(0)+'%',c:'#ffa94d',s:'漂移 '+((fo.drift_score||0)*100).toFixed(0)+'%'},
  ]
  return <div style={{display:'flex',alignItems:'center',gap:6,flexWrap:'wrap',justifyContent:'center',padding:'4px 0'}}>{nodes.map((n,i)=><div key={i} style={{display:'flex',alignItems:'center',gap:6}}><div style={{padding:'8px 12px',borderRadius:10,background:n.c+'15',border:'1px solid '+n.c+'40',textAlign:'center',minWidth:72}}><div style={{fontSize:10,color:'rgba(255,255,255,0.4)',marginBottom:2}}>{n.l}</div><div style={{fontSize:12,fontWeight:700,color:n.c}}>{n.v}</div>{n.s&&<div style={{fontSize:8,color:'rgba(255,255,255,0.25)',marginTop:1}}>{n.s}</div>}</div>{i<nodes.length-1&&<span style={{fontSize:16,color:'rgba(255,255,255,0.1)'}}>→</span>}</div>)}</div>
}
function Insight({r}){
  if(!r) return <div style={s.noData}>暂无洞察</div>
  const ref=r.reflection||{}
  return <div style={{display:'flex',flexDirection:'column',gap:8}}>
    <div style={{fontSize:12,color:'rgba(255,255,255,0.75)',lineHeight:1.7}}>{ref.state_interpretation||'暂无状态解读'}</div>
    {ref.loop_detection && ref.loop_detection!=='No clear loop detected.' && ref.loop_detection!=='未检测到明显回路' && <div style={{fontSize:11,color:'#ffa94d',padding:'6px 10px',borderRadius:8,background:'rgba(255,169,77,0.06)',borderLeft:'2px solid rgba(255,169,77,0.4)'}}>🔄 {ref.loop_detection}</div>}
    <div style={{marginTop:2,padding:10,borderRadius:10,background:'rgba(79,172,254,0.05)',borderLeft:'2px solid rgba(79,172,254,0.25)'}}>
      <span style={{fontSize:10,color:'#4facfe',fontWeight:600}}>💡 反射问题</span>
      <div style={{fontSize:13,color:'#a0d4f7',fontStyle:'italic',marginTop:5}}>{ref.reflective_question||'此刻，什么在你里面最活跃？'}</div>
    </div>
    {ref.bible_verse_hint && <div style={{marginTop:2,padding:10,borderRadius:10,background:'rgba(255,193,7,0.05)',borderLeft:'2px solid rgba(255,193,7,0.25)'}}>
      <span style={{fontSize:10,color:'#ffc107',fontWeight:600}}>📖 应许锚点</span>
      <div style={{fontSize:12,color:'rgba(255,255,255,0.7)',marginTop:5,lineHeight:1.6}}>{ref.bible_verse_hint}</div>
    </div>}
  </div>
}
function LoopCard({g}){
  if(!g||!g.loop_detected) return <div style={{textAlign:'center',padding:'20px 10px'}}><div style={{fontSize:28,marginBottom:8}}>✅</div><div style={{fontSize:12,color:'#51cf66',fontWeight:600}}>未检测到形成回路</div><div style={{fontSize:11,color:'rgba(255,255,255,0.3)',marginTop:4}}>当前状态相对开放，无明显闭环</div></div>
  return <div style={{display:'flex',flexDirection:'column',gap:8}}>
    <div style={{fontSize:12,color:'#ffa94d',fontWeight:600}}>⚠️ {g.loop_type||'检测到形成回路'}</div>
    <div style={{fontSize:11,color:'rgba(255,255,255,0.45)',lineHeight:1.6}}>回路强度: {((g.loop_strength||0)*100).toFixed(0)}%</div>
    {g.dominant_desires?.length>0 && <div style={{fontSize:10,color:'rgba(255,255,255,0.3)'}}>核心渴望: {g.dominant_desires.join(', ')}</div>}
    {g.core_beliefs?.length>0 && <div style={{fontSize:10,color:'rgba(255,255,255,0.3)'}}>核心信念: {g.core_beliefs.join(', ')}</div>}
  </div>
}
function DecFlow({data}){
  if(!data||data.length===0) return <div style={s.noData}>暂无决策数据</div>
  const total=data.length, avoid=data.filter(d=>d.type==='avoidance').length, app=total-avoid, ar=total>0?avoid/total:0
  let lbl='平衡模式', col='#4facfe'
  if(ar>0.6){lbl='回避主导';col='#ff6b6b'}
  else if(ar<0.4){lbl='趋近主导';col='#51cf66'}
  return <div style={{display:'flex',alignItems:'center',gap:14}}>
    <div style={{flex:1,display:'flex',flexDirection:'column',gap:6}}>
      <div style={{display:'flex',gap:6,flexWrap:'wrap'}}>{[...data].reverse().slice(0,8).map((d,i)=><div key={i} style={{padding:'3px 8px',borderRadius:8,fontSize:10,fontWeight:600,background:d.type==='approach'?'rgba(81,207,102,0.12)':'rgba(255,107,107,0.12)',color:d.type==='approach'?'#51cf66':'#ff6b6b',border:'1px solid '+(d.type==='approach'?'rgba(81,207,102,0.2)':'rgba(255,107,107,0.2)')}}>{d.type==='approach'?'→':'↔'}</div>)}</div>
      <div style={{fontSize:11,color:col,fontWeight:600}}>{lbl} — {total} 次决策记录</div>
    </div>
    <div style={{width:80,textAlign:'center'}}>
      <svg viewBox="0 0 80 80" style={{width:70,height:70}}>
        <circle cx="40" cy="40" r="30" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="10"/>
        <circle cx="40" cy="40" r="30" fill="none" stroke="#51cf66" strokeWidth="10" strokeDasharray={2*Math.PI*30*app/total} strokeDashoffset={-2*Math.PI*30*avoid/total} transform="rotate(-90 40 40)"/>
        <circle cx="40" cy="40" r="30" fill="none" stroke="#ff6b6b" strokeWidth="10" strokeDasharray={2*Math.PI*30*avoid/total} transform="rotate(-90 40 40)"/>
        <text x="40" y="43" fill="#fff" fontSize="14" fontWeight="700" textAnchor="middle">{total}</text>
        <text x="40" y="54" fill="rgba(255,255,255,0.3)" fontSize="7" textAnchor="middle">决策</text>
      </svg>
    </div>
  </div>
}

const s = {
  page: {height:'100%',display:'flex',flexDirection:'column',background:'#060b14',overflow:'hidden',fontFamily:'-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif'},
  header: {padding:'14px 16px',display:'flex',alignItems:'center',gap:10,borderBottom:'1px solid rgba(255,255,255,0.06)',flexShrink:0,background:'rgba(255,255,255,0.015)'},
  back: {background:'none',border:'none',color:'#4facfe',fontSize:22,cursor:'pointer',padding:'2px 8px 2px 0'},
  title: {fontSize:16,fontWeight:700,color:'#fff',letterSpacing:'0.5px'},
  subtitle: {fontSize:10,color:'rgba(255,255,255,0.3)',marginTop:2,display:'flex',gap:8,alignItems:'center'},
  btnPrimary: {padding:'7px 16px',borderRadius:10,border:'1px solid rgba(79,172,254,0.25)',background:'rgba(79,172,254,0.08)',color:'#4facfe',fontSize:12,fontWeight:600,cursor:'pointer',whiteSpace:'nowrap'},
  desc: {fontSize:13,color:'rgba(255,255,255,0.6)',marginBottom:12,lineHeight:1.7},
  chip: {padding:'8px 14px',borderRadius:20,border:'1px solid rgba(255,255,255,0.08)',background:'rgba(255,255,255,0.03)',color:'rgba(255,255,255,0.7)',fontSize:12,cursor:'pointer',display:'flex',alignItems:'center',gap:6},
  textarea: {width:'100%',minHeight:90,padding:12,borderRadius:12,border:'1px solid rgba(255,255,255,0.08)',background:'rgba(255,255,255,0.025)',color:'#fff',fontSize:14,lineHeight:1.7,resize:'vertical',outline:'none'},
  analyzeBtn: (processing)=>({width:'100%',marginTop:10,padding:13,borderRadius:12,border:'none',background:processing?'rgba(79,172,254,0.15)':'linear-gradient(135deg,#4facfe 0%,#00f2fe 100%)',color:'#fff',fontSize:14,fontWeight:700,cursor:processing?'wait':'pointer',transition:'all 0.3s'}),
  errorBox: {marginTop:10,padding:'10px 14px',borderRadius:10,background:'rgba(255,50,50,0.06)',color:'#ff6b6b',fontSize:12,borderLeft:'3px solid #ff6b6b'},
  center: {textAlign:'center',padding:'80px 20px',color:'rgba(255,255,255,0.3)'},
  grid4: {display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:8},
  grid2: {display:'grid',gridTemplateColumns:'1fr 1fr',gap:10},
  card: {background:'rgba(255,255,255,0.02)',border:'1px solid rgba(255,255,255,0.05)',borderRadius:14,padding:12,display:'flex',flexDirection:'column'},
  kpi: {background:'rgba(255,255,255,0.02)',border:'1px solid rgba(255,255,255,0.05)',borderRadius:12,padding:10,textAlign:'center'},
  noData: {color:'rgba(255,255,255,0.2)',fontSize:12,textAlign:'center',padding:20},
}
