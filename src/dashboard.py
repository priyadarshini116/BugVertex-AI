"""
BugVertex AI dashboard: bug investigation with sandbox-verified patches.

Tabs:
  Investigate      - retrieval + confidence gate + grounded analysis (inherited pipeline)
  Patch and Verify - AI proposes a fix, the sandbox runs the tests, you see the verdict
  Benchmark        - results of run_patch_eval.py on the 20-bug benchmark
  Routing          - how the confidence gate routes a fixed set of probe queries

Run from the Engine folder:
    python -m streamlit run src\\dashboard.py
"""

import json
import os
from pathlib import Path

import streamlit as st

import core
import patcher

BENCH_DIR = Path(core.BASE_DIR) / "benchmark"
BUGS_DIR = BENCH_DIR / "bugs"
EVAL_FILE = BENCH_DIR / "results" / "patch_eval.json"
NONE_CHOICE = "(none)"

st.set_page_config(page_title="BugVertex AI", page_icon="🐞", layout="wide")

# ---------------------------------------------------------
# Sidebar: configuration and loaded index
# ---------------------------------------------------------
with st.sidebar:
    st.header("BugVertex AI")
    st.caption("Bug investigation with sandbox-verified patches")

    st.subheader("Models")
    st.markdown(
        f"- **Embedding:** `{core.EMBEDDING_MODEL}`\n"
        f"- **Generation:** `{core.CHAT_MODEL}`\n"
        f"- **Rerank:** `{core.RERANK_MODEL}`"
    )

    st.subheader("Retrieval")
    try:
        path, ntotal, dim = core.index_info()
        st.markdown(
            f"- **Index:** `{os.path.relpath(path, core.BASE_DIR)}`\n"
            f"- **Vectors:** {ntotal:,} (dim {dim})\n"
            f"- **Top-K:** {core.TOP_K}\n"
            f"- **Confidence gate:** {core.CONFIDENCE_THRESHOLD}"
        )
    except Exception as e:
        st.error(f"Could not load index: {e}")

    st.divider()
    st.caption(
        "Extends the open-source, MIT-licensed RootCause project by Saksham Katna. "
        "Retrieval and the confidence gate are inherited; the benchmark, sandbox and "
        "patch verifier are new."
    )

st.title("BugVertex AI")
st.caption("Investigate a bug, propose a fix, and check it by actually running the tests.")

tab_investigate, tab_patch, tab_bench, tab_routing = st.tabs(
    ["Investigate", "Patch and Verify", "Benchmark", "Routing"]
)

# ---------------------------------------------------------
# Tab 1: Investigate (inherited pipeline)
# ---------------------------------------------------------
with tab_investigate:
    st.subheader("Analyze a bug")
    st.write(
        "Describe a bug, paste a traceback, or drop in a code snippet. BugVertex retrieves "
        "similar historical bug fixes, gates on retrieval confidence, optionally reranks, "
        "and asks the LLM for a grounded root cause and fix."
    )

    query = st.text_area(
        "Bug description",
        height=140,
        placeholder="e.g. TypeError: 'NoneType' object has no attribute 'get' when a user "
        "record is missing from the cache",
    )

    if st.button("Analyze", type="primary") and query.strip():
        with st.spinner("Embedding, retrieving, and generating..."):
            try:
                result = core.analyze_bug(query)
            except Exception as e:
                st.error(f"Analysis failed: {e}")
                st.stop()

        top_score = result["top_score"]
        used = result["use_rag"]
        st.markdown(
            f"**Top retrieval score:** {top_score:.3f} "
            f"({'above' if used else 'below'} the {result['confidence_threshold']} gate: "
            f"{'grounded on retrieved examples' if used else 'answering from reasoning only'})"
        )

        st.markdown("#### Answer")
        try:
            st.json(json.loads(result["answer"]))
        except (json.JSONDecodeError, TypeError):
            st.code(result["answer"])

        st.markdown("#### Retrieved candidates")
        cand_rows = [
            {
                "score": round(r["score"], 3),
                "bug_type": r["bug_type"],
                "issue": r["issue"],
                "fix": r["fix"],
            }
            for r in result["retrieved"]
        ]
        if cand_rows:
            st.dataframe(cand_rows, width="stretch", hide_index=True)
        else:
            st.info("No candidates retrieved.")


# ---------------------------------------------------------
# Tab 2: Patch and Verify (new)
# ---------------------------------------------------------
def _example_ids():
    if not BUGS_DIR.exists():
        return []
    return sorted(p.name for p in BUGS_DIR.iterdir() if p.is_dir())


def _load_example():
    choice = st.session_state.get("example_choice")
    if choice and choice != NONE_CHOICE:
        d = BUGS_DIR / choice
        st.session_state["patch_code"] = (d / "buggy.py").read_text(encoding="utf-8")
        st.session_state["patch_tests"] = (d / "test_bug.py").read_text(encoding="utf-8")
        st.session_state.pop("patch_result", None)


def _show_patch_result(res):
    verdict = res["verdict"]
    if verdict == "verified":
        st.success(f"PATCH VERIFIED (after {len(res['attempts'])} attempt(s)): all tests pass.")
    elif verdict == "no_bug_found":
        st.info("The tests already pass on this code, so there is nothing to fix.")
    else:
        st.error("NOT VERIFIED: no attempt passed the tests.")

    if res["attempts"]:
        st.markdown("#### Attempts")
        st.dataframe(
            [{"attempt": a["attempt"], "result": a["status"], "detail": a.get("detail", "")}
             for a in res["attempts"]],
            width="stretch", hide_index=True,
        )
    if res["diff"]:
        st.markdown("#### Proposed change")
        st.code(res["diff"], language="diff")
        st.markdown("#### Patched code")
        st.code(res["patch"], language="python")
    st.caption(
        "Verified means the patch passes these tests in the sandbox. It does not prove the "
        "code is correct in every situation, so review a patch before using it."
    )


with tab_patch:
    st.subheader("Patch and verify")
    st.write(
        "The AI sees your code, the tests and the failure output. It proposes a full fix, "
        "the sandbox runs your tests on it, and if it still fails the AI gets another try "
        f"(up to {patcher.MAX_ATTEMPTS} attempts)."
    )

    st.selectbox(
        "Load an example bug from the benchmark",
        [NONE_CHOICE] + _example_ids(),
        key="example_choice",
        on_change=_load_example,
    )

    col_code, col_tests = st.columns(2)
    code = col_code.text_area("Buggy code (saved as buggy.py)", height=280, key="patch_code")
    tests = col_tests.text_area(
        "Tests (saved as test_bug.py; they must import from buggy)", height=280, key="patch_tests"
    )
    st.caption(
        "The code and tests are run on this computer in a temporary folder with a time limit "
        "and without your API keys. This is not a security boundary, so only run code you trust."
    )

    if st.button("Generate and verify patch", type="primary"):
        if not code.strip() or not tests.strip():
            st.warning("Please provide both the buggy code and the tests.")
        else:
            with st.spinner("Asking the model for a fix and running the tests..."):
                try:
                    st.session_state["patch_result"] = patcher.verify_patch(code, tests)
                except Exception as e:
                    st.error(f"Patch generation failed: {e}")

    saved = st.session_state.get("patch_result")
    if saved:
        _show_patch_result(saved)

# ---------------------------------------------------------
# Tab 3: Benchmark (new)
# ---------------------------------------------------------
with tab_bench:
    st.subheader("Benchmark results")
    if not EVAL_FILE.exists():
        st.info("No results yet. Run:  python scripts\\run_patch_eval.py")
    else:
        data = json.loads(EVAL_FILE.read_text(encoding="utf-8"))
        total, verified, first = data["total"], data["verified"], data["verified_first_try"]
        m1, m2, m3 = st.columns(3)
        m1.metric("Verified fixes", f"{verified} / {total}")
        m1.caption(f"{verified / total * 100:.0f}%")
        m2.metric("Verified on first try", f"{first} / {total}")
        m2.caption(f"{first / total * 100:.0f}%")
        m3.metric("Benchmark bugs", total)
        st.caption(f"Model: {data['model']}  |  last run: {data['date']}")

        st.dataframe(
            [{"bug": r["id"], "type": r["bug_type"], "verdict": r["verdict"],
              "attempts": r["attempts_used"]} for r in data["results"]],
            width="stretch", hide_index=True,
        )

        failed = [r["id"] for r in data["results"] if r["verdict"] != "verified"]
        if "bug_018" in failed:
            with st.expander("Why did bug_018 fail?"):
                st.write(
                    "The bug is a missing timeout. The model kept writing `timeout=None`, "
                    "which looks like a timeout but means no timeout. The test checks that a "
                    "real timeout value is passed, so it rejected the patch every time. "
                    "This is the reason patches are verified by running tests instead of "
                    "being trusted."
                )
        st.caption(
            "Limitations: the benchmark is small, hand-written and simple, the model sees the "
            "tests, and results vary slightly between runs. These numbers do not show "
            "performance on real-world codebases."
        )

# ---------------------------------------------------------
# Tab 4: Routing (inherited)
# ---------------------------------------------------------
PROBE_QUERIES = [
    "TypeError: 'NoneType' object has no attribute 'get' when a record is missing",
    "AttributeError because a dict lookup returned None and I called .strip() on it",
    "TypeError: unsupported operand type(s) for +: 'int' and 'str' from parsed CSV",
    "My loop skips the last element because the range upper bound is wrong",
    "The conditional branch falls through when the coupon is empty, applying the discount twice",
    "Variable defined inside the if-block is referenced outside it and raises NameError",
    "A bare except swallows the real error and the program continues with corrupted state",
    "Calling requests without a timeout and the worker hangs forever on a slow endpoint",
    "Two threads increment the same counter without a lock and the total is wrong",
    "os.path.exists passes but the file is deleted before open() runs",
    "A cache dict grows unbounded because entries are never evicted",
    "User input is interpolated directly into an SQL string, enabling injection",
]

with tab_routing:
    st.subheader("Routing: calls diverted to LLM vs RAG-based retrieval")
    st.write(
        f"Every call is routed by the confidence gate. If the top retrieval score is at or "
        f"above **{core.CONFIDENCE_THRESHOLD}**, the answer is grounded on retrieved "
        f"examples; below it, the call is diverted to the LLM and answered from reasoning "
        f"alone. This runs a fixed set of probe queries through the currently loaded index "
        f"(retrieval only, no generation). It is a routing distribution, not an accuracy score."
    )

    if st.button("Run routing analysis"):
        rag = 0
        route_rows = []
        progress = st.progress(0.0, text="Routing probe queries...")
        for i, q in enumerate(PROBE_QUERIES):
            try:
                cands = core.retrieve(q)
            except Exception as e:
                st.error(f"Routing failed: {e}")
                st.stop()
            top = cands[0]["score"] if cands else 0.0
            is_rag = top >= core.CONFIDENCE_THRESHOLD
            rag += is_rag
            route_rows.append({
                "query": q[:55] + ("..." if len(q) > 55 else ""),
                "top_score": round(top, 3),
                "routed_to": "RAG retrieval" if is_rag else "LLM (diverted)",
            })
            progress.progress((i + 1) / len(PROBE_QUERIES))
        progress.empty()

        total = len(PROBE_QUERIES)
        diverted = total - rag
        c1, c2 = st.columns(2)
        c1.metric("RAG-based retrieval", f"{rag}/{total}", f"{rag / total * 100:.0f}%")
        c2.metric("Diverted to LLM", f"{diverted}/{total}", f"{diverted / total * 100:.0f}%")
        st.bar_chart(
            {"RAG-based retrieval": [rag], "Diverted to LLM": [diverted]},
            color=["#2e7d32", "#c62828"],
        )
        st.dataframe(route_rows, width="stretch", hide_index=True)
    else:
        st.caption("Click to route the probe set against the loaded index (embeddings only).")