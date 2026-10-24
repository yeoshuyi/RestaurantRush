"""Per-customer / per-order history derived from monitored TurnRecords only.

Shared by assertions and coverage so both reason over the same facts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .javaparse import parse_money
from .monitor import Transcript


@dataclass
class CustomerHistory:
    name: str
    ctype: str = ""
    arrival_turn: int = -1
    seated_turn: int = -1
    table: int = -1
    order_id: int = -1
    item: str = ""
    ordered_turn: int = -1
    served_turn: int = -1
    first_rtp_snapshot: int = -1  # first turn whose snapshot shows READY_TO_PAY
    paid_turn: int = -1
    paid_cents: int = 0
    departed_turn: int = -1
    state_at_departure: str = ""
    last_state: str = "WAITING"
    last_sat: int = -1
    sats: Dict[int, int] = field(default_factory=dict)  # snapshot turn -> sat
    states: Dict[int, str] = field(default_factory=dict)  # snapshot turn -> state

    @property
    def sat_at_payment(self) -> Optional[int]:
        return self.last_sat if self.paid_turn > 0 else None


@dataclass
class OrderHistory:
    id: int
    customer: str
    item: str
    bill_cents: int
    prep_units: int
    taken_turn: int
    statuses: List[Tuple[int, str]] = field(default_factory=list)  # (turn, status) in order
    ready_turn: int = -1
    served_turn: int = -1
    final: str = "OPEN"

    @property
    def last_status(self) -> str:
        return self.statuses[-1][1] if self.statuses else "PLACED"

    def push(self, turn: int, status: str) -> None:
        if not self.statuses or self.statuses[-1][1] != status:
            self.statuses.append((turn, status))


@dataclass
class Timeline:
    customers: Dict[str, CustomerHistory]
    orders: Dict[int, OrderHistory]


def build(tr: Transcript) -> Timeline:
    cust: Dict[str, CustomerHistory] = {}
    orders: Dict[int, OrderHistory] = {}
    owners = _owners_from_snapshots(tr)

    def c(name: str) -> CustomerHistory:
        if name not in cust:
            cust[name] = CustomerHistory(name)
        return cust[name]

    for rec in tr.turns:
        t = rec.turn
        for name, ctype in rec.arrivals:
            h = c(name)
            h.ctype, h.arrival_turn = ctype, t
        snap = rec.snapshot
        if snap is not None:
            for name, sat in snap.queue:
                h = c(name)
                h.sats[t], h.states[t], h.last_sat, h.last_state = sat, "WAITING", sat, "WAITING"
            for tv in snap.tables:
                if tv.customer is None:
                    continue
                h = c(tv.customer)
                h.sats[t], h.states[t], h.last_sat, h.last_state = tv.sat, tv.state, tv.sat, tv.state
                h.table = tv.id
                if tv.state == "READY_TO_PAY" and h.first_rtp_snapshot < 0:
                    h.first_rtp_snapshot = t
                if tv.order_id is not None and tv.order_id in orders:
                    orders[tv.order_id].push(t, tv.order_status)
        for a in rec.waiter:
            if a.outcome != "ok":
                continue
            if a.task == "seat":
                h = c(a.detail[0])
                h.seated_turn, h.table, h.last_state = t, int(a.detail[1]), "SEATED"
            elif a.task == "take":
                oid, item, done, total, status, bill, units = a.detail
                cname = _owner(rec, int(oid), cust, owners)
                o = OrderHistory(int(oid), cname, item, parse_money(bill), int(units), t)
                o.push(t, status)
                orders[o.id] = o
                if cname:
                    h = c(cname)
                    h.order_id, h.item, h.ordered_turn, h.last_state = o.id, item, t, "ORDERED"
            elif a.task == "serve":
                oid = int(a.detail[0])
                if oid in orders:
                    o = orders[oid]
                    o.served_turn = t
                    o.push(t, "SERVED")
                    if o.customer:
                        h = c(o.customer)
                        h.served_turn, h.last_state = t, "SERVED"
        if rec.chef is not None and rec.chef.kind == "prep":
            oid, item, done, total, status = rec.chef.detail[:5]
            if int(oid) in orders:
                o = orders[int(oid)]
                o.push(t, status)
                if status == "READY":
                    o.ready_turn = t
        for name, amount in rec.payments:
            h = c(name)
            h.paid_turn, h.paid_cents, h.last_state = t, parse_money(amount), "PAID"
            if h.order_id in orders:
                orders[h.order_id].push(t, "PAID")
                orders[h.order_id].final = "PAID"
        for name in rec.departures:
            h = c(name)
            h.departed_turn, h.state_at_departure = t, h.last_state
            h.last_state = "LEFT"
            if h.order_id in orders:
                o = orders[h.order_id]
                o.final = "CANCELLED_" + o.last_status
                o.push(t, "CANCELLED")
    return Timeline(cust, orders)


def _owners_from_snapshots(tr: Transcript) -> Dict[int, str]:
    owners: Dict[int, str] = {}
    for rec in tr.turns:
        if rec.snapshot is not None:
            for tv in rec.snapshot.tables:
                if tv.order_id is not None and tv.customer:
                    owners.setdefault(tv.order_id, tv.customer)
    return owners


def _owner(rec, oid: int, cust: Dict[str, CustomerHistory], owners: Dict[int, str]) -> str:
    """Owner of a just-taken order.

    The take message names only the order. Use a later snapshot's table line
    if one exists, else the chooser options (seated customers without an
    order) when only one candidate is possible.
    """
    if oid in owners:
        return owners[oid]
    for a in rec.waiter:
        if a.task == "take" and a.outcome == "ok" and int(a.detail[0]) == oid:
            cands = [o.split(" ")[0] for o in a.options]
            cands = [n for n in cands if n not in cust or cust[n].order_id < 0]
            if len(cands) == 1:
                return cands[0]
    return ""
