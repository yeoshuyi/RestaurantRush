from __future__ import annotations

from typing import TYPE_CHECKING

from ..spec import MenuItemSpec

if TYPE_CHECKING:
    from .customer import Customer

PLACED = "PLACED"
IN_PREPARATION = "IN_PREPARATION"
READY = "READY"
SERVED = "SERVED"
PAID = "PAID"
CANCELLED = "CANCELLED"


class Order:
    def __init__(self, oid: int, customer: Customer, item: MenuItemSpec, bill_cents: int):
        self.id = oid
        self.customer = customer
        self.item = item
        self.bill_cents = bill_cents
        self.units_done = 0
        self.status = PLACED
        self.ready_turn = -1

    def is_in_kitchen(self) -> bool:
        return self.status in (PLACED, IN_PREPARATION)

    def is_ready(self) -> bool:
        return self.status == READY

    def is_active(self) -> bool:
        return self.status not in (PAID, CANCELLED)

    def advance(self, turn: int) -> None:
        self.units_done += 1
        if self.units_done >= self.item.prep_units:
            self.status = READY
            self.ready_turn = turn
        else:
            self.status = IN_PREPARATION

    @property
    def progress(self) -> str:
        return f"{self.units_done}/{self.item.prep_units}"

    def describe(self) -> str:
        return f"#{self.id} {self.item.name} ({self.units_done}/{self.item.prep_units} units) [{self.status}]"
