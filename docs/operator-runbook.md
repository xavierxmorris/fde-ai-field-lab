# RelayDesk operator and maintainer runbook

## At the desk

1. Use a made-up ticket only. Establish **retailer** and **policy lookup date** before reading any excerpt. They are operator inputs, not inferred order/delivery dates. An unknown retailer produces no evidence. Do not select another retailer or today's date to get an answer.
2. Preview with `python -m relaydesk triage harbor 2025-07-01 "How do I report damage?"`. Expect `HB-DMG-1`, version `1`, starting `2025-03-01`, plus its exact text. Repeat with `2025-02-28`: Harbor has a returns card already but **no damage card**. Expect `no_applicable_policy`.
3. If the task warrants review, use `submit` with a unique ticket-attempt ID. Compare the **entire** question to the **entire** excerpt. Confirm retailer, interval, scope and wording in `data/policies.jsonl`. If you need order status, eligibility, an exception or an additional card, stop and route manually.
4. Accept or reject **the draft only**, never the shopper's request. `review ID reject --note "Second issue needs manual follow-up."` retains the reason locally. `show ID` retrieves accepted, rejected and handoff records; `pending` lists only drafts, not the manual team's backlog.

### What a handoff means

| Reason | What to do next |
|---|---|
| `no_applicable_policy` | Check the supplied retailer and date. Ask the policy owner for the missing version; do not substitute the nearest one. |
| `overlapping_versions` | Stop using this topic for the affected interval. Ask the owner which source applies; ranking cannot answer that. |
| `multiple_topics` | A single excerpt cannot support the whole request. An operator handles the whole ticket or deliberately splits it. |
| `outside_supported_scope` | Check for a case-specific decision, unsupported subject, ambiguous timing or unrecognized language. Answer manually. |
| `uncertain_intent` / `uncertain_retrieval` | The intent and evidence gates did not support a unique draft. Keep a synthetic counterexample in a **development** set, not in acceptance or a live log. |

An error printed to stderr is not a handoff: a malformed date or JSON card is a data/input problem. Exit `0` means the command ran (including a normal handoff); `eval` returns `1` for failed candidate gates; bad CLI input, conflicting IDs or unusable fixtures/database return `2`.

## Record lifecycle, privacy and stop procedure

`submit` inserts either `pending` or `handoff`. Only `pending` can transition to `accepted` or `rejected`. All three terminal states stay terminal. Replaying a known ID returns its current state and **original** versioned snapshot without loading the model, even if policies have since changed. For deliberate re-triage, use a new ID and compare both records.

The SQLite primary key is the request ID across the local desk. The request fingerprint is the canonical JSON payload (tenant, date and question); it is compared for exact equality rather than relying on a hash. `BEGIN IMMEDIATE` serializes insert-or-replay. Review uses a conditional update and checks that one row changed. These local transactions do **not** establish authorization, high availability or multi-user throughput.

**Stop:** do not submit or accept more drafts. Use the policy file/workbook for manual lookup; notify the desk lead and policy owner of the affected scope. There is no daemon, network sender or background queue consumer to turn off. Preserve only the synthetic incident IDs and evidence needed to investigate. Inspect pending records before resuming; a correction to a card does not fix old snapshots. Reject superseded drafts and re-triage with new IDs after validation.

**Retention:** question, retailer, date, snapshot, state and optional note are stored as plaintext in a local SQLite file. Input can also appear in shell history and `--trace` output. There is no secure erasure or automatic retention timer. For the exercise, use a fresh disposable `--db` file per practice session, then close the CLI and delete just that file and its SQLite sidecars from the verified scratch location. This is not a production deletion guarantee. Never publish the database, command history or real tickets.

## Practice a policy incident without touching the shipped data

Place a fresh copy under ignored `.relaydesk/drill`. From the repository root:

```shell
python -c "from pathlib import Path; import shutil; p=Path('.relaydesk/drill'); p.parent.mkdir(exist_ok=True); shutil.copytree('data',p)"
```

`copytree` intentionally fails rather than overwrite an existing exercise. Pick a new folder for the next run. In the copy of `policies.jsonl`, duplicate the `NS-RET-2` row on a **new line**, give it a new `id` and `version`, and change its excerpt. Leave the dates overlapping. Run:

```shell
python -m relaydesk --data-dir .relaydesk/drill triage northstar 2025-07-01 "What is the return window?" --trace
python -m relaydesk --data-dir .relaydesk/drill triage harbor 2025-07-01 "What is the return window?"
python -m relaydesk --data-dir .relaydesk/drill eval
```

Expect a Northstar overlap handoff, an unaffected `HB-RET-1`, and a failed gate if enough previously answerable cases lose coverage. A test failure is evidence, not a reason to edit gold labels. In a separate scratch copy, move `NS-RET-2.effective_from` to `2025-07-02`: July 1 must hand off while June 30 and July 2 still cite their correct versions.

**Recover:** point `--data-dir` back at the original `data` directory. Run `python -m unittest discover -s tests -v`, the original `eval`, and the cutover/other-retailer/affected-date lookups before resuming. Record time to detection, manual mode and recovery. Reject stale pending records; keep the old snapshot to explain why it changed.

## Publish a legitimate new version in your learner branch

Get the policy owner's exact excerpt, tenant, topic, version and inclusive start date. End the preceding card at the new start day; never replace the old card text or reuse its ID. Leave a real historical gap as a gap. Add pre-change, change-day and other-retailer regression cases. Stage the policy change and a separately adjudicated edition of your gold manifest together. The shipped gold manifest in `evaluation.py` intentionally pins even effective intervals: closing an old open interval changes its citation metadata. Keep the original benchmark and oracle reproducible at their original commit, and explain any revised gold outside the router.

**When something seems broken:** `No module named relaydesk` means the interpreter cannot find this checkout; run from the root, not `docs` or its parent. If `sqlite3` is unavailable, choose a CPython build that includes it; there is no project dependency to install. If a database is locked, finish or close the other local writer, then retry with the **same ID**. If a draft is missing from `pending`, inspect it with `show` against the same `--db` path before trying a new submission.
