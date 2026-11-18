"""Step 1: download the official documents and cut them into small passages.

    python fetch_docs.py

Writes docs/<id>.txt (the full text) and docs/chunks.json (the passages the
assistant searches). If a site blocks the download, save the page from your
browser as a PDF named docs/<id>.pdf and run this again.
"""
import io
import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
WORDS_PER_CHUNK = 160


def pdf_text(data):
    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)


def html_text(data):
    soup = BeautifulSoup(data, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()
    main = soup.find("main") or soup.find(id="main-content") or soup.body or soup
    return main.get_text("\n")


def clean(text):
    text = re.sub(r"[ \t\xa0]+", " ", text)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def get_text(source):
    local_pdf = DOCS / f"{source['id']}.pdf"
    if local_pdf.exists():                       # a copy you saved by hand wins
        return pdf_text(local_pdf.read_bytes())
    resp = requests.get(source["url"], headers=HEADERS, timeout=60)
    resp.raise_for_status()
    if source["url"].lower().endswith(".pdf") or resp.content[:4] == b"%PDF":
        return pdf_text(resp.content)
    return html_text(resp.content)


def chunk(text, source):
    """Group lines into passages of about WORDS_PER_CHUNK words."""
    chunks, current, count = [], [], 0
    for line in text.splitlines():
        current.append(line)
        count += len(line.split())
        if count >= WORDS_PER_CHUNK:
            chunks.append(" ".join(current))
            current, count = [], 0
    if current:
        chunks.append(" ".join(current))
    return [{"chunk_id": f"{source['id']}#{i + 1}", "source_id": source["id"],
             "level": source["level"], "title": source["title"], "url": source["url"],
             "text": c} for i, c in enumerate(chunks)]


if __name__ == "__main__":
    sources = json.load(open(ROOT / "sources.json"))
    all_chunks = []
    for source in sources:
        try:
            text = clean(get_text(source))
        except Exception as e:
            print(f"FAILED  {source['id']}: {e}")
            print(f"        Save {source['url']} from your browser as docs/{source['id']}.pdf, then rerun.")
            continue
        (DOCS / f"{source['id']}.txt").write_text(text)
        pieces = chunk(text, source)
        all_chunks += pieces
        print(f"ok      {source['id']}: {len(text.split()):,} words, {len(pieces)} passages")
    (DOCS / "chunks.json").write_text(json.dumps(all_chunks, indent=1))
    print(f"\n{len(all_chunks)} passages saved to docs/chunks.json")
