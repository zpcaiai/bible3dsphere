BEGIN;
INSERT INTO mission_bridge_program_definitions(id,group_type,title,description,active_version,status) VALUES
('driver-audio-7','mobile_worker','司机7分钟音频同行','面向流动劳动者的驾驶安全、低交互、异步音频支持项目。','1.0.0','published'),
('caregiver-support','elder_caregiver','照护者也需要被照护','为失能失智老人家庭照护者提供压力支持、短时替代照护和专业资源。','1.0.0','published'),
('church-harm-recovery','church_harm_survivor','信仰重建与安全对话','为离开教会或经历教会伤害的人提供化名、独立、可自主退出的恢复路径。','1.0.0','published') ON CONFLICT(id) DO NOTHING;
INSERT INTO mission_bridge_program_versions(program_id,version,definition,safeguarding_profile) VALUES
('driver-audio-7','1.0.0','{"durationWeeks":8,"sessionMode":"async","voluntary":true,"steps":8,"audioMinutes":[3,5,7],"drivingMode":"audio_only","fixedDailyCheckin":false}'::jsonb,'{"noCoercion":true,"professionalReferral":true,"noDrivingTextInput":true,"cityLocationOnly":true}'::jsonb),
('caregiver-support','1.0.0','{"durationWeeks":8,"sessionMode":"hybrid","voluntary":true,"steps":8,"features":["stress_assessment","support_group","respite","grief","referrals"]}'::jsonb,'{"noCoercion":true,"professionalReferral":true,"noDiagnosis":true,"humanEscalation":true}'::jsonb),
('church-harm-recovery','1.0.0','{"durationWeeks":6,"sessionMode":"hybrid","voluntary":true,"steps":6,"pseudonymAllowed":true,"participantLed":true}'::jsonb,'{"noCoercion":true,"professionalReferral":true,"independentReview":true,"noOriginalChurchAccess":true}'::jsonb) ON CONFLICT(program_id,version) DO NOTHING;
COMMIT;
