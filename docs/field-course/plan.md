# RelayDesk: a 16-week forward-deployed AI engineering project

**Assignment:** spend four months helping a fictional support desk decide whether AI-assisted policy lookup is worth adopting. Budget 5-7 hours a week (80-112 hours total). The [eight-week engagement](../engagement-plan.md) is the customer contract. Weeks 9-16 are a second engagement: the sponsor asks for expansion and you have to justify, constrain, or decline it. A well-supported **no-go** is a passing outcome.

**Two ways to work:** If this is your first AI project, run the reference and change one behavior per week on your own branch. If you already build services, write the contract tests first, implement a replacement behind `Engine.triage`, then compare it to the reference on exactly the same tickets. Neither track requires a hosted model, real customer data or an account with a cloud provider.

## Day zero: set up a reproducible desk

1. Install Git and a maintained CPython 3.11+ build with SQLite and `venv`. Keep one terminal open for the exercise. Check your interpreter, not just the one selected in your editor. Windows: `py -3 --version`; macOS/Linux: `python3 --version`.
2. Obtain the public repository. To use a ZIP instead, download it from the repository's Code menu, extract it, then open a terminal in the folder containing `README.md`, `data` and `relaydesk`. Do not run these commands inside `relaydesk/`.

```shell
git clone https://github.com/xavierxmorris/fde-ai-field-lab.git
cd fde-ai-field-lab
git rev-parse --short HEAD
```

3. Make an isolated environment. There is deliberately nothing to install into it. These commands do not require activation, admin rights, a changed PowerShell execution policy or access to a package index.

**Windows PowerShell**

```powershell
py -3 -m venv --without-pip .venv
.\.venv\Scripts\python.exe -c "import sys,sqlite3; print(sys.version.split()[0], sqlite3.sqlite_version)"
.\.venv\Scripts\python.exe -m relaydesk demo
.\.venv\Scripts\python.exe -m relaydesk eval
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

**macOS / Linux**

```sh
python3 -m venv --without-pip .venv
.venv/bin/python -c "import sys,sqlite3; print(sys.version.split()[0], sqlite3.sqlite_version)"
.venv/bin/python -m relaydesk demo
.venv/bin/python -m relaydesk eval
.venv/bin/python -m unittest discover -s tests -v
```

4. Below, `python` means the same executable from step 3. If you see `No module named relaydesk`, check the working directory. If `sqlite3` is unavailable, choose your platform's full CPython distribution. If `venv` is not present, install your distributor's `venv` component or use a full interpreter directly; there are no third-party packages to isolate.
5. Record the Git revision, interpreter, demo card IDs, coverage and false-draft fractions. Use the [workbook](../week-one-workbook.md) to time manual work before practicing the answers. Keep notes on synthetic cases only. Start experiments with `git switch -c learner/field-notes` in your own clone. Keep the reference revision for side-by-side comparisons.

**Ready check:** Northstar changes from 14 to 30 days **on** July 1, Harbor stays at 21, the two-topic question produces no excerpt, the candidate passes the fixture gate and tests end in `OK`. If the baseline prints `FAIL` while acceptance prints `PASS`, the lab is behaving as designed.

## How one request really runs

Trace it with `python -m relaydesk triage northstar 2025-07-01 "What is the standard return window?" --trace`. Change only the date, then only the retailer. Read the output before reading the code.

| Stage and source | Implementation detail | A useful failure to reproduce |
|---|---|---|
| Ingest, `data/policies.jsonl` and `engine.Card.parse` | One JSON object per line, one card per version. The immutable envelope has `id`, `tenant`, `topic`, `version`, `effective_from`, `effective_until` and `excerpt`. IDs must be unique; a null end is open. Strict ISO dates sort in calendar order. | An invalid date or duplicate ID is an input error; an overlap is representable so unaffected topics remain usable. |
| Train, `model.IntentModel` | `Engine.load` reads **only** `training.jsonl` for intent training. Count non-stop words by label. The log score is `log(documents_in_class / total_documents) + sum(log((count(word,class)+1)/(tokens_in_class+vocabulary_size)))`. Ignore unseen features for this score; normalize with a max shift before exponentiating. | The normalized scores are not calibrated probabilities of correctness. A limited vocabulary and conditional-independence assumption make plausible mistakes. |
| Scope and retrieve, `engine.Engine.triage` | Keep `tenant == operator_tenant` and `start <= lookup_date < end` (or no end). Rank only those cards by distinct word overlap against excerpt terms and topic descriptors. Baseline takes the best positive match; stable ID order breaks ties **only for this comparator**. | A nearby policy for an ineligible tenant/date never participates. A top-ranked *eligible* card can still answer the wrong question. |
| Gate, `engine.request_topic` and `Engine.triage` | Check topic anchors, the requested facet (window or first damage step) and unexplained terms; allow regular inflections of known terms. Refuse mixed or unfamiliar input. Require exactly one active card for the topic, agreeing classifier label, score >=0.70, lead >=0.20, and unique, positive retrieval winner. | The parser is deliberately narrow; "send it home" is not a new return alias until an owner defines it. A lexical gate is not proof of semantic entailment on arbitrary English. |
| Cite or hand off | A draft copies the **whole card** including its exact source text. A handoff carries `evidence: null` and an actionable reason. No generated text, eligibility inference or refund integration. | A correct number without the correct card, version and interval is not a correct draft. |
| Review, `review.submit` / `review.review` | Only submission writes an immutable result snapshot; duplicates compare the stored request payload. A draft can be accepted/rejected once. Handoffs are terminal for this assistant, not completed customer service. | Without snapshotting, yesterday's replay could misleadingly quote today's version. |
| Measure, `evaluation.evaluate` | `acceptance.jsonl` supplies independent per-ticket labels; the frozen `_CARDS` oracle supplies expected metadata and exact excerpts, independently of live retrieval. Both pipelines see identical inputs. | Editing a live excerpt without changing its ID is detectable; copying the live corpus into the oracle during scoring would conceal the error. |

**What crosses a boundary:** the CLI receives the supplied identity, date and text. A read-only preview goes from local JSONL files through in-memory model/retriever to the terminal. `submit` adds one local plaintext SQLite record; `review` changes only state and note. The process contacts no external provider. The operator-provided tenant is a teaching convenience, **not an authorization boundary**. In the hypothetical shared service, identity would need to come from an authenticated principal before any retrieval. Do not put this CLI on a network port.

## Weeks 1-4: prove you are solving the right problem

**1. Observe the job (5 h).** Do not begin with a model. Run the workbook's six manual tickets and record seconds, source and reason per ticket; include the three refusals. Interview the sponsor, operator, policy owner and privacy owner, or role-play and mark the answers assumed. Ask, "When you needed the wrong retailer's window, was finding a document the slow step or was identifying the retailer the slow step?" Submit a one-page charter with a named owner, non-goals and a reversible pilot. **Gate:** someone else can state why the tool should not approve an exception.

**2. Make time and identity explicit (6 h).** Copy the fixtures using the [runbook drill](../operator-runbook.md#practice-a-policy-incident-without-touching-the-shipped-data). Build an inventory keyed by `(tenant, topic)` and sort by start date. For each adjacent version, classify `old_end == new_start` as a clean cutover, `<` as a gap, and `>` or no old end as an overlap. Test June 30, July 1 and the first day with no evidence. Ask the policy owner which date has legal/business significance; record that the lab deliberately does not choose it. **Artifact:** data dictionary plus a table of boundary results with exact IDs.

**3. Rebuild the first route (6-7 h).** Write down the candidate IDs *before* scoring them. Independently compute the intersection counts for one question and compare them to `--trace`. Change the question to ask for a personal approval while retaining "return window"; compare baseline behavior in `eval` to the gated response. Use a short development-only phrase and inspect whether the loss occurs at `request_topic`, NB prediction or lexical retrieval. **Gate:** explain in three sentences why neither a high score nor an in-scope document warrants a draft by itself.

**4. Design an acceptance test that can fail (6 h).** Write 20 new synthetic cases before viewing predictions. Give two readers the cards and hide candidate output. Record `id`, `tenant`, `lookup_date`, `question`, `intent`, `topic` and `expected_citation` (ID or JSON `null`). Reconcile disagreements; if wording is ambiguous, record why refusal is expected. Use a separate labeled file based on `data/development.jsonl`, not a modified acceptance file. Run `python -m relaydesk eval --cases your-cases.jsonl --json`. The shipped oracle is pinned to the original two tenants and card versions. **Gate:** count exact references, not similarity or tone; preserve every wrong ID and every lost draft.

## Weeks 5-8: run an operator pilot, not a chatbot demo

**5. Fit into the queue (5 h).** From an empty scratch database, run the following. Record states and row counts; don't infer idempotency solely from a green exit code.

```shell
python -m relaydesk --db .relaydesk/week5.sqlite3 submit sample-17 harbor 2025-07-01 "How do I report damage?"
python -m relaydesk --db .relaydesk/week5.sqlite3 submit sample-17 harbor 2025-07-01 "How do I report damage?"
python -m relaydesk --db .relaydesk/week5.sqlite3 pending
python -m relaydesk --db .relaydesk/week5.sqlite3 submit sample-17 northstar 2025-07-01 "How do I report damage?"
python -m relaydesk --db .relaydesk/week5.sqlite3 review sample-17 reject --note "Practicing manual fallback."
python -m relaydesk --db .relaydesk/week5.sqlite3 review sample-17 accept
python -m relaydesk --db .relaydesk/week5.sqlite3 show sample-17
```

The fourth command **should fail**: changing retailer is not a retry. The sixth **should fail**: the rejection is terminal. Rerun `pending` and expect `[]`. Explain why a state update conditional on `state='pending'` is different from checking the state and later unconditionally writing a decision. **Artifact:** an operator walkthrough and one observed objection.

**6. Hold an incident drill (6 h).** Use scratch data only. Introduce a conflicting Northstar return card, a historical gap, then an unfamiliar paraphrase batch. Change one variable at a time. Record first symptom, affected tenant/date/topic, current pending drafts, owner and time spent in manual mode. Fix or discard the scratch fixtures; replay the same incident cases and frozen suite. **Gate:** an operator, not the engineer, can stop submissions, reject obsolete snapshots and safely restart from known-good evidence.

**7. Find the real bottleneck (5-6 h).** Time ten matched synthetic tasks manually and assisted, alternating which method goes first. Include reading, policy lookup, rejections and the manual work for handoffs. Preserve raw paired timings. Compute median seconds by method and report sample size and order effects. Separately estimate peak staffing: at 240 arrivals/hour, 40% handoff at four minutes and 60% drafts at one minute require `(96*4+144*1)/60=8.8` reviewer-hours/hour, before breaks. **Gate:** the 25% time-saving hypothesis is accepted, narrowed or rejected using observations, not the demo speed.

**8. Deliver and hand over (5 h).** Give a peer only the runbook. Have them update a policy in a scratch copy, catch an overlap and explain why an old accepted snapshot should not be rewritten. Ask the sponsor for go/limited go/no-go, scope, owners, rollback triggers and review date. If working alone, record sign-off as simulated. **Artifact:** portfolio packet with timing, worst counterexample, incident timeline and pilot memo. This completes the original engagement.

## Weeks 9-12: the sponsor asks for more scale

These are **learner extensions**, not shipped infrastructure. Continue on your own branch and record a new decision each week. Keep the reference implementation and original acceptance set intact.

**9. Build a repeatable workload (5 h).** Load `Engine` once, then cycle 100 synthetic cases. Use `perf_counter_ns`, save data-load/training time separately and sort per-call samples for warm p50/p95. Repeat five runs, record interpreter and commit; variation matters. This snippet is valid in a Python REPL from the repository root (or as a temporary script in the root). It measures resident triage, **not** CLI startup, database service or operator time.

```python
from itertools import cycle, islice
from statistics import median
from time import perf_counter_ns
from relaydesk.engine import DATA, Engine
from relaydesk.model import json_rows

cases = list(json_rows(DATA / "development.jsonl"))
start = perf_counter_ns()
engine = Engine.load()
load_ms = (perf_counter_ns() - start) / 1e6
elapsed = []
for case in islice(cycle(cases), 100):
    start = perf_counter_ns()
    engine.triage(case["tenant"], case["lookup_date"], case["question"])
    elapsed.append((perf_counter_ns() - start) / 1e6)

print("load ms", load_ms, "warm n", len(elapsed),
      "p50 ms", median(elapsed), "p95 ms", sorted(elapsed)[94])
```

**Gate:** show why reducing warm inference by half might not move end-to-end handling time. Don't claim a latency service-level objective from a five-card laptop test.

**10. Design and test an index (6-7 h).** Generate synthetic copies for 10, 100 and 1,000 retailers with distinct tenant keys and card IDs in scratch data. Compare the list scan with a Python dictionary from `(tenant, topic)` to intervals. For a database alternative propose an index beginning with `(tenant, topic, effective_from)` and an explicit end-date predicate. Query *all* applicable versions; "latest row wins" hides overlaps. **Artifact:** latency and memory at each size, including build cost. **Gate:** the two implementations return identical IDs or handoffs for cutovers, gaps, overlaps and other tenants; one faster run alone does not justify an index.

**11. Handle vocabulary drift (5-7 h).** Ask a second person to paraphrase ten supported and ten unsupported requests without seeing training examples. Freeze them. In a separate development batch try either a scoped alias or additional labeled training examples; change only one lever. The training label `unsupported` and the explicit scope gate are not interchangeable. Compare old/new coverage and false drafts in both corpora and inspect all changed IDs. **Gate:** a wrong-tenant or wrong-version draft blocks the change regardless of average improvement. Keep a conservative refusal if you cannot express a reliable boundary.

**12. Compare a retrieval alternative fairly (6 h).** Implement a scratch term-frequency/inverse-document-frequency or BM25-style scorer behind the scoped ranker; document your token normalization, smoothing, tie policy and corpus used for document frequencies. Use exactly the same scope filter and evaluation harness. An embedding service is a design option, not required. Estimate what would need rebuilding on a policy edit and how stale versions are evicted. **Gate:** demonstrate an example the alternative fixes, one it worsens, its cost, and whether the difference is large enough to keep it. A negative result is useful.

## Weeks 13-16: build an adoption and operations case

**13. Treat a policy release like a migration (6 h).** Stage a new Harbor version effective on a chosen future date in separate data and gold manifests. Test the previous day, first day, a date long after the cutover and the unaffected Northstar tenant. Record a manifest revision in your experimental result envelope; submit a ticket before the change and prove replay returns the original snapshot afterward. Deliberate re-triage needs a new attempt ID. **Gate:** point an operator back to the prior corpus and reproduce a known ticket byte-for-byte, without reverting unrelated work.

**14. Recover from queue pressure (6 h).** Load a synthetic hour of arrivals into an isolated SQLite file. Mix drafts, handoffs, duplicate delivery and conflicting reuse. Model a reviewer going offline mid-hour. Count arrivals, pending drafts, handoffs and completed reviews separately; do not make manual work disappear when it isn't in `pending`. Simulate draining the backlog with different reviewer counts, then justify a cap or narrower pilot. **Gate:** account for every unique request and preserve every terminal decision. Discuss which uniqueness/transaction guarantees must survive a multi-user redesign.

**15. Defend a deployment design without deploying it (5-6 h).** Sketch a production trust boundary: authenticated tenant identity, scoped policy store, idempotent submission, human review and a manual fallback. Specify fields permitted in logs, deletion owner, stale-policy alert, maximum sustainable backlog and a cost cap per **accepted**, not generated, draft. Compare offline lexical, hosted retrieval and hosted generation. For the latter, specify an evidence verifier and what happens on timeout or policy mismatch. **Gate:** state what changes, what stays forbidden and which owner can stop the rollout. Do not provision resources or send data anywhere for this exercise.

**16. Conduct the second customer handoff (5 h).** Ask someone else to run the clean setup, five representative lookups and one unfamiliar case. Time their recovery from the week-six incident. Present the paired-time evidence, queue economics and a diff of the original versus extended evaluation. End with a decision: expand one retailer/topic, hold the original scope or stop. Supply a named owner, measured trigger and reversal steps. **Artifact:** a two-page field report and ten-minute live demonstration, including a refusal chosen by your reviewer.

## Field notebook and release review

At the end of each week, preserve four short entries: **what the customer decided**, **which commit/data set was tested**, **one result with its denominator**, and **what would reverse the decision**. Record observations separately from targets. Suggested columns: `case ID | expected card/handoff | observed result | reason layer | time including fallback | disposition owner`. Never put production tickets in this public project.

On the shipped synthetic acceptance set, scoped retrieval finds all 17 answerable excerpts but drafts on 13 of 17 required handoffs. Gating reduces those false drafts to 0/17 at the cost of three needless transfers, giving 14/17 correct citation coverage. During development the first candidate covered only 11/17; general inflection handling and recognizing delivery terms across both topics improved it without changing the labels. The frozen set has now informed a development decision: use **fresh, blind cases** for any subsequent pilot claim.

A final review should answer: **Who benefits and who absorbs the extra work? Which policy and model were live? What failed closed? What happened to pending drafts during rollback? What does the evidence still not establish?** If the only answer is "the demo ran," keep the pilot closed.

Setup references: [Python virtual environments](https://docs.python.org/3/library/venv.html) and [Python's SQLite interface](https://docs.python.org/3/library/sqlite3.html), consulted 2026-11-18. The lab uses only local standard-library APIs.
