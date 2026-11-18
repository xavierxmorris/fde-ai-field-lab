# Breakwater: solve the payments-outage case

Your job is to brief a human incident commander three times on 14 October 2026. **Write what the bank could substantiate at each cutoff, not what you know in hindsight.** A payment gateway can be healthy while customers still cannot send money. Likewise, "we don't know how many instructions were lost" is different from "none were lost."

This is a fictional Australian bank, its **internal** tolerance register, and synthetic evidence. The software does not decide whether a regulator must be notified. For the regulatory context and the full 12-week assignment, use the [field guide](plan.md).

## 1. Get to the right directory

Use Python 3.11 or newer. From a terminal, for a new checkout:

```shell
git clone https://github.com/xavierxmorris/fde-ai-field-lab.git
cd fde-ai-field-lab/labs/breakwater
python --version
```

If you already have the current repository, start in `labs/breakwater` rather than cloning again. No package install, API key or cloud account is needed. Substitute `py -3` on Windows or `python3` on macOS/Linux if `python` isn't found. If Python can't find `desk.py`, check that your current folder contains both `desk.py` and `case.json`.

## 2. Make a blank brief before running the reference

Open [case.json](case.json). For each cutoff, make a **new** copy of this five-line worksheet. Start a timer before looking up the first receipt. Record minutes through human review, not just time spent searching.

```text
Case: PAY-07 | Entity: TM-AU | Reader: ops | Cutoff (UTC): ____ | Policy: ____
Disruption duration: value or UNKNOWN | threshold | receipt(s) | owner if unknown
Permanently lost instructions: value or UNKNOWN | threshold | receipt(s) | owner if unknown
Fallback batch FB-1: accepted / eligible | threshold | receipt(s) | owner if unknown
Message to commander: what we know; what we cannot say; who should act next.
```

Read `observed` as **when it happened** and `received` as **when the desk could use it**. Exclude cards from another bank, incident, or audience before searching. Then exclude anything with either timestamp after the cutoff. Don't expose excluded text or receipt IDs in the brief, even to explain their absence.

## 3. Pick one policy, then one authority per claim

The outage starts on **14 October**. P4 had been published by then, but it does not take effect until **1 November**. Use **P3** for all three briefs: at most **45 minutes** of disruption, at most **0 permanently lost instructions**, and at least **80%** of eligible instructions accepted in the fixed fallback batch. Equality meets a boundary.

| What you want to say | What would support it | What is not enough |
|---|---|---|
| "Outbound payments recovered at this time." | An end-to-end restoration receipt from `payments-control`, paired with its start receipt for duration. | A provider's green gateway, elapsed time at cutoff, or time the desk received the notice. |
| "No instructions were permanently lost." | A final count from `reconciliation`. | No visible loss report, an interim workpaper, or an inference from the fallback percentage. |
| "FB-1 met its service floor." | `fallback-control`'s accepted and eligible counts for FB-1, with a nonzero denominator. | Counting all payments in the incident or choosing the highest of two counts. |

## 4. Solve the 08:25 brief: resist the green dashboard

Cover later receipts. E01 establishes a start at 08:00; E02 reports component recovery, not an end-to-end restoration. E03 supplies the only usable service calculation: `80 / 100 = 80%`. No eligible final loss count or end time is available.

```shell
python desk.py search 08:25 "gateway recovered"
python desk.py brief 08:25
```

**Checkpoint:** search finds E02; the brief still returns `INCOMPLETE`. Duration and loss are `UNKNOWN`; service is `WITHIN`. This is not a contradiction: search answers *where someone said it*, not *who can verify the claim*.

**What to tell the commander:** "The provider reports its gateway is green. We cannot yet confirm outbound payments recovery or final loss. FB-1 is at the 80% floor; payments control owns restoration evidence and reconciliation owns the loss count."

## 5. Solve the 08:55 brief: escalate the known exception

```shell
python desk.py brief 08:55
```

E04 is now available. It was **observed at 08:48** and **received at 08:53**. Subtract the start observation in E01: `08:48 - 08:00 = 48 minutes`, **3 minutes over** P3. Do not calculate 53 minutes using the receipt clock. FB-1 is still 80/100. E05 was observed at 08:50 but arrives at 09:03, so loss is **still unknown**.

**Checkpoint:** `FLAG_FOR_REVIEW` is correct even with an unknown field. Say: "End-to-end service was restored after 48 minutes, outside the bank's 45-minute tolerance. Flag this to the incident commander and Operational Risk now; reconciliation is outstanding." Do not wait for E05 to escalate and do not infer a reporting decision.

## 6. Solve the 09:10 brief: revise without rewriting history

```shell
python desk.py brief 09:10
python desk.py brief 08:25
```

E05 now establishes **0 permanently lost instructions**. E06, received at 09:08, explicitly **supersedes E03** for FB-1. Calculate `79 / 100 = 79%`, **1 percentage point below** the floor. Do not average the two figures or add their denominators. Duration remains 48 minutes.

**Checkpoint:** the new brief flags **two** internal exceptions, duration and fallback service. The rerun for 08:25 must still cite E03 and show 80%. Tell the commander: "Final reconciliation confirms zero permanent loss. The corrected fallback batch missed the service floor; both that and the duration exception go to Risk for review."

## 7. Prove you understand the failure modes

Run the reference checks, then make one controlled change **in memory**, leaving the original case file untouched:

```shell
python -m unittest -v test_desk
python -c "from desk import load_case, brief; c=load_case(); next(r for r in c['cards'] if r['id']=='E06').pop('supersedes'); print(brief(c,'09:10')['measures']['fallback_service'])"
```

Predict the second output first. Without a link there are **two competing authoritative receipts**, not a proven correction. The result should be `UNKNOWN`, with `fallback-control` as owner. If your own implementation chooses 79 just because it arrived last, fix conflict handling before tuning the ranker.

For code reading, trace [desk.py](desk.py) in this order: `visible` selects what this reader could know; `search` ranks those notes; `fact` chooses an authorised receipt or explains why it cannot; `brief` resolves policy and compares the values. Notice that `brief` does **not** require a search hit. An empty top-three list must never become evidence of zero loss.

## 8. Go beyond the answer key: solve the FDE assignment

The three briefs demonstrate the reference, not the value of an AI pilot. Use the [weekly assignments](plan.md) to work through this sequence:

| Stage | Do this next | What to hand to the customer |
|---|---|---|
| Weeks 1-3: agree what counts | Have a peer independently write the three briefs. Resolve disagreements on who can declare restoration and what counts as loss. Draw separate event and receipt timelines. | A signed-off **simulation** contract: claim, authorised source, unit, access rule, unknown owner. |
| Weeks 4-6: improve evidence search | Label the permitted relevant receipt IDs for 15 queries before looking at results. Run exact word matching and the TF-IDF baseline on the same permitted cards. Try **one** change on development data, such as a reviewer-approved alias for a provider term. Keep `brief` independent. | A before/after sheet: query, expected IDs, returned top three, irrelevant hits, reviewer time. For two relevant IDs with one in the top three, recall@3 is `1/2`, not `1/3`. Show a failure as well as a win. |
| Weeks 7-9: exercise human review | Design separate preparer and reviewer roles. Bind review to one packet version; deliver a late correction and reproduce the old packet. Test manual fallback with search unavailable. Freeze at least 24 labelled snapshots across six distinct synthetic incidents; split by incident, not wording. | A before/after packet pair, one rejected self-approval in your harness, a manual brief, and a failure ledger. These controls are assignments, not features of the supplied CLI. |
| Weeks 10-12: decide whether to pilot | Time at least 20 matched manual/assisted tasks, counting corrections and review. For each pair compute `100 * (manual_minutes - assisted_minutes) / manual_minutes`; report the median and slower cases. Count prohibited citations, false assurances and missed exceptions separately. | One page: **go, limited go, or no-go for synthetic shadow use**, with sample size, worst case, owner and reversal trigger. Any prohibited citation, false assurance or missed confirmed exception stops candidate use; the manual bridge keeps running. |

**Done means** an independent reviewer can reproduce each brief, challenge every claim by receipt and cutoff, and operate without the AI. A simpler system or a no-go is a valid solution if the measurements support it.
