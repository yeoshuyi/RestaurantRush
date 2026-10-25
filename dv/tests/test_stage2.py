"""Stage 2 reference-model tests: VIP and Critic customers."""

import unittest
from pathlib import Path

from tests import _path  # noqa: F401
from rrdv import facts, monitor
from rrdv.model import run_script
from rrdv.sequences import all_directed
from rrdv.spec import CRITIC, STAGE1, STAGE2, VIP, vip_bill
from rrdv.stimulus import generate

REPO = Path(__file__).resolve().parents[2]


class Stage2Test(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual((VIP.wait_penalty, CRITIC.wait_penalty), (5, 12))
        self.assertEqual([vip_bill(c) for c in (900, 1500, 1800)], [810, 1350, 1620])
        self.assertEqual(STAGE2.menu[CRITIC.choose_item(2, STAGE2.menu)].name, "Pasta")

    def test_base_setting_has_vip_and_critic(self):
        kinds = [STAGE2.arrivals[t] for t in sorted(STAGE2.arrivals)]
        self.assertEqual(len(kinds), 6)
        self.assertIn("VIP", kinds)
        self.assertIn("CRITIC", kinds)

    def test_facts_match_old_stage1_constants(self):
        self.assertEqual(facts.abandon_turns(STAGE1), [13, 16])
        self.assertEqual(facts.abandoning_items(STAGE1), {"Salad", "Burger"})
        self.assertEqual(facts.cheapest_bills(STAGE1, 4), 4800)

    def test_facts_stage2(self):
        self.assertEqual(facts.abandon_turns(STAGE2), [12, 13])
        self.assertEqual([a.name for a in facts.can_abandon(STAGE2)], ["C1", "C2"])
        self.assertTrue(facts.multi_unit_cancel_possible(STAGE2))

    def test_greedy_wins_and_all_wait_loses(self):
        win = run_script(STAGE2, generate(STAGE2, 0, "greedy").text)
        self.assertTrue(win.victory)
        self.assertEqual(win.revenue_cents, 6720)
        lazy = run_script(STAGE2, "0\n" * 18)
        self.assertFalse(lazy.victory)
        self.assertEqual(lazy.departures, 2)

    def test_directed_expectations(self):
        for st in all_directed(STAGE2, REPO):
            res = run_script(STAGE2, st.text)
            tr = monitor.parse(res.text)
            if st.expect:
                self.assertEqual(tr.result.outcome if tr.result else None, st.expect, st.name)
            if st.expect_fn:
                self.assertEqual(st.expect_fn(tr), [], st.name)

    def test_fixtures(self):
        for name, want in (("victory", True), ("defeat", False)):
            text = (REPO / "tests" / "stage2" / f"{name}.txt").read_text(encoding="utf-8")
            self.assertEqual(run_script(STAGE2, text).victory, want, name)


if __name__ == "__main__":
    unittest.main()
