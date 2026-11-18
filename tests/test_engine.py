import unittest
from dataclasses import asdict, replace
from unittest.mock import patch

from relaydesk.engine import DATA, Card, Engine
from relaydesk.model import IntentModel, json_rows, words


class RoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = Engine.load()

    def test_workshop_replay(self):
        cases = [
            ("northstar", "2025-06-30", "What is the standard return window?", "NS-RET-1"),
            ("northstar", "2025-07-01", "Same question: how long is the standard window?", "NS-RET-2"),
            ("harbor", "2025-07-01", "How long do I have to request a standard return?", "HB-RET-1"),
            ("harbor", "2024-12-31", "What was the standard window on that date?", None),
            ("northstar", "2025-07-01", "What is the return window, and what should I do about damage in transit?", None),
            ("northstar", "2025-07-01", "My parcel is late and my order is special. Can you approve an exception now?", None),
        ]
        for tenant, day, question, expected in cases:
            with self.subTest(tenant=tenant, day=day, question=question):
                result = self.engine.triage(tenant, day, question)
                if expected is None:
                    self.assertIsNone(result["evidence"])
                    self.assertEqual(result["disposition"], "handoff")
                    self.assertTrue(result["reason"])
                else:
                    card = next(c for c in self.engine.cards if c.id == expected)
                    self.assertEqual(result["evidence"], asdict(card))
                    self.assertEqual(result["disposition"], "draft")

    def test_scope_before_ranking_and_historical_topic_gap(self):
        q = "How do I report damage in transit?"
        feb = self.engine.triage("harbor", "2025-02-28", q, trace=True)
        self.assertEqual(feb["reason"], "no_applicable_policy")
        self.assertEqual(list(feb["trace"]["scoped_scores"]), ["HB-RET-1"])
        march = self.engine.triage("harbor", "2025-03-01", q)
        self.assertEqual(march["evidence"]["id"], "HB-DMG-1")
        unknown = self.engine.triage("unknown", "2025-07-01", q, trace=True)
        self.assertEqual(unknown["trace"]["scoped_scores"], {})
        self.assertIsNone(unknown["evidence"])

    def test_overlap_blocks_only_affected_topic_and_interval(self):
        current = next(c for c in self.engine.cards if c.id == "NS-RET-2")
        overlap = replace(current, id="NS-CONFLICT", excerpt="This conflicting draft has a stronger return window match.",
                          effective_from="2025-08-01", effective_until="2025-09-01")
        engine = Engine(self.engine.cards + (overlap,), self.engine.model)
        q = "What is the return window?"
        self.assertEqual(engine.triage("northstar", "2025-08-01", q)["reason"], "overlapping_versions")
        self.assertEqual(engine.triage("northstar", "2025-09-01", q)["evidence"]["id"], current.id)
        self.assertEqual(engine.triage("northstar", "2025-08-01", "How do I report damage?")["disposition"], "draft")

    def test_ingest_and_calendar_errors_are_visible(self):
        row = asdict(self.engine.cards[0])
        for changes in ({"effective_from": "2025-02-30"}, {"effective_until": row["effective_from"]},
                        {"version": ""}, {"effective_until": "20250630"}, {"topic": "unregistered"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                Card.parse(dict(row, **changes))
        with self.assertRaisesRegex(ValueError, "unique"):
            Engine(self.engine.cards + (self.engine.cards[0],), self.engine.model)
        with self.assertRaises(ValueError):
            self.engine.triage("harbor", "not-a-date", "What is the window?")

    def test_ambiguity_and_unmentioned_conditions_do_not_get_an_excerpt(self):
        for q in ("Can I return this custom item after the window?", "How long does a return take?",
                  "What is the return window for Harbor?", "What kind of photos do I need for damage?",
                  "Would you approve a return for order 817?", "Send it home.", "???"):
            with self.subTest(q=q):
                self.assertIsNone(self.engine.triage("northstar", "2025-07-01", q)["evidence"])

    def test_a_classifier_disagreement_or_tie_can_veto_lexical_match(self):
        q = "What is the return window?"
        for scores in ([("unsupported", .95), ("return_window", .05)],
                       [("return_window", .51), ("damage_steps", .49)]):
            with self.subTest(scores=scores), patch.object(self.engine.model, "predict", return_value=scores):
                self.assertEqual(self.engine.triage("harbor", "2025-07-01", q)["reason"], "uncertain_intent")
                self.assertEqual(self.engine.triage("harbor", "2025-07-01", q, baseline=True)["disposition"], "draft")

    def test_model_learns_from_labels_not_a_lookup_table(self):
        examples = [{"label": "a", "text": "orchid orchid petals"}, {"label": "b", "text": "copper cable"}]
        prediction = lambda rows: IntentModel(rows, {"a", "b"}).predict(words("orchid petals"))[0][0]
        self.assertEqual(prediction(examples), "a")
        self.assertEqual(prediction([dict(row, label=other) for row, other in zip(examples, ("b", "a"))]), "b")

    def test_benchmark_questions_are_not_training_examples(self):
        train = {tuple(words(x["text"])) for x in json_rows(DATA / "training.jsonl")}
        heldout = {tuple(words(x["question"])) for x in json_rows(DATA / "acceptance.jsonl")}
        self.assertFalse(train & heldout)
