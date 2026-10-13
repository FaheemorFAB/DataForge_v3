"""
dataforge/sandbox.py
────────────────────
Secure, process-isolated analytics execution sandbox.
Provides hard limits: CPU, memory, execution timeout, scrubbed environment,
and AST pre-validation to prevent arbitrary code execution vulnerabilities.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import resource
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when untrusted code attempts unauthorized access."""
    pass


class SandboxTimeoutError(SecurityError):
    """Raised when code execution exceeds the allocated time limit."""
    pass


class SecureASTValidator(ast.NodeVisitor):
    """
    AST-level defence-in-depth validator. Rejects imports, dangerous calls,
    and dunder introspection before execution.
    """
    ALLOWED_BUILTINS = {
        "len", "round", "range", "float", "int", "str", "bool",
        "list", "dict", "set", "sum", "max", "min", "abs", "any", "all",
        "enumerate", "zip", "sorted", "reversed",
    }

    FORBIDDEN_NAMES = {
        "__builtins__", "__import__", "eval", "exec", "compile", "open",
        "sys", "os", "subprocess", "shutil", "socket", "urllib", "requests",
        "pty", "platform", "posix", "ctypes", "pickle", "shelve",
        "getattr", "setattr", "delattr",
    }

    def visit_Import(self, node: ast.Import):
        raise SecurityError("Arbitrary import statements are prohibited in analytics sandbox")

    def visit_ImportFrom(self, node: ast.ImportFrom):
        raise SecurityError("Arbitrary import statements are prohibited in analytics sandbox")

    def visit_Attribute(self, node: ast.Attribute):
        if node.attr.startswith("__"):
            raise SecurityError(f"Dunder attribute access prohibited: '{node.attr}'")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        if node.id in self.FORBIDDEN_NAMES:
            raise SecurityError(f"Access to prohibited symbol: '{node.id}'")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id in self.FORBIDDEN_NAMES:
                raise SecurityError(f"Prohibited function call: '{node.func.id}'")
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr.startswith("__"):
                raise SecurityError(f"Dunder attribute execution prohibited: '{node.func.attr}'")
        self.generic_visit(node)


def validate_ast(code: str) -> None:
    """Parse and validate AST against security restrictions."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Syntax error in analytics code: {e}") from e

    validator = SecureASTValidator()
    validator.visit(tree)


def _set_sandbox_limits(max_mem_mb: int = 512, max_cpu_sec: int = 5):
    """Resource limits applied to the child execution process."""
    try:
        # Address space (virtual memory) limit
        mem_bytes = max_mem_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    except (ValueError, OSError):
        pass

    try:
        # CPU time limit in seconds
        resource.setrlimit(resource.RLIMIT_CPU, (max_cpu_sec, max_cpu_sec))
    except (ValueError, OSError):
        pass

    try:
        # Maximum open file descriptors
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    except (ValueError, OSError):
        pass

    try:
        # Maximum generated file size (10 MB)
        max_fsize = 10 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_FSIZE, (max_fsize, max_fsize))
    except (ValueError, OSError):
        pass


_RUNNER_TEMPLATE = '''# Isolated sandbox worker
import json
import sys
import pandas as pd
import numpy as np

def run():
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    code_file = sys.argv[3]

    with open(code_file, "r", encoding="utf-8") as f:
        code_str = f.read()

    df = pd.read_parquet(input_file)

    safe_builtins = {
        "len": len, "round": round, "range": range, "float": float, "int": int,
        "str": str, "bool": bool, "list": list, "dict": dict, "set": set,
        "sum": sum, "max": max, "min": min, "abs": abs, "any": any, "all": all,
        "enumerate": enumerate, "zip": zip, "sorted": sorted, "reversed": reversed,
        "print": lambda *args, **kwargs: None,
    }

    env = {
        "__builtins__": safe_builtins,
        "df": df,
        "pd": pd,
        "np": np,
        "result": None,
    }

    exec(code_str, {"__builtins__": safe_builtins}, env)
    res = env.get("result")

    # Serialize result
    if isinstance(res, pd.DataFrame):
        res.to_parquet(output_file + ".parquet", index=False)
        meta = {"type": "dataframe", "file": output_file + ".parquet"}
    elif isinstance(res, pd.Series):
        res.to_frame(name="value").to_parquet(output_file + ".parquet", index=True)
        meta = {"type": "series", "file": output_file + ".parquet"}
    elif isinstance(res, (int, float, str, bool, list, dict)) or res is None:
        meta = {"type": "scalar", "value": res}
    elif isinstance(res, (np.integer, np.floating)):
        meta = {"type": "scalar", "value": res.item()}
    else:
        meta = {"type": "scalar", "value": str(res)}

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(meta, f)

if __name__ == "__main__":
    run()
'''


def run_sandboxed_code(
    code: str,
    df: pd.DataFrame,
    timeout_sec: int = 10,
    max_mem_mb: int = 512,
) -> Any:
    """
    Execute user- or LLM-generated code in an isolated child process with
    resource limits, scrubbed environment, and pre-execution AST validation.
    """
    # 1. AST Validation
    validate_ast(code)

    # 2. Setup isolated temp directory
    with tempfile.TemporaryDirectory(prefix="dataforge_sandbox_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        input_parquet = tmp_path / "input.parquet"
        output_json = tmp_path / "output.json"
        code_file = tmp_path / "script.py"
        runner_file = tmp_path / "runner.py"

        # Export input dataframe safely
        df.to_parquet(input_parquet, index=False, compression="snappy")
        code_file.write_text(code, encoding="utf-8")
        runner_file.write_text(_RUNNER_TEMPLATE, encoding="utf-8")

        # 3. Scrub environment variables: strictly omit API keys, DB credentials, secrets
        clean_env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONUNBUFFERED": "1",
        }
        # Forward virtualenv site-packages path if running under venv
        if "VIRTUAL_ENV" in os.environ:
            clean_env["VIRTUAL_ENV"] = os.environ["VIRTUAL_ENV"]
            clean_env["PATH"] = f"{os.environ['VIRTUAL_ENV']}/bin:{clean_env['PATH']}"

        # 4. Spawn child process with resource limits
        cmd = [
            sys.executable,
            "-I",  # Isolated mode: do not inherit sys.path, site packages from user
            str(runner_file),
            str(input_parquet),
            str(output_json),
            str(code_file),
        ]

        try:
            proc = subprocess.run(
                cmd,
                env=clean_env,
                cwd=str(tmp_path),
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                preexec_fn=lambda: _set_sandbox_limits(max_mem_mb=max_mem_mb, max_cpu_sec=timeout_sec),
            )
        except subprocess.TimeoutExpired as exc:
            logger.warning("[sandbox] Execution timed out after %s seconds", timeout_sec)
            raise SandboxTimeoutError(f"Execution timed out ({timeout_sec}s limit exceeded)") from exc

        if proc.returncode != 0:
            if proc.returncode in (-9, -24, 137) or proc.returncode < 0:
                raise SandboxTimeoutError(f"Execution timed out or CPU limit exceeded ({timeout_sec}s limit)")
            err = proc.stderr.strip()
            # Sanitize error to avoid leaking system paths
            first_err = err.splitlines()[-1] if err else "Execution failed with non-zero exit code"
            logger.warning("[sandbox] Process execution failed (code %d): %s", proc.returncode, first_err)
            raise RuntimeError(f"Sandbox error: {first_err}")

        # 5. Read back results
        if not output_json.exists():
            raise RuntimeError("Sandbox worker exited without returning a result")

        with open(output_json, "r", encoding="utf-8") as f:
            meta = json.load(f)

        res_type = meta.get("type")
        if res_type == "dataframe":
            return pd.read_parquet(meta["file"])
        elif res_type == "series":
            series_df = pd.read_parquet(meta["file"])
            return series_df["value"]
        else:
            return meta.get("value")
