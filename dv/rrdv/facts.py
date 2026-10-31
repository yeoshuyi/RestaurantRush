"""Facts derived from a StageSpec, used to justify ignore/illegal coverage bins.

Stage 1 covergroups used to hardcode facts such as "only C1/C2 can abandon".
Stage 2 changes who arrives when, so these are now computed from the spec.
Stage 3 adds the Host (one turn faster to the table and the order) and Happy Hour
(recovery delays departures, 20% off lowers bills), so those are accounted for here too.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import List, Optional, Set

from .spec import HH_DURATION, HH_RECOVERY, CustomerKind, MenuItemSpec, StageSpec, hh_bill


@dataclass(frozen=True)
class Arrival:
    cid: int
    name: str
    turn: int
    kind: CustomerKind
    item: MenuItemSpec

    @property
    def bill(self) -> int:
        return self.kind.bill(self.item.price_cents)


def arrivals(spec: StageSpec) -> List[Arrival]:
    out = []
    for cid, turn in enumerate(sorted(spec.arrivals), 1):
        kind = spec.kind_for(turn)
        item = spec.menu[kind.choose_item(cid, spec.menu)]
        out.append(Arrival(cid, f"C{cid}", turn, kind, item))
    return out


def abandon_turn(spec: StageSpec, a: Arrival) -> int:
    """Turn at whose end a never-served customer reaches 0 and leaves (no Happy Hour).

    Satisfaction drops by the penalty at the end of every unserved turn,
    starting on the arrival turn.
    """
    drops = -(-spec.start_satisfaction // a.kind.wait_penalty)  # ceil
    return a.turn + drops - 1


def _leave_with_hh(spec: StageSpec, a: Arrival, start: Optional[int]) -> int:
    """Departure turn of a never-served customer if Happy Hour starts on `start` (None = never).

    Returns max_turns + 1 if it is still there at the end. Happy Hour only delays departures.
    """
    sat = spec.start_satisfaction
    for t in range(a.turn, spec.max_turns + 1):
        if start is not None and start <= t < start + HH_DURATION:
            sat = min(100, sat + HH_RECOVERY)
        sat = max(0, sat - a.kind.wait_penalty)
        if sat == 0:
            return t
    return spec.max_turns + 1


def possible_abandon_turns(spec: StageSpec, a: Arrival) -> Set[int]:
    if not spec.has("happy_hour"):
        t = abandon_turn(spec, a)
        return {t} if t <= spec.max_turns else set()
    starts = [None] + list(range(1, spec.max_turns + 1))
    return {t for t in (_leave_with_hh(spec, a, h) for h in starts) if t <= spec.max_turns}


def latest_abandon_turn(spec: StageSpec, a: Arrival) -> int:
    turns = possible_abandon_turns(spec, a)
    return max(turns) if turns else spec.max_turns + 1


def can_abandon(spec: StageSpec) -> List[Arrival]:
    return [a for a in arrivals(spec) if abandon_turn(spec, a) <= spec.max_turns]


def abandon_turns(spec: StageSpec) -> List[int]:
    return sorted({t for a in can_abandon(spec) for t in possible_abandon_turns(spec, a)})


def ordered_items(spec: StageSpec) -> Set[str]:
    """Menu items some base-setting customer orders (all others can never appear)."""
    return {a.item.name for a in arrivals(spec)}


def fastest_unserved_turns(spec: StageSpec, units: int) -> int:
    """Turns a customer spends unserved (losing satisfaction) on the fastest path.

    Without a Host: seat, then order, then `units` prep turns (the order turn is one of them),
    so units + 1. With the Host seating and the Waiter ordering on the arrival turn: units.
    """
    return units if spec.has("host") else units + 1


def earliest_pay_turn(spec: StageSpec) -> int:
    # Served the turn after READY, one turn of eating, pay the turn after that.
    return min(a.turn + fastest_unserved_turns(spec, a.item.prep_units) + 2 for a in arrivals(spec))


def abandoning_items(spec: StageSpec) -> Set[str]:
    return {a.item.name for a in can_abandon(spec)}


def multi_unit_cancel_possible(spec: StageSpec) -> bool:
    return any(a.item.prep_units > 1 for a in can_abandon(spec))


def payable(spec: StageSpec) -> List[Arrival]:
    return [a for a in arrivals(spec) if a.turn <= spec.last_payable_arrival]


def cheapest_bills(spec: StageSpec, n: int) -> int:
    """Lowest revenue from n payments. Happy Hour can discount at most HH_DURATION orders
    (one Waiter, one order per turn), so it is applied to the most expensive of them."""
    best = None
    for group in combinations(sorted(a.bill for a in payable(spec)), n):
        bills = sorted(group, reverse=True)
        if spec.has("happy_hour"):
            bills = [hh_bill(b) for b in bills[:HH_DURATION]] + bills[HH_DURATION:]
        total = sum(bills)
        best = total if best is None else min(best, total)
    return best or 0


def kind_labels(spec: StageSpec) -> List[str]:
    seen: List[str] = []
    for a in arrivals(spec):
        if a.kind.label not in seen:
            seen.append(a.kind.label)
    return seen
