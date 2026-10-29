from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ..spec import CustomerKind

if TYPE_CHECKING:
    from .order import Order
    from .restaurant import Table

WAITING = "WAITING"
SEATED = "SEATED"
ORDERED = "ORDERED"
SERVED = "SERVED"
READY_TO_PAY = "READY_TO_PAY"
PAID = "PAID"
LEFT = "LEFT"

WAITING_FOR_SERVICE = (WAITING, SEATED, ORDERED)


class Customer:
    def __init__(self, cid: int, kind: CustomerKind, arrival_turn: int, satisfaction: int):
        self.id = cid
        self.kind = kind
        self.arrival_turn = arrival_turn
        self.satisfaction = satisfaction
        self.state = WAITING
        self.table: Optional[Table] = None
        self.order: Optional[Order] = None
        self.served_turn = -1
        self.ready_to_pay_turn = -1

    @property
    def name(self) -> str:
        return f"C{self.id}"

    def is_waiting_for_service(self) -> bool:
        return self.state in WAITING_FOR_SERVICE

    def is_present(self) -> bool:
        return self.state not in (PAID, LEFT)

    def lose_satisfaction(self) -> None:
        if self.is_waiting_for_service():
            self.satisfaction = max(0, self.satisfaction - self.kind.wait_penalty)

    def recover(self, points: int) -> bool:
        if not self.is_waiting_for_service() or self.satisfaction >= 100:
            return False
        self.satisfaction = min(100, self.satisfaction + points)
        return True

    def finish_eating(self, turn: int) -> bool:
        if self.state == SERVED and self.served_turn < turn:
            self.state = READY_TO_PAY
            self.ready_to_pay_turn = turn
            return True
        return False

    def can_pay_on(self, turn: int) -> bool:
        return self.state == READY_TO_PAY and self.ready_to_pay_turn < turn

    def pay(self) -> None:
        self.state = PAID
        if self.order is not None:
            self.order.status = "PAID"
        if self.table is not None:
            self.table.occupant = None

    def leave(self) -> None:
        self.state = LEFT
        if self.order is not None:
            self.order.status = "CANCELLED"
        if self.table is not None:
            self.table.occupant = None
