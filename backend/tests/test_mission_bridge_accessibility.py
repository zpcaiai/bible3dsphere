from pathlib import Path
from routers.mission_bridge_accessibility import FORMATS,STANDARDS
def test_six_accessible_formats_and_wcag_standards():assert len(FORMATS)==6 and 'sign_language_video' in FORMATS and 'WCAG 2.2 AA' in STANDARDS and '200%字号' in STANDARDS
def test_disabled_people_can_review_author_and_lead():
 sql=(Path(__file__).parents[1]/'migrations'/'0172_mission_bridge_accessibility.sql').read_text()
 assert 'mission_bridge_disability_user_reviews' in sql and 'mission_bridge_accessible_contributors' in sql
 for role in ('author','facilitator','reviewer','leader'):assert role in sql
 assert 'caption_url' in sql and 'audio_description' in sql and 'low_bandwidth_bytes' in sql
