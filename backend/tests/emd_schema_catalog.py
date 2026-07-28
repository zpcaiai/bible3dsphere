"""Thin re-export of `core.schema_catalog` so test modules keep their short import.

The parsing itself lives in production code because `emotional_maturity_privacy_assessment`
needs the same catalog to build its data inventory — and a privacy inventory built by a
second, subtly different parser is the worst possible place for drift. There is one parser.
"""
from core.schema_catalog import (  # noqa: F401
    catalog,
    columns_of,
    emd_tables,
    split_top_level,
    tables_with,
)
