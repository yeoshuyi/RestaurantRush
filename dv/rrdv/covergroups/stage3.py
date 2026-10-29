"""Stage 3 functional coverage: Host, ComboMeal and Happy Hour (brief 4.3).

Bins come from the spec and rrdv.facts. Facts for the Stage 3 base setting:
  * The menu adds Salad+Burger ($21.60, 2u), Salad+Pasta ($24.30, 3u) and Burger+Pasta
    ($29.70, 3u). Under the position rule C4, C5 and C6 order these; the Critic (C2)
    orders the most demanding one, Burger+Pasta. The VIP (C3) orders Pasta.
  * The Host acts before the Waiter, so a customer can be seated by the Host and have
    its order taken by the Waiter in the same turn, and two customers can be seated per turn.
  * Happy Hour runs on its start turn and the next. Started on turn 18 it only has one turn.
"""

from __future__ import annotations

from .. import facts
from ..spec import HH_DURATION, hh_bill
from . import SampleCtx, covergroup

WAIT_STATES = ("WAITING", "SEATED", "ORDERED")


def _bucket_start(t: int, max_turns: int) -> str:
    if t == max_turns:
        return "last_turn"
    if t <= 3:
        return "1-3"
    if t <= 9:
        return "4-9"
    if t <= 15:
        return "10-15"
    return "16-17"


@covergroup(stage=3)
def host(db, spec):
    g = db.group("cg_host", "Host seating alongside the Waiter")
    cp_act = g.coverpoint("action", ["seat", "wait", "no_customers", "no_free_table"])
    cp_seats = g.coverpoint("seats_per_turn", ["0", "1", "2"],
                            illegal={"3+": "one Host seat plus one Waiter seat at most"})
    cp_after = g.coverpoint("waiter_after_host_seat",
                            ["take_same_customer", "seat_another", "other_task", "wait"])
    cp_pick = g.coverpoint("pick", ["front_of_queue", "not_front"])
    cp_tab = g.coverpoint("table", [str(i) for i in range(1, spec.tables + 1)])

    def sample(ctx: SampleCtx):
        for t in ctx.tr.turns:
            h = t.host
            if h is None or t.end is None:
                continue
            cp_act.sample(h.kind, f"turn {t.turn}")
            oks = [a for a in t.waiter if a.outcome == "ok"]
            seats = (h.kind == "seat") + sum(1 for a in oks if a.task == "seat")
            cp_seats.sample(str(seats) if seats < 3 else "3+", f"turn {t.turn}")
            if h.kind != "seat":
                continue
            name = h.detail[0]
            cp_tab.sample(h.detail[1])
            front = t.snapshot.queue[0][0] if t.snapshot and t.snapshot.queue else None
            cp_pick.sample("front_of_queue" if name == front else "not_front")
            w = oks[-1] if oks else None
            if w is None or w.task == "wait":
                cp_after.sample("wait")
            elif w.task == "seat":
                cp_after.sample("seat_another")
            elif w.task == "take" and ctx.tl.orders.get(int(w.detail[0])) is not None \
                    and ctx.tl.orders[int(w.detail[0])].customer == name:
                cp_after.sample("take_same_customer")
            else:
                cp_after.sample("other_task")
    return sample


@covergroup(stage=3)
def combo(db, spec):
    g = db.group("cg_combo", "combo meals ordered, prepared and billed")
    arr = facts.arrivals(spec)
    combos = {i.name for i in spec.menu if "+" in i.name}
    kx = sorted({(a.kind.label, a.item.name) for a in arr if a.item.name in combos})
    cp_kind = g.coverpoint("kind_x_combo", kx)
    bills = set()
    for a in arr:
        if a.item.name in combos:
            bills.add(f"{a.item.name}={a.bill}")
            bills.add(f"{a.item.name}={hh_bill(a.bill)}")
    cp_bill = g.coverpoint("combo_bill", sorted(bills))
    cp_fate = g.coverpoint("combo_final", ["PAID", "CANCELLED_PLACED", "CANCELLED_IN_PREPARATION",
                                           "CANCELLED_READY", "OPEN"])

    def sample(ctx: SampleCtx):
        for o in ctx.tl.orders.values():
            if o.item not in combos or not o.customer:
                continue
            h = ctx.tl.customers[o.customer]
            cp_kind.sample((h.ctype, o.item), f"order #{o.id}")
            cp_bill.sample(f"{o.item}={o.bill_cents}", f"order #{o.id}")
            if not ctx.eof:
                cp_fate.sample(o.final, f"order #{o.id}")
    return sample


@covergroup(stage=3)
def happy_hour(db, spec):
    g = db.group("cg_happy_hour", "Happy Hour start, display, recovery and pricing")
    cp_start = g.coverpoint("start_turn", ["never", "1-3", "4-9", "10-15", "16-17", "last_turn"])
    cp_disp = g.coverpoint("display", ["available", "ACTIVE, 2 turns left", "ACTIVE, 1 turn left", "used"])
    cp_rec = g.cross("recovery_state_x_amount", WAIT_STATES, ["+15", "capped"])
    arr = facts.arrivals(spec)
    labels = facts.kind_labels(spec)
    cp_kind = g.coverpoint("kind_x_order", [(lab, w) for lab in labels for w in ("hh", "normal")])
    cp_bill = g.coverpoint("hh_bill", sorted({f"{a.kind.label}:{a.item.name}={hh_bill(a.bill)}"
                                               for a in arr if a.turn < spec.max_turns}))
    # Fastest payment is 3 turns after the order (serve, eat, pay), Happy Hour lasts 2.
    cp_lock = g.coverpoint("price_lock", ["taken_before_paid_during", "taken_during_paid_after"],
                           illegal={"taken_during_paid_during": "payment comes at least 3 turns after the order"})
    # A recovery gains min(15, 100 - sat) and sat <= 100 - penalty, so it always buys at
    # least one full turn (penalties are <= 15).
    cp_left = g.coverpoint("departure_vs_no_hh", ["delayed"],
                           illegal={"earlier": "Happy Hour only adds satisfaction",
                                    "same_turn": "a recovery always buys at least one turn"})

    def sample(ctx: SampleCtx):
        start = None
        prev = {}
        hh_turns = set()
        for t in ctx.tr.turns:
            s = t.snapshot
            if s is None:
                continue
            if t.hh_started:
                start = t.turn
            if s.hh is not None:
                cp_disp.sample(s.hh)
                if s.hh.startswith("ACTIVE"):
                    hh_turns.add(t.turn)
            cur = {n: (sat, "WAITING") for n, sat in s.queue}
            cur.update({tv.customer: (tv.sat, tv.state) for tv in s.tables if tv.customer})
            for n, sat in t.recoveries:
                h = ctx.tl.customers.get(n)
                state = cur.get(n, (0, "?"))[1]
                if n in prev and h is not None:
                    a = next((x for x in arr if x.name == n), None)
                    before = max(0, prev[n] - a.kind.wait_penalty) if a else -1
                    cp_rec.sample((state, "+15" if sat - before == 15 else "capped"), f"turn {t.turn} {n}")
            prev = {n: v[0] for n, v in cur.items()}
        if not ctx.eof and ctx.tr.result is not None:
            cp_start.sample("never" if start is None else _bucket_start(start, spec.max_turns))
        for o in ctx.tl.orders.values():
            if not o.customer:
                continue
            h = ctx.tl.customers[o.customer]
            cp_kind.sample((h.ctype, "hh" if o.hh else "normal"), f"order #{o.id}")
            if o.hh:
                cp_bill.sample(f"{h.ctype}:{o.item}={o.bill_cents}", f"order #{o.id}")
            if h.paid_turn > 0:
                paid_hh = h.paid_turn in hh_turns
                if not o.hh and paid_hh:
                    cp_lock.sample("taken_before_paid_during")
                elif o.hh:
                    cp_lock.sample("taken_during_paid_during" if paid_hh else "taken_during_paid_after")
        by_name = {a.name: a for a in arr}
        for h in ctx.tl.customers.values():
            a = by_name.get(h.name)
            if h.departed_turn > 0 and a is not None:
                base = facts.abandon_turn(spec, a)
                if h.recovered_turns:
                    d = h.departed_turn - base
                    cp_left.sample("same_turn" if d == 0 else "delayed" if d > 0 else "earlier", h.name)
    return sample
