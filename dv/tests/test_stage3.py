"""Stage 3 reference-model tests: Host, ComboMeal and Happy Hour."""

import unittest
from pathlib import Path

from tests import _path  # noqa: F401
from rrdv import facts, monitor
from rrdv.model import run_script
from rrdv.sequences import all_directed
from rrdv.spec import CRITIC, STAGE2, STAGE3, combo, hh_bill, vip_bill
from rrdv.stimulus import generate

REPO = Path(__file__).resolve().parents[2]


class Stage3Test(unittest.TestCase):
    def test_pricing(self):
        salad, burger, pasta = STAGE3.menu[:3]
        self.assertEqual(combo(salad, pasta).price_cents, 2430)  # brief 4.3 example
        self.assertEqual(combo(salad, pasta).prep_units, 3)
        self.assertEqual([i.price_cents for i in STAGE3.menu[3:]], [2160, 2430, 2970])
        self.assertEqual(hh_bill(vip_bill(1500)), 1080)  # brief 4.3: VIP Burger in Happy Hour $10.80
        self.assertEqual(hh_bill(vip_bill(1800)), 1296)

    def test_choices(self):
        items = [a.item.name for a in facts.arrivals(STAGE3)]
        self.assertEqual(items, ["Salad", "Burger+Pasta", "Pasta", "Salad+Burger", "Salad+Pasta", "Burger+Pasta"])
        self.assertEqual(STAGE3.menu[CRITIC.choose_item(2, STAGE3.menu)].name, "Burger+Pasta")

    def test_facts(self):
        self.assertEqual(STAGE3.last_payable_arrival, 15)
        self.assertEqual(facts.earliest_pay_turn(STAGE3), 4)
        self.assertEqual(facts.abandon_turns(STAGE3), [12, 13, 14, 15, 16, 17])
        self.assertNotIn("Burger", facts.ordered_items(STAGE3))
        # Stage 2 facts are unchanged by the Stage 3 additions.
        self.assertEqual(facts.abandon_turns(STAGE2), [12, 13])
        self.assertEqual(facts.earliest_pay_turn(STAGE2), 5)

    def test_greedy_wins_and_all_wait_loses(self):
        self.assertTrue(run_script(STAGE3, generate(STAGE3, 0, "greedy").text).victory)
        lazy = run_script(STAGE3, "0\n" * 54)
        self.assertFalse(lazy.victory)
        self.assertEqual(lazy.departures, 2)

    def test_directed_expectations(self):
        for st in all_directed(STAGE3, REPO):
            res = run_script(STAGE3, st.text)
            tr = monitor.parse(res.text)
            if st.expect:
                self.assertEqual(tr.result.outcome if tr.result else None, st.expect, st.name)
            if st.expect_fn:
                self.assertEqual(st.expect_fn(tr), [], st.name)

    def test_fixtures(self):
        for name, want in (("victory", True), ("defeat", False)):
            text = (REPO / "tests" / "stage3" / f"{name}.txt").read_text(encoding="utf-8")
            self.assertEqual(run_script(STAGE3, text).victory, want, name)
        win = run_script(STAGE3, (REPO / "tests" / "stage3" / "victory.txt").read_text(encoding="utf-8"))
        self.assertEqual((win.revenue_cents, win.paid_satisfactions), (9594, [92, 64, 85, 98, 84]))


if __name__ == "__main__":
    unittest.main()
