"""Constrained-random stimulus generation.

The generator steps the reference model in lockstep, so at every prompt it sees
the exact menu the DUT will show (queue, free tables, ready orders...). A
decision is a weighted random draw over candidate choices, filtered by
constraints in the style of SystemVerilog `constraint` blocks:

  * hard constraints remove candidates (e.g. the waiter-attempt cap),
  * soft constraints are kept when they can be met and dropped when they can't
    (e.g. "prefer serving a READY order" in the greedy profile).

Junk input (robustness) is added before the valid answer of a prompt, and
the valid answer itself may be written in an unusual but legal form ("+2", "02", " 2 ").
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field, replace
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .model.game import GameModel, InputRequest, InputSource, join_script
from .spec import StageSpec

# --------------------------------------------------------------------------- constraints


@dataclass
class Candidate:
    value: int
    tag: str  # semantic tag, e.g. "seat", "back", "opt:C3"
    weight: float = 1.0


@dataclass
class Constraint:
    name: str
    pred: Callable[[InputRequest, Candidate], bool]
    soft: bool = False


def solve(req: InputRequest, cands: List[Candidate], constraints: Sequence[Constraint],
          rng: random.Random) -> Candidate:
    pool = [c for c in cands if all(k.pred(req, c) for k in constraints if not k.soft)]
    if not pool:
        raise RuntimeError(f"Over-constrained at {req.kind}: {[c.tag for c in cands]}")
    for k in constraints:
        if k.soft:
            preferred = [c for c in pool if k.pred(req, c)]
            if preferred:
                pool = preferred
    total = sum(max(c.weight, 0.0) for c in pool)
    if total <= 0:
        return rng.choice(pool)
    x = rng.uniform(0, total)
    for c in pool:
        x -= max(c.weight, 0.0)
        if x <= 0:
            return c
    return pool[-1]


# --------------------------------------------------------------------------- knobs

JUNK_CLASSES = ("non_numeric", "out_of_range_high", "negative", "overflow", "int_max",
                "decimal", "sign_only", "inner_space", "blank", "comment", "non_ascii")
VALID_VARIANTS = ("plain", "padded", "tab", "plus_sign", "leading_zero", "neg_zero", "unicode_digit")


@dataclass
class Knobs:
    waiter_weights: Dict[str, float] = field(default_factory=lambda: {"wait": 1, "seat": 3, "take": 3, "serve": 3})
    smart: float = 0.5  # probability that greedy soft constraints are applied to a decision
    back_prob: float = 0.05  # pick "0) Back" in a waiter chooser
    chef_wait_prob: float = 0.15
    host_wait_prob: float = 0.2  # Stage 3: Host chooses "0) Wait"
    hh_prob: float = 0.08  # Stage 3: chance per offer to start Happy Hour (random draws)
    junk_prob: float = 0.0  # per prompt
    junk_max: int = 3
    junk_weights: Dict[str, float] = field(default_factory=lambda: {k: 1.0 for k in JUNK_CLASSES})
    variant_prob: float = 0.0
    variant_weights: Dict[str, float] = field(default_factory=lambda: {k: 1.0 for k in VALID_VARIANTS})
    max_waiter_attempts: int = 5
    crlf_prob: float = 0.0
    eof_prob: float = 0.0
    no_final_newline_prob: float = 0.0


PROFILES: Dict[str, Knobs] = {
    "greedy": Knobs(smart=1.0, back_prob=0.0, chef_wait_prob=0.0, host_wait_prob=0.0),
    "mostly_greedy": Knobs(smart=0.85, back_prob=0.03, chef_wait_prob=0.05, junk_prob=0.03, variant_prob=0.05),
    "random": Knobs(smart=0.0, back_prob=0.1, chef_wait_prob=0.25, junk_prob=0.05, variant_prob=0.1,
                    crlf_prob=0.2, no_final_newline_prob=0.2),
    "lazy": Knobs(waiter_weights={"wait": 6, "seat": 1, "take": 1, "serve": 1}, smart=0.2,
                  back_prob=0.1, chef_wait_prob=0.6, host_wait_prob=0.7),
    "chaos": Knobs(smart=0.2, back_prob=0.3, chef_wait_prob=0.3, junk_prob=0.4, variant_prob=0.4,
                   max_waiter_attempts=8, crlf_prob=0.5, eof_prob=0.3, no_final_newline_prob=0.3),
}


# --------------------------------------------------------------------------- policy


def greedy_happy_hour(req: InputRequest) -> bool:
    """Start Happy Hour once at least two customers are waiting and one is below 85."""
    waiting = [c for c in req.model.r.present_customers() if c.is_waiting_for_service()]
    return len(waiting) >= 2 and any(c.satisfaction < 85 for c in waiting)


def greedy_task(req: InputRequest) -> str:
    """Best Waiter task with no lookahead: serve > take > seat > wait."""
    r = req.model.r
    if r.ready_orders():
        return "serve"
    if r.awaiting_order():
        return "take"
    if r.queue and r.free_table() is not None:
        return "seat"
    return "wait"


class Policy(InputSource):
    """Constrained-random InputSource. Records what it injected for coverage."""

    def __init__(self, knobs: Knobs, rng: random.Random,
                 extra_constraints: Sequence[Constraint] = ()):
        self.k = knobs
        self.rng = rng
        self.extra = list(extra_constraints)
        self.pending: List[str] = []
        self.pending_req = -1
        self.injected: Counter = Counter()  # junk/variant class -> count
        self.injected_at: Counter = Counter()  # (class, prompt kind) -> count
        self.decisions: List[Tuple[int, str, str]] = []  # (turn, kind, tag)
        self.turn_marks: Dict[int, int] = {}  # turn -> index of first line consumed in it
        self.lines_out = 0

    # -- InputSource
    def next_line(self, req: InputRequest) -> Optional[str]:
        if req.request_id != self.pending_req:
            self.pending_req = req.request_id
            self.pending = self._plan(req)
        self.turn_marks.setdefault(req.model.turn, self.lines_out)
        self.lines_out += 1
        return self.pending.pop(0)

    # -- planning one prompt
    def _plan(self, req: InputRequest) -> List[str]:
        lines: List[str] = []
        if self.rng.random() < self.k.junk_prob:
            for _ in range(self.rng.randint(1, self.k.junk_max)):
                cls = self._weighted(self.k.junk_weights)
                lines.append(self.junk(cls, req))
                self.injected[cls] += 1
                self.injected_at[(cls, req.kind)] += 1
        choice = self.decide(req)
        self.decisions.append((req.model.turn, req.kind, choice.tag))
        lines.append(self.encode(choice.value, req))
        return lines

    def decide(self, req: InputRequest) -> Candidate:
        cands = self.candidates(req)
        cons = list(self.extra) + self.constraints(req)
        return solve(req, cands, cons, self.rng)

    def candidates(self, req: InputRequest) -> List[Candidate]:
        k = self.k
        if req.kind == "waiter_task":
            return [Candidate(i, t, k.waiter_weights.get(t, 1.0)) for i, t in enumerate(req.options)]
        if req.kind == "happy_hour":
            return [Candidate(0, "not_now", 1 - k.hh_prob), Candidate(1, "start", k.hh_prob)]
        if req.kind in ("chef", "host"):
            n = len(req.options)
            p = k.chef_wait_prob if req.kind == "chef" else k.host_wait_prob
            out = [Candidate(0, "wait", p * n / max(1e-9, 1 - p))]
            out += [Candidate(i, f"opt{i}", 1.0) for i in range(1, n + 1)]
            return out
        n = len(req.options)
        out = [Candidate(0, "back", k.back_prob * n / max(1e-9, 1 - k.back_prob))]
        out += [Candidate(i, f"opt{i}", 1.0) for i in range(1, n + 1)]
        return out

    def constraints(self, req: InputRequest) -> List[Constraint]:
        cons: List[Constraint] = []
        if req.kind == "waiter_task" and req.model.waiter_attempts >= self.k.max_waiter_attempts:
            cons.append(Constraint("attempt_cap", lambda q, c: c.tag == "wait"))
        if self.rng.random() < self.k.smart:
            if req.kind == "waiter_task":
                best = greedy_task(req)
                cons.append(Constraint("greedy_task", lambda q, c, b=best: c.tag == b, soft=True))
            elif req.kind in ("chef", "take", "serve"):
                cons.append(Constraint("oldest_first", lambda q, c: c.value == 1, soft=True))
            elif req.kind == "happy_hour":
                want = "start" if greedy_happy_hour(req) else "not_now"
                cons.append(Constraint("greedy_happy_hour", lambda q, c, w=want: c.tag == w, soft=True))
            elif req.kind in ("seat", "host"):
                # Seat the customer with the most patience left (keeps the paid average high).
                sats = [o.satisfaction for o in req.options]
                best_i = sats.index(max(sats)) + 1
                cons.append(Constraint("most_patient", lambda q, c, b=best_i: c.value == b, soft=True))
        return cons

    # -- encoding
    def encode(self, value: int, req: InputRequest) -> str:
        if self.rng.random() >= self.k.variant_prob:
            return str(value)
        cls = self._weighted(self.k.variant_weights)
        if cls == "neg_zero" and value != 0:
            cls = "plain"
        self.injected[cls] += 1
        self.injected_at[(cls, req.kind)] += 1
        if cls == "padded":
            return f"  {value}   "
        if cls == "tab":
            return f"\t{value}"
        if cls == "plus_sign":
            return f"+{value}"
        if cls == "leading_zero":
            return f"00{value}"
        if cls == "neg_zero":
            return "-0"
        if cls == "unicode_digit":
            return "".join(chr(0xFF10 + int(d)) for d in str(value))  # fullwidth digits (Unicode Nd)
        return str(value)

    def junk(self, cls: str, req: InputRequest) -> str:
        rng = self.rng
        if cls == "non_numeric":
            return rng.choice(["abc", "x", "wait", "seat", "?", "one", "0x1", "1a"])
        if cls == "out_of_range_high":
            return str(req.hi + rng.randint(1, 50))
        if cls == "negative":
            return str(-rng.randint(1, 99))
        if cls == "overflow":
            return rng.choice(["99999999999", "2147483648", "-2147483649"])
        if cls == "int_max":
            return rng.choice(["2147483647", "-2147483648"])
        if cls == "decimal":
            return rng.choice(["1.0", "0.5", "1e2", "1,0"])
        if cls == "sign_only":
            return rng.choice(["+", "-", "+-1"])
        if cls == "inner_space":
            return "1 2"
        if cls == "blank":
            return rng.choice(["", "   ", "\t"])
        if cls == "comment":
            return rng.choice(["# comment", "  #0", "#"])
        if cls == "non_ascii":
            return rng.choice(["café", "日本", "ü"])
        raise ValueError(cls)

    def _weighted(self, weights: Dict[str, float]) -> str:
        keys = list(weights)
        return self.rng.choices(keys, weights=[weights[k] for k in keys])[0]


# --------------------------------------------------------------------------- stimulus


@dataclass
class Stimulus:
    name: str
    seed: int
    profile: str
    text: str
    injected: Counter = field(default_factory=Counter)
    injected_at: Counter = field(default_factory=Counter)
    file_classes: List[str] = field(default_factory=list)  # crlf / eof / no_final_newline
    annotated: str = ""
    expect: Optional[str] = None  # directed tests: VICTORY / DEFEAT
    expect_fn: Optional[Callable] = None  # directed tests: extra check(transcript) -> [str]


def annotate(lines: List[str], pol: Policy) -> str:
    starts = {idx: turn for turn, idx in pol.turn_marks.items()}
    out: List[str] = []
    for i, line in enumerate(lines):
        if i in starts:
            out.append(f"# Turn {starts[i]}")
        out.append(line)
    return join_script(out)


def generate(spec: StageSpec, seed: int, profile: str, knobs: Optional[Knobs] = None,
             extra_constraints: Sequence[Constraint] = (), name: Optional[str] = None) -> Stimulus:
    rng = random.Random(seed)
    k = knobs or PROFILES[profile]
    pol = Policy(k, rng, extra_constraints)
    res = GameModel(spec, pol).run()
    lines = list(res.consumed)
    file_classes: List[str] = []
    annotated = annotate(lines, pol)
    newline = "\n"
    if rng.random() < k.crlf_prob:
        newline = "\r\n"
        file_classes.append("crlf")
    if lines and rng.random() < k.eof_prob:
        cut = rng.randrange(0, len(lines))
        lines = lines[:cut]
        file_classes.append("eof")
    text = join_script(lines, newline)
    if text and rng.random() < k.no_final_newline_prob:
        text = text[: -len(newline)]
        if text.endswith("\r") or text.endswith("\n") or text == "":
            text += newline  # keep line count unchanged if last line was blank
        else:
            file_classes.append("no_final_newline")
    return Stimulus(name or f"{profile}_s{seed}", seed, profile, text, pol.injected, pol.injected_at,
                    file_classes, annotated)


def with_knobs(base: str, **changes) -> Knobs:
    return replace(PROFILES[base], **changes)
