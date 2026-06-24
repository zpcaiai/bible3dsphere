"""Regression guard for the psycopg2 list-adapter footgun.

Background: the app used to globally register ``register_adapter(list, Json)``,
which silently turned any Python ``list`` passed to ``= ANY(%s)`` / ``IN %s``
into a JSON string ("malformed array literal") — a failure that was then
swallowed by surrounding ``except`` blocks. We removed that global adapter and
standardized on ``col IN %s`` + ``tuple(...)`` for multi-value filters, and
explicit ``json.dumps(...)`` / ``psycopg2.extras.Json(...)`` for JSONB writes.

These static checks lock the invariants in so the footgun cannot return:
  1. No runtime SQL uses ``= ANY(%s)`` (use ``IN %s`` + ``tuple(...)``).
  2. No raw Python list literal is passed as a single ``execute()`` param value.

They are pure source scans (no DB needed) — marked ``no_db``.
"""
import ast
import os

import pytest

pytestmark = pytest.mark.no_db

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Offline/dev scripts and generated migrations may legitimately build raw SQL.
SKIP = ("/migrations", "/.git", "/tests", "/scripts", "/__pycache__", "/mvfe/db")


def _runtime_py_files():
    for root, _dirs, files in os.walk(BACKEND):
        if any(seg in root for seg in SKIP):
            continue
        for fn in files:
            if fn.endswith(".py"):
                yield os.path.join(root, fn)


def test_no_any_s_in_runtime_sql():
    """`= ANY(%s)` with a list param is broken by psycopg2 adaptation."""
    offenders = []
    for path in _runtime_py_files():
        src = open(path, encoding="utf-8").read()
        if "ANY(%s)" in src:
            offenders.append(os.path.relpath(path, BACKEND))
    assert not offenders, (
        "Use `col IN %s` with a tuple() instead of `= ANY(%s)`; list params get "
        f"JSON-adapted and fail at runtime. Offending files: {offenders}"
    )


def test_no_raw_list_literal_execute_param():
    """A raw list literal as an execute() value would need explicit Json()."""
    offenders = []
    for path in _runtime_py_files():
        try:
            tree = ast.parse(open(path, encoding="utf-8").read())
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "execute"
                and len(node.args) >= 2
            ):
                params = node.args[1]
                elts = params.elts if isinstance(params, (ast.Tuple, ast.List)) else []
                if any(isinstance(e, ast.List) for e in elts):
                    offenders.append(f"{os.path.relpath(path, BACKEND)}:{node.lineno}")
    assert not offenders, (
        "Wrap JSONB list values in json.dumps(...) / Json(...); don't pass a raw "
        f"list literal as an execute() param. Offending: {offenders}"
    )
