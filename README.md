# Leave Policy Assistant

Answers employee leave questions using only official sources, cites where each
answer came from, and says so when the sources don't cover the question.

Sources (public): the U.S. DOL Employee's Guide to the FMLA, the Illinois Paid Leave for All
Workers Act FAQ, and the City of Chicago Paid Leave and Paid Sick and Safe Leave
FAQ. See `sources.json`.

General information only. Not legal advice.

## Run it

```bash
pip install -r requirements.txt
python fetch_docs.py                     # download and split the sources
python assistant.py "Is FMLA leave paid?"
python run_eval.py smart                 # score all 20 test questions
SEARCH=basic python run_eval.py basic    # same, with plain keyword search
```

## How it works

1. `fetch_docs.py` downloads each source and splits it into passages of about 160 words.
2. `assistant.py` finds the 6 passages that best match the question (BM25 keyword search),
   then asks Claude to answer from those passages only, as JSON: a status
   (`answered`, `not_in_sources` or `depends`), the answer, and the passage IDs it used.
   Citations to passages it was not given are dropped.
3. `run_eval.py` scores 20 questions: 10 answerable, 5 the sources can't answer,
   and 5 where the answer depends on facts like location or employer size.

## Results

Smart search: 19/20. Never made up an answer (5/5 on questions the sources can't answer, every run). See [CASE_STUDY.md](CASE_STUDY.md).
