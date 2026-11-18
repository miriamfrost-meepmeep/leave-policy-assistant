"""Score the assistant on the 20 test questions.

    python run_eval.py baseline        # the label names the results file

A question passes when the status is right, it cites at least one expected
source (answered and depends questions), and every keyword appears in the answer.
"""
import json
import sys
from pathlib import Path

from assistant import ask, CHUNKS

ROOT = Path(__file__).resolve().parent
label = sys.argv[1] if len(sys.argv) > 1 else "run"
by_id = {c["chunk_id"]: c for c in CHUNKS}
questions = json.load(open(ROOT / "questions.json"))

rows, total_cost = [], 0.0
for q in questions:
    try:
        r = ask(q["q"])
    except Exception as e:
        r = {"status": "error", "answer": str(e), "citations": [], "retrieved": [], "cost_usd": 0}
    total_cost += r["cost_usd"]
    cited = {by_id[c]["source_id"] for c in r["citations"]}
    found = {by_id[c]["source_id"] for c in r["retrieved"] if c in by_id}
    status_ok = r["status"] in q["status"]
    source_ok = not q["sources"] or bool(cited & set(q["sources"]))
    retrieval_ok = not q["sources"] or bool(found & set(q["sources"]))
    keyword_ok = all(k.lower() in r["answer"].lower() for k in q["keywords"])
    passed = status_ok and source_ok and keyword_ok
    why = [n for n, ok in [("status", status_ok), ("source", source_ok), ("keyword", keyword_ok)] if not ok]
    if not retrieval_ok:
        why.append("retrieval")
    rows.append({**q, "got_status": r["status"], "answer": r["answer"], "cited": sorted(cited),
                 "retrieval_ok": retrieval_ok, "passed": passed, "why": why, "cost_usd": r["cost_usd"]})
    print(f"{'PASS' if passed else 'FAIL'}  {q['id']}  [{r['status']}]  {', '.join(why)}")

print()
for t in ["answerable", "unanswerable", "conflict"]:
    group = [r for r in rows if r["type"] == t]
    print(f"{t:13} {sum(r['passed'] for r in group)}/{len(group)}")
passed = sum(r["passed"] for r in rows)
print(f"{'total':13} {passed}/{len(rows)}   est. cost ${total_cost:.3f}")

out = ROOT / "results"
out.mkdir(exist_ok=True)
(out / f"eval_{label}.json").write_text(json.dumps(rows, indent=1))
print(f"details saved to results/eval_{label}.json")
