"""
BugVertex sandbox runner.

Runs Python code against a test file in a throwaway temp folder, with a
time limit and a stripped-down environment (API keys are NOT passed in).

NOTE: this is a "lite" sandbox (separate process + timeout + clean env).
It is NOT a security boundary against hostile code. Docker mode is the
planned upgrade.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

DEFAULT_TIMEOUT = 10  # seconds
DEFAULT_CMD = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_bug.py"]

# Only these environment variables are passed to the code being tested.
_SAFE_ENV_KEYS = ("PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "USERPROFILE")


def _clean_env():
    env = {k: v for k, v in os.environ.items() if k.upper() in _SAFE_ENV_KEYS}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _count(pattern, text):
    m = re.search(pattern, text)
    return int(m.group(1)) if m else 0


def run_tests(code, test_code, timeout=DEFAULT_TIMEOUT, test_cmd=None):
    """Write `code` as buggy.py and `test_code` as test_bug.py in a temp folder,
    run the tests, and return a dict:

        {"status": "passed" | "failed" | "timeout" | "error",
         "passed": int, "failed": int, "seconds": float, "output": str}
    """
    tmp = Path(tempfile.mkdtemp(prefix="bugvertex_"))
    start = time.time()
    try:
        (tmp / "buggy.py").write_text(code, encoding="utf-8")
        (tmp / "test_bug.py").write_text(test_code, encoding="utf-8")
        cmd = test_cmd or DEFAULT_CMD
        try:
            proc = subprocess.run(
                cmd, cwd=tmp, env=_clean_env(), capture_output=True,
                text=True, encoding="utf-8", errors="replace", timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "passed": 0, "failed": 0,
                    "seconds": round(time.time() - start, 2),
                    "output": f"Timed out after {timeout}s"}

        out = (proc.stdout or "") + (proc.stderr or "")
        passed = _count(r"(\d+) passed", out)
        failed = _count(r"(\d+) failed", out) + _count(r"(\d+) error", out)
        if proc.returncode == 0:
            status = "passed"
        elif passed or failed:
            status = "failed"
        else:
            status = "error"
        return {"status": status, "passed": passed, "failed": failed,
                "seconds": round(time.time() - start, 2), "output": out[-2000:]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)