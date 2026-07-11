from __future__ import annotations
import hashlib
from typing import Any

AGENTS={
 'intake':{'label':'Intake Agent','human':False},'program_recommendation':{'label':'Program Recommendation Agent','human':False},
 'content_adaptation':{'label':'Content Adaptation Agent','human':False},'facilitator_copilot':{'label':'Facilitator Copilot','human':False},
 'follow_up_planner':{'label':'Follow-up Planner','human':True},'risk_triage':{'label':'Risk Triage Agent','human':True},
 'referral_assistant':{'label':'Referral Assistant','human':False},'quality_audit':{'label':'Quality Audit Agent','human':False},
}
RISK_TERMS={'L3':('自杀','杀死','立即伤害','immediate danger','suicide'),'L2':('虐待','家暴','严重抑郁','abuse','violence'),'L1':('焦虑','孤独','压力','anxious','lonely')}
COERCION=('必须信','不信就','上帝惩罚你','must convert')
STIGMA=('疯子','精神病都是','残障是因为犯罪')

def input_hash(text:str)->str:return hashlib.sha256(text.strip().encode()).hexdigest()
def risk_scan(text:str,current:str='L0')->tuple[str,list[str]]:
 order={'L0':0,'L1':1,'L2':2,'L3':3};detected='L0';flags=[];lower=text.lower()
 for level,terms in RISK_TERMS.items():
  if any(term in lower for term in terms):detected=level;flags.append(f'risk:{level}');break
 return (current if order[current]>=order[detected] else detected),flags
def quality_flags(text:str)->list[str]:
 lower=text.lower();flags=[]
 if any(x in lower for x in COERCION):flags.append('coercive_language')
 if any(x in lower for x in STIGMA):flags.append('stigmatizing_language')
 return flags
def orchestrate(agent_key:str,text:str,goal:str|None=None,programs:list[dict[str,Any]]|None=None,referrals:list[dict[str,Any]]|None=None,current_risk:str='L0')->dict[str,Any]:
 if agent_key not in AGENTS:raise ValueError('unknown_agent')
 risk,flags=risk_scan(text,current_risk);flags+=quality_flags(text)
 output={'agent':agent_key,'summary':text[:500].strip(),'recommendations':[],'reasons':[],'citations':[],'riskLevel':risk,'requiresHumanReview':risk in ('L2','L3') or AGENTS[agent_key]['human'],'autoSend':False,'boundaries':['不提供诊断','不自动报名','不替代真人或专业人员']}
 if agent_key=='program_recommendation':
  selected=(programs or [])[:3];output['recommendations']=[{'programId':p['id'],'title':p['title']} for p in selected];output['reasons']=[f"与用户明确目标相关：{goal or '待与用户确认'}" for _ in selected]
 if agent_key=='content_adaptation':output['recommendations']=['仅调整长度、语言难度或媒介形式；经文原文保持不变']
 if agent_key=='facilitator_copilot':output['recommendations']=['开放式问题','敏感点提醒','预留倾听与休息时间']
 if agent_key=='follow_up_planner':output['recommendations']=['同工审核后再联系','由参与者确认下一步'];output['requiresHumanReview']=True
 if agent_key=='risk_triage':output['recommendations']=['L2/L3 转真人处理' if risk in ('L2','L3') else '维持支持并观察'];output['requiresHumanReview']=risk in ('L2','L3')
 if agent_key=='referral_assistant':output['recommendations']=[{**r,'disclaimer':'请自行确认当前接收能力'} for r in (referrals or []) if r.get('verified')][:3]
 if agent_key=='quality_audit':output['recommendations']=['人工复核发现的强迫、无来源事实、隐私或污名化风险'];output['safetyFindings']=flags
 return {'output':output,'riskLevel':risk,'safetyFlags':flags}
