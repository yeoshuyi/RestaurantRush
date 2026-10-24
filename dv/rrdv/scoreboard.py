"""Scoreboard: expected (reference model) vs actual (DUT) comparison.

Two levels:
  * semantic: both transcripts are parsed by the monitor and compared turn by
    turn, field by field, which gives readable mismatch reports;
  * strict (print verification): full text diff after normalisation.
"""

from __future__ import annotations

import difflib
from dataclasses import asdict
from typing import List

from .monitor import Transcript

FIELDS = ("arrivals", "snapshot", "waiter", "chef", "payments", "departures", "end", "input_errors")


def _ascii_fold(s: str) -> str:
    # Non-ASCII junk echoed back may be re-encoded by the console on some
    # platforms; compare it as '?' so it can't cause false mismatches.
    return "".join(ch if ord(ch) < 128 else "?" for ch in s)


def compare(expected: Transcript, actual: Transcript, exp_text: str, act_text: str,
            strict: bool = True, max_diffs: int = 15) -> List[str]:
    errs: List[str] = []
    if len(expected.turns) != len(actual.turns):
        errs.append(f"SB_TURNS: expected {len(expected.turns)} turns, DUT printed {len(actual.turns)}")
    for e, a in zip(expected.turns, actual.turns):
        for f in FIELDS:
            ev, av = getattr(e, f), getattr(a, f)
            ev = asdict(ev) if hasattr(ev, "__dataclass_fields__") else ev
            av = asdict(av) if hasattr(av, "__dataclass_fields__") else av
            if f in ("waiter",):
                ev, av = [asdict(x) for x in e.waiter], [asdict(x) for x in a.waiter]
            if _ascii_fold(repr(ev)) != _ascii_fold(repr(av)):
                errs.append(f"SB_FIELD turn {e.turn} {f}: expected {ev!r} got {av!r}")
                if len(errs) >= max_diffs:
                    return errs
    er = asdict(expected.result) if expected.result else None
    ar = asdict(actual.result) if actual.result else None
    if er != ar:
        errs.append(f"SB_RESULT: expected {er} got {ar}")
    if expected.error_line != actual.error_line:
        errs.append(f"SB_ERROR_LINE: expected {expected.error_line!r} got {actual.error_line!r}")
    if strict:
        el = _ascii_fold(exp_text).splitlines()
        al = _ascii_fold(act_text).splitlines()
        if el != al:
            diff = list(difflib.unified_diff(el, al, "expected(model)", "actual(java)", n=2, lineterm=""))
            errs.append("SB_TEXT: transcript differs:\n" + "\n".join(diff[:60]))
    return errs
