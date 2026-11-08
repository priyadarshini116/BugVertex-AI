"""
Debug one bug: show exactly what the AI replied and how the tests reacted.

Run from the Engine folder:   python scripts\\debug_bug.py bug_018
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import patcher  # noqa: E402
from sandbox import run_tests  # noqa: E402

bug_id = sys.argv[1] if len(sys.argv) > 1 else "bug_018"
d = ROOT / "benchmark" / "bugs" / bug_id
buggy = (d / "buggy.py").read_text(encoding="utf-8")
tests = (d / "test_bug.py").read_text(encoding="utf-8")


def spy(prompt):
    reply = patcher.ask_llm(prompt)
    print("=" * 60)
    print("AI REPLY:")
    print(reply)
    code = patcher.extract_code(reply)
    if code:
        r = run_tests(code, tests)
        print("-" * 60)
        print("TEST RESULT:", r["status"])
        print(r["output"][-800:])
    return reply


res = patcher.verify_patch(buggy, tests, llm=spy, max_attempts=1)
print("=" * 60)
print("VERDICT:", res["verdict"])