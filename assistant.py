"""The leave policy assistant: find the right passages, then answer only from them.

    python assistant.py "How many weeks of leave does FMLA give?"

SEARCH=basic  uses the question as typed and the top 6 passages overall (the baseline).
SEARCH=smart  (default) first has Haiku rewrite the question in the documents' own
              words, then takes the top 2 passages from each source plus the best
              2 overall, so every level of law (federal, Illinois, Chicago) is seen.
"""
import json
import os
import sys
from pathlib import Path

import anthropic
from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parent
MODEL = "claude-sonnet-5"
REWRITE_MODEL = "claude-haiku-4-5"
SEARCH = os.environ.get("SEARCH", "smart")
TOP_K = 6           # basic mode
PER_SOURCE = 2      # smart mode: passages guaranteed from each source
EXTRA = 2           # smart mode: best remaining passages overall

CHUNKS = json.load(open(ROOT / "docs" / "chunks.json"))
SYSTEM = (ROOT / "prompts" / "system.md").read_text()
client = anthropic.Anthropic()             # reads ANTHROPIC_API_KEY


def tokens(text):
    return [w for w in "".join(c.lower() if c.isalnum() else " " for c in text).split() if len(w) > 1]


BM25 = BM25Okapi([tokens(c["level"] + " " + c["title"] + " " + c["text"]) for c in CHUNKS])

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["status", "answer", "citations"],
    "properties": {
        "status": {"type": "string", "enum": ["answered", "not_in_sources", "depends"]},
        "answer": {"type": "string"},
        "citations": {"type": "array", "items": {"type": "string"}},
    },
}


def rewrite(question):
    """Turn an employee's question into the words a government FAQ would use."""
    response = client.messages.create(
        model=REWRITE_MODEL,
        max_tokens=100,
        messages=[{"role": "user", "content":
                   "Rewrite this employee question as a short search query using the "
                   "formal words an official leave-law FAQ would use (for example "
                   "'begin using', 'waiting period', 'days of employment', 'accrue', "
                   "'covered employee'). Keep any place names. Reply with the query only.\n\n"
                   f"Question: {question}"}],
    )
    text = next(b.text for b in response.content if b.type == "text").strip()
    cost = (response.usage.input_tokens * 1 + response.usage.output_tokens * 5) / 1e6
    return text, cost


def ranked(query):
    scores = BM25.get_scores(tokens(query))
    return sorted(range(len(CHUNKS)), key=lambda i: scores[i], reverse=True)


def retrieve(question):
    """Returns (passages, search_query, rewrite_cost)."""
    if SEARCH == "basic":
        return [CHUNKS[i] for i in ranked(question)[:TOP_K]], question, 0.0
    rewritten, cost = rewrite(question)
    order = ranked(question + " " + rewritten)
    picked = []
    for source_id in dict.fromkeys(c["source_id"] for c in CHUNKS):
        picked += [i for i in order if CHUNKS[i]["source_id"] == source_id][:PER_SOURCE]
    picked += [i for i in order if i not in picked][:EXTRA]
    picked.sort(key=order.index)
    return [CHUNKS[i] for i in picked], rewritten, cost


def ask(question):
    passages, search_query, rewrite_cost = retrieve(question)
    context = "\n\n".join(f"[{p['chunk_id']}] ({p['level']}) {p['title']}\n{p['text']}" for p in passages)
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=SYSTEM,
        messages=[{"role": "user", "content":
                   f"Passages:\n\n{context}\n\nQuestion: {question}"}],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )
    text = next(b.text for b in response.content if b.type == "text")
    result = json.loads(text)
    known = {p["chunk_id"] for p in passages}
    result["citations"] = [c for c in result["citations"] if c in known]   # drop made-up IDs
    result["retrieved"] = [p["chunk_id"] for p in passages]
    result["search_query"] = search_query
    answer_cost = (response.usage.input_tokens * 3 + response.usage.output_tokens * 15) / 1e6
    result["cost_usd"] = round(answer_cost + rewrite_cost, 4)
    return result


def show(question, result):
    by_id = {c["chunk_id"]: c for c in CHUNKS}
    print(f"\nQ: {question}")
    if result["search_query"] != question:
        print(f"   (searched for: {result['search_query']})")
    print(f"\n[{result['status']}] {result['answer']}\n")
    checked = result["status"] == "not_in_sources"
    if checked and result["citations"]:
        print("  Sources checked (none answer this question):")
    label = "checked" if checked else "source"
    for cid in result["citations"]:
        c = by_id[cid]
        print(f"  {label}: {c['title']} ({cid})\n          {c['url']}")
    print(f"\n  est. cost: ${result['cost_usd']}   search: {SEARCH}")


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "How many weeks of leave does the FMLA give?"
    show(q, ask(q))
