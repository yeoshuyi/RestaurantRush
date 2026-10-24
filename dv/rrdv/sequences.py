"""Directed sequences: hand-written scenarios for spec examples and corner cases.

Each one is a function intent(req) -> option index, run through the same
lockstep generator as the random tests, so it always lines up with the menus
the DUT shows. Optional expectations (outcome, extra checks) are attached.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Callable, Dict, List

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


def all_directed(spec: StageSpec, repo: Path) -> List[Stimulus]:
    seqs: List[Stimulus] = []
    g = generate(spec, 0, "greedy", name="d_victory_greedy")
    g.expect = "VICTORY"
    seqs.append(g)

    seqs.append(directed(spec, "d_defeat_all_wait", lambda r: 0, expect="DEFEAT",
                         expect_fn=_left_check("C1", 13, "WAITING")))

    # Brief 3.3 example, done with C3 (the first Pasta customer under the item rule):
    # arrives+seated t7 (92), order t8 + unit 1 (84), unit 2 t9 READY (76), serve t10 (76),
    # eat t11 (76), pay t12 $18.00 recording 76.
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
    for name, knobs, flags in (
            ("d_rev_met_paid_missed_sat_met", with_knobs("greedy"), ("MISSED", "met", "met")),
            ("d_rev_met_paid_missed_sat_missed",
             with_knobs("greedy", smart=0.5, chef_wait_prob=0.5,
                        waiter_weights={"wait": 3, "seat": 1, "take": 1, "serve": 1}),
             ("MISSED", "met", "MISSED"))):
        st = generate(spec, 0, "directed", knobs, [skip], name=name)
        st.expect, st.expect_fn = "DEFEAT", _flags_check(flags)
        seqs.append(st)

    # Same abandonment cases for C2 (Burger), who leaves on turn 16.
    seqs.append(directed(spec, "d_abandon_c2_ordered_placed",
                         _plan({4: (SEAT, "C2"), 5: (TAKE, "C2")}, chef_turns=set()),
                         expect="DEFEAT", expect_fn=_left_check("C2", 16, "ORDERED")))
    seqs.append(directed(spec, "d_abandon_c2_ready_unserved",
                         _plan({4: (SEAT, "C2"), 5: (TAKE, "C2")}, chef_turns={5}),
                         expect="DEFEAT", expect_fn=_left_check("C2", 16, "ORDERED")))

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
