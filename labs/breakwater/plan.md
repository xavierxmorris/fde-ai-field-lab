# Breakwater | The bank outage evidence lab

**A 12-week forward-deployed AI engineering engagement in Australian financial services.** Solo or in pairs; allow 4-6 hours a week. You work inside Tidemark Mutual, a fictional authorised deposit-taking institution. The payments team wants a useful incident brief before its next executive call. Operational Risk wants to be able to reconstruct what the team actually knew at the time. Both are your customers.

> **The opening question:** It is 08:25 UTC. The gateway provider says payments are green. Can the incident commander tell the executive team that outbound payments have recovered? Find the evidence you would stake that sentence on. If it does not exist, write the sentence you *can* defend instead.

## What you get and what you build

| Supplied in this kit | Your engineering work | Explicitly out of scope |
|---|---|---|
| A printable field guide; a synthetic incident with late and conflicting-looking evidence; a versioned tolerance register; an offline Python reference; a tabletop and facilitator key. | Benchmark manual work; compare retrieval approaches; implement and evaluate one AI improvement; design dual review; run a failure exercise; recommend a shadow pilot or a no-go. | Live bank feeds, payment instructions, customer records, real notifications, legal advice, certification, or a decision that a regulatory obligation has or has not been triggered. |

**Day zero.** Unpack the kit. For the paper exercise, nothing else is needed. For the reference, use Python 3.11+; from the folder containing `desk.py`, run `python desk.py brief 08:25`, then `python desk.py search 08:25 "gateway recovered"` and `python desk.py brief 09:10`. On Windows use `py -3` if needed. No packages, network, keys or model download. The reference ranks text and computes a draft from already-structured evidence; it does not pretend to turn arbitrary bank documents into verified facts.

## 1 | Get the customer contract right

| Counterparty | Ask them to show you | Record the decision, not just the answer |
|---|---|---|
| Incident commander | The last brief they had to walk back. Was the cause missing evidence, late evidence, or ambiguous language? | Define each permissible claim, who owns it, and how the manual bridge keeps running when the tool is down. |
| Payments and reconciliation leads | Which signal means the **customer operation** recovered? Who can attest to permanently lost instructions? | Give each fact type one authoritative source in the exercise. A green component is not a restored payment service. An unmatched instruction is not necessarily lost. |
| Operational Risk / Legal | How they receive facts, track the incident clock, and decide whether an obligation needs action. | The desk escalates evidence and uncertainty. These teams retain interpretation and reporting responsibility through their existing process. Never wait for a complete AI brief before alerting them. |
| Privacy, records and internal audit | What proof a reviewer may see, what must be retained, and what must never appear in a general operations packet. | Specify the access basis, retention owner, and audit sample. Audit can reconstruct a packet without receiving restricted source material. |

**Sponsor hypothesis, not a result:** a reviewer can prepare a *defensible* first brief 25% faster than manually, including time correcting drafts, without a single prohibited citation or false assurance in the frozen exercise. Do not equate retrieval speed with time saved by the bank.

### Regulatory anchor versus simulation

The primary reading is [APRA CPS 230 Operational Risk Management](https://www.apra.gov.au/standards/cps-230), in-force version commencing **1 July 2026**, checked **18 November 2026**. Read the sections *Critical operations and tolerance levels*, *Business continuity plan*, *Operational risk incidents* and *Testing and review*. The standard addresses disruption duration, data loss and minimum service levels under alternative arrangements, and includes separate governance, testing and notification requirements.

**APRA does not supply the numbers in this lab.** The fictional operation, source authority, evaluation batch, units, thresholds and release gates below are teaching assumptions. A comparison outside an internal tolerance is a reason for human attention, not software's finding of a legal breach. A comparison inside tolerance is **not** a conclusion that no notification is due. A real institution must validate applicability, triggers, clocks and escalation routes with its own accountable specialists.

## 2 | Run the first 45 minutes without AI

Give one person the incident bridge and another the reviewer chair; if solo, timestamp your first answer before opening the key. All times are UTC on **14 October 2026**. Tidemark's case is `PAY-07`; audience is `ops`. The applicable policy is the approved version effective at incident start and already published by the brief's cutoff.

| Policy | Effective interval: start inclusive, end exclusive | Maximum disruption | Maximum permanently lost instructions | Minimum accepted share of fallback batch |
|---|---|---:|---:|---:|
| P3 | 1 Oct to 1 Nov 2026 | 45 min | 0 | 80% |
| P4 | 1 Nov 2026 onward; already published on 12 Oct | 60 min | 0 | 75% |

For **this exercise only**, fallback service is measured on the reconciled *fixed batch* FB-1, not the entire disruption. The number of eligible unique instructions is the denominator. The equality boundary meets the internal threshold. A zero denominator is unknown, not 100%. The duration calculation needs authoritative start and end observations; while the end is missing the desk does not invent a final duration.

| ID | Observed | Available to desk | Evidence card |
|---|---|---|---|
| E01 | 08:00 | 08:02 | Payments control: outbound operation disrupted. |
| E02 | 08:17 | 08:18 | Provider: gateway component green. No end-to-end assertion. |
| X01 | 08:18 | 08:19 | Another institution and incident: service recovered. Not available for this brief. |
| X02 | 08:20 | 08:21 | Restricted reconciliation workpaper. Outside the ops audience; do not cite even its ID in the brief. |
| E03 | 08:20 | 08:24 | Fallback controller: 80 of 100 eligible FB-1 instructions accepted. |
| E04 | 08:48 | 08:53 | Payments control: end-to-end outbound service restored. |
| E05 | 08:50 | 09:03 | Reconciliation lead: signed final loss count of zero. |
| E06 | 08:20 | 09:08 | Fallback controller corrects E03 for **the same batch**: 79 of 100 accepted. The correction does not change what an earlier reviewer could have known. |

1. **0-10 min:** agree what recovery means. Cover everything not available at 08:25. Draft a three-sentence update with evidence IDs, an unknown and its owner. Start a timer.
2. **10-20 min:** repeat at 08:55. A manager says, "The next policy gives us an hour." Decide which register entry you used and why. Does an unresolved loss count prevent escalation of a known duration exception?
3. **20-30 min:** repeat at 09:10. Identify the changed measures. Can you reproduce the early packet unchanged after seeing the correction?
4. **30-45 min:** compare your packets with the reference and the key at the end. Record manual minutes, any unsupported assertion, and the next person who must act. Keep these teaching snapshots out of the acceptance set.

## 3 | System design: where AI earns its place

```text
Synthetic receipts ----> identity, case, audience and as-of filters
                                     |
                       +-------------+----------------+
                       |                              |
                  rank permitted notes          verified typed facts
                  (AI experiment here)          + effective policy
                       |                              |
                  candidate excerpts              exact arithmetic
                       +-------------+----------------+
                                     |
                           reviewer sees a draft
                     + evidence IDs + gaps + cutoff
                                     |
                         separate human risk process
```

**Make two clocks first-class.** `observed` says when the fact pertains to the operation; `received` says when the desk could know it. Apply both cutoffs, entity, incident and audience *before* building the candidate index. For policy, check approved publication time and effective interval separately. The executable fixes the identity and incident scope to one synthetic desk; a production system must derive them from trusted identity and case entitlements, never from text in a prompt.

**Baseline versus candidate.** The reference uses sparse TF-IDF cosine similarity to rank eligible notes. Try “gateway recovered.” Ranking the provider note is useful for finding what was said; it does not make the note an authority for recovery. The structured comparison deliberately reads **all** eligible authoritative facts regardless of the ranker's top-k. For your experiment, choose a local embedding reranker *or* a constrained extraction model. Compare on the same permitted candidates. For extraction, propose `{fact_type, value, units, source_id, quoted_span}`; reject proposals without an exact matching excerpt and an authorised source. A quote match establishes provenance, not truth. Model failure must leave manual lookup available.

**Packet and conflict contract.** Include scope, cutoff, policy ID, observed values and units, per-measure status and citation IDs, then gaps and owners. Do not silently use the newest row: a later correction needs an explicit same-source, same-fact predecessor. Incomparable eligible facts make that measure unknown. Any established outside-tolerance fact flags the packet even if another measure is unknown; otherwise missing evidence yields an incomplete packet. Only complete internal comparisons with none outside yield a ready-for-review packet. None of these states means “compliant,” “safe,” or “send.”

**Operational design to implement during the course.** Separate the preparer from the risk reviewer. Bind review to an immutable packet version and manifest; a late receipt creates a new revision, not an edit to a signed one. Capture reviewer role, decision, reason, time and previous packet reference. Store raw evidence separately under source permissions. Operational metrics contain case pseudonyms and counts, not transcripts. A hash can detect changed bytes against a trusted reference; it does not authenticate a source, grant access, or by itself make a store immutable. In production, review access, legal holds, deletion, and data residency with actual control owners.

## 4 | Twelve weekly customer engagements

Use the same cadence each week: agree on one decision with its owner; run the smallest experiment that could change it; finish with a five-minute demo of the worst case as well as the best. If a partner plays a customer, record that sign-off as simulated.

| Week | Your assignment | Demo artifact and exit criterion |
|---|---|---|
| **1. Sit on the incident bridge** | Run the tabletop by hand. Interview the commander and Risk separately. Compare the language each considers supportable. | A one-page charter, three timed packets and a named escalation owner. Gate: both roles can explain why “gateway green” is insufficient. |
| **2. Map evidence authority** | Map each source to facts, units, permitted readers, correction semantics and an accountable owner. Ask what “loss” excludes. | A data contract plus one valid and one invalid example per measure. If the denominator owner cannot define FB-1, that measure stays unknown. |
| **3. Build point-in-time replay** | Draw event time and desk receipt time on two axes. Test immediately before and at a receipt, before a policy cutover, and with an overlap. | Replay diff. No future, wrong-entity or restricted card may enter the searchable set or packet. Record why a published future policy was rejected. |
| **4. Establish retrieval baselines** | Compare manual scan, exact keyword matching and the supplied TF-IDF search. Have a second reader label relevant allowed cards for 15 queries. | A case-by-case top-3 relevance sheet. Keep misses and empty permitted sets. Pick a baseline to beat, not a favourite model. |
| **5. Trial one AI improvement** | Add paraphrases, acronyms and ambiguous vendor language. Run the candidate on the same frozen candidate lists as the baseline. | Side-by-side evidence IDs, retrieval quality, cold/warm latency and cost per reviewed packet. Gate: show a query that improves and one that does not, or retain the simpler baseline. |
| **6. Make claims reproducible** | Implement a packet validator. Test exactly 45 minutes, 46 minutes, 80/100, 79/100, zero denominator, missing loss, and two competing receipts with no correction link. | Unit-tagged expected values and citations. Any unsupported “within” on an unknown measure blocks release. |
| **7. Design review and records** | Sketch preparer/reviewer roles, version IDs, storage boundaries and retention ownership. Attempt a self-approval in your synthetic harness; replay an old signed packet after correction. | Decision history and a rejected self-approval. A reviewer must be able to return the packet without blocking the existing incident bridge. |
| **8. Run the provider-failure exercise** | Have the facilitator delay reconciliation and stop the retrieval component. A support engineer volunteers raw transaction details: use a synthetic receipt instead. | A timeline, manual fallback brief, corrective action and owner. Gate: staff can escalate a known exception without the AI, and without waiting for the missing field. |
| **9. Build independent assurance** | Use distinct synthetic incidents, not time-shifted copies of PAY-07 alone. Freeze labels and allowed evidence before tuning. Have the second-line role adjudicate disputes. | A signed-off exercise set, error ledger and held-out results by hard slice. Publish both numerator and denominator, including empty slices. |
| **10. Prove the operating model** | Estimate steady and burst review capacity, propose an on-call owner, and compare the AI candidate with the manual workflow end to end. | Queue worksheet and load-shedding rule. If the queue is unstable, narrow scope or keep the manual path; a faster ranker is not a staffing plan. |
| **11. Shadow without sending** | Counterbalance manual-first and assisted-first runs on matched synthetic cases. Count corrections, handoffs and reviewer minutes. A short draft that takes longer to verify is not a win. | Sponsor memo: go, limited go, or no-go for *synthetic shadow use*. Name the stop threshold and the person who can stop the pilot. |
| **12. Hand over and defend** | A peer replays a historic packet, introduces a late correction, disables AI ranking and produces a manual brief without help. Present your rejected architecture and worst failure. | Runbook, model/evidence card, release memo and a recorded five-minute customer demo. Gate: someone other than the builder can reconstruct and challenge the output. |

## 5 | Blocker playbook

| Inject / signal | What to inspect first | Owner, response and proof to resume |
|---|---|---|
| Executive wants one green tick while evidence is missing | Was “unknown” collapsed to a number? Is the packet label hiding a per-measure flag? | Risk lead: separate known exceptions and unknowns. Resume when both can appear on one packet. |
| Search looks excellent but historic packets change | Check corpus filtering before indexing, model version, both clocks and policy publication versus effective date. | FDE: freeze the manifest and replay an earlier cutoff after a correction; evidence IDs must not change. |
| Provider promises that all payments cleared | Identify which component the note covers and which source can attest to customer-facing restoration. | Payments lead: seek end-to-end evidence. Keep the note as context only; never let similarity change authority. |
| A ledger extract is delayed or restricted | Distinguish “cannot access,” “not reconciled,” and an authoritative final zero. Do not expose restricted IDs in ops telemetry. | Reconciliation owner issues an approved aggregate receipt. Restore the claim only after an eligible receipt arrives. |
| Two teams quote different fallback percentages | Check batch identity, numerator, denominator and explicit correction link before comparing percentages. | Control owner reconciles the cohort. Competing live facts must not resolve by rank or arrival order. |
| The expensive model improves recall but reviews back up | Count analyst minutes including rejected packets. At 12 packets/hour and 7 min each, demand is 84 reviewer-minutes/hour; one reviewer cannot keep up. | Sponsor narrows the pilot or reserves capacity. Demonstrate that the fallback still works under burst load. |

## 6 | Evaluation and pilot contract

Measure at incident level as well as packet level; ten revisions of one outage are not ten independent outages. The thresholds below are **proposed lab targets**, not measured results or regulatory minima.

| Metric | Definition | Proposed gate |
|---|---|---|
| Evidence exposure | Prohibited, wrong-case or future card IDs in search results, packets or ordinary logs / inspected outputs | Zero occurrences; any occurrence stops the exercise immediately. Inspect actual IDs, not just a rate rounded to zero. |
| False assurance | Unknown/outside gold measure labelled within / all gold unknown-or-outside measures | Zero on frozen exercise. Test missing receipts, zero denominator, authority mismatch and corrections. |
| Missed exception | Gold outside measures not flagged outside / all gold outside measures | Zero; also count correct flags with an independently missing field. |
| Evidence recall@3 | Relevant permitted IDs in first three / labelled relevant permitted IDs, macro-averaged over queries with relevant evidence | Target 85%; report no-answer queries separately. A failed search is never a reason to call an operation healthy. |
| Useful complete packets | Correct fully cited packets / gold-completable snapshots | Target at least 80% while meeting the hard gates. Refusing everything is not a working alternative. |
| Operator value | Paired total minutes from brief request to reviewer decision, including rejected drafts; publish median within-pair percentage change and sample size | Target at least 25% reduction on 20 or more paired tasks. Report slower cases and decision uncertainty. |

Build a frozen set with **at least 24 snapshots across six distinct synthetic incidents**. Include restricted and wrong-entity notes, out-of-order receipts, policy boundaries, contradictory authoritative facts, equality, known exception with a missing field, and entirely complete within-tolerance cases. Assign incidents to development or acceptance **before** creating paraphrases. If a denominator is zero, report N/A and add coverage; do not count it as a pass. These numbers justify at most a scoped synthetic shadow decision, never production accreditation.

**Stop and rollback:** stop generating candidate packets on any access leak, false assurance or lost confirmed exception. The commander continues the existing manual incident bridge immediately; never stop the bank's incident response. Preserve permitted evidence and the failed manifest for investigation. The FDE reverts to the last approved model/data contract; an independent reviewer reproduces the failure and reruns the frozen set before resuming shadow use.

## 7 | Portfolio and facilitator key

**What to take to an FDE interview:** one customer objection that changed the design; a two-clock data-flow drawing; a baseline-versus-candidate result including its worst miss; an incident/rollback note; and a one-page release decision. A credible no-go beats a polished demo that quietly accepts future evidence.

**Release memo template:** Requested decision / bounded population and excluded uses / sample size / hard-gate counts / useful coverage and reviewer minutes / worst counterexample / unresolved control and owner / recommendation and rollback trigger.

**Facilitator key - read after the first timed pass:**

| Cutoff | Supportable internal comparisons | What the reviewer should say |
|---|---|---|
| 08:25 | P3. Duration unknown; loss unknown; FB-1 80/100 = 80%, meets the floor (E03). | “We have evidence the gateway component recovered, not that outbound payments recovered. Payments control owns restoration evidence; reconciliation owns the loss figure.” Do not cite the excluded cards. |
| 08:55 | P3. E01 + E04 = 48 minutes, **3 over**; FB-1 still 80%; loss unknown. | Flag the duration to the human incident/risk process now. Do not wait for reconciliation, use P4's 60 minutes, or declare that a regulatory notification has been decided. |
| 09:10 | P3. Duration still 48; signed loss 0 (E05); corrected FB-1 79/100 = 79% (E06), **1 percentage point below** the floor. | Show two internal exceptions, attach the correction and issue a new draft. The 08:25 draft still correctly reflects E03 as of its cutoff. |

**The final design question:** If a better model cannot change the allowable facts, where can it still create value? Demonstrate less analyst search or verification time on unfamiliar incident language, with the same scope, authority and escalation guarantees. If you cannot, recommend the baseline.
