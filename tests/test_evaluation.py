import json
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

from relaydesk.evaluation import evaluate, format_report


DAY = "2025-07-01"
CITATION = {
    "id": "NS-RET-2", "tenant": "northstar", "topic": "return_window",
    "version": "2", "effective_from": DAY, "effective_until": None,
    "excerpt": "Standard returns must be requested within 30 days of delivery.",
}


def case(case_id, answerable=True, **changes):
    row = {
        "id": case_id, "question": f"Question {case_id}?", "lookup_date": DAY,
        "tenant": "northstar" if answerable else "harbor",
        "intent": "return_window" if answerable else "account",
        "topic": "return_window" if answerable else None,
        "expected_citation": "NS-RET-2" if answerable else None,
    }
    return dict(row, **changes)


class Stub:
    """Baseline always hands off. Candidate drafts only the specified replies."""

    def __init__(self, drafts):
        self.drafts = drafts
        self.calls = {True: [], False: []}

    def triage(self, tenant, lookup_date, question, *, baseline=False):
        self.calls[baseline].append((tenant, lookup_date, question))
        envelope = {"tenant": tenant, "lookup_date": lookup_date}
        if not baseline and question in self.drafts:
            return dict(envelope, disposition="draft", evidence=self.drafts[question])
        return dict(envelope, disposition="handoff", reason="needs review", evidence=None)


def run(stub, rows):
    text = "\n".join(map(json.dumps, rows))
    with patch.object(Path, "open", mock_open(read_data=text)):
        return evaluate(stub, Path("fixture.jsonl"))


class EvaluationTests(unittest.TestCase):
    def test_denominators_slices_and_all_failures(self):
        rows = [case("good"), case("miss"), case("unsafe", False),
                case("safe1", False), case("safe2", False)]
        stub = Stub({rows[0]["question"]: CITATION, rows[2]["question"]: CITATION})
        report = run(stub, rows)
        expected_calls = [(r["tenant"], r["lookup_date"], r["question"]) for r in rows]
        self.assertEqual(stub.calls, {False: expected_calls, True: expected_calls})
        candidate = report["candidate"]
        metrics = candidate["metrics"]
        for key, n, d in (("coverage", 1, 2), ("false_drafts", 1, 3),
                          ("wrong_citations", 1, 2), ("correct", 3, 5)):
            self.assertEqual(metrics[key], {"numerator": n, "denominator": d, "rate": n / d})
        self.assertEqual([f["id"] for f in candidate["failures"]], ["miss", "unsafe"])
        self.assertFalse(report["passed"])
        self.assertEqual(report["baseline"]["metrics"]["correct"]["numerator"], 3)
        slices = candidate["slices"]
        self.assertEqual(slices["tenant"]["harbor"]["false_drafts"], metrics["false_drafts"])
        self.assertEqual(slices["intent"]["return_window"]["coverage"], metrics["coverage"])
        self.assertEqual(slices["answerability"]["must_handoff"]["coverage"],
                         {"numerator": 0, "denominator": 0, "rate": None})
        text = format_report(report)
        for fragment in ("baseline", "candidate", "0/0 (n/a)", "1/3", "miss:", "unsafe:"):
            self.assertIn(fragment, text)

    def test_coverage_gate_includes_exactly_eighty_percent(self):
        rows = [case(str(i)) for i in range(5)] + [case("account", False)]
        for covered, passed in ((4, True), (3, False)):
            with self.subTest(covered=covered):
                report = run(Stub({r["question"]: CITATION for r in rows[:covered]}), rows)
                self.assertEqual(report["passed"], passed)
                self.assertEqual(report["candidate"]["metrics"]["coverage"]["rate"], covered / 5)
                self.assertFalse(report["baseline"]["passed"])

    def test_wrong_citation_blocks_release_even_at_coverage_threshold(self):
        rows = [case(str(i)) for i in range(5)] + [case("human", False)]
        for field, wrong in (("id", "NS-RET-1"), ("tenant", "harbor"), ("version", "1"),
                             ("topic", "damage_steps"), ("effective_from", "2025-01-01"),
                             ("effective_until", DAY), ("excerpt", "A different policy.")):
            with self.subTest(field=field):
                drafts = {r["question"]: CITATION for r in rows[:4]}
                drafts[rows[4]["question"]] = dict(CITATION, **{field: wrong})
                report = run(Stub(drafts), rows)
                metrics = report["candidate"]["metrics"]
                self.assertEqual(metrics["coverage"]["rate"], 0.8)
                self.assertEqual(metrics["false_drafts"]["numerator"], 0)
                self.assertEqual(metrics["wrong_citations"]["numerator"], 1)
                self.assertFalse(report["passed"])
                failure, = report["candidate"]["failures"]
                self.assertEqual(failure["id"], "4")
                self.assertIn("evidence." + field, " ".join(failure["problems"]))

    def test_uncited_draft_fails_without_counting_a_spurious_citation(self):
        rows = [case("policy"), case("account", False)]
        drafts = {rows[0]["question"]: CITATION, rows[1]["question"]: None}
        report = run(Stub(drafts), rows)
        self.assertFalse(report["passed"])
        metrics = report["candidate"]["metrics"]
        self.assertEqual(metrics["coverage"]["rate"], 1)
        self.assertEqual(metrics["false_drafts"]["rate"], 1)
        self.assertEqual(metrics["wrong_citations"]["numerator"], 0)
        self.assertEqual(metrics["invalid_responses"]["numerator"], 1)

    def test_bad_labels_or_unscorable_populations_fail_before_inference(self):
        yes, no = case("yes"), case("no", False)
        for rows in (
            [], [yes], [no], [yes, no, yes], [yes, no, dict(yes, id="copy")],
            [yes, no, dict(no, id="yes", question="Different input")],
            [dict(yes, expected_citation="does-not-exist"), no],
            [dict(yes, expected_citation="NS-RET-1"), no],  # expired at midnight
            [dict(yes, expected_citation="HB-RET-1"), no],  # other tenant
            [dict(yes, expected_citation="NS-DMG-1"), no],  # other topic
            [dict(yes, lookup_date="2025-06-31"), no],
            [dict(yes, intent="exception"), no],
            [yes, no, case("unlabeled", expected_citation=None)],
            [yes, no, {k: v for k, v in no.items() if k != "expected_citation"}],
        ):
            with self.subTest(rows=rows):
                stub = Stub({})
                with self.assertRaises(ValueError):
                    run(stub, rows)
                self.assertEqual(stub.calls, {True: [], False: []})

    def test_malformed_json_reports_line_number(self):
        text = json.dumps(case("first")) + "\n{"
        with patch.object(Path, "open", mock_open(read_data=text)):
            with self.assertRaisesRegex(ValueError, "fixture.jsonl:2:"):
                evaluate(Stub({}), Path("fixture.jsonl"))
