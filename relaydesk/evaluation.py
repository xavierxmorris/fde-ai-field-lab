"""Score two triage pipelines on one frozen UTF-8 JSON Lines file.

Each line is an object with seven required fields: ``id`` (unique string),
``tenant``, ``lookup_date`` (YYYY-MM-DD), ``question``, ``intent`` (slice
label), ``topic`` (return_window, damage_steps, or null), and
``expected_citation`` (one card ID for a draft, null for a required handoff).
A topic can be known even when there is no applicable card or an exception
requires a human. Intent is the topic name for ordinary policy requests;
other intents, e.g. "exception" or "mixed", require handoff.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import NamedTuple


class _GoldCard(NamedTuple):
    tenant: str
    topic: str
    version: str
    effective_from: str
    effective_until: str | None
    excerpt: str

    def applies(self, tenant, topic, day):
        return (tenant == self.tenant and topic == self.topic
                and self.effective_from <= day
                and (self.effective_until is None or day < self.effective_until))


# The acceptance oracle is independent of the router and its retrieved metadata.
_CARDS = {
    "NS-RET-1": _GoldCard("northstar", "return_window", "1", "2025-01-01", "2025-07-01",
                          "Standard returns must be requested within 14 days of delivery."),
    "NS-RET-2": _GoldCard("northstar", "return_window", "2", "2025-07-01", None,
                          "Standard returns must be requested within 30 days of delivery."),
    "HB-RET-1": _GoldCard("harbor", "return_window", "1", "2025-01-01", None,
                          "Standard returns must be requested within 21 days of delivery."),
    "NS-DMG-1": _GoldCard("northstar", "damage_steps", "1", "2025-01-01", None,
                          "For an item that arrived damaged, retain the packaging and contact the desk."),
    "HB-DMG-1": _GoldCard("harbor", "damage_steps", "1", "2025-03-01", None,
                          "For an item that arrived damaged, photograph the item and contact the desk."),
}
_TOPICS = ("return_window", "damage_steps")


@dataclass(frozen=True)
class _Case:
    id: str
    tenant: str
    lookup_date: str
    question: str
    intent: str
    topic: str | None
    expected_citation: str | None

    @property
    def answerable(self):
        return self.expected_citation is not None

    def validate(self):
        for field in ("id", "tenant", "lookup_date", "question", "intent"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a non-empty string")
        if self.tenant not in ("northstar", "harbor"):
            raise ValueError("unknown tenant")
        if date.fromisoformat(self.lookup_date).isoformat() != self.lookup_date:
            raise ValueError("lookup_date must use YYYY-MM-DD")
        if self.topic is not None and self.topic not in _TOPICS:
            raise ValueError("unknown topic")
        if self.intent in _TOPICS and self.topic != self.intent:
            raise ValueError("ordinary policy intent requires the matching topic")
        if self.answerable:
            card = _CARDS.get(self.expected_citation)
            if (not card or self.intent != self.topic
                    or not card.applies(self.tenant, self.topic, self.lookup_date)):
                raise ValueError("citation is not applicable to this intent, tenant, topic and date")
        elif self.intent in _TOPICS and any(
            card.applies(self.tenant, self.topic, self.lookup_date) for card in _CARDS.values()
        ):
            raise ValueError("ordinary policy request has an applicable card but a null label")


def _unique_fields(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate JSON field {key!r}")
        obj[key] = value
    return obj


def _load_cases(path):
    cases, ids, inputs = [], set(), set()
    with path.open(encoding="utf-8") as lines:
        for number, line in enumerate(lines, 1):
            try:
                case = _Case(**json.loads(line, object_pairs_hook=_unique_fields))
                case.validate()
                key = (case.tenant, case.lookup_date, case.question)
                if case.id in ids or key in inputs:
                    raise ValueError(f"duplicate ID or input: {case.id}")
                ids.add(case.id)
                inputs.add(key)
                cases.append(case)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{path}:{number}: {exc}") from exc
    if not cases:
        raise ValueError(f"{path}: empty acceptance set")
    if {case.answerable for case in cases} != {False, True}:
        raise ValueError(f"{path}: need both answerable and must-handoff cases to score gates")
    return cases


def _citation_errors(case, evidence):
    if not isinstance(evidence, dict):
        return ["evidence is not an object"]
    if not case.answerable:
        return ["no citation is appropriate"]
    card_id = case.expected_citation
    expected = dict(_CARDS[card_id]._asdict(), id=card_id)
    return [f"wrong or missing evidence.{key}" for key, value in expected.items()
            if key not in evidence or evidence[key] != value]


def _grade(case, result):
    if not isinstance(result, dict):
        result = {}
    disposition = result.get("disposition")
    draft = disposition == "draft"
    evidence = result.get("evidence")
    cited = evidence is not None
    invalid = []
    for key in ("tenant", "lookup_date"):
        if result.get(key) != getattr(case, key):
            invalid.append(f"wrong or missing response {key}")
    if disposition not in ("draft", "handoff"):
        invalid.append("unknown or missing disposition")
    if "evidence" not in result or (draft and not cited):
        invalid.append("missing evidence")
    if disposition == "handoff":
        if not isinstance(result.get("reason"), str) or not result["reason"].strip():
            invalid.append("missing handoff reason")
        if cited:
            invalid.append("handoff includes evidence")

    citation_errors = _citation_errors(case, evidence) if cited else []
    problems = invalid + citation_errors
    false_draft = draft and not case.answerable
    if false_draft:
        problems.append("false draft")
    if disposition == "handoff" and case.answerable:
        problems.append("needless handoff")
    counts = {
        "total": 1, "correct": int(not problems),
        "answerable": int(case.answerable), "must_handoff": int(not case.answerable),
        "covered": int(case.answerable and draft and not problems),
        "false_drafts": int(false_draft), "cited": int(cited),
        "wrong_citations": int(bool(citation_errors)), "invalid_responses": int(bool(invalid)),
    }
    failure = None
    if problems:
        failure = {
            "id": case.id, "expected_citation": case.expected_citation,
            "disposition": disposition, "reason": result.get("reason"),
            "actual_citation": evidence.get("id") if isinstance(evidence, dict) else None,
            "problems": problems,
        }
    return counts, failure


def _ratio(n, d):
    return {"numerator": n, "denominator": d, "rate": n / d if d else None}


def _metrics(c):
    return {
        "correct": _ratio(c["correct"], c["total"]),
        "coverage": _ratio(c["covered"], c["answerable"]),
        "false_drafts": _ratio(c["false_drafts"], c["must_handoff"]),
        "wrong_citations": _ratio(c["wrong_citations"], c["cited"]),
        "invalid_responses": _ratio(c["invalid_responses"], c["total"]),
    }


def _run(engine, cases, baseline):
    total, failures = Counter(), []
    slices = {key: {} for key in ("tenant", "intent", "answerability")}
    for case in cases:
        result = engine.triage(case.tenant, case.lookup_date, case.question, baseline=baseline)
        counts, failure = _grade(case, result)
        total.update(counts)
        if failure is not None:
            failures.append(failure)
        for key, group in (("tenant", case.tenant), ("intent", case.intent),
                           ("answerability", "answerable" if case.answerable else "must_handoff")):
            slices[key].setdefault(group, Counter()).update(counts)
    passed = (5 * total["covered"] >= 4 * total["answerable"]
              and not (total["wrong_citations"] or total["false_drafts"] or total["invalid_responses"]))
    return {
        "passed": passed, "metrics": _metrics(total), "failures": failures,
        "slices": {key: {group: _metrics(counts) for group, counts in sorted(groups.items())}
                   for key, groups in slices.items()},
    }


def evaluate(engine, cases_path: Path) -> dict:
    """Return {passed, baseline, candidate}; only the candidate gates release.

    Both pipelines receive the same inputs in file order. Each has ``passed``,
    ``metrics``, ``slices`` (tenant, intent, answerability), and ``failures``.
    Each metric has a numerator, denominator and rate (null when undefined).
    Correctness requires the right disposition and evidence. Coverage is correct
    drafts / answerable; false drafts are drafts / must-handoff on that subset.
    Wrong citations are mismatched evidence / outputs with non-null evidence;
    a false draft with a citation counts in both metrics. Missing draft evidence
    is an invalid response, not an invented citation. Invalid envelopes fail
    closed in addition to the 80% coverage and zero unsafe-draft/citation gates.

    Card identity, scope, version, interval and verbatim excerpt are checked
    against the frozen workbook manifest, not the engine's own metadata.
    Neither generated prose nor reason wording is graded.
    Invalid fixtures raise ValueError before either pipeline is called.
    """
    cases = _load_cases(cases_path)
    baseline = _run(engine, cases, baseline=True)
    candidate = _run(engine, cases, baseline=False)
    return {"passed": candidate["passed"], "baseline": baseline, "candidate": candidate}


def _metric_line(metrics):
    parts = []
    for name, value in metrics.items():
        rate = "n/a" if value["rate"] is None else f"{value['rate']:.1%}"
        parts.append(f"{name}={value['numerator']}/{value['denominator']} ({rate})")
    return "; ".join(parts)


def format_report(report) -> str:
    """Format overall and sliced fractions, including 0/0, and every failed ID."""
    lines = ["Acceptance: " + ("PASS" if report["passed"] else "FAIL")]
    for name in ("baseline", "candidate"):
        run = report[name]
        lines.append(f"{name} ({'PASS' if run['passed'] else 'FAIL'}): {_metric_line(run['metrics'])}")
        for dimension, groups in run["slices"].items():
            for group, metrics in groups.items():
                lines.append(f"  {dimension}={group}: {_metric_line(metrics)}")
        lines.append(f"  Failures: {len(run['failures'])}")
        for failure in run["failures"]:
            lines.append(f"    {failure['id']}: {', '.join(failure['problems'])}; "
                         f"expected={failure['expected_citation']!r}, "
                         f"got={failure['disposition']!r}/{failure['actual_citation']!r}")
    return "\n".join(lines)
