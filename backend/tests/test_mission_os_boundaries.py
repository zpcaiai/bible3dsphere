"""Architecture guards for the Mission OS domain package."""

import ast
from pathlib import Path

from mission_os.subdomains import EXTERNAL_AGGREGATES, OWNED_AGGREGATES, SUBDOMAINS

ROOT = Path(__file__).parents[1]
DOMAIN = ROOT / "mission_os"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_domain_has_all_canonical_subdomains_and_no_owned_external_overlap():
    assert len(SUBDOMAINS) == 12
    assert OWNED_AGGREGATES.isdisjoint(EXTERNAL_AGGREGATES)
    assert {"User", "GiftProfile", "FormationPlan"} <= EXTERNAL_AGGREGATES


def test_domain_does_not_depend_on_framework_database_or_ai_provider():
    forbidden = ("fastapi", "sqlalchemy", "psycopg", "openai", "anthropic")
    violations = []
    for path in DOMAIN.glob("*.py"):
        for module in _imports(path):
            if module.startswith(forbidden):
                violations.append(f"{path.name}: {module}")
    assert violations == []


def test_ai_and_router_layers_do_not_live_in_domain_package():
    names = {path.name for path in DOMAIN.iterdir()}
    assert not {"router.py", "models.py", "agents.py"} & names
