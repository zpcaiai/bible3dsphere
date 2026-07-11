#!/usr/bin/env python3
"""Generate a small Mission OS application-module skeleton.

The generator refuses to overwrite files. A migration placeholder is emitted
outside the real migration sequence so a developer must review and number it.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

NAME = re.compile(r"^[a-z][a-z0-9_]{1,62}$")

TEMPLATES = {
    "domain.py": '"""{title} domain model; framework independent."""\n',
    "repository.py": '"""{title} repository port."""\n\nfrom typing import Protocol\n\nclass Repository(Protocol):\n    pass\n',
    "service.py": '"""{title} application service."""\n',
    "schemas.py": '"""{title} public schemas."""\n',
    "test_domain.py": '"""Tests for {title}."""\n\ndef test_module_imports():\n    assert True\n',
    "migration.sql.todo": '-- Review, number, add tenant_id/created_at/updated_at, indexes, RLS, and rollback for {title}.\n',
}


def generate(root: Path, name: str) -> list[Path]:
    if not NAME.fullmatch(name):
        raise ValueError("name must be lower snake_case")
    target = root / name
    target.mkdir(parents=True, exist_ok=True)
    created = []
    for filename, template in TEMPLATES.items():
        path = target / filename
        if path.exists():
            raise FileExistsError(path)
        path.write_text(template.format(title=name.replace("_", " ").title()), encoding="utf-8")
        created.append(path)
    return created


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("--root", type=Path, default=Path("backend/mission_os/modules"))
    args = parser.parse_args()
    for path in generate(args.root, args.name):
        print(path)


if __name__ == "__main__":
    main()
