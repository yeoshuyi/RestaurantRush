"""Official requirements (docs/instruction.pdf) as data.

Everything the reference model, assertions and coverage need to know about
the rules lives here, keyed by stage, so a later stage only registers new
customer kinds / menu items / settings instead of editing the checkers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Sequence, Tuple


@dataclass(frozen=True)
class MenuItemSpec:
    name: str
    price_cents: int
    prep_units: int


def position_rule(cid: int, menu: Sequence[MenuItemSpec]) -> int:
    """Customer.chooseItem(): customer N orders item (N - 1) mod menu size."""
    return (cid - 1) % len(menu)


def most_demanding(cid: int, menu: Sequence[MenuItemSpec]) -> int:
    """CriticCustomer.chooseItem(): most prep units, ties broken by higher price.

    Java's Stream.max keeps the first of equal maxima, so a later item must be
    strictly greater to win.
    """
    best = 0
    for i, item in enumerate(menu):
        b = menu[best]
        if (item.prep_units, item.price_cents) > (b.prep_units, b.price_cents):
            best = i
    return best


def vip_bill(base_cents: int) -> int:
    """VIPCustomer.computeBill(): 90% rounded half up to the nearest cent."""
    return (base_cents * 90 + 50) // 100


@dataclass(frozen=True)
class CustomerKind:
    """Per-type behaviour (brief 4.2 table)."""

    key: str
    label: str
    wait_penalty: int
    bill: Callable[[int], int] = lambda base: base
    # Index into the menu for customer number `cid` (1-based). The brief only
    # requires a documented deterministic rule; these mirror the Java overrides
    # of Customer.chooseItem().
    choose_item: Callable[[int, Sequence[MenuItemSpec]], int] = position_rule


CUSTOMER_KINDS: Dict[str, CustomerKind] = {}


def register_kind(kind: CustomerKind) -> CustomerKind:
    CUSTOMER_KINDS[kind.key] = kind
    return kind


REGULAR = register_kind(CustomerKind("REGULAR", "Regular", 8))
# Stage 2 (brief 4.2)
VIP = register_kind(CustomerKind("VIP", "VIP", 5, bill=vip_bill))
CRITIC = register_kind(CustomerKind("CRITIC", "Critic", 12, choose_item=most_demanding))


@dataclass(frozen=True)
class StageSpec:
    stage: int
    max_turns: int
    tables: int
    arrivals: Dict[int, str]  # turn -> CustomerKind key
    menu: Tuple[MenuItemSpec, ...]
    target_paid: int
    target_revenue_cents: int
    target_avg_satisfaction: int
    start_satisfaction: int = 100
    main_class: str = "rush.Main"
    features: Tuple[str, ...] = field(default_factory=tuple)

    def kind_for(self, turn: int) -> CustomerKind:
        return CUSTOMER_KINDS[self.arrivals[turn]]

    def menu_by_name(self, name: str) -> MenuItemSpec:
        for item in self.menu:
            if item.name == name:
                return item
        raise KeyError(name)

    @property
    def last_payable_arrival(self) -> int:
        # Fastest path: seat(t) take(t+1) [chef same turn] serve(t+2) eat(t+3) pay(t+4)
        return self.max_turns - 4


STANDARD_MENU = (
    MenuItemSpec("Salad", 900, 1),
    MenuItemSpec("Burger", 1500, 1),
    MenuItemSpec("Pasta", 1800, 2),
)

STAGE1 = StageSpec(
    stage=1,
    max_turns=18,
    tables=2,
    arrivals={t: "REGULAR" for t in (1, 4, 7, 10, 13, 16)},
    menu=STANDARD_MENU,
    target_paid=4,
    target_revenue_cents=4500,
    target_avg_satisfaction=60,
    features=("regular", "waiter", "chef", "cashier"),
)

# Stage 2 base setting: the turn-4 arrival is a Critic, the turn-7 arrival a VIP.
STAGE2 = StageSpec(
    stage=2,
    max_turns=18,
    tables=2,
    arrivals={1: "REGULAR", 4: "CRITIC", 7: "VIP", 10: "REGULAR", 13: "REGULAR", 16: "REGULAR"},
    menu=STANDARD_MENU,
    target_paid=4,
    target_revenue_cents=4500,
    target_avg_satisfaction=60,
    features=("regular", "waiter", "chef", "cashier", "vip", "critic"),
)

STAGES: Dict[int, StageSpec] = {1: STAGE1, 2: STAGE2}


def get_stage(n: int) -> StageSpec:
    try:
        return STAGES[n]
    except KeyError:
        raise SystemExit(f"Stage {n} is not defined in rrdv.spec (have {sorted(STAGES)})")
