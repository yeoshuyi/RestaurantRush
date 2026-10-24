"""Spec assertions over monitored DUT behaviour (not over the model).

Each check is tagged with an ID and the brief clause it enforces, so a failure
says which requirement broke. They work like SVA properties: evaluated over
the whole monitored trace after the run.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from .driver import RunResult
from .javaparse import format_average, format_money, parse_money
from .model.game import EOF_ERROR
from .monitor import Transcript, TurnRecord
from .spec import CUSTOMER_KINDS, StageSpec
from .timeline import Timeline

WAITING_STATES = ("WAITING", "SEATED", "ORDERED")


@dataclass
class Ctx:
    spec: StageSpec
    tr: Transcript
    tl: Timeline
    run: Optional[RunResult]
    text: str
    eof_expected: bool


@dataclass
class Assertion:
    id: str
    clause: str
    fn: Callable[[Ctx], List[str]]


REGISTRY: List[Assertion] = []


def assertion(aid: str, clause: str):
    def deco(fn):
        REGISTRY.append(Assertion(aid, clause, fn))
        return fn
    return deco


def check_all(ctx: Ctx) -> List[str]:
    out: List[str] = []
    for a in REGISTRY:
        try:
            msgs = a.fn(ctx)
        except Exception as e:  # a checker crash is itself a failure worth seeing
            msgs = [f"checker raised {type(e).__name__}: {e}"]
        out += [f"{a.id} [{a.clause}] {m}" for m in msgs]
    return out


def _complete_turns(ctx: Ctx) -> List[TurnRecord]:
    return [t for t in ctx.tr.turns if t.end is not None]


def _kind_by_label(label: str):
    for k in CUSTOMER_KINDS.values():
        if k.label == label:
            return k
    return None


def _cid(name: str) -> int:
    return int(name[1:])


# ------------------------------------------------------------------ process / format


@assertion("A_NO_CRASH", "3.4 robust input; game must not crash")
def a_no_crash(ctx: Ctx) -> List[str]:
    e: List[str] = []
    if ctx.run is not None:
        if ctx.run.timed_out:
            e.append("DUT timed out (possible infinite loop)")
        if ctx.run.returncode != 0:
            e.append(f"exit code {ctx.run.returncode}")
        if ctx.run.stderr.strip():
            e.append("stderr not empty: " + ctx.run.stderr.strip()[:300])
    if re.search(r"^\s+at [\w.$]+\(", ctx.text, re.M) or "Exception in thread" in ctx.text:
        e.append("stack trace in stdout")
    if ctx.tr.error_line is not None and ctx.tr.error_line != EOF_ERROR:
        e.append(f"unexpected error line {ctx.tr.error_line!r}")
    return e


@assertion("A_PRINT_FORMAT", "3.1/3.5 display")
def a_print_format(ctx: Ctx) -> List[str]:
    e = [f"unrecognised output line {t.lineno}: {t.raw!r}" for t in ctx.tr.unknown[:5]]
    if not ctx.tr.banner:
        e.append("missing RestaurantRush banner")
    for m in re.finditer(r"\$\d[\d.]*", ctx.text):
        if not re.fullmatch(r"\$\d+\.\d\d\.?", m.group(0)):
            e.append(f"money not $D.CC: {m.group(0)!r}")
    return e


@assertion("A_ALL_TURNS", "3.2 step 6: always 18 turns, result after the last")
def a_all_turns(ctx: Ctx) -> List[str]:
    e: List[str] = []
    nums = [t.turn for t in ctx.tr.turns]
    if nums != list(range(1, len(nums) + 1)):
        e.append(f"turn numbers not consecutive: {nums}")
    if any(t.max_turns != ctx.spec.max_turns for t in ctx.tr.turns):
        e.append("header max turns != spec")
    if ctx.eof_expected:
        if ctx.tr.result is not None:
            e.append("result printed although input ended early")
        if ctx.tr.error_line != EOF_ERROR:
            e.append(f"expected input-ended error, got {ctx.tr.error_line!r}")
    else:
        if len(nums) != ctx.spec.max_turns:
            e.append(f"played {len(nums)} turns, expected {ctx.spec.max_turns}")
        if ctx.tr.result is None:
            e.append("no RESULT block")
    return e


@assertion("A_TURN_STRUCT", "3.1 start-of-turn display, 3.5 end-of-turn results")
def a_turn_struct(ctx: Ctx) -> List[str]:
    e: List[str] = []
    for t in _complete_turns(ctx):
        s = t.snapshot
        if s is None:
            e.append(f"turn {t.turn}: no state display")
            continue
        if len(s.tables) != ctx.spec.tables:
            e.append(f"turn {t.turn}: {len(s.tables)} tables shown")
        if not t.waiter:
            e.append(f"turn {t.turn}: waiter was not offered a task")
        if t.chef is None:
            e.append(f"turn {t.turn}: no chef step")
        if s.staff != "Waiter (1 task available) | Chef (1 prep unit available) | Cashier automatic, 1 payment":
            e.append(f"turn {t.turn}: staff availability line {s.staff!r}")
        if int(t.end[0]) != t.turn or int(t.end[5]) != t.turn or int(t.end[6]) != ctx.spec.max_turns:
            e.append(f"turn {t.turn}: end-of-turn turn/turns-used mismatch {t.end}")
    return e


# ------------------------------------------------------------------ arrivals


@assertion("A_ARRIVAL_SCHED", "2.1 arrivals at 1,4,7,10,13,16 with satisfaction 100")
def a_arrivals(ctx: Ctx) -> List[str]:
    e: List[str] = []
    n = 0
    for t in ctx.tr.turns:
        if t.snapshot is None:
            continue
        exp = []
        if t.turn in ctx.spec.arrivals:
            n += 1
            exp = [(f"C{n}", ctx.spec.kind_for(t.turn).label)]
        if t.arrivals != exp:
            e.append(f"turn {t.turn}: arrivals {t.arrivals} expected {exp}")
            continue
        for name, _ in exp:
            q = dict(t.snapshot.queue)
            if q.get(name) != ctx.spec.start_satisfaction:
                e.append(f"turn {t.turn}: {name} not in queue with sat {ctx.spec.start_satisfaction}")
            elif t.snapshot.queue[-1][0] != name:
                e.append(f"turn {t.turn}: {name} not at back of queue")
    return e


@assertion("A_QUEUE_ORDER", "3.2 step 1 waiting queue")
def a_queue_order(ctx: Ctx) -> List[str]:
    e: List[str] = []
    for t in ctx.tr.turns:
        if t.snapshot and [_cid(n) for n, _ in t.snapshot.queue] != sorted(_cid(n) for n, _ in t.snapshot.queue):
            e.append(f"turn {t.turn}: queue not in arrival order {t.snapshot.queue}")
    return e


# ------------------------------------------------------------------ waiter


@assertion("A_WAITER_ONE", "3.4 waiter completes at most one task per turn")
def a_waiter_one(ctx: Ctx) -> List[str]:
    e: List[str] = []
    for t in _complete_turns(ctx):
        oks = [a for a in t.waiter if a.outcome == "ok" and a.task != "wait"]
        if len(oks) > 1:
            e.append(f"turn {t.turn}: {len(oks)} successful waiter tasks")
    return e


@assertion("A_FAIL_NO_CONSUME", "3.4 invalid choice explains why and lets the manager choose again")
def a_fail_no_consume(ctx: Ctx) -> List[str]:
    e: List[str] = []
    for t in _complete_turns(ctx):
        if not t.waiter:
            continue
        *head, last = t.waiter
        if last.outcome != "ok":
            e.append(f"turn {t.turn}: waiter step ended on a non-success ({last.task}/{last.outcome})")
        for a in head:
            if a.outcome == "ok":
                e.append(f"turn {t.turn}: waiter re-prompted after a successful {a.task}")
            if a.outcome is None or a.task is None:
                e.append(f"turn {t.turn}: waiter attempt had no visible outcome {a}")
    return e


@assertion("A_WAITER_LEGAL", "3.2 step 2: seat queued at free table; take seated; serve READY")
def a_waiter_legal(ctx: Ctx) -> List[str]:
    e: List[str] = []
    for t in ctx.tr.turns:
        s = t.snapshot
        if s is None:
            continue
        free = [tv.id for tv in s.tables if tv.customer is None]
        queued = [n for n, _ in s.queue]
        seated = [tv.customer for tv in s.tables if tv.state == "SEATED"]
        ready = [tv.order_id for tv in s.tables if tv.order_status == "READY"]
        for a in t.waiter:
            if a.task == "seat":
                if a.outcome == "empty" and queued:
                    e.append(f"turn {t.turn}: 'no customers waiting' but queue {queued}")
                if a.outcome == "no_free_table" and free:
                    e.append(f"turn {t.turn}: 'No free table' but tables {free} free")
                if a.outcome == "ok":
                    name, tid = a.detail[0], int(a.detail[1])
                    if name not in queued:
                        e.append(f"turn {t.turn}: seated {name} who was not queued")
                    if tid not in free:
                        e.append(f"turn {t.turn}: seated at occupied table {tid}")
                if a.options and [o.split(" ")[0] for o in a.options] != queued:
                    e.append(f"turn {t.turn}: seat options {a.options} != queue {queued}")
            elif a.task == "take":
                if a.outcome == "empty" and seated:
                    e.append(f"turn {t.turn}: 'no seated customers' but {seated} seated")
                if a.outcome == "ok" and a.detail[4] != "PLACED":
                    e.append(f"turn {t.turn}: new order status {a.detail[4]} != PLACED")
                if a.options and sorted(o.split(" ")[0] for o in a.options) != sorted(seated):
                    e.append(f"turn {t.turn}: take options {a.options} != seated {seated}")
            elif a.task == "serve":
                if a.outcome == "empty" and ready:
                    e.append(f"turn {t.turn}: 'no orders ready' but READY {ready}")
                if a.outcome == "ok" and int(a.detail[0]) not in ready:
                    e.append(f"turn {t.turn}: served order #{a.detail[0]} that was not READY "
                             f"at start of turn (3.2 step 3)")
                if a.outcome == "ok" and a.detail[4] != "SERVED":
                    e.append(f"turn {t.turn}: served order shows {a.detail[4]}")
    return e


@assertion("A_ORDER_CHOICE", "2.2 customer chooses food by a documented deterministic rule")
def a_order_choice(ctx: Ctx) -> List[str]:
    e: List[str] = []
    for h in ctx.tl.customers.values():
        if not h.item:
            continue
        kind = _kind_by_label(h.ctype) or ctx.spec.kind_for(h.arrival_turn)
        exp = ctx.spec.menu[kind.choose_item(_cid(h.name), len(ctx.spec.menu))]
        if h.item != exp.name:
            e.append(f"{h.name} ordered {h.item}, rule says {exp.name}")
    for o in ctx.tl.orders.values():
        item = ctx.spec.menu_by_name(o.item)
        if o.prep_units != item.prep_units:
            e.append(f"order #{o.id} {o.item}: {o.prep_units} prep units, menu says {item.prep_units}")
        if o.customer:
            h = ctx.tl.customers[o.customer]
            kind = _kind_by_label(h.ctype) or ctx.spec.kind_for(h.arrival_turn)
            if o.bill_cents != kind.bill(item.price_cents):
                e.append(f"order #{o.id}: bill {format_money(o.bill_cents)} != "
                         f"{format_money(kind.bill(item.price_cents))}")
    return e


# ------------------------------------------------------------------ chef


@assertion("A_CHEF", "3.2 step 2/3: chef advances at most one order by one unit; READY at last unit")
def a_chef(ctx: Ctx) -> List[str]:
    e: List[str] = []
    for t in _complete_turns(ctx):
        s = t.snapshot
        kitchen = {tv.order_id: tv for tv in s.tables
                   if tv.order_status in ("PLACED", "IN_PREPARATION")}
        taken = [int(a.detail[0]) for a in t.waiter if a.task == "take" and a.outcome == "ok"]
        expected_n = len(kitchen) + len(taken)
        c = t.chef
        if c.kind == "no_orders" and expected_n:
            e.append(f"turn {t.turn}: chef says no orders but {expected_n} in kitchen")
        if c.kind in ("wait", "prep") and len(c.options) != expected_n:
            e.append(f"turn {t.turn}: chef offered {len(c.options)} orders, expected {expected_n} "
                     f"(incl. orders taken this turn)")
        if c.kind == "prep":
            oid, item, done, total, status, d2, t2, ready = c.detail
            done, total = int(done), int(total)
            prev = kitchen[int(oid)].units_done if int(oid) in kitchen else (0 if int(oid) in taken else None)
            if prev is None:
                e.append(f"turn {t.turn}: chef prepared #{oid} which was not in the kitchen")
            elif done != prev + 1:
                e.append(f"turn {t.turn}: #{oid} went {prev}->{done} units")
            want = "READY" if done >= total else "IN_PREPARATION"
            if status != want or bool(ready) != (want == "READY"):
                e.append(f"turn {t.turn}: #{oid} at {done}/{total} shows {status}{ready or ''}")
            if total != ctx.spec.menu_by_name(item).prep_units:
                e.append(f"turn {t.turn}: {item} needs {ctx.spec.menu_by_name(item).prep_units} units, shown {total}")
    return e


# ------------------------------------------------------------------ eating / payment


@assertion("A_EAT_DELAY", "3.2 step 4: one full turn of eating; pay next turn at the earliest")
def a_eat_delay(ctx: Ctx) -> List[str]:
    e: List[str] = []
    snaps = {t.turn: t for t in ctx.tr.turns if t.snapshot is not None}
    for h in ctx.tl.customers.values():
        if h.served_turn < 0:
            continue
        s = h.served_turn
        if s + 1 in snaps and h.states.get(s + 1) not in (None, "SERVED"):
            e.append(f"{h.name}: served turn {s} but shows {h.states.get(s + 1)} at turn {s + 1}")
        if s + 2 in snaps and h.paid_turn != s + 1 and h.states.get(s + 2) not in (None, "READY_TO_PAY"):
            e.append(f"{h.name}: should be READY_TO_PAY at turn {s + 2}, shows {h.states.get(s + 2)}")
        if 0 < h.paid_turn < s + 2:
            e.append(f"{h.name}: served turn {s} paid turn {h.paid_turn} (< served+2)")
        if h.first_rtp_snapshot > 0 and h.first_rtp_snapshot < s + 2:
            e.append(f"{h.name}: READY_TO_PAY too early (turn {h.first_rtp_snapshot})")
    return e


@assertion("A_CASHIER", "3.2 step 4: at most one payment per turn, oldest READY_TO_PAY first, automatic")
def a_cashier(ctx: Ctx) -> List[str]:
    e: List[str] = []
    for t in _complete_turns(ctx):
        rtp = [tv.customer for tv in t.snapshot.tables if tv.state == "READY_TO_PAY"]
        if len(t.payments) > 1:
            e.append(f"turn {t.turn}: {len(t.payments)} payments")
        if rtp and not t.payments:
            e.append(f"turn {t.turn}: {rtp} READY_TO_PAY but nobody charged")
        for name, _ in t.payments:
            if name not in rtp:
                e.append(f"turn {t.turn}: charged {name} who was not READY_TO_PAY at start of turn (3.4)")
            elif rtp:
                oldest = min(rtp, key=lambda n: (ctx.tl.customers[n].first_rtp_snapshot, _cid(n)))
                if name != oldest:
                    e.append(f"turn {t.turn}: charged {name} before older {oldest}")
    return e


@assertion("A_PAY_AMOUNT", "3.2 step 4: payment adds the bill; 3.4 revenue excludes unpaid/abandoned")
def a_pay_amount(ctx: Ctx) -> List[str]:
    e: List[str] = []
    for h in ctx.tl.customers.values():
        if h.paid_turn > 0:
            o = ctx.tl.orders.get(h.order_id)
            if o is None:
                e.append(f"{h.name} paid without an order")
            elif h.paid_cents != o.bill_cents:
                e.append(f"{h.name} paid {format_money(h.paid_cents)}, bill {format_money(o.bill_cents)}")
            if h.departed_turn > 0:
                e.append(f"{h.name} both paid and left")
    return e


# ------------------------------------------------------------------ satisfaction / abandonment


@assertion("A_SAT_DECAY", "3.2 step 5: waiting/seated unserved lose penalty (min 0); served+ lose nothing")
def a_sat_decay(ctx: Ctx) -> List[str]:
    e: List[str] = []
    prev: Dict[str, tuple] = {}
    for t in ctx.tr.turns:
        if t.snapshot is None:
            continue
        cur: Dict[str, tuple] = {n: (s, "WAITING", None) for n, s in t.snapshot.queue}
        for tv in t.snapshot.tables:
            if tv.customer:
                cur[tv.customer] = (tv.sat, tv.state, tv.ctype)
        arrived = {n for n, _ in t.arrivals}
        for name, (sat, state, ctype) in cur.items():
            if name in arrived:
                continue
            if name not in prev:
                e.append(f"turn {t.turn}: {name} appeared from nowhere")
                continue
            psat = prev[name][0]
            h = ctx.tl.customers.get(name)
            kind = _kind_by_label(h.ctype if h else "") or ctx.spec.kind_for(h.arrival_turn)
            want = max(0, psat - kind.wait_penalty) if state in WAITING_STATES else psat
            if sat != want:
                e.append(f"turn {t.turn}: {name} ({state}) sat {psat}->{sat}, expected {want}")
            if sat <= 0:
                e.append(f"turn {t.turn}: {name} still present with satisfaction {sat}")
        prev = cur
    return e


@assertion("A_ABANDON", "3.2 step 5: at 0 the customer leaves, order cancelled, table freed")
def a_abandon(ctx: Ctx) -> List[str]:
    e: List[str] = []
    gone: Dict[str, int] = {}
    for t in _complete_turns(ctx):
        s = t.snapshot
        served = {ctx.tl.orders[int(a.detail[0])].customer for a in t.waiter
                  if a.task == "serve" and a.outcome == "ok" and int(a.detail[0]) in ctx.tl.orders}
        states = {n: ("WAITING", sat) for n, sat in s.queue}
        states.update({tv.customer: (tv.state, tv.sat) for tv in s.tables if tv.customer})
        must_leave = set()
        for n, (st, sat) in states.items():
            h = ctx.tl.customers.get(n)
            kind = _kind_by_label(h.ctype if h else "") or ctx.spec.kind_for(h.arrival_turn)
            if st in WAITING_STATES and n not in served and sat - kind.wait_penalty <= 0:
                must_leave.add(n)
        if set(t.departures) != must_leave:
            e.append(f"turn {t.turn}: departures {sorted(t.departures)} expected {sorted(must_leave)}")
        for n in t.departures:
            gone[n] = t.turn
        for n, when in gone.items():
            if t.turn > when and n in states:
                e.append(f"turn {t.turn}: {n} left on turn {when} but is still shown")
    return e


@assertion("A_TABLES", "3.4 a table stays occupied until its customer pays or leaves")
def a_tables(ctx: Ctx) -> List[str]:
    e: List[str] = []
    seat_of: Dict[str, int] = {}
    for t in ctx.tr.turns:
        if t.snapshot is None:
            continue
        on_tables = [tv.customer for tv in t.snapshot.tables if tv.customer]
        if len(on_tables) != len(set(on_tables)):
            e.append(f"turn {t.turn}: customer at two tables {on_tables}")
        if set(on_tables) & {n for n, _ in t.snapshot.queue}:
            e.append(f"turn {t.turn}: customer both queued and seated")
        for tv in t.snapshot.tables:
            if tv.customer:
                if tv.customer in seat_of and seat_of[tv.customer] != tv.id:
                    e.append(f"turn {t.turn}: {tv.customer} moved table {seat_of[tv.customer]}->{tv.id}")
                seat_of[tv.customer] = tv.id
                if tv.state == "WAITING":
                    e.append(f"turn {t.turn}: {tv.customer} at table but WAITING")
        # customers that were seated earlier and have not paid/left must still be at their table
        for n, tid in seat_of.items():
            h = ctx.tl.customers.get(n)
            done = h and ((0 < h.paid_turn < t.turn) or (0 < h.departed_turn < t.turn))
            if not done and n not in on_tables:
                e.append(f"turn {t.turn}: {n} vanished from table {tid} without paying or leaving")
    return e


# ------------------------------------------------------------------ metrics / result


@assertion("A_METRICS", "3.1/3.5 revenue, paid, served, departures, average (N/A if none)")
def a_metrics(ctx: Ctx) -> List[str]:
    e: List[str] = []
    revenue = served = departures = 0
    sats: List[int] = []
    for t in ctx.tr.turns:
        s = t.snapshot
        if s is not None:
            if parse_money(s.revenue) != revenue or s.paid != len(sats) or s.avg != format_average(sats):
                e.append(f"turn {t.turn}: status shows {s.revenue}/{s.paid}/{s.avg}, expected "
                         f"{format_money(revenue)}/{len(sats)}/{format_average(sats)}")
        served += sum(1 for a in t.waiter if a.task == "serve" and a.outcome == "ok")
        departures += len(t.departures)
        for name, amount in t.payments:
            revenue += parse_money(amount)
            sats.append(ctx.tl.customers[name].sats.get(t.turn, -1))
        if t.end is not None:
            got = (int(t.end[1]), int(t.end[2]), parse_money(t.end[3]), t.end[4])
            want = (served, departures, revenue, format_average(sats))
            if got != want:
                e.append(f"turn {t.turn}: end-of-turn {got} expected {want}")
    return e


@assertion("A_MAX_PAID", "3.4 the turn-16 customer cannot pay; at most five payments")
def a_max_paid(ctx: Ctx) -> List[str]:
    late = [f"C{i}" for i, turn in enumerate(sorted(ctx.spec.arrivals), 1)
            if turn > ctx.spec.last_payable_arrival]
    paid = [h.name for h in ctx.tl.customers.values() if h.paid_turn > 0]
    return [f"{n} paid although arriving too late" for n in paid if n in late]


@assertion("A_RESULT", "2.1 objective / 3.2 step 6: VICTORY iff all three targets met")
def a_result(ctx: Ctx) -> List[str]:
    r = ctx.tr.result
    if r is None:
        return []
    e: List[str] = []
    turns = _complete_turns(ctx)
    if not turns:
        return ["result without any turn"]
    last = turns[-1].end
    paid = sum(len(t.payments) for t in turns)
    revenue = parse_money(last[3])
    sats = [ctx.tl.customers[n].sats.get(t.turn, -1) for t in turns for n, _ in t.payments]
    sp = ctx.spec
    paid_met = paid >= sp.target_paid
    rev_met = revenue >= sp.target_revenue_cents
    sat_met = bool(sats) and sum(sats) >= sp.target_avg_satisfaction * len(sats)
    victory = paid_met and rev_met and sat_met
    mark = lambda m: "met" if m else "MISSED"
    if r.outcome != ("VICTORY" if victory else "DEFEAT"):
        e.append(f"outcome {r.outcome} but paid={paid} revenue={format_money(revenue)} sats={sats}")
    if r.paid != (str(paid), str(sp.target_paid), mark(paid_met)):
        e.append(f"paid line {r.paid}")
    if r.revenue != (format_money(revenue), format_money(sp.target_revenue_cents), mark(rev_met)):
        e.append(f"revenue line {r.revenue}")
    if r.avg != (format_average(sats), str(sp.target_avg_satisfaction), mark(sat_met)):
        e.append(f"avg line {r.avg}")
    if r.summary != (last[1], last[2], str(sp.max_turns), str(sp.max_turns)):
        e.append(f"summary line {r.summary} vs end-of-turn {last}")
    return e


# ------------------------------------------------------------------ input


@assertion("A_INPUT", "3.4 invalid input explains why and re-prompts")
def a_input(ctx: Ctx) -> List[str]:
    e: List[str] = []
    toks = ctx.tr.tokens
    last_prompt = None
    for i, tok in enumerate(toks):
        if tok.kind == "prompt":
            last_prompt = tok.groups
        elif tok.kind in ("in_nan", "in_range"):
            nxt = toks[i + 1] if i + 1 < len(toks) else None
            if last_prompt is None:
                e.append(f"line {tok.lineno}: input error without a prompt")
                continue
            if tok.groups[-2:] != last_prompt[1:]:
                e.append(f"line {tok.lineno}: error range {tok.groups[-2:]} != prompt {last_prompt}")
            if tok.kind == "in_range":
                v, lo, hi = (int(x) for x in tok.groups)
                if lo <= v <= hi:
                    e.append(f"line {tok.lineno}: {v} reported out of range [{lo},{hi}]")
            if nxt is None or not (nxt.kind == "prompt" and nxt.groups == last_prompt or
                                   nxt.kind in ("blank", "error")):
                e.append(f"line {tok.lineno}: no re-prompt after invalid input")
    return e
