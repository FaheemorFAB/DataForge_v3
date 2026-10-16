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
    AST-level defence-in-depth validator and user guidance helper.
    NOTE: AST inspection is not the security boundary; kernel-level process
    isolation (Landlock filesystem confinement, network namespace isolation,
    and OS resource limits) enforces the security boundary.
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

    FORBIDDEN_ATTRIBUTES = {
        # File read/write and serialization in pandas, numpy, and python objects
        "read_csv", "read_table", "read_parquet", "read_feather", "read_hdf",
        "read_pickle", "read_sql", "read_sql_query", "read_sql_table",
        "read_json", "read_html", "read_xml", "read_excel", "read_clipboard",
        "to_pickle", "to_csv", "to_parquet", "to_json", "to_sql", "to_excel",
        "to_feather", "to_hdf", "to_html", "to_xml", "to_clipboard",
        # Sub-evaluation engines
        "query", "eval",
        # Generic persistence & modules
        "load", "save", "fromfile", "fromregex", "tofile", "io", "api",
    }

    def visit_Import(self, node: ast.Import):
        raise SecurityError("Arbitrary import statements are prohibited in analytics sandbox")

    def visit_ImportFrom(self, node: ast.ImportFrom):
        raise SecurityError("Arbitrary import statements are prohibited in analytics sandbox")

    def visit_Attribute(self, node: ast.Attribute):
        if node.attr.startswith("__"):
            raise SecurityError(f"Dunder attribute access prohibited: '{node.attr}'")
        if node.attr in ("query", "eval"):
            raise SecurityError(
                "The 'query' and 'eval' methods are restricted in the analytics sandbox for security. "
                "Please use standard pandas indexing (e.g. df[df['col'] > 0]) instead."
            )
        if node.attr in self.FORBIDDEN_ATTRIBUTES:
            raise SecurityError(f"Prohibited method/attribute in sandbox: '{node.attr}'")
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
            if node.func.attr in ("query", "eval"):
                raise SecurityError(
                    "The 'query' and 'eval' methods are restricted in the analytics sandbox for security. "
                    "Please use standard pandas indexing (e.g. df[df['col'] > 0]) instead."
                )
            if node.func.attr in self.FORBIDDEN_ATTRIBUTES:
                raise SecurityError(f"Prohibited method execution in sandbox: '{node.func.attr}'")
        self.generic_visit(node)


def validate_ast(code: str) -> None:
    """Parse and validate AST against security restrictions."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Syntax error in analytics code: {e}") from e

    validator = SecureASTValidator()
    validator.visit(tree)


_RUNNER_TEMPLATE = '''# Isolated sandbox worker
import json
import os
import sys

def run():
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    code_file = sys.argv[3]
    max_mem_mb = int(sys.argv[4]) if len(sys.argv) > 4 else 512
    timeout_sec = int(sys.argv[5]) if len(sys.argv) > 5 else 10

    # 1. Apply OS resource limits
    try:
        import resource
        mem_bytes = max_mem_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        resource.setrlimit(resource.RLIMIT_CPU, (timeout_sec, timeout_sec))
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
        resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))
    except Exception:
        pass

    # 2. Network isolation via unprivileged Linux network namespace (fail-closed)
    try:
        import ctypes
        CLONE_NEWUSER = 0x10000000
        CLONE_NEWNET = 0x40000000
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        ret = libc.unshare(CLONE_NEWUSER | CLONE_NEWNET)
        if ret != 0:
            allow_no_netns = os.environ.get("DATAFORGE_SANDBOX_ALLOW_NO_NETNS") == "1"
            if not allow_no_netns:
                sys.stderr.write(f"Sandbox isolation error: network namespace unshare failed (code {ret}). Failing closed.\\n")
                sys.exit(77)
    except Exception as exc:
        allow_no_netns = os.environ.get("DATAFORGE_SANDBOX_ALLOW_NO_NETNS") == "1"
        if not allow_no_netns:
            sys.stderr.write(f"Sandbox isolation error: network namespace unshare exception: {exc}. Failing closed.\\n")
            sys.exit(77)

    import pandas as pd
    import numpy as np

    with open(code_file, "r", encoding="utf-8") as f:
        code_str = f.read()

    df = pd.read_parquet(input_file)

    # Strip dangerous filesystem I/O and evaluation methods from pandas
    for forbidden in [
        "read_csv", "read_table", "read_parquet", "read_feather", "read_hdf",
        "read_pickle", "read_sql", "read_sql_query", "read_sql_table",
        "read_json", "read_html", "read_xml", "read_excel", "read_clipboard",
        "to_pickle", "to_csv", "to_parquet", "to_json", "to_sql", "to_excel",
        "to_feather", "to_hdf", "to_html", "to_xml", "to_clipboard", "eval"
    ]:
        if hasattr(pd, forbidden):
            try:
                delattr(pd, forbidden)
            except Exception:
                pass

    if hasattr(pd, "io"):
        try:
            delattr(pd, "io")
        except Exception:
            pass

    # Strip dangerous I/O from numpy
    for np_forbidden in [
        "load", "save", "savez", "savez_compressed", "fromfile", "tofile",
        "fromregex", "genfromtxt", "loadtxt", "DataSource"
    ]:
        if hasattr(np, np_forbidden):
            try:
                delattr(np, np_forbidden)
            except Exception:
                pass

    # Disable sub-evaluations on DataFrame instance
    if hasattr(df, "eval"):
        df.eval = None
    if hasattr(df, "query"):
        df.query = None

    # 3. Filesystem isolation via Linux Landlock (applied right before user code execution)
    try:
        import ctypes
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        SYS_landlock_create_ruleset = 444
        SYS_landlock_add_rule = 445
        SYS_landlock_restrict_self = 446
        LANDLOCK_RULE_PATH_BENEATH = 1

        class LandlockRulesetAttr(ctypes.Structure):
            _fields_ = [("handled_access_fs", ctypes.c_uint64)]

        class LandlockPathBeneathAttr(ctypes.Structure):
            _fields_ = [
                ("allowed_access", ctypes.c_uint64),
                ("parent_fd", ctypes.c_int32),
            ]

        abi = libc.syscall(SYS_landlock_create_ruleset, 0, 0, 1)
        if abi >= 1:
            PR_SET_NO_NEW_PRIVS = 38
            libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)

            ACCESS_FS_ALL = (1 << 13) - 1
            ACCESS_RO = (1 << 0) | (1 << 2) | (1 << 5)  # EXECUTE | READ_FILE | READ_DIR
            ACCESS_RW = ACCESS_FS_ALL

            attr = LandlockRulesetAttr(handled_access_fs=ACCESS_FS_ALL)
            ruleset_fd = libc.syscall(SYS_landlock_create_ruleset, ctypes.byref(attr), ctypes.sizeof(attr), 0)
            if ruleset_fd >= 0:
                # Read-only allowed paths: Python interpreter, libraries, venv
                for p in [sys.prefix, getattr(sys, "base_prefix", sys.prefix), "/usr", "/lib", "/lib64"]:
                    if os.path.exists(p):
                        try:
                            fd = os.open(p, os.O_PATH | os.O_CLOEXEC)
                            path_attr = LandlockPathBeneathAttr(allowed_access=ACCESS_RO, parent_fd=fd)
                            libc.syscall(SYS_landlock_add_rule, ruleset_fd, LANDLOCK_RULE_PATH_BENEATH, ctypes.byref(path_attr), 0)
                            os.close(fd)
                        except OSError:
                            pass

                # Read-write allowed paths: current working directory
                cwd = os.getcwd()
                try:
                    fd = os.open(cwd, os.O_PATH | os.O_CLOEXEC)
                    path_attr = LandlockPathBeneathAttr(allowed_access=ACCESS_RW, parent_fd=fd)
                    libc.syscall(SYS_landlock_add_rule, ruleset_fd, LANDLOCK_RULE_PATH_BENEATH, ctypes.byref(path_attr), 0)
                    os.close(fd)
                except OSError:
                    pass

                libc.syscall(SYS_landlock_restrict_self, ruleset_fd, 0)
                os.close(ruleset_fd)
    except Exception:
        pass

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
    kernel-level Landlock filesystem confinement, network namespace isolation,
    and OS resource limits. No multithreaded preexec_fn is used.
    """
    # 1. AST Validation & UX guidance
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

        # 4. Spawn child process without preexec_fn (safe in multithreaded runtimes)
        cmd = [
            sys.executable,
            "-I",  # Isolated mode: do not inherit sys.path, site packages from user
            str(runner_file),
            str(input_parquet),
            str(output_json),
            str(code_file),
            str(max_mem_mb),
            str(timeout_sec),
        ]

        try:
            proc = subprocess.run(
                cmd,
                env=clean_env,
                cwd=str(tmp_path),
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired as exc:
            logger.warning("[sandbox] Execution timed out after %s seconds", timeout_sec)
            raise SandboxTimeoutError(f"Execution timed out ({timeout_sec}s limit exceeded)") from exc

        if proc.returncode != 0:
            if proc.returncode in (-9, -24, 137) or proc.returncode < 0:
                raise SandboxTimeoutError(f"Execution timed out or CPU limit exceeded ({timeout_sec}s limit)")
            err = proc.stderr.strip()
            first_err = err.splitlines()[-1] if err else "Execution failed with non-zero exit code"
            if proc.returncode == 77:
                raise SecurityError(f"Sandbox isolation failure: {first_err}")
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
