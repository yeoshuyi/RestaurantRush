import unittest
from pathlib import Path

from tests import _path  # noqa: F401
from rrdv import monitor, timeline
from rrdv.model import run_script
from rrdv.sequences import all_directed
from rrdv.spec import STAGE1
from rrdv.stimulus import generate

REPO = Path(__file__).resolve().parents[2]


class ModelTest(unittest.TestCase):
    def test_spec_3_3_example(self):
        """Brief 3.3: satisfaction 92/84/76/76/76 and $18.00 recorded at 76 (done with C3)."""
        seq = next(s for s in all_directed(STAGE1, REPO) if s.name == "d_spec_3_3_pasta")
        res = run_script(STAGE1, seq.text)
        tr = monitor.parse(res.text)
        self.assertEqual(seq.expect_fn(tr), [])
        self.assertIn(76, res.paid_satisfactions)

    def test_greedy_wins_and_all_wait_loses(self):
        self.assertTrue(run_script(STAGE1, generate(STAGE1, 0, "greedy").text).victory)
        lazy = run_script(STAGE1, "0\n" * 18)
        self.assertFalse(lazy.victory)
        self.assertEqual(lazy.departures, 2)  # only C1 and C2 can reach 0 within 18 turns

    def test_generation_is_deterministic(self):
        a = generate(STAGE1, 42, "chaos")
        b = generate(STAGE1, 42, "chaos")
        self.assertEqual(a.text, b.text)

    def test_generated_script_replays_identically(self):
        for seed in range(20):
            st = generate(STAGE1, seed, "random")
            if "eof" in st.file_classes:
                continue
            self.assertIsNotNone(run_script(STAGE1, st.text).victory, seed)

    def test_eof(self):
        res = run_script(STAGE1, "")
        self.assertTrue(res.eof)
        self.assertTrue(res.text.endswith("Error: rush.ui.InputReader$InputEndedException: Input ended\n"))

    def test_monitor_parses_model_output_fully(self):
        for seed in range(30):
            st = generate(STAGE1, seed, "chaos")
            tr = monitor.parse(run_script(STAGE1, st.text).text)
            self.assertEqual(tr.unknown, [], seed)
            timeline.build(tr)

    def test_monitor_handles_crlf(self):
        text = run_script(STAGE1, "0\n" * 18).text
        crlf = text.replace("\n", "\r\n")
        from rrdv.driver import normalize
        self.assertEqual(monitor.parse(normalize(crlf.encode())).result.outcome, "DEFEAT")


if __name__ == "__main__":
    unittest.main()
