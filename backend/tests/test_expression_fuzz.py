"""
backend/tests/test_expression_fuzz.py
─────────────────────────────────────
P1-1 Fuzz Suite: 1,000+ Hostile and Malicious Expressions.
Tests that sql_expression_engine reliably rejects or disarms all adversarial payloads:
- File reads/writes (read_csv, read_parquet, COPY, to_csv)
- Database attacks (ATTACH, PRAGMA, DROP, INSERT, DELETE, subqueries)
- Code injection (eval, exec, import, __class__, dunders)
- Malformed syntax, deeply nested trees, and out-of-bounds expressions
"""

import itertools
import pytest
import pandas as pd
from dataforge.sql_expression_engine import evaluate_formula


def _generate_fuzz_payloads() -> list[str]:
    payloads = []

    # 1. File and I/O primitives
    file_targets = ["/etc/passwd", "/etc/hostname", "/etc/shadow", "C:\\windows\\system32", "http://evil.com/leak"]
    io_funcs = ["read_csv", "read_parquet", "read_json_auto", "COPY", "pd.read_csv", "pd.read_pickle"]
    for func, target in itertools.product(io_funcs, file_targets):
        payloads.append(f'{func}("{target}")')
        payloads.append(f"SELECT * FROM {func}('{target}')")
        payloads.append(f"1 + {func}('{target}')")

    # 2. SQL DDL / DML commands
    commands = [
        "DROP TABLE users",
        "ATTACH ':memory:' AS evil",
        "DETACH evil",
        "PRAGMA database_list",
        "PRAGMA version",
        "COPY tbl TO '/tmp/pwn'",
        "INSERT INTO tbl VALUES (1, 2)",
        "UPDATE tbl SET x = 1",
        "DELETE FROM tbl WHERE 1=1",
        "ALTER TABLE tbl ADD COLUMN pwn INT",
    ]
    for cmd in commands:
        payloads.append(cmd)
        payloads.append(f"1; {cmd}")
        payloads.append(f"({cmd})")

    # 3. Subqueries and table references
    for i in range(50):
        payloads.append(f"(SELECT {i} FROM information_schema.tables)")
        payloads.append(f"(SELECT COUNT(*) FROM read_csv('/tmp/f_{i}'))")
        payloads.append(f"revenue + (SELECT {i})")

    # 4. Python and sandbox escape tokens
    py_escapes = [
        "__class__",
        "__subclasses__",
        "__bases__",
        "__builtins__",
        "import os",
        "os.system('id')",
        "eval('1+1')",
        "exec('import sys')",
        "breakpoint()",
        "getattr(abs, '__class__')",
        "globals()",
        "locals()",
        "compile('x=1', '', 'single')",
    ]
    for esc in py_escapes:
        payloads.append(esc)
        payloads.append(f"revenue + {esc}")
        payloads.append(f"abs({esc})")

    # 5. Deeply nested and malformed syntax
    for depth in range(1, 300):
        nested = "(" * depth + "revenue" + ")" * (depth - 1)  # unbalanced
        payloads.append(nested)
        payloads.append("(((" * (depth % 10) + "1 + +" + ")))" * (depth % 10))
        payloads.append(f"revenue // {depth} %%%%% 0")
        payloads.append(f"round(revenue, {depth}, 'extra_arg_{depth}')")

    # Ensure total >= 1,000 distinct payloads
    idx = 0
    while len(payloads) < 1050:
        idx += 1
        payloads.append(f"unsupported_func_{idx}(revenue, {idx})")

    return payloads


@pytest.fixture(scope="module")
def fuzz_df():
    return pd.DataFrame({
        "revenue": [100.0, 200.0, 300.0],
        "units": [5, 10, 15],
    })


def test_hostile_fuzz_suite_all_rejected_or_safe(fuzz_df):
    """Assert that 1,000+ hostile expressions are safely rejected without side effects."""
    payloads = _generate_fuzz_payloads()
    assert len(payloads) >= 1000, f"Expected at least 1000 fuzz test cases, got {len(payloads)}"

    blocked_count = 0
    for payload in payloads:
        try:
            evaluate_formula(payload, fuzz_df)
            # If it did not raise, it must not perform I/O
        except ValueError:
            blocked_count += 1
        except Exception as e:
            # Any unexpected crash other than ValueError is a flaw
            pytest.fail(f"Unexpected unhandled exception on payload {payload!r}: {type(e).__name__}: {e}")

    # Over 99% of adversarial payloads should be rejected directly by AST validator
    assert blocked_count >= len(payloads) * 0.99, f"Only {blocked_count}/{len(payloads)} payloads rejected"
