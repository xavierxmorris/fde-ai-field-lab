# RelayDesk | First customer workshop

**Time:** 45 minutes. **Equipment:** this sheet, a timer and a blank page. No software or GitHub setup required. Work with a partner or play both roles. These four fictional policy cards form a standalone exercise, not the software benchmark. Look at the facilitator key only after timing the six tickets.

## 0-5 minutes: make a promise you can measure

The sponsor says, "Could AI take these returns tickets off our hands by Friday?" Give a two-sentence reply that distinguishes looking up policy from deciding eligibility. Agree on when the clock starts and stops. A manual handoff counts as work, not as a ticket you get to discard.

## 5-18 minutes: do the operator's job by hand

Use the retailer and lookup date supplied on the ticket. An interval includes its start day and excludes its end day. Your desk may offer one policy excerpt; it may not decide eligibility, quote two cards, or guess what an unpublished policy said.

| Card | Retailer | Effective dates | Approved wording |
|---|---|---|---|
| Workshop N-1 | Northstar | 2025-01-01 to 2025-07-01 | Standard returns must be requested within 14 days of delivery. |
| Workshop N-2 | Northstar | 2025-07-01 onward | Standard returns must be requested within 30 days of delivery. |
| Workshop N-D | Northstar | 2025-01-01 onward | For an item that arrived damaged, retain the packaging and contact the desk. |
| Workshop H-1 | Harbor | 2025-01-01 onward | Standard returns must be requested within 21 days of delivery. |

| ID | Retailer / lookup date | Ticket |
|---|---|---|
| A | Northstar / 2025-06-30 | What is the standard return window? |
| B | Northstar / 2025-07-01 | Same question: how long is the standard window? |
| C | Harbor / 2025-07-01 | How long do I have to request a standard return? |
| D | Harbor / 2024-12-31 | What was the standard window on that date? |
| E | Northstar / 2025-07-01 | What is the return window, and what should I do about damage in transit? |
| F | Northstar / 2025-07-01 | My parcel is late and my order is special. Can you approve an exception now? |

For **each** ticket, record `ID | seconds | card ID or handoff | reason | additional information or owner needed`. Count a draft as correct only if both its disposition and its source are right. Never award credit for getting the number right using the wrong retailer's policy.

## 18-30 minutes: turn observations into system design

1. Circle the two tickets most likely to fool a system that simply picks the closest text. Identify the input information that similarity cannot recover.
2. Draw the data path from ticket to operator decision. Put a box around the step that excludes the wrong retailer and date. Draw a second arrow for the no-evidence case; name who does the work at the arrow's end.
3. Give the sponsor two numbers: correct citations divided by answerable cases, and false drafts divided by cases requiring handoff. Write out both denominators. Show how a system that always hands off can score zero false drafts and still be useless.
4. Log one assumption the engineer cannot settle. A good example: does customer contact date or delivery date choose the policy version? Name who must answer it before live use.

## 30-45 minutes: defend a pilot decision

Copy this sentence and fill in the blanks: "I recommend ___ for retailer ___ and topic ___ because ___; we will stop if ___; ___ owns manual fallback." Use your measured times, not an estimated time saving. For a partner demo, let the partner choose the inconvenient ticket. End by showing what the system **would not** do.

<details>
<summary>Facilitator key: open after the first pass</summary>

| ID | Expected | Why |
|---|---|---|
| A | N-1 | June 30 still belongs to the first interval. |
| B | N-2 | The cutover is inclusive on July 1. |
| C | H-1 | The date and wording match B, but the retailer does not. |
| D | Handoff to policy owner | No Harbor card is valid then; today's answer cannot stand in for it. |
| E | Handoff to an operator | Both topics are covered individually, but a one-card draft would be incomplete. |
| F | Handoff to an operator | A return-window excerpt cannot authorize a customer-specific exception. |

There are three answerable and three must-handoff cases. A system that refuses all six has correct citation coverage **0/3**, false drafts **0/3**, and exact disposition-plus-source correctness **3/6**. That is why a single accuracy measure is not enough. Six rehearsed cases are useful for finding failure modes, not for estimating production precision.

</details>
