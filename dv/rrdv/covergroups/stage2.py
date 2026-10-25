"""Stage 2 functional coverage: VIP and Critic customers (brief 4.2).

All bins are derived from the spec (rrdv.facts), so changing which arrivals
are VIP / Critic only changes the bins, not this code.
Facts for the Stage 2 base setting (C2 Critic at turn 4, C3 VIP at turn 7):
  * The Critic always orders the most demanding dish (Pasta), not the item the
    position rule would give (Burger for C2).
  * The VIP loses 5 per turn, so it would need 20 unserved turns to leave:
    it can never abandon within 18 turns.
  * The Critic loses 12 per turn and leaves at the end of turn 12 if never served.
"""

from __future__ import annotations

from typing import Dict, Set, Tuple

from .. import facts
from ..spec import position_rule
from . import SampleCtx, covergroup

FATES = ("PAID", "LEFT", "UNPAID_AT_END")
WAIT_STATES = ("WAITING", "SEATED", "ORDERED")


def _reachable_fates(spec) -> Set[Tuple[str, str]]:
    out = set()
    for a in facts.arrivals(spec):
        leave = facts.abandon_turn(spec, a)
        if leave <= spec.max_turns:
            out.add((a.kind.label, "LEFT"))
        if a.turn <= spec.last_payable_arrival:
            out.add((a.kind.label, "PAID"))
        # Served on the leave turn at the latest; payment needs two more turns.
        if leave >= spec.max_turns - 1:
            out.add((a.kind.label, "UNPAID_AT_END"))
    return out


def _extra_bucket(extra: int) -> str:
    if extra < 0:
        return "faster_than_possible"
    if extra == 0:
        return "min"
    if extra == 1:
        return "+1"
    if extra <= 4:
        return "+2-4"
    return "+5+"


@covergroup(stage=2)
def customer_kind(db, spec):
    g = db.group("cg_customer_kind", "VIP / Critic arrivals, food choice and fate")
    arr = facts.arrivals(spec)
    labels = facts.kind_labels(spec)
    cp_arr = g.coverpoint("kind_at_turn", [(a.kind.label, str(a.turn)) for a in arr])
    items = sorted({(a.kind.label, a.item.name) for a in arr})
    critic_items = {(a.kind.label, i.name) for a in arr if a.kind.key == "CRITIC"
                    for i in spec.menu if i.name != a.item.name}
    cp_item = g.coverpoint("kind_x_item", items,
                           illegal={k: "Critic always orders the most demanding dish" for k in critic_items})
    pref = {}
    for a in arr:
        if a.kind.key == "CRITIC":
            rule = spec.menu[position_rule(a.cid, spec.menu)].name
            pref[a.name] = "differs_from_position_rule" if rule != a.item.name else "same_as_position_rule"
    cp_pref = g.coverpoint("critic_choice", sorted(set(pref.values())))
    reach = _reachable_fates(spec)
    ignore: Dict[Tuple[str, str], str] = {}
    for lab in labels:
        for f in FATES:
            if (lab, f) not in reach:
                ignore[(lab, f)] = f"no {lab} arrival can end {f} (see rrdv.facts)"
    cx_fate = g.cross("kind_x_fate", labels, FATES, ignore=ignore)

    def sample(ctx: SampleCtx):
        for t in ctx.tr.turns:
            for name, label in t.arrivals:
                cp_arr.sample((label, str(t.turn)), name)
        for h in ctx.tl.customers.values():
            if h.item:
                cp_item.sample((h.ctype, h.item), h.name)
                if h.name in pref:
                    cp_pref.sample(pref[h.name])
            if ctx.eof or ctx.tr.result is None:
                continue
            fate = "PAID" if h.paid_turn > 0 else "LEFT" if h.departed_turn > 0 else "UNPAID_AT_END"
            cx_fate.sample((h.ctype, fate), h.name)
    return sample


@covergroup(stage=2)
def pricing(db, spec):
    g = db.group("cg_pricing", "bill per customer kind (VIP 10% off)")
    labels = facts.kind_labels(spec)
    kinds = {a.kind.label: a.kind for a in facts.arrivals(spec)}
    bins, illegal = [], {}
    for lab in labels:
        discounted = kinds[lab].bill(10000) != 10000
        want = "10_off" if discounted else "full"
        bins.append((lab, want))
        for other in ("full", "10_off"):
            if other != want:
                illegal[(lab, other)] = f"{lab} pays {want}"
        illegal[(lab, "other")] = "bill matches neither full price nor 10% off"
    cp = g.coverpoint("kind_x_bill", bins, illegal=illegal)
    cp_vip = g.coverpoint("vip_bill_cents", sorted({str(a.bill) for a in facts.arrivals(spec)
                                                    if a.kind.key == "VIP"}))

    def sample(ctx: SampleCtx):
        for o in ctx.tl.orders.values():
            if not o.customer:
                continue
            h = ctx.tl.customers[o.customer]
            price = spec.menu_by_name(o.item).price_cents
            kind = "full" if o.bill_cents == price else \
                "10_off" if o.bill_cents == (price * 90 + 50) // 100 else "other"
            cp.sample((h.ctype, kind), f"order #{o.id}")
            if h.ctype == "VIP":
                cp_vip.sample(str(o.bill_cents), f"order #{o.id}")
    return sample


@covergroup(stage=2)
def kind_satisfaction(db, spec):
    g = db.group("cg_kind_satisfaction", "per-kind satisfaction decay, payment and abandonment")
    arr = {a.name: a for a in facts.arrivals(spec)}
    special = [lab for lab in facts.kind_labels(spec) if lab != "Regular"]
    cx_decay = g.cross("kind_x_decay_state", facts.kind_labels(spec), WAIT_STATES)
    cx_pay = g.cross("kind_x_pay_delay", special, ["min", "+1", "+2-4", "+5+"],
                     illegal={(lab, "faster_than_possible"): "seat, order, prep and serve each take a turn"
                              for lab in special})
    leavers = {a.kind.label for a in facts.can_abandon(spec)}
    ignore = {(lab, s): f"{lab} cannot abandon within {spec.max_turns} turns"
              for lab in facts.kind_labels(spec) if lab not in leavers for s in WAIT_STATES}
    cx_leave = g.cross("kind_x_abandon_from", facts.kind_labels(spec), WAIT_STATES, ignore=ignore,
                       illegal={(lab, s): "served customers lose nothing"
                                for lab in facts.kind_labels(spec) for s in ("SERVED", "READY_TO_PAY")})

    def sample(ctx: SampleCtx):
        prev: Dict[str, int] = {}
        prev_state: Dict[str, str] = {}
        for t in ctx.tr.turns:
            s = t.snapshot
            if s is None:
                continue
            cur = {n: (sat, "WAITING") for n, sat in s.queue}
            cur.update({tv.customer: (tv.sat, tv.state) for tv in s.tables if tv.customer})
            for n, (sat, state) in cur.items():
                h = ctx.tl.customers.get(n)
                if n in prev and h is not None and sat < prev[n]:
                    # decayed during the previous turn; bin by the state shown at its start
                    cx_decay.sample((h.ctype, prev_state[n]), f"turn {t.turn} {n}")
            prev = {n: v[0] for n, v in cur.items()}
            prev_state = {n: v[1] for n, v in cur.items()}
        for h in ctx.tl.customers.values():
            a = arr.get(h.name)
            if a is None:
                continue
            if h.paid_turn > 0 and h.ctype in special:
                best = spec.start_satisfaction - a.kind.wait_penalty * (a.item.prep_units + 1)
                sat = h.sats.get(h.paid_turn, -1)
                cx_pay.sample((h.ctype, _extra_bucket((best - sat) // a.kind.wait_penalty)), h.name)
            if h.departed_turn > 0:
                cx_leave.sample((h.ctype, h.state_at_departure), h.name)
    return sample
