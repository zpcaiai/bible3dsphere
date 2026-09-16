"""JSON Schema conformance for both shipped schemas."""

import json

from jsonschema import Draft202012Validator

from backend.discernment_platform.batch01_core import DiscernmentCase, DiscernmentOrchestrator
from backend.discernment_platform.batch01_core.intake import normalize


def test_all_fixtures_validate_against_case_schema(case_schema):
    validator = Draft202012Validator(case_schema)
    for name in ("01_success_influencer", "02_self_control", "03_scrupulosity_risk"):
        from backend.tests.batch01_core.conftest import FIXTURES

        data = json.loads((FIXTURES / f"{name}.json").read_text("utf-8"))
        validator.validate(data)


def test_case_model_roundtrips_through_schema(influencer_case, case_schema):
    Draft202012Validator(case_schema).validate(influencer_case.model_dump(mode="json"))


def test_report_validates_against_report_schema(influencer_case, report_schema):
    result = DiscernmentOrchestrator().run(influencer_case)
    Draft202012Validator(report_schema).validate(result["report"])


def test_report_schema_requires_all_declared_sections(report_schema, influencer_case):
    result = DiscernmentOrchestrator().run(influencer_case)
    for key in report_schema["required"]:
        assert key in result["report"]


def test_normalized_case_is_json_serialisable(influencer_case):
    json.dumps(normalize(influencer_case).model_dump(mode="json"), ensure_ascii=False)


def test_both_schemas_are_valid_draft_2020_12(case_schema, report_schema):
    Draft202012Validator.check_schema(case_schema)
    Draft202012Validator.check_schema(report_schema)
