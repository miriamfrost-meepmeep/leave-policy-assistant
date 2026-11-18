# Leave Policy Assistant: a cited answer, or an honest "I don't know"

Miriam Frost, November 2026. My own project, designed and tested end to end.

## The problem

Employees ask HR the same leave questions over and over. In Chicago, three layers of law can apply at once: federal FMLA, the Illinois Paid Leave for All Workers Act, and the Chicago Paid Leave ordinance. A wrong answer about leave is worse than no answer.

So the bar was not "answers everything." It was: **answer only from official sources, show where the answer came from, and say so when the sources don't cover it.**

## What I built

- **Sources:** 3 official documents, split into 77 short passages. The DOL Employee's Guide to the FMLA, the Illinois Department of Labor FAQ, and the City of Chicago FAQ (Version 4.0, September 2025).
- **Search:** finds the passages that best match the question.
- **Answer:** Claude answers only from those passages. Every answer has one of three labels: *answered*, *not in sources*, or *depends* (when location or employer size changes the rule).
- **Guard:** any citation to a passage Claude wasn't given is thrown out.
- **Test set:** 20 questions. 10 the sources answer, 5 they don't, 5 where the answer depends on facts the question leaves out.

## Results

| Run | Answerable | Can't answer | Depends | Total | Cost (20 Qs) |
| --- | --- | --- | --- | --- | --- |
| Baseline | 8/10 | 5/5 | 4/5 | 17/20 | $0.229 |
| + "Sources checked" wording | 9/10 | 5/5 | 4/5 | 18/20 | $0.236 |
| Basic search, rerun | 9/10 | 5/5 | 4/5 | 18/20 | $0.243 |
| **Smart search** | 9/10 | 5/5 | **5/5** | **19/20** | $0.315 |

**It never made up an answer.** 5 of 5 on questions the sources can't answer, in every run. For an HR tool, that's the number that matters most.

## Decisions I made

**1. Sources.** Only the agencies that enforce each law. No law-firm summaries. FAQs and guides over statute text, because they're written the way employees ask. I started with one FMLA guide instead of several fact sheets and planned to add more only if the tests showed gaps. They didn't.

**2. "Sources checked" instead of hiding citations.** When it can't answer, it still shows what it read, labeled "Sources checked (none answer this question)," and starts with "Based on the sources I checked." The employee can see where it looked. Tested: no loss in accuracy.

**3. Fix search, not the prompt.** Two questions kept failing. Before changing anything, I checked whether Claude was wrong or whether it never saw the answer.

- **"I started in Chicago two weeks ago. Can I use Paid Sick Leave yet?"** The answer (the 30th day) was in the Chicago FAQ. Keyword search ranked that passage **22nd of 77**, and Claude only reads the top 6. Claude correctly said "not in my sources," because it wasn't in what it was given.
- **"How much paid leave do I earn each year?"** Search returned **zero Chicago passages**, so Claude couldn't say "it depends on whether you work in Chicago."

Both were search failures. Claude behaved correctly with what it had.

**4. Test cheap fixes for free first.** Search runs locally at no cost, so I checked options before spending anything:

| Option | Result |
| --- | --- |
| Read 12 passages instead of 6 | No. The right passage ranked 22nd. |
| Take the top passages from each law | Fixes the Chicago coverage case. Not the other (13th of 23 Chicago passages). |
| Rewrite the question in the documents' words | Moved the right passage from **22nd to 1st** with a hand-written rewrite. |

I built "smart search": Haiku rewrites the question, then search takes 2 passages from each law plus the best 2 overall.

## Trade-offs and what didn't work

- **Cost up 30%** ($0.016 vs $0.012 per question) for 1 more correct answer out of 20.
- **The Chicago coverage fix is solid.** Balancing by source is a rule, so it works every time.
- **The vocabulary fix is not.** The rewrite fixed the "two weeks ago" question in a single test, then missed it in the full run and in a later spot check. Haiku drifted to its own words ("eligibility") instead of the document's ("begin using"). Improved, not solved.
- **My first retrieval check was too coarse.** It checked for the right document, not the right passage. Lesson: measure retrieval at the passage level.
- **Sources go stale.** The Chicago FAQ I first picked (2024) had been taken down by the time I used it. A real product needs a freshness check on its sources.

## Limits

- 20 questions, one run per setup. Results vary between runs.
- Costs are estimates from token counts, not billing.
- General information only. Not legal advice.

## What I'd do next

- Meaning-based search (embeddings) for the vocabulary gap, or a fixed glossary of document terms for the rewrite.
- Run each setup 3 times and report the range, not one number.
- Grow the test set to 50 questions, including Cook County and employer-size edge cases.
- A monthly check that every source URL still works and hasn't changed.
