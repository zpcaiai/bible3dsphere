from pathlib import Path
from routers.mission_bridge_localization import REQUIRED_REVIEWS,localization_publishable
def test_localization_requires_three_human_reviews():assert not localization_publishable({'human_translation'}) and localization_publishable(REQUIRED_REVIEWS)
def test_core_languages_audio_linkage_and_narrator_rights():
 sql=(Path(__file__).parents[1]/'migrations'/'0182_mission_bridge_localization.sql').read_text()
 for locale in ('zh-CN','zh-TW','en'):assert locale in sql
 assert 'text_version_id' in sql and 'attribution_choice' in sql and 'license TEXT NOT NULL' in sql
 assert 'model_training_consent BOOLEAN NOT NULL DEFAULT FALSE' in sql and '不把汉语标准版本强制视为唯一正确表达' in sql
