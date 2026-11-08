"""
Patch evaluation: how many benchmark bugs does BugVertex fix AND verify?

For every bug in benchmark/bugs/, the AI sees only buggy.py + the tests (never
fixed.py), proposes a patch, and the sandbox checks it. Results are saved to
benchmark/results/patch_eval.json.

Run from the Engine folder:   python scripts\\run_patch_eval.py
(Calls your AI model up to 3 times per bug, so up to ~60 small requests.)
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from patcher import verify_patch  # noqa: E402


def main(llm=None, test_cmd=None, model_name=None):
    if model_name is None:
        from core import CHAT_MODEL
        model_name = CHAT_MODEL
    kwargs = {"test_cmd": test_cmd}
    if llm is not None:
        kwargs["llm"] = llm

    folders = sorted(p for p in (ROOT / "benchmark" / "bugs").iterdir() if p.is_dir())
    rows = []
    print(f"Model: {model_name}\n")
    print(f"{'bug':<9} {'type':<24} {'verdict':<13} attempts")
    print("-" * 60)
    for d in folders:
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        buggy = (d / "buggy.py").read_text(encoding="utf-8")
        tests = (d / "test_bug.py").read_text(encoding="utf-8")
        res = verify_patch(buggy, tests, **kwargs)
        used = len(res["attempts"])
        rows.append({"id": d.name, "bug_type": meta["bug_type"], "verdict": res["verdict"],
                     "attempts_used": used, "attempts": res["attempts"], "patch": res["patch"]})
        print(f"{d.name:<9} {meta['bug_type']:<24} {res['verdict']:<13} {used}")

    total = len(rows)
    verified = sum(r["verdict"] == "verified" for r in rows)
    first_try = sum(r["verdict"] == "verified" and r["attempts_used"] == 1 for r in rows)
    print("-" * 60)
    print(f"Verified fixes:          {verified} / {total}  ({100 * verified / total:.0f}%)")
    print(f"Verified on first try:   {first_try} / {total}  ({100 * first_try / total:.0f}%)")
    failed = [r["id"] for r in rows if r["verdict"] != "verified"]
    if failed:
        print("Not verified:            " + ", ".join(failed))

    out = ROOT / "benchmark" / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / "patch_eval.json").write_text(json.dumps({
        "model": model_name, "date": time.strftime("%Y-%m-%d"),
        "total": total, "verified": verified, "verified_first_try": first_try,
        "results": rows}, indent=2), encoding="utf-8")
    print(f"\nSaved: {out / 'patch_eval.json'}")


if __name__ == "__main__":
    main()