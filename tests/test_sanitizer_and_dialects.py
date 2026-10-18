"""Unit tests for core.sanitizer and extended core.dialect_converter functions."""

import pytest
from core.sanitizer import (
    sanitize_sql,
    sanitize_with_postgres,
    ParameterizedStatement,
    SanitizationError,
)
from core.dialect_converter import (
    convert_sql,
    convert_to_postgres,
    convert_to_mysql,
    convert_to_oracle,
    convert_to_sqlserver,
    DialectSQL,
)
from validator import parse_yaml_schema, parse_sql, is_multi_statement


def test_sanitizer_basic():
    raw_sql = "SELECT id, name FROM users WHERE age > 25 AND active = true;"
    stmt = sanitize_sql(raw_sql, dialect="postgres")
    assert isinstance(stmt, ParameterizedStatement)
    assert len(stmt.params) >= 1
    assert "$1" in stmt.sql
    assert 25 in stmt.params


def test_sanitizer_sqlite_placeholder():
    raw_sql = "SELECT * FROM orders WHERE total > 100;"
    stmt = sanitize_sql(raw_sql, dialect="sqlite")
    assert "?" in stmt.sql
    assert 100 in stmt.params


def test_dialect_conversion_m8_api():
    raw_sql = "SELECT id, name FROM users LIMIT 10;"
    conv = convert_sql(raw_sql, target_dialects=["postgres", "mysql"])
    assert len(conv.conversions) == 2
    pg = conv.conversions[0]
    my = conv.conversions[1]
    assert pg.dialect == "postgres"
    assert my.dialect == "mysql"
    assert "LIMIT 10" in pg.sql


def test_dialect_conversions_single():
    raw_sql = "SELECT id FROM users;"
    pg = convert_to_postgres(raw_sql)
    assert isinstance(pg, DialectSQL)
    assert pg.dialect == "postgres"

    my = convert_to_mysql(raw_sql)
    assert my.dialect == "mysql"

    ora = convert_to_oracle(raw_sql)
    assert ora.dialect == "oracle"

    ms = convert_to_sqlserver(raw_sql)
    assert ms.dialect == "sqlserver"


def test_validator_helpers():
    parsed_yaml = parse_yaml_schema("table: users\ncolumns: [id, name]")
    assert parsed_yaml["loaded"] is True

    single_sql = "SELECT 1;"
    ast = parse_sql(single_sql)
    assert ast is not None
    assert is_multi_statement("SELECT 1; SELECT 2;") is True
    assert is_multi_statement("SELECT 1;") is False
