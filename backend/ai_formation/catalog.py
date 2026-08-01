"""Non-content registry for the bounded Sunday School AI formation module."""

MODULE_MANIFEST = {
    "moduleId": "sunday_school.ai_formation",
    "version": "1.0.0",
    "status": "release_candidate",
    "route": "/sunday-school/ai-formation",
    "title": {
        "zh-CN": "AI时代心意更新与家庭门训",
        "en": "Renewing the Mind in the AI Age",
    },
    "summary": {
        "zh-CN": "在AI和注意力经济中操练分辨、真实关系与家庭门训。",
        "en": "Practice discernment, embodied faithfulness, and family discipleship in the AI age.",
    },
    "tracks": [
        "adult_self_governance",
        "parent_family_discipleship",
        "child_youth_formation",
        "teacher_pastoral_support",
    ],
    "theologicalProfile": "historic_christian_core_v1",
    "safetyPolicyVersion": "1.0.0",
    "featureFlag": "sundaySchoolAiFormation",
    "teacherPermission": "sunday_school.ai_formation.manage",
    "analyticsNamespace": "sunday_school.ai_formation",
}

TRACKS = [
    {
        "id": "adult_self_governance",
        "title": {"zh-CN": "成人自我治理", "en": "Adult self-governance"},
        "batchIds": ["01", "02", "03", "04"],
    },
    {
        "id": "parent_family_discipleship",
        "title": {"zh-CN": "父母与家庭门训", "en": "Parent and family discipleship"},
        "batchIds": ["05", "06"],
    },
    {
        "id": "child_youth_formation",
        "title": {"zh-CN": "儿童青少年形成", "en": "Child and youth formation"},
        "batchIds": ["07", "08"],
    },
    {
        "id": "teacher_pastoral_support",
        "title": {"zh-CN": "教师与牧养支持", "en": "Teacher and pastoral support"},
        "batchIds": ["09", "10", "11", "12"],
    },
]

_BATCH_TITLES = (
    ("01", "模块基础、神学护栏、领域模型与牧养安全契约", "foundation"),
    ("02", "攻克己身、注意力治理与数字属灵操练", "adult"),
    ("03", "AI认知外包、算法世界观与属灵分辨", "discernment"),
    ("04", "身份、欲望、性与虚拟亲密分辨及恢复", "identity_intimacy_recovery"),
    ("05", "父母先被塑造：榜样、焦虑、认罪修复与权柄", "parent_formation"),
    ("06", "家庭注意力生态、数字公约与家庭AI公约", "family_attention_covenant"),
    ("07", "0-6岁与7-12岁儿童形成", "child_formation"),
    ("08", "13-15岁与16-18岁青少年自治交还", "youth_autonomy"),
    ("09", "课程、课时、教师讲义与审核发布引擎", "curriculum_teacher_engine"),
    ("10", "情境模拟、后果、恩典、修复与苏格拉底运行时", "scenario_runtime"),
    ("11", "Formation Twin纵向成长回顾", "formation_twin"),
    ("12", "生产认证、治理、红队、隐私与发布证据", "production_certification"),
)

BATCHES = [
    {
        "id": batch_id,
        "moduleKey": f"sunday_school.ai_formation.{module_key}",
        "title": {"zh-CN": title},
        "implementationStatus": "release_candidate",
        "contentReviewStatus": "review_pending",
        "learnerContentAvailable": False,
    }
    for batch_id, title, module_key in _BATCH_TITLES
]

RELEASE_GATES = (
    "theology",
    "pastoral_safety",
    "child_safety",
    "privacy_security",
    "tenant_isolation",
    "accessibility_automated",
    "accessibility_manual",
    "content_quality",
    "skill_evals",
    "rollback_rehearsal",
)
