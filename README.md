# RelayDesk | A forward-deployed AI field lab

Two fictional retailers share a returns desk. An agent asks, "What is the standard return window?" On June 30 the Northstar answer is **14 days**; on July 1 it is **30**. Harbor's answer is **21**. RelayDesk gives the agent one exact, versioned policy excerpt or explains why a human must take over. It does not decide eligibility, retrieve order records, send replies, or move money.

**Start here:** [16-week build and fieldwork plan](docs/field-course/plan.md) · [original eight-week customer engagement](docs/engagement-plan.md) · [45-minute week-one workbook](docs/week-one-workbook.md) · [operator and maintainer runbook](docs/operator-runbook.md). For an offline, printable edition, open [docs/field-course/plan.html](docs/field-course/plan.html) in a browser after cloning. The reference implementation is complete; the measurements, incidents and release decisions in the course are **your** work.

**Companion lab:** [Breakwater: the bank outage evidence lab](labs/breakwater/) asks what a fictional Australian bank can tell its incident commander at three points during a payments outage. Try the tabletop first, then compare your briefs with the [step-by-step solution](labs/breakwater/SOLUTION.md).

## Get it running

Use CPython **3.11 or newer** with SQLite support and Git (or download and extract this repository's ZIP). No API keys, model download, GPU, database server or `pip install`. Only obtaining the repository requires network access. Run from the directory that contains `relaydesk/` and `data/`.

```shell
git clone https://github.com/xavierxmorris/fde-ai-field-lab.git
cd fde-ai-field-lab
python -m relaydesk demo
python -m relaydesk eval
python -m unittest discover -s tests -v
```

If `python` is not the installed interpreter, use `py -3` on Windows or `python3` on macOS/Linux. See [step-by-step setup](docs/field-course/plan.md#day-zero-set-up-a-reproducible-desk) for a clean virtual environment, a SQLite check and common errors. The three demo stops should show `NS-RET-1` then `NS-RET-2`, `HB-RET-1`, and a `multiple_topics` handoff. Demo, triage and eval do not write a queue.

## Work one synthetic ticket

```shell
python -m relaydesk triage northstar 2025-07-01 "What is the return window?" --trace
python -m relaydesk submit lab-001 northstar 2025-07-01 "What is the return window?"
python -m relaydesk pending
python -m relaydesk review lab-001 reject --note "Practicing manual fallback."
python -m relaydesk show lab-001
```

Run the same `submit` twice: you get one record. After review, replay returns the stored decision; changing the input under `lab-001` is an error. Accepting a draft only records an operator decision. Queue commands store **unencrypted synthetic text** in `.relaydesk/review.sqlite3`, excluded from Git. Put `--db PATH` or `--data-dir DIR` **before** the subcommand to isolate experiments.

## What the benchmark shows

The same 34 independently labeled synthetic tickets go through both systems. Coverage counts **correct drafts / answerable tickets**; a false draft is a draft on a ticket that required handoff. The wrong-citation count includes citations on must-handoff tickets.

| Pipeline | Correct disposition + evidence | Correct citation coverage | False drafts | Wrong citations / citations |
|---|---:|---:|---:|---:|
| Tenant/date-scoped lexical baseline | 21/34 | 17/17 | 13/17 | 13/30 |
| Gated, review-only candidate | 31/34 | 14/17 | 0/17 | 0/14 |

The candidate clears the fixture gate (at least 80% coverage; no false drafts, wrong citations or invalid envelopes), **but hands off three answerable questions**. `eval` prints their IDs, all denominators and retailer/intent/answerability slices; `eval --json` is suitable for comparisons. This is not a production safety rate or a measured time saving. Fork or branch for experiments; do not teach the frozen questions to the model.

## Where to start reading code

| File | Question it answers |
|---|---|
| [`data/policies.jsonl`](data/policies.jsonl) | What was actually in force for this retailer and date? |
| [`relaydesk/model.py`](relaydesk/model.py) | How are word likelihoods learned from 36 labeled examples? |
| [`relaydesk/engine.py`](relaydesk/engine.py) | Which conditions can veto the top-ranked excerpt? |
| [`relaydesk/review.py`](relaydesk/review.py) | Why does a retry not produce a second review task? |
| [`relaydesk/evaluation.py`](relaydesk/evaluation.py) | How can plausible but wrong evidence fail a release? |
| [`tests/`](tests/) | What happens when evidence overlaps, expires, or someone reviews twice? |
