# Policy Assistant: "The Policy That Changed"

Offline question-answering over three conflicting policy documents. No API key, no network, standard library only (Python 3.8+).

## Run
```bash
python3 demo.py        # the 8 required questions (Q1-Q8) with answers and citations
python3 run_eval.py    # 21 own eval questions (13 adversarial) -> score table
```
```python
from policy_qa import ask
ask("Can a customer pay Rs.1,00,000 twice in one day?", "2026-08-15")
# -> {"answer", "status", "resolution", "citations": [{"document","clause","text"}], "calculation", "as_of_date"}
```
`ask(question, as_of_date, context=None, holidays=())`. `context` carries an earlier question for follow-ups like "same merchant" (needed for Q3). `holidays` is an optional list of bank-holiday dates for working-day maths.

## How it works
- `policy_qa/docs.py`: parses the three markdown files into clauses (master `2.3`, circular items `A`-`F`, FAQ `Q1`-`Q5`). Holds the amendment table (item -> clause -> action -> effective date) and `in_force(clause, date)`, which returns the original, replaced or deleted version. `cite()` raises on any clause that does not exist, so a clause number cannot be invented.
- `policy_qa/calc.py`: all arithmetic (Decimal, never floats): MDR, cap, GST, working-day counting, date-dependent rates and caps.
- `policy_qa/assistant.py`: hand-written keyword rules, one handler per question type. Unrecognised questions return `CANNOT_ANSWER`.

Key reasoning rules: the circular wins over the master only from its effective date (1 Aug, item D 1 Sep, not the 20 Jul issue date); the master and circular win over the FAQ, which is a stale summary; missing information gives `CANNOT_ANSWER`.

## What works
All of Q1-Q8, plus date-boundary, false-premise, deleted-clause, non-existent-clause and pre-policy-date cases (see `eval.json`).

## What doesn't
Keyword matching is brittle: paraphrases without the expected words get `CANNOT_ANSWER` (safe, but unhelpful). See `WHERE_IT_BREAKS.md` and `DECISIONS.md`. The eval set was written by the same author as the rules, so 21/21 overstates real-world accuracy.
