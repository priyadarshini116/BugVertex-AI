"""
Benchmark self-check.

For every bug in benchmark/bugs/, run its tests twice in the sandbox:
  1. against buggy.py  -> should FAIL   (the bug is real)
  2. against fixed.py  -> should PASS   (the known fix works)
A bug is "valid" only if both are true. Results are saved to
benchmark/results/self_check.json.

Run from the Engine folder:   python scripts\\run_benchmark.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from sandbox import run_tests  # noqa: E402


def main():
    bugs_dir = ROOT / "benchmark" / "bugs"
    folders = sorted(p for p in bugs_dir.iterdir() if p.is_dir())
    rows, valid = [], 0

    print(f"{'bug':<9} {'type':<24} {'buggy':<8} {'fixed':<8} result")
    print("-" * 62)
    for d in folders:
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        test = (d / "test_bug.py").read_text(encoding="utf-8")
        buggy = run_tests((d / "buggy.py").read_text(encoding="utf-8"), test)
        fixed = run_tests((d / "fixed.py").read_text(encoding="utf-8"), test)
        ok = buggy["status"] == "failed" and fixed["status"] == "passed"
        valid += ok
        print(f"{d.name:<9} {meta['bug_type']:<24} {buggy['status']:<8} {fixed['status']:<8} {'OK' if ok else 'PROBLEM'}")
        rows.append({"id": d.name, "bug_type": meta["bug_type"],
                     "buggy_status": buggy["status"], "fixed_status": fixed["status"],
                     "valid": ok})

    print("-" * 62)
    print(f"Valid benchmark bugs: {valid} / {len(folders)}")

    out = ROOT / "benchmark" / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / "self_check.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"Saved: {out / 'self_check.json'}")


if __name__ == "__main__":
    main()