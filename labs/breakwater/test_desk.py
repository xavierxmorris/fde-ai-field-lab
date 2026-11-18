import json
import unittest

from desk import brief, load_case, search


class Tabletop(unittest.TestCase):
    def setUp(self):
        self.case = load_case()

    def receipt(self, key):
        return next(c for c in self.case["cards"] if c["id"] == key)

    def test_three_bridge_calls(self):
        for at, expected in {
            "08:25": ("INCOMPLETE", "UNKNOWN", "UNKNOWN", "WITHIN", "E03"),
            "08:55": ("FLAG_FOR_REVIEW", "OUTSIDE", "UNKNOWN", "WITHIN", "E03"),
            "09:10": ("FLAG_FOR_REVIEW", "OUTSIDE", "WITHIN", "OUTSIDE", "E06"),
        }.items():
            with self.subTest(at=at):
                b = brief(self.case, at)
                m = b["measures"]
                self.assertEqual(expected, (b["state"], m["duration"]["status"], m["loss"]["status"],
                                            m["fallback_service"]["status"], *m["fallback_service"]["evidence"]))
                self.assertEqual(b["policy"], "P3")
                self.assertTrue(b["human_review_required"])
                self.assertNotIn("X0", json.dumps(b))
        end = brief(self.case, "08:55")["measures"]["duration"]
        self.assertEqual((end["value"], end["evidence"]), ("48 min", ["E01", "E04"]))

    def test_notes_are_searchable_not_authority(self):
        self.receipt("E02")["kind"] = "end"  # Provider mistakenly classifies its own signal.
        self.assertEqual(search(self.case, "08:25", "gateway recovered")[0]["id"], "E02")
        self.assertEqual(brief(self.case, "08:25")["measures"]["duration"]["status"], "UNKNOWN")
        self.assertEqual(search(self.case, "08:25", "restricted reconciliation fictional"), [])

    def test_both_clocks_and_incident_scope(self):
        row = dict(self.receipt("E04"), id="NEW", received="08:22", text="unidentifiedtoken")
        self.case["cards"].append(row)
        self.assertEqual(search(self.case, "08:25", "unidentifiedtoken"), [])
        row.update(observed="08:21", case="PAY-08")
        self.assertEqual(search(self.case, "08:25", "unidentifiedtoken"), [])
        row.update(case="PAY-07", entity="OTHER-AU")
        self.assertEqual(search(self.case, "08:25", "unidentifiedtoken"), [])

    def test_correction_has_an_inclusive_receipt_boundary(self):
        for at, ref in [("09:07", "E03"), ("09:08", "E06"), ("08:25", "E03")]:
            self.assertEqual(brief(self.case, at)["measures"]["fallback_service"]["evidence"], [ref])
        self.receipt("E06").pop("supersedes")
        self.assertEqual(brief(self.case, "09:10")["measures"]["fallback_service"]["status"], "UNKNOWN")
        self.receipt("E06")["supersedes"] = "X02"
        self.assertEqual(brief(self.case, "09:10")["measures"]["fallback_service"]["status"], "UNKNOWN")

    def test_zero_denominator_never_means_within(self):
        self.receipt("E03").update(accepted=0, eligible=0)
        m = brief(self.case, "08:25")["measures"]["fallback_service"]
        self.assertEqual((m["status"], m["owner"]), ("UNKNOWN", "fallback-control"))

    def test_boundary_and_explicit_review_even_for_complete_packet(self):
        self.receipt("E04")["observed"] = "08:45"
        self.receipt("E06")["accepted"] = 80
        b = brief(self.case, "09:10")
        self.assertEqual(b["state"], "READY_FOR_REVIEW")
        self.assertTrue(b["human_review_required"])
        self.receipt("E04")["observed"] = "08:46"
        self.assertEqual(brief(self.case, "09:10")["state"], "FLAG_FOR_REVIEW")

    def test_register_cutover_ambiguity_and_publication(self):
        self.case["date"] = "2026-11-01"
        self.assertEqual(brief(self.case, "09:10")["policy"], "P4")
        self.case["register"][0]["until"] = None
        self.assertIsNone(brief(self.case, "09:10")["policy"])
        self.case["register"][0]["until"] = "2026-11-01"
        self.case["register"][1]["published"] = "2026-11-02"
        self.assertEqual(brief(self.case, "09:10")["state"], "INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
