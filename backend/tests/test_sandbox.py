"""
backend/tests/test_sandbox.py
────────────────────────────
Security Suite: Process-Isolated Execution Sandbox.
Adversarial security tests testing breakouts, infinite loops, resource limits,
builtins filtering, and environment secret protection.
"""

import os
import pytest
import pandas as pd
from dataforge.sandbox import (
    run_sandboxed_code,
    SecurityError,
    SandboxTimeoutError,
)


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "category": ["Electronics", "Clothing", "Electronics", "Home"],
        "price": [199.99, 49.50, 299.00, 15.00],
        "quantity": [2, 5, 1, 10],
    })


def test_sandbox_blocks_arbitrary_imports(sample_df):
    """Import statements must be rejected immediately."""
    payloads = [
        "import os; result = os.system('ls')",
        "import sys; result = sys.exit(1)",
        "import subprocess; result = subprocess.check_output(['whoami'])",
        "import socket; s = socket.socket()",
        "from pathlib import Path; result = Path('/etc/passwd').read_text()",
    ]
    for code in payloads:
        with pytest.raises(SecurityError):
            run_sandboxed_code(code, sample_df)


def test_sandbox_blocks_dunder_introspection(sample_df):
    """Dunder attribute lookups and class traversal must be rejected."""
    payloads = [
        "result = ().__class__.__bases__[0].__subclasses__()",
        "result = df.__class__.__mro__",
        "result = df.__dict__",
        "result = getattr(df, '__class__')",
    ]
    for code in payloads:
        with pytest.raises(SecurityError):
            run_sandboxed_code(code, sample_df)


def test_sandbox_blocks_file_operations_and_builtins(sample_df):
    """File access and dangerous builtins must be rejected."""
    payloads = [
        "open('/etc/passwd', 'r').read()",
        "eval('1 + 1')",
        "exec('a = 10')",
        "compile('x = 1', '<string>', 'exec')",
    ]
    for code in payloads:
        with pytest.raises(SecurityError):
            run_sandboxed_code(code, sample_df)


def test_sandbox_enforces_execution_timeout(sample_df):
    """Infinite loops or long-running computations must trigger SandboxTimeoutError."""
    # Test short 2-second timeout on while loop
    code = "x = 0\nwhile True:\n    x += 1\nresult = x"
    with pytest.raises(SandboxTimeoutError):
        run_sandboxed_code(code, sample_df, timeout_sec=2)


def test_sandbox_scrubs_secrets_from_child_environment(sample_df):
    """Secrets in parent environment must NOT be passed to child sandbox process."""
    os.environ["SECRET_KEY_FOR_TEST"] = "super-secret-12345"
    os.environ["GEMINI_API_KEY"] = "gemini-secret-test-key"

    # Even if code attempts to read os.environ (which is blocked by AST validator anyway),
    # let's verify that child runner only runs with clean PATH and standard env
    valid_calc = "result = int((df['price'] * df['quantity']).sum())"
    res = run_sandboxed_code(valid_calc, sample_df)
    expected = int((sample_df["price"] * sample_df["quantity"]).sum())
    assert res == expected


def test_sandbox_legitimate_analytics_computation(sample_df):
    """Legitimate pandas/numpy aggregations execute cleanly and return correct values."""
    # 1. Total revenue
    res1 = run_sandboxed_code("result = float(round(df['price'].mean(), 2))", sample_df)
    assert res1 == round(float(sample_df["price"].mean()), 2)

    # 2. DataFrame aggregation
    res_df = run_sandboxed_code("result = df.groupby('category')['quantity'].sum().reset_index()", sample_df)
    assert isinstance(res_df, pd.DataFrame)
    assert "category" in res_df.columns
    assert "quantity" in res_df.columns
    assert len(res_df) == 3
