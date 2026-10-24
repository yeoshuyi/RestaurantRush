from __future__ import annotations

from typing import List, Optional

from ..spec import StageSpec
from . import customer as cs
from .customer import Customer
from .order import Order


class Table:
    def __init__(self, tid: int):
        self.id = tid
        self.occupant: Optional[Customer] = None

    def is_free(self) -> bool:
        return self.occupant is None


class Restaurant:
    """State container. Ordering rules mirror the brief and the Java lists."""

    def __init__(self, spec: StageSpec):
        self.spec = spec
        self.tables = [Table(i) for i in range(1, spec.tables + 1)]
        self.queue: List[Customer] = []
        self.customers: List[Customer] = []
        self.next_order_id = 1

    def admit(self, c: Customer) -> None:
        self.customers.append(c)
        self.queue.append(c)

    def free_table(self) -> Optional[Table]:
        for t in self.tables:
            if t.is_free():
                return t
        return None

    def seat(self, c: Customer) -> Table:
        t = self.free_table()
        assert t is not None and c.state == cs.WAITING
        self.queue.remove(c)
        c.table = t
        c.state = cs.SEATED
        t.occupant = c
        return t

    def awaiting_order(self) -> List[Customer]:
        return [c for c in self.customers if c.state == cs.SEATED]

    def orders(self) -> List[Order]:
        return sorted((c.order for c in self.customers if c.order is not None), key=lambda o: o.id)

    def active_orders(self) -> List[Order]:
        return [o for o in self.orders() if o.is_active()]

    def ready_orders(self) -> List[Order]:
        return [o for o in self.active_orders() if o.is_ready()]

    def kitchen_orders(self) -> List[Order]:
        return [o for o in self.orders() if o.is_in_kitchen()]

    def present_customers(self) -> List[Customer]:
        return [c for c in self.customers if c.is_present()]

    def ready_to_pay(self) -> List[Customer]:
        return [c for c in self.customers if c.state == cs.READY_TO_PAY]
