import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_db

from backend.discernment_platform.batch01_core import DiscernmentCase
from backend.discernment_platform.batch01_core.intake import normalize

FIXTURES = Path(__file__).parent / "fixtures"
SCHEMAS = Path(__file__).parents[2] / "discernment_platform" / "data" / "schemas" / "batch01"


def load_case(name: str) -> DiscernmentCase:
    return DiscernmentCase(**json.loads((FIXTURES / f"{name}.json").read_text("utf-8")))


@pytest.fixture
def influencer_case():
    return load_case("01_success_influencer")


@pytest.fixture
def self_control_case():
    return load_case("02_self_control")


@pytest.fixture
def scrupulosity_case():
    return load_case("03_scrupulosity_risk")


@pytest.fixture
def influencer_normalized(influencer_case):
    return normalize(influencer_case)


@pytest.fixture
def case_schema():
    return json.loads((SCHEMAS / "discernment_case.schema.json").read_text("utf-8"))


@pytest.fixture
def report_schema():
    return json.loads((SCHEMAS / "discernment_report.schema.json").read_text("utf-8"))
