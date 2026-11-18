# RelayDesk: the eight-week field engagement

You are the forward-deployed engineer embedded with a fictional shared returns desk. A support lead says, "People keep pasting the wrong retailer's returns window. Make us faster." That is a complaint, not a specification. Your deliverable is a release decision backed by evidence, not a chatbot that always answers. Budget **5-7 hours a week** for one person. In a team, rotate the operator, engineer and skeptical customer roles. All people, tickets, policies and targets in the lab are simulated.

## Contract before code

**User:** a support agent comparing a ticket with a policy, not a shopper. **Input:** a retailer, the policy lookup date and a short question. **Output:** one verbatim, versioned policy excerpt or a handoff reason. A draft can be accepted or rejected by a human; accepting is not an entitlement decision. No money moves and no messages are sent. The initial customer authorizes synthetic data and a single-user, offline pilot only. Live customer data, eligibility decisions, SSO, production hosting and autonomous refunds are out of scope.

| Counterparty | Ask in discovery | Evidence they need to sign off |
|---|---|---|
| Desk lead (sponsor) | Is policy lookup or order lookup the bottleneck? What would you stop doing? | Paired timing with and without assistance, including failed lookups. |
| Returns specialist (operator) | Walk me through one ordinary return and one exception. Where would you challenge the draft? | Exact excerpt, retailer, source version, date, and an easy way to reject. |
| Policy owner | When an amendment takes effect, do you use order, delivery or contact date? Who resolves overlaps? | Written date semantics, cutover and overlap cases signed off. |
| Platform/privacy owner | Who assigns retailer identity? Where does ticket text persist? What would prevent a real-data rollout? | Data-flow diagram, retention proposal and tested stop procedure. |

**Initial decision:** the operator supplies a *policy lookup date*, not a claim that today's policy governs an order. Real event-date rules are unresolved until the policy owner signs them. **Success hypothesis:** reduce median policy-lookup time by 25% without increasing wrong-policy use. This is a target, not a measured result. Track medians on matched tasks and rejections/abstentions separately so faster easy cases cannot conceal slower hard ones.

## Detailed schedule

| Week / focus | Work in order | Deliverable, demo and exit gate |
|---|---|---|
| **1. Find the job** | Run the three-stop demo. Role-play the four interviews above. Manually answer six tickets without the assistant. Time from reading the ticket to locating the excerpt. Mark where you needed an order record or manager. Write down what the sponsor initially asked for versus what agents actually needed. | One-page charter, case timings, non-goals and a proposed pilot owner. Demo one case the tool should *not* handle. Gate: both sponsor and policy owner can state the same refusal boundary. |
| **2. Turn messy data into a contract** | Inventory every policy by tenant, topic, version and effective interval. Trace a Northstar return on either side of the change date. Make a scratch copy of the fixtures; introduce one gap and one overlapping interval. Decide which anomalies should fail ingestion and which should fail closed at lookup. | Data dictionary, data lineage sketch and two negative examples. Gate: no old or future text is used on either boundary; overlapping applicable versions do not silently win a tie. |
| **3. Build the first retrieval path** | Trace one question from tokenization through intent prediction and evidence selection. Compare the scoped retrieval baseline to the gated pipeline on the supplied benchmark. Add five new paraphrases to a separate development file and classify failures as intent, retrieval or missing evidence. | Two annotated request traces and a decision record: lexical vs embedding/hybrid retrieval for *this* corpus. Gate: demonstrate one case where refusing rather than retrieving is valuable and one where caution hurts coverage. |
| **4. Make quality measurable** | Agree on the unit of correctness: right disposition **and** exact evidence ID for drafts. Independently label 20 new synthetic cases. Have a second reader adjudicate disagreements, or relabel blind a day later. Separate development from a frozen acceptance set before tuning. Slice by retailer, intent and answerability. | Versioned evaluation sheet with numerator, denominator and every failure ID. Gate: no wrong-tenant or wrong-version citations, no drafts on must-handoff cases, and at least 80% correct citation coverage on answerable cases. A tiny green fixture suite is not permission to pilot. |
| **5. Fit the operator's day** | Replay one idempotent submission twice, then try changing its contents under the same ID. Reject a draft; verify it no longer waits for review. Ask the operator to identify the evidence without an engineer. Turn three objections into a ranked backlog. | Five-minute workflow demo plus a review-state diagram. Gate: a replay cannot create duplicate work, conflicting reuse is visible, and the same draft cannot be reviewed twice. |
| **6. Break it on purpose** | Use the drills below on synthetic copies. Replay stale dates, a policy overlap, paraphrase drift and a burst of handoffs. Time a 100-case local run; separate cold model loading from warm inference. Sketch the production queue and trust boundary *without* building infrastructure yet. | Incident timeline, workload sheet and corrected release checklist. Gate: the operator can switch to manual lookup without the engineer; recovered output passes the frozen cases before resuming. |
| **7. Decide whether to pilot** | Shadow ten more matched tasks; alternate manual-first and assistant-first order to reduce learning bias. Do not send drafts. Compute time saved *including reviews*, rejection reasons and queue capacity. If the demo looks good but capacity fails, narrow to one retailer/topic. | Sponsor memo: **go**, **limited go** or **no-go**; attach the worst counterexample, scope, owner and reversal trigger. Gate: both operator and policy owner sign or leave an explicit blocker. |
| **8. Hand off something maintainable** | Have a peer add a policy version from the runbook without your help. Rerun cutover, isolation and handoff cases. Restore a known-good fixture if the change fails. Present the incident, the economics, a rejected design and one thing you still cannot claim. | Portfolio packet: charter, architecture decision record, evaluation diff, incident review, pilot memo and operator handoff. Gate: someone else can reproduce the demo and explain how to stop it. |

**Weekly rhythm:** Monday write down one customer decision and its owner. Midweek ship the smallest experiment that could change it. Friday demo a success *and a refusal*, log one dissent, attach evidence and agree on the next gate. If stakeholder access stalls, role-play both sides and mark the decision **assumed**, never **approved**.

## Change orders and blockers

Run these after the baseline works. The first six exercise the shipped system; the last two are design/measurement assignments. Do not overwrite the shipped benchmark to make an experiment pass.

| Customer change or blocker | What to look for / how to reproduce | Your decision and pass condition |
|---|---|---|
| "Our returns window changed overnight." | Ask the same Northstar question on 2025-06-30 and 2025-07-01. Look at evidence IDs, not just numbers in the text. | Decide how to obtain the authoritative lookup date. An exclusive end date gives no overlap at midnight, and the two results cite different cards. |
| "That answer belongs to our other brand." | Ask the same question for Northstar and Harbor; then try a date before either policy existed. | Tenant/date selection precedes ranking. No eligible evidence means no excerpt, not a cached generic answer. A real tenant ID must come from authenticated context. |
| "Operations sent us a second, conflicting policy." | In a copy of `data/`, add a card with a new ID and overlapping dates for the same tenant/topic. | The policy owner decides the authoritative version. Until then the covered topic must hand off; ranking is not a conflict-resolution mechanism. |
| "We get questions about returns *and* damage." | Compare a short, single-topic request with a two-topic one; inspect the reason and the reviewer workload. | Pick a unit of work: one card or a multi-step plan. The shipped pilot is one card; extend it only with labeled multi-topic cases. |
| "The integration retried a message." | Submit the same synthetic ID twice, then reuse it for different text. Check the pending queue after each attempt. | Exact replay returns the original record; conflicting reuse fails visibly. Explain when a deliberate re-triage needs a new request ID. |
| "Customers now say 'send it home' instead of 'return'." | Add a batch in a new development set using the phrase. Compare increased handoffs against wrong citations. | Decide between training examples, an alias, or embeddings. Freeze the old set; report both before/after by slice. Do not teach the test questions to the model. |
| "The demo is fast but our queue is growing." | Simulate 240 requests/hour with 40% handoffs taking 4 min each. Add 1 min review for each draft. | Compute `(96*4 + 144*1)/60 = 8.8` reviewer-hours per arrival hour, before breaks. Reduce volume or increase staffing; faster inference alone cannot clear this queue. |
| "Can we turn on a hosted LLM tomorrow?" | Identify what leaves the machine, how stale citations are checked, and what happens on timeout or a budget stop. | Present a buy-vs-build memo, maximum cost per *accepted* draft, fallback and deletion procedure. No real data or external model is required for this exercise. |

## Architecture interview prompts

1. At 100 retailers with 10,000 policies each, what breaks first in the local scan? Sketch an index keyed by tenant and time before vector search; defend how deletes and new versions propagate. Explain why filtering only after top-k can miss valid evidence.
2. Which is worse: a wrong excerpt or a needless transfer? Put candidate costs on both with the sponsor. Show which gate changes as cost or staffing changes; leave tenant isolation a hard invariant.
3. If you add generation, what new behavior do you buy over an exact excerpt? Specify the response schema, evidence checks, timeouts and fallback. Compare it to the shipped baseline before budgeting for it.
4. How would a horizontally scaled service keep duplicate submissions and reviews consistent? Name the database uniqueness constraint, request fingerprint, authorization point and rollback path. Identify what a SQLite demonstration does *not* prove.

## Reusable handoff forms

**Decision record:** Decision / customer owner / evidence for and against / option rejected / what would reverse it / review date.

**Failure ledger:** Case ID / expected disposition and citation / actual disposition and citation / failure layer / affected retailer / impact / smallest falsifiable fix / regression case.

**Pilot memo:** Scope and exclusion / manual vs assisted timing with sample sizes / safe coverage and false drafts / reviewer capacity at peak / recommendation / stop conditions / who owns the kill switch.

**Portfolio rubric (0-2 each):** customer problem, data contract, evaluation, operations, communication. Score 0 for an assertion, 1 for an artifact, 2 for a falsifiable observation that changed a decision. A polished demo alone cannot pass. A well-evidenced no-go can.
