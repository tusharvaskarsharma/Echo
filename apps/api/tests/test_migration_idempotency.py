"""Guardrails for migrations that may be retried after an interrupted deploy."""

import re
from pathlib import Path


MIGRATIONS_DIR = Path("app/db/migrations")


def _files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def test_schema_objects_use_idempotent_creation_forms() -> None:
    """A database that has already received a migration must tolerate a retry."""
    for migration in _files():
        sql = migration.read_text(encoding="utf-8")
        assert not re.search(r"\bCREATE\s+TABLE\s+(?!IF\s+NOT\s+EXISTS\b)", sql, re.IGNORECASE), migration
        assert not re.search(
            r"\bCREATE\s+(?:UNIQUE\s+)?INDEX\s+(?!IF\s+NOT\s+EXISTS\b)", sql, re.IGNORECASE
        ), migration
        assert not re.search(r"\bCREATE\s+EXTENSION\s+(?!IF\s+NOT\s+EXISTS\b)", sql, re.IGNORECASE), migration
        assert not re.search(r"\bCREATE\s+SCHEMA\s+(?!IF\s+NOT\s+EXISTS\b)", sql, re.IGNORECASE), migration
        assert not re.search(r"\bCREATE\s+FUNCTION\b", sql, re.IGNORECASE), migration
        assert not re.search(r"\bADD\s+COLUMN\s+(?!IF\s+NOT\s+EXISTS\b)", sql, re.IGNORECASE), migration


def test_policies_and_triggers_are_dropped_before_recreation() -> None:
    for migration in _files():
        sql = migration.read_text(encoding="utf-8")

        for created in re.finditer(
            r"\bCREATE\s+POLICY\s+(?P<name>\"[^\"]+\"|[\w]+)\s+ON\s+(?P<table>[\w.%]+)",
            sql,
            re.IGNORECASE,
        ):
            name, table = created.group("name", "table")
            expected_drop = rf"\bDROP\s+POLICY\s+IF\s+EXISTS\s+{re.escape(name)}\s+ON\s+{re.escape(table)}"
            assert re.search(expected_drop, sql[: created.start()], re.IGNORECASE), migration

        for created in re.finditer(
            r"\bCREATE\s+TRIGGER\s+(?P<name>[\w]+).*?\s+ON\s+(?P<table>[\w.%]+)",
            sql,
            re.IGNORECASE,
        ):
            name, table = created.group("name", "table")
            expected_drop = rf"\bDROP\s+TRIGGER\s+IF\s+EXISTS\s+{re.escape(name)}\s+ON\s+{re.escape(table)}"
            prefix = sql[: created.start()]
            dynamically_guarded = (
                "DROP TRIGGER IF EXISTS %I ON %I" in prefix and f"'{name}'" in prefix
            )
            assert re.search(expected_drop, prefix, re.IGNORECASE) or dynamically_guarded, migration


def test_constraints_types_and_publications_have_retry_guards() -> None:
    for migration in _files():
        sql = migration.read_text(encoding="utf-8")

        for constraint in re.finditer(r"\bADD\s+CONSTRAINT\s+(?P<name>[\w]+)", sql, re.IGNORECASE):
            name = constraint.group("name")
            prefix = sql[: constraint.start()]
            assert (
                re.search(rf"\bDROP\s+CONSTRAINT\s+IF\s+EXISTS\s+{re.escape(name)}\b", prefix, re.IGNORECASE)
                or re.search(rf"\bconname\s*=\s*'{re.escape(name)}'", prefix, re.IGNORECASE)
            ), migration

        if re.search(r"\bCREATE\s+TYPE\b", sql, re.IGNORECASE):
            assert "duplicate_object" in sql, migration
        if re.search(r"\bALTER\s+PUBLICATION\b", sql, re.IGNORECASE):
            assert "pg_publication_tables" in sql, migration
