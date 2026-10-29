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
from .javaparse import format_money
from .model.game import GameModel, InputRequest, InputSource, join_script
from .monitor import Transcript
from .spec import StageSpec, hh_bill
from .stimulus import Constraint, Policy, Stimulus, annotate, generate, with_knobs

WAIT, SEAT, TAKE, SERVE = 0, 1, 2, 3


STAGE3_KINDS = ("host", "happy_hour")


class IntentSource(InputSource):
    """Answers prompts with intent(req). Intents written before Stage 3 don't know the Host or
    Happy Hour prompts, so those get 0 (Wait / Not now) unless the intent sets `stage3 = True`."""

    def __init__(self, intent: Callable[[InputRequest], int]):
        self.intent = intent
        self.pol = Policy(with_knobs("greedy"), random.Random(0))  # only for annotate()

    def next_line(self, req: InputRequest):
        self.pol.turn_marks.setdefault(req.model.turn, self.pol.lines_out)
        self.pol.lines_out += 1
        if req.kind in STAGE3_KINDS and not getattr(self.intent, "stage3", False):
            return "0"
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


def _fast_sats(start: int, penalty: int, arrive: int, units: int, extra: int = 0) -> Dict[int, int]:
    """Snapshot satisfaction on the no-Host fast path: seated on arrival, order next turn,
    Chef every turn, served the turn after READY (`extra` more waiting turns before serving)."""
    lost = units + 1 + extra
    sats = {arrive + k: start - penalty * k for k in range(1, lost + 1)}
    for k in range(lost + 1, lost + 3):
        sats[arrive + k] = start - penalty * lost
    return sats


def stage2_directed(spec: StageSpec, arr, leave) -> List[Stimulus]:
    """Stage 2 scenarios for the Critic (C2, turn 4) and the VIP (C3, turn 7).

    Items, units and bills come from rrdv.facts, so they also hold in Stage 3, where the
    Critic orders a 3-unit combo. Host / Happy Hour prompts are answered with 0.
    """
    seqs: List[Stimulus] = []
    critic = next(a for a in arr.values() if a.kind.key == "CRITIC")
    vip = next(a for a in arr.values() if a.kind.key == "VIP")
    c, v = critic.name, vip.name
    ct, vt = critic.turn, vip.turn
    cu, vu = critic.item.prep_units, vip.item.prep_units
    cbill, vbill = format_money(critic.bill), format_money(vip.bill)
    start = spec.start_satisfaction

    # Critic fast path: seated on arrival, order + Chef every turn, served the turn after READY,
    # pays full price for the most demanding dish (Stage 2 Pasta: 88/76/64, pays at 64).
    sats = _fast_sats(start, critic.kind.wait_penalty, ct, cu)
    seqs.append(directed(
        spec, "d_critic_fast",
        _plan({ct: (SEAT, c), ct + 1: (TAKE, c), ct + cu + 1: (SERVE, None)},
              chef_turns=set(range(ct + 1, ct + cu + 1))),
        expect_fn=_all(_sat_check(c, sats, ct + cu + 3, cbill), _order_check(c, critic.item.name, cbill))))
    # VIP fast path: 95 / 90 / 85, 10% off Pasta = $16.20.
    sats = _fast_sats(start, vip.kind.wait_penalty, vt, vu)
    seqs.append(directed(
        spec, "d_vip_fast",
        _plan({vt: (SEAT, v), vt + 1: (TAKE, v), vt + vu + 1: (SERVE, None)},
              chef_turns=set(range(vt + 1, vt + vu + 1))),
        expect_fn=_all(_sat_check(v, sats, vt + vu + 3, vbill), _order_check(v, vip.item.name, vbill))))
    if cu > 1:
        # Critic abandons with a half-cooked dish (IN_PREPARATION -> CANCELLED).
        seqs.append(directed(
            spec, "d_critic_abandon_in_prep",
            _plan({ct: (SEAT, c), ct + 1: (TAKE, c)}, chef_turns={ct + 1}),
            expect="DEFEAT", expect_fn=_left_check(c, leave[c], "ORDERED")))
    # Critic abandons while seated without ordering.
    seqs.append(directed(spec, "d_critic_abandon_seated", _plan({ct: (SEAT, c)}, chef_turns=set()),
                         expect="DEFEAT", expect_fn=_left_check(c, leave[c], "SEATED")))
    # Critic rescued on its last turn (sat 4): served on turn leave[c], pays two turns later.
    last = start - critic.kind.wait_penalty * (leave[c] - ct)
    seqs.append(directed(
        spec, "d_critic_last_chance",
        _plan({ct: (SEAT, c), ct + 1: (TAKE, c), leave[c]: (SERVE, c)},
              chef_turns=set(range(ct + 1, ct + cu + 1))),
        expect_fn=_sat_check(c, {leave[c]: last, leave[c] + 1: last, leave[c] + 2: last},
                             leave[c] + 2, cbill)))
    # VIP served as late as possible and still pays on the last turn (satisfaction 55).
    last_serve = spec.max_turns - 2
    seqs.append(directed(
        spec, "d_vip_late_payment",
        _plan({vt: (SEAT, v), last_serve - vu - 1: (TAKE, v), last_serve: (SERVE, v)},
              chef_turns=set(range(last_serve - vu - 1, last_serve - 1))),
        expect_fn=_sat_check(v, {last_serve: start - vip.kind.wait_penalty * (last_serve - vt)},
                             spec.max_turns, vbill)))
    # Revenue met with only three payers (Critic + VIP + C5) but the average misses:
    # the Critic is served on its last turn (4). The Chef always works on the oldest order.
    seqs.append(directed(
        spec, "d_rev_met_paid_missed_sat_missed",
        _plan({ct: (SEAT, c), ct + 1: (TAKE, c), vt: (SEAT, v), vt + 1: (TAKE, v), vt + vu + 1: (SERVE, v),
               leave[c]: (SERVE, c), 13: (SEAT, "C5"), 14: (TAKE, "C5"),
               14 + arr["C5"].item.prep_units: (SERVE, "C5")}),
        expect="DEFEAT", expect_fn=_flags_check(("MISSED", "met", "MISSED"))))
    # VIP never leaves: waiting all game it is still in the queue at 100 - 5*17 = 15.
    def vip_stays(tr: Transcript) -> List[str]:
        last = tr.turns[-1].snapshot if tr.turns else None
        q = dict(last.queue) if last else {}
        want = spec.start_satisfaction - vip.kind.wait_penalty * (spec.max_turns - vt)
        return [] if q.get(v) == want else [f"{v} queue sat on last turn {q.get(v)}, expected {want}"]
    seqs.append(directed(spec, "d_vip_never_abandons", lambda r: 0, expect="DEFEAT", expect_fn=vip_stays))
    return seqs


def _plan3(waiter: Dict[int, tuple], host: Dict[int, str] = None, hh: int = -1, chef_turns=None):
    """Stage 3 plan: `host` turn -> customer the Host seats, Happy Hour started on turn `hh`."""
    base = _plan(waiter, chef_turns)
    host = host or {}

    def intent(req: InputRequest) -> int:
        t = req.model.turn
        if req.kind == "happy_hour":
            return 1 if t == hh else 0
        if req.kind == "host":
            return pick(req, host[t]) if t in host else 0
        return base(req)
    intent.stage3 = True
    return intent


def _check(fn):
    """Directed check on the parsed transcript and its timeline."""
    def check(tr: Transcript) -> List[str]:
        from .timeline import build
        return fn(tr, build(tr))
    return check


def stage3_directed(spec: StageSpec, arr) -> List[Stimulus]:
    """Host, combo and Happy Hour scenarios (brief 4.3)."""
    seqs: List[Stimulus] = []
    c1, c2, c3 = arr["C1"], arr["C2"], arr["C3"]
    p1 = c1.kind.wait_penalty

    # Host seats C1 and the Waiter takes its order on turn 1; Chef finishes the Salad the same
    # turn; served turn 2, eats turn 3, pays turn 4 with one turn of loss (92).
    seqs.append(directed(
        spec, "d_host_take_same_turn",
        _plan3({1: (TAKE, "C1"), 2: (SERVE, None)}, host={1: "C1"}),
        expect_fn=_sat_check("C1", {2: 92, 3: 92, 4: 92}, 4, format_money(c1.bill))))
    # Two seats in one turn: C1 waits in the queue until C2 arrives, then the Host seats C1
    # and the Waiter seats C2.
    def two_seated(tr, tl):
        got = (tl.customers["C1"].seated_turn, tl.customers["C1"].seated_by,
               tl.customers["C2"].seated_turn, tl.customers["C2"].seated_by)
        return [] if got == (4, "Host", 4, "Waiter") else [f"seats {got}, expected both on turn 4"]
    seqs.append(directed(spec, "d_host_and_waiter_seat", _plan3({4: (SEAT, "C2")}, host={4: "C1"}),
                         expect="DEFEAT", expect_fn=_check(two_seated)))
    # Both tables taken by unserved customers when C3 arrives: "The host has no free table."
    def no_table(tr, tl):
        t7 = tr.turns[6]
        return [] if t7.host is not None and t7.host.kind == "no_free_table" else [f"turn 7 host {t7.host}"]
    seqs.append(directed(spec, "d_host_no_free_table", _plan3({}, host={1: "C1", 4: "C2"}),
                         expect="DEFEAT", expect_fn=_check(no_table)))
    # Critic seated by the Host and ordering on arrival: its combo needs Chef turns 4-6,
    # served turn 7 (lost 3 x 12 = 64), pays full price two turns later.
    cu = c2.item.prep_units
    seqs.append(directed(
        spec, "d_host_critic_combo",
        _plan3({c2.turn: (TAKE, "C2"), c2.turn + cu: (SERVE, "C2")}, host={c2.turn: "C2"}),
        expect_fn=_all(_sat_check("C2", {c2.turn + cu + 2: 100 - c2.kind.wait_penalty * cu},
                                  c2.turn + cu + 2, format_money(c2.bill)),
                       _order_check("C2", c2.item.name, format_money(c2.bill)))))
    # Happy Hour recovery: C1 waits in the queue (92 at turn 2, 84 after turn 2). Started on
    # turn 3: 84 + 15 = 99 at turn 3, 99 - 8 + 15 capped at 100 on turn 4, then 92 at turn 5.
    seqs.append(directed(spec, "d_hh_recovery", _plan3({}, hh=3), expect="DEFEAT",
                         expect_fn=_sat_check("C1", {2: 92, 3: 99, 4: 100, 5: 100 - p1})))
    # Price lock: C1's Salad is taken before Happy Hour and paid during it (full price);
    # C2's combo is taken during Happy Hour (20% off) and paid after it ended.
    def lock(tr, tl):
        o1 = tl.orders[tl.customers["C1"].order_id]
        o2 = tl.orders[tl.customers["C2"].order_id]
        got = (o1.hh, tl.customers["C1"].paid_cents, o2.hh, tl.customers["C2"].paid_cents)
        want = (False, c1.bill, True, hh_bill(c2.bill))
        return [] if got == want else [f"price lock {got}, expected {want}"]
    seqs.append(directed(
        spec, "d_hh_price_lock",
        _plan3({1: (TAKE, "C1"), 2: (SERVE, "C1"), 4: (TAKE, "C2"), 4 + cu: (SERVE, "C2")},
               host={1: "C1", 4: "C2"}, hh=3),
        expect_fn=_check(lock)))
    # VIP order during Happy Hour: VIP discount first, then 20% (Pasta $18 -> $16.20 -> $12.96).
    seqs.append(directed(
        spec, "d_hh_vip",
        _plan3({c3.turn: (TAKE, "C3"), c3.turn + c3.item.prep_units: (SERVE, "C3")},
               host={c3.turn: "C3"}, hh=c3.turn),
        expect_fn=_order_check("C3", c3.item.name, format_money(hh_bill(c3.bill)))))
    # Happy Hour started on the last turn only gets one active turn.
    def last(tr, tl):
        t = tr.turns[-1]
        return [] if t.snapshot.hh == "ACTIVE, 2 turns left" and tr.turns[-2].snapshot.hh == "available" \
            else [f"last turns show {tr.turns[-2].snapshot.hh!r}, {t.snapshot.hh!r}"]
    seqs.append(directed(spec, "d_hh_last_turn", _plan3({}, hh=spec.max_turns), expect="DEFEAT",
                         expect_fn=_check(last)))
    # Happy Hour delays departures: everyone waits. One run per reachable departure turn that
    # needs Happy Hour, using the earliest start turn that produces it (rrdv.facts).
    plain = {facts.abandon_turn(spec, a) for a in facts.can_abandon(spec)}
    done = set()
    for start in range(1, spec.max_turns + 1):
        exp = {a.name: facts._leave_with_hh(spec, a, start) for a in facts.can_abandon(spec)}
        new = {t for t in exp.values() if t <= spec.max_turns} - plain - done
        if not new:
            continue
        done |= new
        seqs.append(directed(spec, f"d_hh_delays_departure_s{start}", _plan3({}, hh=start), expect="DEFEAT",
                             expect_fn=_all(*(_left_check(n, t, "WAITING") for n, t in exp.items()
                                              if t <= spec.max_turns))))
    # Happy Hour keeps C1 long enough to be served on its (delayed) last turn, so its Salad is
    # still unpaid (SERVED) when the game ends.
    late = facts._leave_with_hh(spec, c1, 11)
    if late >= spec.max_turns - 1:
        seqs.append(directed(
            spec, "d_hh_late_serve_unpaid",
            _plan3({1: (TAKE, "C1"), late: (SERVE, "C1")}, host={1: "C1"}, hh=11),
            expect="DEFEAT", expect_fn=_check(lambda tr, tl: [] if tl.orders[1].final == "OPEN"
                                              else [f"C1 order final {tl.orders[1].final}"])))
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
        q.kind in ("seat", "host") and c.value > 0 and q.options[c.value - 1].name in ("C1", "C4")))
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
    if spec.has("host") and spec.has("happy_hour"):
        seqs += stage3_directed(spec, arr)

    eof = Stimulus("d_eof_immediate", 0, "directed", "")
    eof.file_classes = ["eof"]
    seqs.append(eof)
    # Input ends exactly at each kind of prompt (greedy, no junk: one line per prompt).
    rng = random.Random(0)
    pol = Policy(with_knobs("greedy"), rng)
    lines = GameModel(spec, pol).run().consumed
    for kind in ("waiter_task", "seat", "take", "serve", "chef") + STAGE3_KINDS:
        idx = next((i for i, (turn, k, _) in enumerate(pol.decisions) if k == kind and turn > 1), None)
        if idx is None:
            continue  # e.g. Stage 3 greedy play lets the Host do all the seating (see stage3_directed)
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
