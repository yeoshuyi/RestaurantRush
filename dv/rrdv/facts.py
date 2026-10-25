"""Facts derived from a StageSpec, used to justify ignore/illegal coverage bins.

Stage 1 covergroups used to hardcode facts such as "only C1/C2 can abandon".
Stage 2 changes who arrives when, so these are now computed from the spec.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Set

from .spec import CustomerKind, MenuItemSpec, StageSpec


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
    """Turn at whose end a never-served customer reaches 0 and leaves.

    Satisfaction drops by the penalty at the end of every unserved turn,
    starting on the arrival turn.
    """
    drops = -(-spec.start_satisfaction // a.kind.wait_penalty)  # ceil
    return a.turn + drops - 1


def can_abandon(spec: StageSpec) -> List[Arrival]:
    return [a for a in arrivals(spec) if abandon_turn(spec, a) <= spec.max_turns]


def abandon_turns(spec: StageSpec) -> List[int]:
    return sorted({abandon_turn(spec, a) for a in can_abandon(spec)})


def abandoning_items(spec: StageSpec) -> Set[str]:
    return {a.item.name for a in can_abandon(spec)}


def multi_unit_cancel_possible(spec: StageSpec) -> bool:
    return any(a.item.prep_units > 1 for a in can_abandon(spec))


def payable(spec: StageSpec) -> List[Arrival]:
    return [a for a in arrivals(spec) if a.turn <= spec.last_payable_arrival]


def cheapest_bills(spec: StageSpec, n: int) -> int:
    return sum(sorted(a.bill for a in payable(spec))[:n])


def kind_labels(spec: StageSpec) -> List[str]:
    seen: List[str] = []
    for a in arrivals(spec):
        if a.kind.label not in seen:
            seen.append(a.kind.label)
    return seen
