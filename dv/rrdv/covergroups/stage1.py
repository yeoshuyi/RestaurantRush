"""Stage 1 functional coverage (also sampled in later stages).

Every ignore/illegal bin says why it is unreachable under the base setting.
Facts that depend on who arrives when (who can abandon, on which turn, which
items they order, cheapest bills) come from rrdv.facts, so the same groups
stay correct when Stage 2 swaps arrivals for VIP / Critic customers.
Facts used repeatedly:
  * An unserved customer hits 0 at the end of turn arrival + ceil(100/penalty) - 1.
    Stage 1: only C1 (turn 13) and C2 (turn 16) abandon, ordering Salad / Burger.
    Stage 2: C2 is a Critic (turn 12, Pasta) and C1 a Regular (turn 13, Salad).
  * There is one Waiter, so at most one customer is served per turn, which means at most one
    customer becomes READY_TO_PAY per turn and the Cashier never builds a queue.
  * The Waiter acts before the Chef, so a dish finished this turn is never in the
    serve list ("only became ready this turn" can't be printed).
  * Stage 3: the Host lets a customer be seated and order on the arrival turn (one turn faster),
    Happy Hour delays departures and discounts bills, and nobody orders a plain Burger.
    Customers who recovered during Happy Hour are binned in stage3.py instead.
"""

from __future__ import annotations

from .. import facts
from ..javaparse import format_money
from ..monitor import FEATURE_OF, LINE_PATTERNS, MSG_PATTERNS
from ..spec import CUSTOMER_KINDS
from ..stimulus import JUNK_CLASSES, VALID_VARIANTS
from . import SampleCtx, covergroup

PROMPT_LABELS = ("Choose Waiter task", "Choose customer", "Choose order", "Choose Chef task")
STAGE3_PROMPTS = {"Choose Host task": "host", "Choose Happy Hour": "happy_hour"}


def _prompt_labels(spec):
    return list(PROMPT_LABELS) + [p for p, f in STAGE3_PROMPTS.items() if spec.has(f)]


def _feature_split(spec, kinds):
    """Bins for kinds the stage has; ignore (with reason) for kinds of features it lacks."""
    bins = [k for k in kinds if FEATURE_OF.get(k) is None or spec.has(FEATURE_OF[k])]
    ignore = {k: f"needs feature {FEATURE_OF[k]}" for k in kinds if k not in bins}
    return bins, ignore
ONE_WAITER = "single Waiter serves one customer per turn, so READY_TO_PAY never overlaps"


def _abandon_reason(spec) -> str:
    who = ", ".join(f"{a.name} {a.kind.label} turn {facts.abandon_turn(spec, a)} ({a.item.name})"
                    for a in facts.can_abandon(spec))
    return f"only these customers can abandon within {spec.max_turns} turns: {who or 'none'}"


def _penalty(label: str) -> int:
    for k in CUSTOMER_KINDS.values():
        if k.label == label:
            return k.wait_penalty
    raise KeyError(label)


def _bucket(n: int, edges):
    """edges: list of (label, lo, hi) inclusive."""
    for label, lo, hi in edges:
        if lo <= n <= hi:
            return label
    return f"out_of_range({n})"


def _work_available(snap) -> bool:
    free = any(tv.customer is None for tv in snap.tables)
    return (bool(snap.queue) and free) or any(tv.state == "SEATED" for tv in snap.tables) \
        or any(tv.order_status == "READY" for tv in snap.tables)


@covergroup(stage=1)
def turn_and_arrivals(db, spec):
    g = db.group("cg_turn_arrival", "turn sequence and scheduled arrivals")
    sched = sorted(spec.arrivals)
    cp_turn = g.coverpoint("turn", [str(t) for t in range(1, spec.max_turns + 1)])
    cp_arr = g.coverpoint("arrival_turn", [str(t) for t in sched])
    cx_q = g.cross("arrival_x_queue_before", [str(t) for t in sched], ["0", "1", "2+"], ignore={
        (str(sched[0]), "1"): "queue is empty before the first arrival",
        (str(sched[0]), "2+"): "queue is empty before the first arrival",
        (str(sched[1]), "2+"): "only one earlier customer exists at the second arrival",
    })
    cx_t = g.cross("arrival_x_free_tables", [str(t) for t in sched], ["0", "1", "2"], ignore={
        (str(sched[0]), "0"): "all tables free on turn 1",
        (str(sched[0]), "1"): "all tables free on turn 1",
        (str(sched[1]), "0"): "only one earlier customer exists at the second arrival",
    })
    cp_qlen = g.coverpoint("queue_len", ["0", "1", "2", "3", "4+"])

    def sample(ctx: SampleCtx):
        for t in ctx.tr.turns:
            if t.snapshot is None:
                continue
            cp_turn.sample(str(t.turn))
            q = len(t.snapshot.queue)
            cp_qlen.sample(_bucket(q, [("0", 0, 0), ("1", 1, 1), ("2", 2, 2), ("3", 3, 3), ("4+", 4, 99)]))
            if t.arrivals:
                cp_arr.sample(str(t.turn))
                before = q - len(t.arrivals)
                cx_q.sample((str(t.turn), _bucket(before, [("0", 0, 0), ("1", 1, 1), ("2+", 2, 99)])))
                free = sum(1 for tv in t.snapshot.tables if tv.customer is None)
                cx_t.sample((str(t.turn), str(free)))
    return sample


@covergroup(stage=1)
def waiter(db, spec):
    g = db.group("cg_waiter", "Waiter task choices and outcomes")
    illegal = {
        ("serve", "ready_this_turn"): "Waiter acts before Chef, so listed READY orders are from earlier turns",
        ("serve", "not_ready"): "serve list only contains READY orders",
        ("seat", "not_waiting"): "seat list only contains queued customers",
        ("take", "not_seated"): "take list only contains SEATED customers",
    }
    for task in ("wait", "seat", "take", "serve"):
        illegal[(task, "busy")] = "waiter loop stops after one success"
        illegal[(task, "other")] = "unknown error text"
    cp = g.coverpoint("task_x_outcome", [
        ("wait", "ok"),
        ("seat", "ok"), ("seat", "empty"), ("seat", "no_free_table"), ("seat", "back"),
        ("take", "ok"), ("take", "empty"), ("take", "back"),
        ("serve", "ok"), ("serve", "empty"), ("serve", "back"),
    ], illegal=illegal)
    cp_att = g.coverpoint("attempts_per_turn", ["1", "2", "3", "4+"])
    cp_tab = g.coverpoint("seat_table", [str(i) for i in range(1, spec.tables + 1)])
    cp_wait = g.coverpoint("wait_kind", ["idle_wait", "strategic_wait"],
                           desc="waited with nothing to do vs. while useful work existed")
    cp_pick = g.coverpoint("seat_pick", ["front_of_queue", "not_front"])

    def sample(ctx: SampleCtx):
        for t in ctx.tr.turns:
            if not t.waiter or t.snapshot is None:
                continue
            done = t.end is not None
            if done:
                n = len(t.waiter)
                cp_att.sample(_bucket(n, [("1", 1, 1), ("2", 2, 2), ("3", 3, 3), ("4+", 4, 999)]))
            for a in t.waiter:
                if a.task is None or a.outcome is None:
                    continue
                cp.sample((a.task, a.outcome), f"turn {t.turn}")
                if a.task == "seat" and a.outcome == "ok":
                    cp_tab.sample(a.detail[1])
                    front = t.snapshot.queue[0][0] if t.snapshot.queue else None
                    cp_pick.sample("front_of_queue" if a.detail[0] == front else "not_front")
                if a.task == "wait":
                    cp_wait.sample("strategic_wait" if _work_available(t.snapshot) else "idle_wait")
    return sample


@covergroup(stage=1)
def chef(db, spec):
    g = db.group("cg_chef", "Chef preparation choices")
    acts = ["no_orders", "wait"]
    never = {}
    ordered = facts.ordered_items(spec)
    for item in spec.menu:
        for u in range(1, item.prep_units + 1):
            key = f"prep_{item.name}_{u}of{item.prep_units}"
            if item.name in ordered:
                acts.append(key)
            else:
                never[key] = f"no base-setting customer orders {item.name}"
    cp = g.coverpoint("action", acts, ignore=never, illegal={"error": "chef only offered kitchen orders"})
    cp_same = g.coverpoint("prepared_order", ["taken_this_turn", "taken_earlier"])
    cp_depth = g.coverpoint("kitchen_depth", [str(i) for i in range(1, spec.tables + 1)])
    cp_pick = g.coverpoint("pick", ["oldest", "newer"])

    def sample(ctx: SampleCtx):
        for t in ctx.tr.turns:
            c = t.chef
            if c is None or t.end is None:
                continue
            if c.kind == "prep":
                oid, item, done, total = c.detail[0], c.detail[1], c.detail[2], c.detail[3]
                cp.sample(f"prep_{item}_{done}of{total}", f"turn {t.turn}")
                taken = [a.detail[0] for a in t.waiter if a.task == "take" and a.outcome == "ok"]
                cp_same.sample("taken_this_turn" if oid in taken else "taken_earlier")
                first = c.options[0].split(" ")[0].lstrip("#") if c.options else None
                cp_pick.sample("oldest" if oid == first else "newer")
            else:
                cp.sample(c.kind, f"turn {t.turn}")
            if c.kind in ("prep", "wait") and c.options:
                cp_depth.sample(str(len(c.options)))
    return sample


@covergroup(stage=1)
def order_lifecycle(db, spec):
    g = db.group("cg_order_lifecycle", "order states PLACED -> ... -> PAID/CANCELLED")
    finals = ["PAID", "CANCELLED_PLACED", "CANCELLED_IN_PREPARATION", "CANCELLED_READY", "OPEN"]
    ignore, illegal = {}, {}
    why = _abandon_reason(spec)
    abandoning = facts.abandoning_items(spec)
    ordered = facts.ordered_items(spec)
    for item in spec.menu:
        illegal[(item.name, "CANCELLED_SERVED")] = "served customers lose no satisfaction"
        if item.name not in ordered:
            for f in finals:
                ignore[(item.name, f)] = f"no base-setting customer orders {item.name}"
        elif item.name not in abandoning:
            for f in ("CANCELLED_PLACED", "CANCELLED_IN_PREPARATION", "CANCELLED_READY"):
                ignore[(item.name, f)] = why
        elif item.prep_units == 1:
            ignore[(item.name, "CANCELLED_IN_PREPARATION")] = "1-unit items skip IN_PREPARATION"
    cx = g.cross("item_x_final", [i.name for i in spec.menu], finals, ignore=ignore, illegal=illegal)
    transitions = ["PLACED->IN_PREPARATION", "IN_PREPARATION->READY", "PLACED->READY", "READY->SERVED",
                   "SERVED->PAID", "PLACED->CANCELLED", "READY->CANCELLED"]
    tr_ignore = {}
    if facts.multi_unit_cancel_possible(spec):
        transitions.append("IN_PREPARATION->CANCELLED")
    else:
        tr_ignore["IN_PREPARATION->CANCELLED"] = why
    cp_tr = g.coverpoint("transition", transitions,
        ignore=tr_ignore,
        illegal={"SERVED->CANCELLED": "served customers lose no satisfaction",
                 "PLACED->SERVED": "must be READY first", "IN_PREPARATION->SERVED": "must be READY first",
                 "PLACED->PAID": "must be served first", "READY->PAID": "must be served first"})
    cp_rw = g.coverpoint("ready_to_serve_turns", ["1", "2", "3+"],
                         illegal={"0": "dish finished this turn is served next turn at the earliest"})
    cp_open = g.coverpoint("open_status_at_end", ["PLACED", "IN_PREPARATION", "READY", "SERVED"])

    def sample(ctx: SampleCtx):
        for o in ctx.tl.orders.values():
            st = [s for _, s in o.statuses]
            for a, b in zip(st, st[1:]):
                cp_tr.sample(f"{a}->{b}", f"order #{o.id}")
            if o.ready_turn > 0 and o.served_turn > 0:
                d = o.served_turn - o.ready_turn
                cp_rw.sample(_bucket(d, [("0", -99, 0), ("1", 1, 1), ("2", 2, 2), ("3+", 3, 99)]))
            if not ctx.eof:
                cx.sample((o.item, o.final), f"order #{o.id}")
                if o.final == "OPEN":
                    cp_open.sample(o.last_status)
    return sample


@covergroup(stage=1)
def satisfaction(db, spec):
    g = db.group("cg_satisfaction", "satisfaction decay and abandonment")
    # Regular customers only; other kinds have their own bins in stage2.py.
    # Best Regular payment satisfaction: 100 - 8 x fastest unserved turns of its quickest dish.
    regular_units = min((a.item.prep_units for a in facts.arrivals(spec) if a.kind.key == "REGULAR"),
                        default=1)
    best = spec.start_satisfaction - 8 * facts.fastest_unserved_turns(spec, regular_units)
    pay_bins = ["84", "76-83", "60-75", "1-59"]
    pay_ignore = {}
    if best >= 85:
        pay_bins.insert(0, "85-100")
    else:
        pay_ignore["85-100"] = "a Regular loses 8 on arrival turn and on order turn before it can be served"
    cp_pay = g.coverpoint("sat_at_payment", pay_bins, ignore=pay_ignore)
    cp_from = g.coverpoint("abandon_from", ["WAITING", "SEATED", "ORDERED"],
                           illegal={"SERVED": "served customers lose nothing",
                                    "READY_TO_PAY": "served customers lose nothing"})
    # Anything outside the derived turns is undeclared -> violation.
    cp_turn = g.coverpoint("abandon_turn", [str(t) for t in facts.abandon_turns(spec)])
    cp_dep = g.coverpoint("departures_per_game", [str(i) for i in range(len(facts.can_abandon(spec)) + 1)])
    cp_last = g.coverpoint("last_chance", ["left", "rescued"],
                           desc="customer at <= penalty satisfaction either leaves or is served that turn")

    def sample(ctx: SampleCtx):
        for h in ctx.tl.customers.values():
            if h.paid_turn > 0 and h.ctype == "Regular" and not h.recovered_turns:
                s = h.sats.get(h.paid_turn, -1)
                cp_pay.sample(_bucket(s, [("1-59", 1, 59), ("60-75", 60, 75), ("76-83", 76, 83),
                                          ("84", 84, 84), ("85-100", 85, 100)]))
            if h.departed_turn > 0:
                cp_from.sample(h.state_at_departure, h.name)
                cp_turn.sample(str(h.departed_turn), h.name)
        if not ctx.eof:
            cp_dep.sample(str(sum(1 for h in ctx.tl.customers.values() if h.departed_turn > 0)))
        for t in ctx.tr.turns:
            if t.snapshot is None or t.end is None:
                continue
            for tv in t.snapshot.tables:
                if tv.customer and tv.state in ("SEATED", "ORDERED") and tv.sat <= _penalty(tv.ctype):
                    h = ctx.tl.customers[tv.customer]
                    cp_last.sample("rescued" if h.served_turn == t.turn else "left")
    return sample


@covergroup(stage=1)
def eating_payment(db, spec):
    g = db.group("cg_eat_pay", "eating delay, cashier and table release")
    cp_lat = g.coverpoint("serve_to_pay_turns", ["2"], ignore={"3+": ONE_WAITER},
                          illegal={"0": "one full turn of eating", "1": "pay the turn after READY_TO_PAY"})
    cp_rtp = g.coverpoint("ready_to_pay_concurrency", ["1"], ignore={"2+": ONE_WAITER})
    if facts.earliest_pay_turn(spec) <= 4:  # Stage 3 Host: seat + order on turn 1, pay on turn 4
        cp_pt = g.coverpoint("pay_turn", ["1-4", "5-9", "10-14", "15-18"])
    else:
        cp_pt = g.coverpoint("pay_turn", ["5-9", "10-14", "15-18"],
                             illegal={"1-4": "seat, order, serve, eat, pay needs 5 turns"})
    cp_cnt = g.coverpoint("payments_per_game", [str(i) for i in range(0, 6)])
    cp_reuse = g.coverpoint("table_reuse", ["after_payment", "after_departure"])
    cp_end = g.coverpoint("unpaid_at_end", ["SERVED", "READY_TO_PAY"])

    def sample(ctx: SampleCtx):
        freed = {}  # table id -> (turn, why)
        for t in ctx.tr.turns:
            if t.snapshot is None:
                continue
            rtp = [tv for tv in t.snapshot.tables if tv.state == "READY_TO_PAY"]
            if rtp:
                cp_rtp.sample("1" if len(rtp) == 1 else "2+")
            for a in t.waiter:
                if a.task == "seat" and a.outcome == "ok" and int(a.detail[1]) in freed:
                    cp_reuse.sample(freed.pop(int(a.detail[1]))[1])
            for name, _ in t.payments:
                h = ctx.tl.customers[name]
                freed[h.table] = (t.turn, "after_payment")
                cp_pt.sample(_bucket(t.turn, [("1-4", 1, 4), ("5-9", 5, 9), ("10-14", 10, 14), ("15-18", 15, 18)]))
                if h.served_turn > 0:
                    d = t.turn - h.served_turn
                    cp_lat.sample(_bucket(d, [("0", -99, 0), ("1", 1, 1), ("2", 2, 2), ("3+", 3, 99)]))
            for name in t.departures:
                h = ctx.tl.customers[name]
                if h.table > 0:
                    freed[h.table] = (t.turn, "after_departure")
        if not ctx.eof and ctx.tr.result is not None:
            cp_cnt.sample(ctx.tr.result.paid[0])
            for h in ctx.tl.customers.values():
                if h.served_turn > 0 and h.paid_turn < 0:
                    # served on the last turn -> still SERVED; one turn earlier -> READY_TO_PAY
                    cp_end.sample("SERVED" if h.served_turn == spec.max_turns else "READY_TO_PAY")
    return sample


@covergroup(stage=1)
def result(db, spec):
    g = db.group("cg_result", "end-of-game metrics and outcome")
    cp_out = g.coverpoint("outcome", ["VICTORY", "DEFEAT"])
    cp_paid = g.coverpoint("paid", [str(i) for i in range(0, 6)])
    cp_rev = g.coverpoint("revenue", ["$0", "<$45", "$45-$59.99", ">=$60"])
    cp_avg = g.coverpoint("avg_satisfaction", ["N/A", "<60", "60.0", "60.1-69.9", "70+"])
    cheapest = facts.cheapest_bills(spec, spec.target_paid)
    rev_ignore = {}
    if cheapest >= spec.target_revenue_cents:
        why = (f"{spec.target_paid} cheapest payable bills = {format_money(cheapest)} >= "
               f"{format_money(spec.target_revenue_cents)}")
        rev_ignore = {("met", "MISSED", "met"): why, ("met", "MISSED", "MISSED"): why}
    cx = g.cross("targets_paid_rev_sat", ["met", "MISSED"], ["met", "MISSED"], ["met", "MISSED"],
                 ignore=rev_ignore)
    cp_eof = g.coverpoint("ended_by", ["result", "input_ended"])

    def sample(ctx: SampleCtx):
        cp_eof.sample("input_ended" if ctx.eof else "result")
        r = ctx.tr.result
        if r is None or r.paid is None or r.revenue is None or r.avg is None:
            return
        cp_out.sample(r.outcome)
        cp_paid.sample(r.paid[0])
        cents = int(r.revenue[0].replace("$", "").replace(".", ""))
        cp_rev.sample(_bucket(cents, [("$0", 0, 0), ("<$45", 1, 4499), ("$45-$59.99", 4500, 5999),
                                      (">=$60", 6000, 10 ** 9)]))
        a = r.avg[0]
        if a == "N/A":
            cp_avg.sample("N/A")
        else:
            v = float(a)
            cp_avg.sample("<60" if v < 60 else "60.0" if a == "60.0" else "60.1-69.9" if v < 70 else "70+")
        cx.sample((r.paid[2], r.revenue[2], r.avg[2]))
    return sample


@covergroup(stage=1)
def print_verification(db, spec):
    g = db.group("cg_print", "every UI line type observed and parsed")
    kinds, kind_ignore = _feature_split(spec, [k for k, _ in LINE_PATTERNS] + ["prompt"])
    cp_line = g.coverpoint("line_kind", kinds, ignore=kind_ignore, illegal={"unknown": "unparseable output"})
    msgs, msg_ignore = _feature_split(spec, [k for k, _ in MSG_PATTERNS])
    cp_msg = g.coverpoint("message_kind", msgs, ignore=msg_ignore)
    cp_avg = g.coverpoint("avg_display", ["N/A", "value"])
    cp_q = g.coverpoint("queue_display", ["empty", "1", "2", "3+"])
    cp_tab = g.coverpoint("table_state_display", ["free", "SEATED", "ORDERED", "SERVED", "READY_TO_PAY"],
                          illegal={"WAITING": "", "PAID": "", "LEFT": ""})
    cp_ord = g.coverpoint("order_status_display", ["PLACED", "IN_PREPARATION", "READY", "SERVED"],
                          illegal={"PAID": "paid customers leave the table",
                                   "CANCELLED": "departed customers leave the table"})

    def sample(ctx: SampleCtx):
        for k in ctx.tr.line_kinds:
            cp_line.sample(k)
        for t in ctx.tr.turns:
            for _ in t.arrivals:
                cp_msg.sample("arrive")
            for a in t.waiter:
                key = {("wait", "ok"): "w_wait", ("seat", "empty"): "w_seat_empty",
                       ("take", "empty"): "w_take_empty", ("serve", "empty"): "w_serve_empty",
                       ("seat", "ok"): "w_seat_ok", ("take", "ok"): "w_take_ok",
                       ("serve", "ok"): "w_serve_ok"}.get((a.task, a.outcome))
                if key:
                    cp_msg.sample(key)
            if t.chef is not None and t.chef.kind == "no_orders":
                cp_msg.sample("c_none")
            if t.chef is not None and t.chef.kind == "prep":
                cp_msg.sample("c_prep")
            if t.payments:
                cp_msg.sample("pay")
            if t.hh_started:
                cp_msg.sample("hh_start")
            if t.recoveries:
                cp_msg.sample("hh_recover")
            if t.host is not None and t.host.kind in ("no_customers", "no_free_table", "seat"):
                cp_msg.sample({"no_customers": "h_none", "no_free_table": "h_no_table",
                               "seat": "h_seat_ok"}[t.host.kind])
            if t.departures:
                cp_msg.sample("leave")
            s = t.snapshot
            if s is None:
                continue
            cp_avg.sample("N/A" if s.avg == "N/A" else "value")
            n = len(s.queue)
            cp_q.sample("empty" if n == 0 else str(n) if n < 3 else "3+")
            for tv in s.tables:
                cp_tab.sample("free" if tv.customer is None else tv.state)
                if tv.order_status:
                    cp_ord.sample(tv.order_status)
    return sample


@covergroup(stage=1)
def input_robustness(db, spec):
    g = db.group("cg_input", "malformed / unusual input handling")
    cp_junk = g.coverpoint("junk_class", list(JUNK_CLASSES))
    cp_var = g.coverpoint("valid_variant", list(VALID_VARIANTS))
    labels = _prompt_labels(spec)
    cx = g.cross("dut_error_x_prompt", ["in_nan", "in_range"], labels)
    cp_file = g.coverpoint("file_format", ["lf", "crlf", "no_final_newline", "eof"])
    cp_eof = g.coverpoint("eof_at_prompt", labels)

    def sample(ctx: SampleCtx):
        st = ctx.stim
        if st is not None:
            for cls, n in st.injected.items():
                if n:
                    (cp_junk if cls in JUNK_CLASSES else cp_var).sample(cls)
            cp_file.sample("crlf" if "crlf" in st.file_classes else "lf")
            for fc in st.file_classes:
                if fc != "crlf":
                    cp_file.sample(fc)
        for t in ctx.tr.turns:
            for kind, label, _ in t.input_errors:
                cx.sample((kind, label))
        if ctx.eof:
            last = None
            for tok in ctx.tr.tokens:
                if tok.kind == "prompt":
                    last = tok.groups[0]
            if last:
                cp_eof.sample(last)
    return sample
