"""Reference model of one game, following the brief's six turn steps (3.2).

It produces the exact transcript the Java ConsoleUI should print for a given
input, so the scoreboard can compare line by line. Input comes from an
InputSource: a fixed script (replay) or a constrained-random policy
(generation), which sees the same menus the DUT will show.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional, Sequence

from ..javaparse import (format_average, format_money, java_parse_int,
                         java_trim, split_java_lines)
from ..spec import HH_DURATION, HH_RECOVERY, StageSpec, hh_bill
from . import customer as cs
from .customer import Customer
from .order import Order
from .restaurant import Restaurant

THICK = "=" * 60
THIN = "-" * 60
EOF_ERROR = "Error: rush.ui.InputReader$InputEndedException: Input ended"

WAITER_TASKS = ("Wait", "Seat a customer", "Take an order", "Serve an order")
TASK_KEYS = ("wait", "seat", "take", "serve")


class InputEnded(Exception):
    pass


@dataclass
class InputRequest:
    """One InputReader.readInt() call, as seen by the input source."""

    request_id: int
    kind: str  # happy_hour | host | waiter_task | seat | take | serve | chef
    label: str
    lo: int
    hi: int
    options: Sequence[Any]
    attempt: int
    model: "GameModel"


class InputSource:
    def next_line(self, req: InputRequest) -> Optional[str]:
        raise NotImplementedError


class ScriptSource(InputSource):
    """Replays a fixed input text, split like BufferedReader."""

    def __init__(self, text: str):
        self.lines = split_java_lines(text)
        self.pos = 0

    def next_line(self, req: InputRequest) -> Optional[str]:
        if self.pos >= len(self.lines):
            return None
        line = self.lines[self.pos]
        self.pos += 1
        return line


@dataclass
class ModelResult:
    text: str
    consumed: List[str]
    eof: bool
    victory: Optional[bool]
    paid_satisfactions: List[int] = field(default_factory=list)
    revenue_cents: int = 0
    served: int = 0
    departures: int = 0


class _Out:
    def __init__(self) -> None:
        self.parts: List[str] = []

    def print(self, s: str = "") -> None:
        self.parts.append(s)

    def println(self, s: str = "") -> None:
        self.parts.append(s + "\n")

    def text(self) -> str:
        return "".join(self.parts)


class GameModel:
    def __init__(self, spec: StageSpec, source: InputSource):
        self.spec = spec
        self.source = source
        self.out = _Out()
        self.r = Restaurant(spec)
        self.turn = 0
        self.next_customer_id = 1
        self.revenue_cents = 0
        self.paid_sats: List[int] = []
        self.served = 0
        self.departures = 0
        self.turns_used = 0
        self.consumed: List[str] = []
        self._req_id = 0
        # Per-turn facts a policy may want (e.g. orders taken this turn).
        self.taken_this_turn: List[Order] = []
        self.waiter_attempts = 0

    # ---------------------------------------------------------------- input
    def read_int(self, kind: str, label: str, lo: int, hi: int, options: Sequence[Any]) -> int:
        self._req_id += 1
        prompt = f"{label} [{lo}-{hi}]: "
        attempt = 0
        need_prompt = True
        while True:
            # Blank and '#' lines are skipped without re-printing the prompt.
            if need_prompt:
                self.out.print(prompt)
            need_prompt = True
            line = self.source.next_line(
                InputRequest(self._req_id, kind, label, lo, hi, options, attempt, self))
            attempt += 1
            if line is None:
                self.out.println()
                raise InputEnded()
            self.consumed.append(line)
            t = java_trim(line)
            if t == "" or t.startswith("#"):
                need_prompt = False
                continue
            try:
                v = java_parse_int(t)
            except ValueError:
                self.out.println(f"  '{t}' is not a whole number. Enter a number from {lo} to {hi}.")
                continue
            if v < lo or v > hi:
                self.out.println(f"  {v} is out of range. Enter a number from {lo} to {hi}.")
                continue
            return v

    # ----------------------------------------------------------------- view
    def msg(self, s: str) -> None:
        self.out.println("  > " + s)

    def err(self, s: str) -> None:
        self.out.println("  ! " + s)

    @staticmethod
    def describe_customer(c: Customer) -> str:
        s = f"{c.name} ({c.kind.label}) sat {c.satisfaction}, {c.state}"
        if c.order is not None:
            o = c.order
            s += f", order #{o.id} {o.item.name} {o.status} {o.progress}"
        return s

    @staticmethod
    def describe_order_option(o: Order) -> str:
        return f"{o.describe()} [{o.status} {o.progress}]"

    def avg(self) -> str:
        return format_average(self.paid_sats)

    def show_state(self) -> None:
        o = self.out
        o.println(f"Revenue: {format_money(self.revenue_cents)}   Paid: {len(self.paid_sats)}"
                  f"   Avg satisfaction (paid): {self.avg()}")
        if self.spec.has("happy_hour"):
            o.println("Happy Hour: " + self.r.hh_display())
        line = "Waiting queue:"
        if not self.r.queue:
            line += " (empty)"
        for c in self.r.queue:
            line += f" {c.name}[sat {c.satisfaction}]"
        o.println(line)
        o.println("Tables:")
        for t in self.r.tables:
            o.println(f"  Table {t.id}: " + ("free" if t.is_free() else self.describe_customer(t.occupant)))
        o.println(staff_line(self.spec))
        o.println(THIN)

    def choose_customer(self, kind: str, title: str, options: List[Customer]) -> Optional[Customer]:
        self.out.println(title)
        self.out.println("  0) Back")
        for i, c in enumerate(options, 1):
            self.out.println(f"  {i}) {self.describe_customer(c)}")
        v = self.read_int(kind, "Choose customer", 0, len(options), options)
        return None if v == 0 else options[v - 1]

    def choose_order(self, kind: str, title: str, zero: str, label: str, options: List[Order]) -> Optional[Order]:
        self.out.println(title)
        self.out.println(f"  0) {zero}")
        for i, od in enumerate(options, 1):
            self.out.println(f"  {i}) {self.describe_order_option(od)}")
        v = self.read_int(kind, label, 0, len(options), options)
        return None if v == 0 else options[v - 1]

    # ----------------------------------------------------------------- game
    def run(self) -> ModelResult:
        self.out.println("RestaurantRush")
        eof = False
        victory: Optional[bool] = None
        try:
            while self.turn < self.spec.max_turns:
                self.play_turn()
            victory = self.show_result()
        except InputEnded:
            eof = True
            self.out.println(EOF_ERROR)
        return ModelResult(self.out.text(), self.consumed, eof, victory, list(self.paid_sats),
                           self.revenue_cents, self.served, self.departures)

    def play_turn(self) -> None:
        self.turn += 1
        self.taken_this_turn = []
        self.waiter_attempts = 0
        o = self.out
        o.println()
        o.println(THICK)
        o.println(f" TURN {self.turn} / {self.spec.max_turns}")
        o.println(THICK)
        self.step_arrivals()
        if self.spec.has("happy_hour"):
            self.step_happy_hour()
        self.show_state()
        if self.spec.has("host"):
            self.step_host()
        self.step_waiter()
        self.step_chef()
        self.step_eating_and_payment()
        self.step_waiting_and_abandonment()
        if self.r.hh_left > 0:
            self.r.hh_left -= 1
        self.turns_used = self.turn
        o.println(THIN)
        o.println(f"End of turn {self.turn}: served {self.served} | unhappy departures {self.departures}"
                  f" | revenue {format_money(self.revenue_cents)} | avg satisfaction {self.avg()}"
                  f" | turns used {self.turns_used}/{self.spec.max_turns}")

    def step_arrivals(self) -> None:
        if self.turn in self.spec.arrivals:
            kind = self.spec.kind_for(self.turn)
            c = Customer(self.next_customer_id, kind, self.turn, self.spec.start_satisfaction)
            self.next_customer_id += 1
            self.r.admit(c)
            self.msg(f"{c.name} arrives ({kind.label}).")

    def step_happy_hour(self) -> None:
        r = self.r
        if not r.hh_used:
            o = self.out
            o.println("Happy Hour (once per game, this turn and next): start now?")
            o.println("  0) Not now")
            o.println("  1) Start Happy Hour")
            if self.read_int("happy_hour", "Choose Happy Hour", 0, 1, ("not_now", "start")) == 1:
                r.hh_used, r.hh_left = True, HH_DURATION
                self.msg(f"Happy Hour starts: {HH_DURATION} turns (this turn and next), 20% off new orders.")
        if r.hh_active():
            for c in r.present_customers():
                if c.recover(HH_RECOVERY):
                    self.msg(f"{c.name} recovers to {c.satisfaction} (Happy Hour).")

    def step_host(self) -> None:
        if not self.r.queue:
            self.msg("The host has no customers to seat.")
            return
        if self.r.free_table() is None:
            self.msg("The host has no free table.")
            return
        self.out.println("Host: seat which customer?")
        self.out.println("  0) Wait")
        options = list(self.r.queue)
        for i, c in enumerate(options, 1):
            self.out.println(f"  {i}) {self.describe_customer(c)}")
        v = self.read_int("host", "Choose Host task", 0, len(options), options)
        if v == 0:
            return
        c = options[v - 1]
        t = self.r.seat(c)
        self.msg(f"Host seats {c.name} at table {t.id}.")

    def step_waiter(self) -> None:
        while True:
            self.waiter_attempts += 1
            self.out.println("Waiter tasks:")
            for i, label in enumerate(WAITER_TASKS):
                self.out.println(f"  {i}) {label}")
            task = TASK_KEYS[self.read_int("waiter_task", "Choose Waiter task", 0, 3, TASK_KEYS)]
            if task == "wait":
                self.msg("The waiter takes no action this turn.")
                return
            if getattr(self, "_waiter_" + task)():
                return

    def _waiter_seat(self) -> bool:
        if not self.r.queue:
            self.msg("No customers are waiting to be seated.")
            return False
        c = self.choose_customer("seat", "Choose a customer to seat", list(self.r.queue))
        if c is None:
            return False
        t = self.r.free_table()
        if t is None:
            self.err("No free table.")
            return False
        self.r.seat(c)
        self.msg(f"Waiter seats {c.name} at table {t.id}.")
        return True

    def _waiter_take(self) -> bool:
        awaiting = self.r.awaiting_order()
        if not awaiting:
            self.msg("No seated customers are waiting to order.")
            return False
        c = self.choose_customer("take", "Choose a customer to take an order from", awaiting)
        if c is None:
            return False
        item = self.spec.menu[c.kind.choose_item(c.id, self.spec.menu)]
        bill = c.kind.bill(item.price_cents)
        if self.r.hh_active():
            bill = hh_bill(bill)
        od = Order(self.r.next_order_id, c, item, bill)
        self.r.next_order_id += 1
        c.order = od
        c.state = cs.ORDERED
        self.taken_this_turn.append(od)
        units = "unit" if item.prep_units == 1 else "units"
        self.msg(f"Waiter takes order {od.describe()} ({format_money(od.bill_cents)}, {item.prep_units} prep {units}).")
        return True

    def _waiter_serve(self) -> bool:
        ready = self.r.ready_orders()
        if not ready:
            self.msg("No orders are ready to serve.")
            return False
        od = self.choose_order("serve", "Choose an order to serve", "Back", "Choose order", ready)
        if od is None:
            return False
        if od.ready_turn >= self.turn:
            self.err(f"Order {od.describe()} only became ready this turn. Serve next turn.")
            return False
        od.status = "SERVED"
        od.customer.state = cs.SERVED
        od.customer.served_turn = self.turn
        self.served += 1
        self.msg(f"Waiter serves {od.describe()}.")
        return True

    def step_chef(self) -> None:
        orders = self.r.kitchen_orders()
        if not orders:
            self.msg("The chef has no orders to prepare.")
            return
        od = self.choose_order("chef", "Chef: prepare which order?", "Wait", "Choose Chef task", orders)
        if od is None:
            return
        od.advance(self.turn)
        if od.is_ready():
            self.msg(f"Chef prepares {od.describe()} ({od.progress}): READY.")
        else:
            self.msg(f"Chef prepares {od.describe()} ({od.progress}).")

    def step_eating_and_payment(self) -> None:
        for c in self.r.customers:
            c.finish_eating(self.turn)
        due = [c for c in self.r.ready_to_pay() if c.can_pay_on(self.turn)]
        if due:
            c = min(due, key=lambda x: (x.ready_to_pay_turn, x.id))
            c.pay()
            self.revenue_cents += c.order.bill_cents
            self.paid_sats.append(c.satisfaction)
            self.msg(f"{c.name} pays {format_money(c.order.bill_cents)}.")

    def step_waiting_and_abandonment(self) -> None:
        for c in self.r.present_customers():
            if not c.is_waiting_for_service():
                continue
            c.lose_satisfaction()
            if c.satisfaction == 0:
                if c in self.r.queue:
                    self.r.queue.remove(c)
                c.leave()
                self.departures += 1
                self.msg(f"{c.name} leaves unhappy.")

    def show_result(self) -> bool:
        s = self.spec
        paid = len(self.paid_sats)
        paid_met = paid >= s.target_paid
        rev_met = self.revenue_cents >= s.target_revenue_cents
        sat_met = paid > 0 and sum(self.paid_sats) >= s.target_avg_satisfaction * paid
        victory = paid_met and rev_met and sat_met
        mark = lambda m: "[met]" if m else "[MISSED]"
        o = self.out
        o.println()
        o.println(THICK)
        o.println(" RESULT: " + ("VICTORY" if victory else "DEFEAT"))
        o.println(THICK)
        o.println(f"  Paid customers:   {paid} (target >= {s.target_paid}) {mark(paid_met)}")
        o.println(f"  Revenue:          {format_money(self.revenue_cents)} (target >= "
                  f"{format_money(s.target_revenue_cents)}) {mark(rev_met)}")
        o.println(f"  Avg satisfaction: {self.avg()} (target >= {s.target_avg_satisfaction}) {mark(sat_met)}")
        o.println(f"  Served {self.served} | unhappy departures {self.departures} | turns used "
                  f"{self.turns_used}/{s.max_turns}")
        return victory


def staff_line(spec: StageSpec) -> str:
    host = "Host (1 seat available) | " if spec.has("host") else ""
    return f"Staff: {host}Waiter (1 task available) | Chef (1 prep unit available) | Cashier automatic, 1 payment"


def run_script(spec: StageSpec, text: str) -> ModelResult:
    return GameModel(spec, ScriptSource(text)).run()


def join_script(lines: Iterable[str], newline: str = "\n") -> str:
    lines = list(lines)
    return newline.join(lines) + (newline if lines else "")
