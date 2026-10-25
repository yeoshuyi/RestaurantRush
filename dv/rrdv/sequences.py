"""Directed sequences: hand-written scenarios for spec examples and corner cases.

Each one is a function intent(req) -> option index, run through the same
lockstep generator as the random tests, so it always lines up with the menus
the DUT shows. Optional expectations (outcome, extra checks) are attached.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Callable, Dict, List

from . import facts
from .model.game import GameModel, InputRequest, InputSource, join_script
from .monitor import Transcript
from .spec import StageSpec
from .stimulus import Constraint, Policy, Stimulus, annotate, generate, with_knobs

WAIT, SEAT, TAKE, SERVE = 0, 1, 2, 3


class IntentSource(InputSource):
    def __init__(self, intent: Callable[[InputRequest], int]):
        self.intent = intent
        self.pol = Policy(with_knobs("greedy"), random.Random(0))  # only for annotate()

    def next_line(self, req: InputRequest):
        self.pol.turn_marks.setdefault(req.model.turn, self.pol.lines_out)
        self.pol.lines_out += 1
        return str(self.intent(req))


def pick(req: InputRequest, name: str) -> int:
    for i, o in enumerate(req.options, 1):
        if getattr(o, "name", None) == name or getattr(getattr(o, "customer", None), "name", None) == name:
            return i
    return 0


def directed(spec: StageSpec, name: str, intent: Callable[[InputRequest], int], expect=None,
             expect_fn=None) -> Stimulus:
    src = IntentSource(intent)
    res = GameModel(spec, src).run()
    st = Stimulus(name, 0, "directed", join_script(res.consumed))
    st.annotated = annotate(res.consumed, src.pol)
    st.expect, st.expect_fn = expect, expect_fn
    return st


def _plan(waiter: Dict[int, tuple], chef_turns=None, chef_default: int = 1):
    """waiter: turn -> (task, target customer name or None). Chef preps oldest on chef_turns."""

    def intent(req: InputRequest) -> int:
        t = req.model.turn
        task, who = waiter.get(t, (WAIT, None))
        if req.kind == "waiter_task":
            return task
        if req.kind in ("seat", "take"):
            return pick(req, who) if who else 1
        if req.kind == "serve":
            return pick(req, who) if who else 1
        if req.kind == "chef":
            if chef_turns is None:
                return chef_default
            return 1 if t in chef_turns else 0
        return 0
    return intent


def _sat_check(name: str, by_turn: Dict[int, int], paid_turn: int = -1, paid: str = ""):
    def check(tr: Transcript) -> List[str]:
        errs = []
        for t in tr.turns:
            if t.turn in by_turn and t.snapshot is not None:
                cur = dict(t.snapshot.queue)
                cur.update({tv.customer: tv.sat for tv in t.snapshot.tables if tv.customer})
                if cur.get(name) != by_turn[t.turn]:
                    errs.append(f"{name} sat at turn {t.turn} = {cur.get(name)}, spec example says {by_turn[t.turn]}")
            if t.turn == paid_turn and (name, paid) not in t.payments:
                errs.append(f"{name} should pay {paid} on turn {paid_turn}, payments {t.payments}")
        return errs
    return check


def _left_check(name: str, turn: int, state: str):
    def check(tr: Transcript) -> List[str]:
        from .timeline import build
        h = build(tr).customers.get(name)
        if h is None or h.departed_turn != turn or h.state_at_departure != state:
            got = (h.departed_turn, h.state_at_departure) if h else None
            return [f"{name} should leave on turn {turn} from {state}, got {got}"]
        return []
    return check


def _flags_check(flags):
    def check(tr: Transcript) -> List[str]:
        r = tr.result
        got = (r.paid[2], r.revenue[2], r.avg[2]) if r and r.paid and r.revenue and r.avg else None
        return [] if got == flags else [f"target flags {got}, expected {flags}"]
    return check


def _order_check(name: str, item: str, bill: str):
    def check(tr: Transcript) -> List[str]:
        from .timeline import build
        h = build(tr).customers.get(name)
        got = None
        if h is not None and h.order_id > 0:
            o = build(tr).orders[h.order_id]
            got = (o.item, o.bill_cents)
        from .javaparse import parse_money
        want = (item, parse_money(bill))
        return [] if got == want else [f"{name} order {got}, expected {want}"]
    return check


def _all(*checks):
    def check(tr: Transcript) -> List[str]:
        return [m for c in checks for m in c(tr)]
    return check


def stage2_directed(spec: StageSpec, arr, leave) -> List[Stimulus]:
    """Stage 2 scenarios for the Critic (C2, turn 4) and the VIP (C3, turn 7)."""
    seqs: List[Stimulus] = []
    critic = next(a for a in arr.values() if a.kind.key == "CRITIC")
    vip = next(a for a in arr.values() if a.kind.key == "VIP")
    c, v = critic.name, vip.name
    ct, vt = critic.turn, vip.turn

    # Critic fast path: seated on arrival (88), order + unit 1 (76), unit 2 READY (64),
    # served (64), eats, pays full price for Pasta recording 64.
    seqs.append(directed(
        spec, "d_critic_fast_pasta",
        _plan({ct: (SEAT, c), ct + 1: (TAKE, c), ct + 3: (SERVE, None)}, chef_turns={ct + 1, ct + 2}),
        expect_fn=_all(_sat_check(c, {ct + 1: 88, ct + 2: 76, ct + 3: 64, ct + 4: 64, ct + 5: 64},
                                  ct + 5, "$18.00"),
                       _order_check(c, "Pasta", "$18.00"))))
    # VIP fast path: 95 / 90 / 85, 10% off Pasta = $16.20.
    seqs.append(directed(
        spec, "d_vip_fast_pasta",
        _plan({vt: (SEAT, v), vt + 1: (TAKE, v), vt + 3: (SERVE, None)}, chef_turns={vt + 1, vt + 2}),
        expect_fn=_all(_sat_check(v, {vt + 1: 95, vt + 2: 90, vt + 3: 85, vt + 4: 85, vt + 5: 85},
                                  vt + 5, "$16.20"),
                       _order_check(v, "Pasta", "$16.20"))))
    # Critic abandons with a half-cooked Pasta (IN_PREPARATION -> CANCELLED).
    seqs.append(directed(
        spec, "d_critic_abandon_in_prep",
        _plan({ct: (SEAT, c), ct + 1: (TAKE, c)}, chef_turns={ct + 1}),
        expect="DEFEAT", expect_fn=_left_check(c, leave[c], "ORDERED")))
    # Critic abandons while still in the queue / seated without ordering.
    seqs.append(directed(spec, "d_critic_abandon_seated", _plan({ct: (SEAT, c)}, chef_turns=set()),
                         expect="DEFEAT", expect_fn=_left_check(c, leave[c], "SEATED")))
    # Critic rescued on its last turn (sat 4): served on turn leave[c], pays two turns later.
    seqs.append(directed(
        spec, "d_critic_last_chance",
        _plan({ct: (SEAT, c), ct + 1: (TAKE, c), leave[c]: (SERVE, c)}, chef_turns={ct + 1, ct + 2}),
        expect_fn=_sat_check(c, {leave[c]: 4, leave[c] + 1: 4, leave[c] + 2: 4}, leave[c] + 2, "$18.00")))
    # VIP served as late as possible and still pays on the last turn (satisfaction 55).
    last_serve = spec.max_turns - 2
    seqs.append(directed(
        spec, "d_vip_late_payment",
        _plan({vt: (SEAT, v), last_serve - 3: (TAKE, v), last_serve: (SERVE, v)},
              chef_turns={last_serve - 3, last_serve - 2}),
        expect_fn=_sat_check(v, {last_serve: 55}, spec.max_turns, "$16.20")))
    # Revenue met with only three payers (Critic $18 + VIP $16.20 + C5 Burger $15 = $49.20)
    # but the average misses: the Critic is served on its last turn (4), VIP 85, C5 84 -> 57.7.
    seqs.append(directed(
        spec, "d_rev_met_paid_missed_sat_missed",
        _plan({ct: (SEAT, c), ct + 1: (TAKE, c), vt: (SEAT, v), vt + 1: (TAKE, v), vt + 3: (SERVE, v),
               leave[c]: (SERVE, c), 13: (SEAT, "C5"), 14: (TAKE, "C5"), 15: (SERVE, "C5")},
              chef_turns={ct + 1, ct + 2, vt + 1, vt + 2, 14}),
        expect="DEFEAT", expect_fn=_flags_check(("MISSED", "met", "MISSED"))))
    # VIP never leaves: waiting all game it is still in the queue at 100 - 5*17 = 15.
    def vip_stays(tr: Transcript) -> List[str]:
        last = tr.turns[-1].snapshot if tr.turns else None
        q = dict(last.queue) if last else {}
        want = spec.start_satisfaction - vip.kind.wait_penalty * (spec.max_turns - vt)
        return [] if q.get(v) == want else [f"{v} queue sat on last turn {q.get(v)}, expected {want}"]
    seqs.append(directed(spec, "d_vip_never_abandons", lambda r: 0, expect="DEFEAT", expect_fn=vip_stays))
    return seqs


def all_directed(spec: StageSpec, repo: Path) -> List[Stimulus]:
    seqs: List[Stimulus] = []
    g = generate(spec, 0, "greedy", name="d_victory_greedy")
    g.expect = "VICTORY"
    seqs.append(g)

    arr = {a.name: a for a in facts.arrivals(spec)}
    leave = {n: facts.abandon_turn(spec, a) for n, a in arr.items()}
    seqs.append(directed(spec, "d_defeat_all_wait", lambda r: 0, expect="DEFEAT",
                         expect_fn=_left_check("C1", leave["C1"], "WAITING")))

    # Brief 3.3 example, done with C3 (the first Pasta customer under the item rule):
    # arrives+seated t7 (92), order t8 + unit 1 (84), unit 2 t9 READY (76), serve t10 (76),
    # eat t11 (76), pay t12 $18.00 recording 76. Stage 2 makes C3 a VIP (see below).
    if arr["C3"].kind.key == "REGULAR":
        seqs.append(directed(
            spec, "d_spec_3_3_pasta",
            _plan({7: (SEAT, "C3"), 8: (TAKE, "C3"), 10: (SERVE, None)}, chef_turns={8, 9}),
            expect_fn=_sat_check("C3", {8: 92, 9: 84, 10: 76, 11: 76, 12: 76}, 12, "$18.00")))

    seqs.append(directed(spec, "d_abandon_seated", _plan({1: (SEAT, "C1")}, chef_turns=set()),
                         expect="DEFEAT", expect_fn=_left_check("C1", 13, "SEATED")))
    seqs.append(directed(spec, "d_abandon_ordered_placed",
                         _plan({1: (SEAT, "C1"), 2: (TAKE, "C1")}, chef_turns=set()),
                         expect="DEFEAT", expect_fn=_left_check("C1", 13, "ORDERED")))
    seqs.append(directed(spec, "d_abandon_ready_unserved",
                         _plan({1: (SEAT, "C1"), 2: (TAKE, "C1")}, chef_turns={2}),
                         expect="DEFEAT", expect_fn=_left_check("C1", 13, "ORDERED")))
    # C1 at satisfaction 4 on turn 13 is served just in time and pays on turn 15 with 4.
    seqs.append(directed(spec, "d_last_chance_rescue",
                         _plan({1: (SEAT, "C1"), 2: (TAKE, "C1"), 13: (SERVE, None)}, chef_turns={12}),
                         expect_fn=_sat_check("C1", {13: 4, 14: 4, 15: 4}, 15, "$9.00")))
    # Both tables full when C3 arrives: try to seat (No free table), then Back, then Wait.
    def no_table(req: InputRequest) -> int:
        t, m = req.model.turn, req.model
        if req.kind == "waiter_task":
            if t in (1, 4):
                return SEAT
            if t == 7 and m.waiter_attempts == 1:
                return SEAT
            if t == 7 and m.waiter_attempts == 2:
                return SEAT
            return WAIT
        if req.kind == "seat":
            return 0 if (t == 7 and m.waiter_attempts == 2) else 1
        return 0
    seqs.append(directed(spec, "d_no_free_table_and_back", no_table, expect="DEFEAT"))
    # Every empty-list message on turn 1-2 (queue empty after seating, no ready orders).
    def empties(req: InputRequest) -> int:
        t, m = req.model.turn, req.model
        if req.kind == "waiter_task":
            if t == 1:
                return [TAKE, SERVE, SEAT][min(m.waiter_attempts - 1, 2)]
            if t == 2:
                return [SEAT, SERVE, WAIT][min(m.waiter_attempts - 1, 2)]
            return WAIT
        return 1
    seqs.append(directed(spec, "d_empty_lists", empties, expect="DEFEAT"))

    # Revenue target met with only 3 paid needs exactly C2+C3+C5 ($15+$18+$15 = $48):
    # never seat C1/C4. Fast service meets the average; slow service misses it.
    skip = Constraint("skip_C1_C4", lambda q, c: not (
        q.kind == "seat" and c.value > 0 and q.options[c.value - 1].name in ("C1", "C4")))
    # (Stage 2 builds the "sat missed" case explicitly in stage2_directed.)
    variants = [("d_rev_met_paid_missed_sat_met", with_knobs("greedy"), ("MISSED", "met", "met"))]
    if spec.stage < 2:
        variants.append(("d_rev_met_paid_missed_sat_missed",
                         with_knobs("greedy", smart=0.5, chef_wait_prob=0.5,
                                    waiter_weights={"wait": 3, "seat": 1, "take": 1, "serve": 1}),
                         ("MISSED", "met", "MISSED")))
    for name, knobs, flags in variants:
        st = generate(spec, 0, "directed", knobs, [skip], name=name)
        st.expect, st.expect_fn = "DEFEAT", _flags_check(flags)
        seqs.append(st)

    # Same abandonment cases for C2 (Stage 1: Burger, leaves turn 16;
    # Stage 2: Critic with Pasta, leaves turn 12).
    c2_units = arr["C2"].item.prep_units
    seqs.append(directed(spec, "d_abandon_c2_ordered_placed",
                         _plan({4: (SEAT, "C2"), 5: (TAKE, "C2")}, chef_turns=set()),
                         expect="DEFEAT", expect_fn=_left_check("C2", leave["C2"], "ORDERED")))
    seqs.append(directed(spec, "d_abandon_c2_ready_unserved",
                         _plan({4: (SEAT, "C2"), 5: (TAKE, "C2")}, chef_turns=set(range(5, 5 + c2_units))),
                         expect="DEFEAT", expect_fn=_left_check("C2", leave["C2"], "ORDERED")))
    if spec.stage >= 2:
        seqs += stage2_directed(spec, arr, leave)

    eof = Stimulus("d_eof_immediate", 0, "directed", "")
    eof.file_classes = ["eof"]
    seqs.append(eof)
    # Input ends exactly at each kind of prompt (greedy, no junk: one line per prompt).
    rng = random.Random(0)
    pol = Policy(with_knobs("greedy"), rng)
    lines = GameModel(spec, pol).run().consumed
    for kind in ("waiter_task", "seat", "take", "serve", "chef"):
        idx = next(i for i, (turn, k, _) in enumerate(pol.decisions) if k == kind and turn > 1)
        st = Stimulus(f"d_eof_at_{kind}", 0, "directed", join_script(lines[:idx]))
        st.file_classes = ["eof"]
        seqs.append(st)

    storm = generate(spec, 7, "greedy", with_knobs("greedy", junk_prob=1.0, variant_prob=1.0, junk_max=3),
                     name="d_junk_storm")
    storm.expect = "VICTORY"
    seqs.append(storm)

    for path in sorted((repo / "tests" / f"stage{spec.stage}").glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        seqs.append(Stimulus(f"replay_{path.stem}", 0, "replay", text))
    return seqs
