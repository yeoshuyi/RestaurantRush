"""Monitor: turns raw game stdout into structured per-turn records.

It does not use the reference model. It only knows the UI print format, so
assertions and coverage are computed from what the DUT actually printed.
Prompts end without a newline, so the next output continues on the same line
(e.g. "Choose customer [0-1]:   > Waiter seats C1 at table 1."). The tokenizer
splits those prompts off before classifying the rest of the line.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

PROMPT_RE = re.compile(r"^(Choose [A-Za-z ]+?) \[(-?\d+)-(-?\d+)\]: ")

LINE_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("banner", re.compile(r"^RestaurantRush$")),
    ("thick", re.compile(r"^={60}$")),
    ("thin", re.compile(r"^-{60}$")),
    ("turn_header", re.compile(r"^ TURN (\d+) / (\d+)$")),
    ("status", re.compile(r"^Revenue: (-?\$\d+\.\d\d)   Paid: (\d+)   Avg satisfaction \(paid\): (N/A|\d+\.\d)$")),
    ("queue", re.compile(r"^Waiting queue:((?: \(empty\))|(?: C\d+\[sat \d+\])*)$")),
    ("hh_status", re.compile(r"^Happy Hour: (available|used|ACTIVE, (\d+) turns? left)$")),
    ("hh_offer", re.compile(r"^Happy Hour \(once per game, this turn and next\): start now\?$")),
    ("tables_hdr", re.compile(r"^Tables:$")),
    ("table", re.compile(r"^  Table (\d+): (.*)$")),
    ("staff", re.compile(r"^Staff: (.*)$")),
    ("waiter_menu", re.compile(r"^Waiter tasks:$")),
    ("chooser", re.compile(r"^(Choose a customer to seat|Choose a customer to take an order from"
                           r"|Choose an order to serve|Chef: prepare which order\?|Host: seat which customer\?)$")),
    ("option", re.compile(r"^  (\d+)\) (.*)$")),
    ("msg", re.compile(r"^  > (.*)$")),
    ("err", re.compile(r"^  ! (.*)$")),
    ("in_nan", re.compile(r"^  '(.*)' is not a whole number\. Enter a number from (-?\d+) to (-?\d+)\.$")),
    ("in_range", re.compile(r"^  (-?\d+) is out of range\. Enter a number from (-?\d+) to (-?\d+)\.$")),
    ("end_turn", re.compile(r"^End of turn (\d+): served (\d+) \| unhappy departures (\d+) \| revenue "
                            r"(-?\$\d+\.\d\d) \| avg satisfaction (N/A|\d+\.\d) \| turns used (\d+)/(\d+)$")),
    ("result", re.compile(r"^ RESULT: (VICTORY|DEFEAT)$")),
    ("res_paid", re.compile(r"^  Paid customers:   (\d+) \(target >= (\d+)\) \[(met|MISSED)\]$")),
    ("res_rev", re.compile(r"^  Revenue:          (-?\$\d+\.\d\d) \(target >= (\$\d+\.\d\d)\) \[(met|MISSED)\]$")),
    ("res_avg", re.compile(r"^  Avg satisfaction: (N/A|\d+\.\d) \(target >= (\d+)\) \[(met|MISSED)\]$")),
    ("res_summary", re.compile(r"^  Served (\d+) \| unhappy departures (\d+) \| turns used (\d+)/(\d+)$")),
    ("error", re.compile(r"^Error: (.*)$")),
    ("blank", re.compile(r"^$")),
]

# Item names may be combos such as "Salad+Pasta" (Stage 3).
ITEM = r"([\w+]+)"
CUSTOMER_DESC_RE = re.compile(
    r"^(C\d+) \((\w+)\) sat (\d+), (\w+)(?:, order #(\d+) " + ITEM + r" (\w+) (\d+)/(\d+))?$")
ORDER_DESC = r"#(\d+) " + ITEM + r" \((\d+)/(\d+) units\) \[(\w+)\]"
ORDER_OPTION_RE = re.compile(r"^" + ORDER_DESC + r" \[(\w+) (\d+)/(\d+)\]$")

MSG_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("arrive", re.compile(r"^(C\d+) arrives \((\w+)\)\.$")),
    ("w_wait", re.compile(r"^The waiter takes no action this turn\.$")),
    ("w_seat_empty", re.compile(r"^No customers are waiting to be seated\.$")),
    ("w_take_empty", re.compile(r"^No seated customers are waiting to order\.$")),
    ("w_serve_empty", re.compile(r"^No orders are ready to serve\.$")),
    ("w_seat_ok", re.compile(r"^Waiter seats (C\d+) at table (\d+)\.$")),
    ("w_take_ok", re.compile(r"^Waiter takes order " + ORDER_DESC +
                             r" \((-?\$\d+\.\d\d), (\d+) prep units?\)\.$")),
    ("w_serve_ok", re.compile(r"^Waiter serves " + ORDER_DESC + r"\.$")),
    ("c_none", re.compile(r"^The chef has no orders to prepare\.$")),
    ("c_prep", re.compile(r"^Chef prepares " + ORDER_DESC + r" \((\d+)/(\d+)\)(: READY)?\.$")),
    ("pay", re.compile(r"^(C\d+) pays (-?\$\d+\.\d\d)\.$")),
    ("leave", re.compile(r"^(C\d+) leaves unhappy\.$")),
    ("hh_start", re.compile(r"^Happy Hour starts: (\d+) turns \(this turn and next\), 20% off new orders\.$")),
    ("hh_recover", re.compile(r"^(C\d+) recovers to (\d+) \(Happy Hour\)\.$")),
    ("h_none", re.compile(r"^The host has no customers to seat\.$")),
    ("h_no_table", re.compile(r"^The host has no free table\.$")),
    ("h_seat_ok", re.compile(r"^Host seats (C\d+) at table (\d+)\.$")),
]

# Line / message kinds that only exist when a stage feature is on.
FEATURE_OF: Dict[str, str] = {
    "hh_status": "happy_hour", "hh_offer": "happy_hour", "hh_start": "happy_hour",
    "hh_recover": "happy_hour", "h_none": "host", "h_no_table": "host", "h_seat_ok": "host",
}

ERR_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("no_free_table", re.compile(r"^No free table\.$")),
    ("ready_this_turn", re.compile(r"only became ready this turn")),
    ("not_ready", re.compile(r"is not READY")),
    ("not_waiting", re.compile(r"is not waiting in the queue")),
    ("not_seated", re.compile(r"is not seated and waiting to order")),
    ("busy", re.compile(r"has already acted this turn")),
    ("chef_done", re.compile(r"needs no more preparation")),
]

CHOOSER_TASK = {
    "Choose a customer to seat": "seat",
    "Choose a customer to take an order from": "take",
    "Choose an order to serve": "serve",
}


@dataclass
class Token:
    kind: str
    groups: Tuple[str, ...]
    lineno: int
    raw: str


@dataclass
class TableView:
    id: int
    customer: Optional[str] = None
    ctype: Optional[str] = None
    sat: Optional[int] = None
    state: Optional[str] = None
    order_id: Optional[int] = None
    item: Optional[str] = None
    order_status: Optional[str] = None
    units_done: Optional[int] = None
    units_total: Optional[int] = None


@dataclass
class Snapshot:
    revenue: str = ""
    paid: int = 0
    avg: str = ""
    queue: List[Tuple[str, int]] = field(default_factory=list)
    tables: List[TableView] = field(default_factory=list)
    staff: str = ""
    hh: Optional[str] = None  # Happy Hour status line, Stage 3


@dataclass
class HostAction:
    kind: str = ""  # no_customers | no_free_table | wait | seat
    options: List[str] = field(default_factory=list)
    detail: Tuple[str, ...] = ()


@dataclass
class WaiterAttempt:
    task: Optional[str] = None  # wait | seat | take | serve
    outcome: Optional[str] = None  # ok | empty | back | <err kind>
    options: List[str] = field(default_factory=list)
    detail: Tuple[str, ...] = ()


@dataclass
class ChefAction:
    kind: str = ""  # no_orders | wait | prep | error
    options: List[str] = field(default_factory=list)
    detail: Tuple[str, ...] = ()


@dataclass
class TurnRecord:
    turn: int
    max_turns: int
    arrivals: List[Tuple[str, str]] = field(default_factory=list)
    snapshot: Optional[Snapshot] = None
    hh_offered: bool = False
    hh_started: bool = False
    recoveries: List[Tuple[str, int]] = field(default_factory=list)
    host: Optional[HostAction] = None
    waiter: List[WaiterAttempt] = field(default_factory=list)
    chef: Optional[ChefAction] = None
    payments: List[Tuple[str, str]] = field(default_factory=list)
    departures: List[str] = field(default_factory=list)
    end: Optional[Tuple[str, ...]] = None
    input_errors: List[Tuple[str, str, str]] = field(default_factory=list)  # (kind, prompt, token)
    prompts: List[Tuple[str, int, int]] = field(default_factory=list)
    other_msgs: List[str] = field(default_factory=list)


@dataclass
class ResultRecord:
    outcome: str = ""
    paid: Optional[Tuple[str, ...]] = None
    revenue: Optional[Tuple[str, ...]] = None
    avg: Optional[Tuple[str, ...]] = None
    summary: Optional[Tuple[str, ...]] = None


@dataclass
class Transcript:
    tokens: List[Token]
    turns: List[TurnRecord]
    result: Optional[ResultRecord]
    error_line: Optional[str]
    banner: bool
    unknown: List[Token]
    line_kinds: Dict[str, int]


def tokenize(text: str) -> List[Token]:
    tokens: List[Token] = []
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for n, line in enumerate(lines, 1):
        rest = line
        while True:
            m = PROMPT_RE.match(rest)
            if not m:
                break
            tokens.append(Token("prompt", m.groups(), n, m.group(0)))
            rest = rest[m.end():]
            if rest == "":
                break
        if rest == "" and line != "":
            continue  # line held only prompt(s) (EOF or newline right after)
        for kind, pat in LINE_PATTERNS:
            m = pat.match(rest)
            if m:
                tokens.append(Token(kind, m.groups(), n, rest))
                break
        else:
            tokens.append(Token("unknown", (), n, rest))
    return tokens


def _classify(table: List[Tuple[str, re.Pattern]], text: str) -> Tuple[Optional[str], Tuple[str, ...]]:
    for kind, pat in table:
        m = pat.search(text) if table is ERR_PATTERNS else pat.match(text)
        if m:
            return kind, m.groups()
    return None, ()


def parse_table(tid: int, desc: str) -> TableView:
    tv = TableView(tid)
    if desc == "free":
        return tv
    m = CUSTOMER_DESC_RE.match(desc)
    if not m:
        tv.state = "UNPARSEABLE:" + desc
        return tv
    g = m.groups()
    tv.customer, tv.ctype, tv.sat, tv.state = g[0], g[1], int(g[2]), g[3]
    if g[4] is not None:
        tv.order_id, tv.item, tv.order_status = int(g[4]), g[5], g[6]
        tv.units_done, tv.units_total = int(g[7]), int(g[8])
    return tv


def parse(text: str) -> Transcript:
    tokens = tokenize(text)
    turns: List[TurnRecord] = []
    result: Optional[ResultRecord] = None
    error_line: Optional[str] = None
    banner = False
    unknown: List[Token] = []
    kinds: Dict[str, int] = {}

    cur: Optional[TurnRecord] = None
    phase = "pre"  # pre | state | waiter | chef | post | result
    attempt: Optional[WaiterAttempt] = None
    last_prompt = ""

    def close_attempt_as_back() -> None:
        if attempt is not None and attempt.task in CHOOSER_TASK.values() and attempt.outcome is None:
            attempt.outcome = "back"

    for tok in tokens:
        kinds[tok.kind] = kinds.get(tok.kind, 0) + 1
        k, g = tok.kind, tok.groups
        if k == "banner":
            banner = True
        elif k == "turn_header":
            cur = TurnRecord(int(g[0]), int(g[1]))
            turns.append(cur)
            phase, attempt = "pre", None
        elif k == "unknown":
            unknown.append(tok)
        elif k == "error":
            error_line = tok.raw
        elif k == "result":
            phase = "result"
            result = ResultRecord(outcome=g[0])
        elif phase == "result" and k in ("res_paid", "res_rev", "res_avg", "res_summary"):
            setattr(result, {"res_paid": "paid", "res_rev": "revenue", "res_avg": "avg",
                             "res_summary": "summary"}[k], g)
        elif cur is None:
            continue
        elif k == "prompt":
            last_prompt = g[0]
            cur.prompts.append((g[0], int(g[1]), int(g[2])))
        elif k in ("in_nan", "in_range"):
            cur.input_errors.append((k, last_prompt, g[0]))
        elif k == "status":
            phase = "state"
            cur.snapshot = Snapshot(revenue=g[0], paid=int(g[1]), avg=g[2])
        elif k == "queue" and cur.snapshot is not None:
            cur.snapshot.queue = [(n, int(s)) for n, s in re.findall(r"(C\d+)\[sat (\d+)\]", g[0])]
        elif k == "table" and cur.snapshot is not None and phase == "state":
            cur.snapshot.tables.append(parse_table(int(g[0]), g[1]))
        elif k == "staff" and cur.snapshot is not None:
            cur.snapshot.staff = g[0]
        elif k == "hh_status" and cur.snapshot is not None:
            cur.snapshot.hh = g[0]
        elif k == "hh_offer":
            phase = "hh"
            cur.hh_offered = True
        elif k == "waiter_menu":
            close_attempt_as_back()
            phase = "waiter"
            attempt = WaiterAttempt()
            cur.waiter.append(attempt)
        elif k == "chooser":
            if g[0] == "Chef: prepare which order?":
                phase = "chef"
                cur.chef = ChefAction(kind="wait")
            elif g[0] == "Host: seat which customer?":
                phase = "host"
                cur.host = HostAction(kind="wait")
            elif attempt is not None:
                attempt.task = CHOOSER_TASK[g[0]]
        elif k == "option":
            if g[0] == "0":
                pass  # "0) Back" / "0) Wait" / waiter "0) Wait"
            elif phase == "chef" and cur.chef is not None:
                cur.chef.options.append(g[1])
            elif phase == "host" and cur.host is not None:
                cur.host.options.append(g[1])
            elif phase == "waiter" and attempt is not None and attempt.task is not None:
                attempt.options.append(g[1])
        elif k == "err":
            ek, eg = _classify(ERR_PATTERNS, g[0])
            ek = ek or "other"
            if phase == "waiter" and attempt is not None:
                attempt.outcome, attempt.detail = ek, (g[0],)
            elif phase == "chef" and cur.chef is not None:
                cur.chef.kind, cur.chef.detail = "error", (g[0],)
            else:
                cur.other_msgs.append("! " + g[0])
        elif k == "msg":
            mk, mg = _classify(MSG_PATTERNS, g[0])
            if mk == "arrive":
                cur.arrivals.append((mg[0], mg[1]))
            elif mk == "hh_start":
                cur.hh_started = True
            elif mk == "hh_recover":
                cur.recoveries.append((mg[0], int(mg[1])))
            elif mk in ("h_none", "h_no_table"):
                cur.host = HostAction(kind="no_customers" if mk == "h_none" else "no_free_table")
            elif mk == "h_seat_ok" and cur.host is not None:
                cur.host.kind, cur.host.detail = "seat", mg
            elif mk is not None and mk.startswith("w_") and attempt is not None:
                task, outcome = {"w_wait": ("wait", "ok"), "w_seat_empty": ("seat", "empty"),
                                 "w_take_empty": ("take", "empty"), "w_serve_empty": ("serve", "empty"),
                                 "w_seat_ok": ("seat", "ok"), "w_take_ok": ("take", "ok"),
                                 "w_serve_ok": ("serve", "ok")}[mk]
                attempt.task, attempt.outcome, attempt.detail = task, outcome, mg
            elif mk == "c_none":
                phase = "chef"
                cur.chef = ChefAction(kind="no_orders")
            elif mk == "c_prep" and cur.chef is not None:
                cur.chef.kind, cur.chef.detail = "prep", mg
            elif mk == "pay":
                phase = "post"
                cur.payments.append((mg[0], mg[1]))
            elif mk == "leave":
                phase = "post"
                cur.departures.append(mg[0])
            else:
                cur.other_msgs.append(g[0])
        elif k == "end_turn":
            close_attempt_as_back()
            cur.end = g
            phase = "post"
    return Transcript(tokens, turns, result, error_line, banner, unknown, kinds)
