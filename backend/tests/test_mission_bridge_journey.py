from pathlib import Path
from routers.mission_bridge import CarePlanBody,GoalBody

def test_goal_and_care_plan_contracts_require_explainability():
 goal=GoalBody(title='建立可信任关系',successDescription='每周能主动联系一位可信任同伴')
 plan=CarePlanBody(title='第一阶段',rationale='基于参与者确认的关系目标',actions=[{'title':'联系同伴','suggestionReason':'参与者把孤立列为当前主要困难'}])
 assert goal.title and plan.actions[0]['suggestionReason']

def test_journey_schema_restricts_sensitive_notes():
 sql=(Path(__file__).parents[1]/'migrations'/'0158_mission_bridge_participant_journey.sql').read_text(encoding='utf-8')
 assert "sensitivity IN('normal','restricted','safeguarding')" in sql
 assert 'participant_confirmed_at' in sql
 assert 'suggestion_reason' in sql
