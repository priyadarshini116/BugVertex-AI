"""
BugVertex patch generator + verifier.

Flow:  buggy code + tests -> run tests (confirm failure) -> ask the LLM for a fix
       -> run the tests on the fix in the sandbox -> verified / not verified.
If a fix still fails, the new failure output is sent back to the LLM and it tries
again, up to MAX_ATTEMPTS (a bounded repair loop).

Try one bug from the Engine folder:   python src\\patcher.py bug_001
"""
import difflib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sandbox import run_tests  # noqa: E402

MAX_ATTEMPTS = 3
FENCE = "`" * 3  # three backticks, built here so this file has no literal fences


def build_prompt(code, tests, output, extra=""):
    return (
        "You are fixing a bug in a small Python module.\n\n"
        f"Return the COMPLETE corrected contents of buggy.py inside ONE {FENCE}python code block.\n"
        "Change as little as possible. Do not change the tests. "
        "No explanation outside the code block.\n\n"
        f"Current buggy.py:\n{FENCE}python\n{code}\n{FENCE}\n\n"
        "Tests (do not change them; they define the expected behaviour):\n"
        f"{FENCE}python\n{tests}\n{FENCE}\n\n"
        f"Test failure output:\n{FENCE}\n{output}\n{FENCE}\n{extra}"
    )


def ask_llm(prompt):
    """Send the prompt to the project's configured model and return its text reply."""
    from core import client, CHAT_MODEL, GEN_REASONING  # imported here so the rest works offline
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        extra_body={"reasoning": GEN_REASONING},
    )
    return resp.choices[0].message.content or ""


def extract_code(text):
    """Return the first python code block in the reply (or any code block), else None."""
    if not text:
        return None
    m = (re.search(FENCE + r"python\s*\n(.*?)" + FENCE, text, re.S)
         or re.search(FENCE + r"\s*\n(.*?)" + FENCE, text, re.S))
    return m.group(1).strip() + "\n" if m else None


def make_diff(old, new):
    return "".join(difflib.unified_diff(
        old.splitlines(True), new.splitlines(True), "buggy.py", "patched.py"))


def verify_patch(buggy_code, test_code, llm=ask_llm, max_attempts=MAX_ATTEMPTS, test_cmd=None):
    """Try to fix `buggy_code`. Returns a dict with:
        verdict: "verified" | "not_verified" | "no_bug_found"
        attempts: list of per-attempt records;  patch / diff: the final fix (if verified)
    """
    baseline = run_tests(buggy_code, test_code, test_cmd=test_cmd)
    if baseline["status"] == "passed":
        return {"verdict": "no_bug_found", "attempts": [], "patch": None, "diff": None,
                "baseline": baseline["output"]}

    output, extra, attempts = baseline["output"], "", []
    for n in range(1, max_attempts + 1):
        prompt = build_prompt(buggy_code, test_code, output[-1500:], extra)
        try:
            reply = llm(prompt)
        except Exception as e:  # network / API problem: stop, don't loop forever
            attempts.append({"attempt": n, "status": "llm_error", "detail": str(e)[:200]})
            break
        patched = extract_code(reply)
        if not patched:
            attempts.append({"attempt": n, "status": "no_code"})
            extra = f"\nYour last reply had no {FENCE}python block. Return the full file in one block."
            continue
        result = run_tests(patched, test_code, test_cmd=test_cmd)
        attempts.append({"attempt": n, "status": result["status"]})
        if result["status"] == "passed":
            return {"verdict": "verified", "attempts": attempts, "baseline": baseline["output"],
                    "patch": patched, "diff": make_diff(buggy_code, patched)}
        output = result["output"]
        extra = (f"\nYour previous attempt was:\n{FENCE}python\n{patched}\n{FENCE}\n"
                 "It still failed the tests. Try a genuinely different fix.")
    return {"verdict": "not_verified", "attempts": attempts, "patch": None, "diff": None,
            "baseline": baseline["output"]}


if __name__ == "__main__":
    bug_id = sys.argv[1] if len(sys.argv) > 1 else "bug_001"
    d = ROOT / "benchmark" / "bugs" / bug_id
    buggy = (d / "buggy.py").read_text(encoding="utf-8")
    tests = (d / "test_bug.py").read_text(encoding="utf-8")
    res = verify_patch(buggy, tests)
    print(f"Bug:      {bug_id}")
    print(f"Verdict:  {res['verdict'].upper()}")
    print(f"Attempts: {json.dumps(res['attempts'])}")
    if res["diff"]:
        print("\nProposed change:\n" + res["diff"])