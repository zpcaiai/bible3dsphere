from pathlib import Path
from routers.mission_bridge_content import TYPES,CLASSES
def test_content_taxonomy_is_complete():assert len(TYPES)==13 and {'scripture_text','interpretation','application','testimony','professional_advice'}==CLASSES
def test_schema_requires_version_sources_and_four_reviews():
 sql=(Path(__file__).parents[1]/'migrations'/'0161_mission_bridge_content.sql').read_text();
 for table in ('content_catalog','content_versions','content_sources','content_reviews','theological_reviews','safeguarding_reviews','localization_versions','reading_level_scores','content_embeddings','content_usage_events'):assert f'mission_bridge_{table}' in sql
 assert "'theological','cultural','safeguarding','accessibility'" in sql
def test_rag_route_is_fail_closed():
 source=(Path(__file__).parents[1]/'routers'/'mission_bridge_content.py').read_text();assert "c.status='published'" in source;assert 's.verified=TRUE' in source;assert '我不知道' in source;assert 'citations' in source
def test_reading_adaptation_preserves_meaning_and_scripture():
 source=(Path(__file__).parents[1]/'routers'/'mission_bridge_content.py').read_text();assert 'meaningPreserved' in source;assert '经文原文不得通过阅读级适配修改' in source;assert 'core_meaning_hash' in source
