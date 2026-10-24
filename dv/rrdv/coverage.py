"""Small functional-coverage library in the style of SystemVerilog covergroups.

    cg = CoverGroup("cg_waiter", "Waiter task outcomes")
    cp = cg.coverpoint("task", bins=["wait", "seat"], ignore={"x": "why"}, illegal={"y": "why"})
    cx = cg.cross("task_x_outcome", ["seat", "take"], ["ok", "empty"], ignore={("seat", "empty"): "why"})
    cp.sample("seat")

* bins: the values that must each be hit at least once (at_least)
* ignore: values that are allowed but not counted (unreachable by design, with a reason)
* illegal: values that must never happen; sampling one records a violation
* values not declared as a bin, ignore or illegal are also recorded as violations,
  so a coverage model that falls out of date with the DUT can't go unnoticed.

Counts from several runs are merged with CoverageDB.merge(), and reports are written
as text, JSON and Markdown (Markdown goes in the GitHub job summary).
"""

from __future__ import annotations

import itertools
import json
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


def _key(v: Any) -> str:
    if isinstance(v, tuple):
        return " x ".join(str(x) for x in v)
    return str(v)


class CoverPoint:
    def __init__(self, group: "CoverGroup", name: str, bins: Iterable[Any],
                 ignore: Optional[Dict[Any, str]] = None, illegal: Optional[Dict[Any, str]] = None,
                 at_least: int = 1, desc: str = ""):
        self.group = group
        self.name = name
        self.desc = desc
        self.at_least = at_least
        self.bins: Dict[str, int] = {_key(b): 0 for b in bins}
        self.ignore: Dict[str, str] = {_key(k): v for k, v in (ignore or {}).items()}
        self.illegal: Dict[str, str] = {_key(k): v for k, v in (illegal or {}).items()}
        self.ignored_hits: Dict[str, int] = {k: 0 for k in self.ignore}
        for k in list(self.ignore) + list(self.illegal):
            self.bins.pop(k, None)

    @property
    def full(self) -> str:
        return f"{self.group.name}.{self.name}"

    def sample(self, value: Any, where: str = "") -> None:
        k = _key(value)
        if k in self.bins:
            self.bins[k] += 1
        elif k in self.ignore:
            self.ignored_hits[k] += 1
        elif k in self.illegal:
            self.group.db.violations.append(
                f"ILLEGAL_BIN {self.full}={k} ({self.illegal[k]}) {where}".rstrip())
        else:
            self.group.db.violations.append(f"UNDECLARED_BIN {self.full}={k} {where}".rstrip())

    def covered(self) -> Tuple[int, int]:
        hit = sum(1 for c in self.bins.values() if c >= self.at_least)
        return hit, len(self.bins)

    def holes(self) -> List[str]:
        return [k for k, c in self.bins.items() if c < self.at_least]


class CoverGroup:
    def __init__(self, db: "CoverageDB", name: str, desc: str = ""):
        self.db = db
        self.name = name
        self.desc = desc
        self.points: Dict[str, CoverPoint] = {}

    def coverpoint(self, name: str, bins: Iterable[Any], **kw) -> CoverPoint:
        cp = CoverPoint(self, name, bins, **kw)
        self.points[name] = cp
        return cp

    def cross(self, name: str, *axes: Sequence[Any], **kw) -> CoverPoint:
        return self.coverpoint(name, list(itertools.product(*axes)), **kw)

    def __getitem__(self, name: str) -> CoverPoint:
        return self.points[name]

    def covered(self) -> Tuple[int, int]:
        h = t = 0
        for cp in self.points.values():
            a, b = cp.covered()
            h, t = h + a, t + b
        return h, t


class CoverageDB:
    def __init__(self) -> None:
        self.groups: Dict[str, CoverGroup] = {}
        self.violations: List[str] = []

    def group(self, name: str, desc: str = "") -> CoverGroup:
        g = CoverGroup(self, name, desc)
        self.groups[name] = g
        return g

    def __getitem__(self, name: str) -> CoverGroup:
        return self.groups[name]

    # -- merge / persistence
    def counts(self) -> Dict[str, Dict[str, Dict[str, int]]]:
        return {g.name: {cp.name: dict(cp.bins) for cp in g.points.values()} for g in self.groups.values()}

    def merge_counts(self, counts: Dict[str, Dict[str, Dict[str, int]]]) -> None:
        for gname, points in counts.items():
            g = self.groups.get(gname)
            if g is None:
                continue
            for pname, bins in points.items():
                cp = g.points.get(pname)
                if cp is None:
                    continue
                for b, c in bins.items():
                    if b in cp.bins:
                        cp.bins[b] += c

    def merge(self, other: "CoverageDB") -> None:
        self.merge_counts(other.counts())
        for g in other.groups.values():
            mine = self.groups.get(g.name)
            if mine is None:
                continue
            for cp in g.points.values():
                for k, c in cp.ignored_hits.items():
                    mine.points[cp.name].ignored_hits[k] = mine.points[cp.name].ignored_hits.get(k, 0) + c
        self.violations.extend(other.violations)

    # -- metrics
    def covered(self) -> Tuple[int, int]:
        h = t = 0
        for g in self.groups.values():
            a, b = g.covered()
            h, t = h + a, t + b
        return h, t

    def percent(self) -> float:
        h, t = self.covered()
        return 100.0 * h / t if t else 100.0

    # -- reports
    def to_json(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"percent": round(self.percent(), 2), "violations": self.violations, "groups": {}}
        for g in self.groups.values():
            h, t = g.covered()
            out["groups"][g.name] = {
                "desc": g.desc, "hit": h, "total": t,
                "points": {cp.name: {"desc": cp.desc, "bins": cp.bins, "holes": cp.holes(),
                                     "ignore": cp.ignore, "ignored_hits": cp.ignored_hits,
                                     "illegal": cp.illegal}
                           for cp in g.points.values()},
            }
        return out

    def write_json(self, path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_json(), f, indent=2)

    def text_report(self, verbose: bool = False) -> str:
        lines = [f"Functional coverage: {self.percent():.1f}% ({'/'.join(map(str, self.covered()))} bins)"]
        for g in self.groups.values():
            h, t = g.covered()
            pct = 100.0 * h / t if t else 100.0
            lines.append(f"  {g.name:<22} {pct:6.1f}%  {h}/{t}  {g.desc}")
            for cp in g.points.values():
                a, b = cp.covered()
                holes = cp.holes()
                if verbose or holes:
                    lines.append(f"      {cp.name:<26} {a}/{b}" + (f"  holes: {', '.join(holes)}" if holes else ""))
                if verbose:
                    for k, c in cp.bins.items():
                        lines.append(f"          {k:<40} {c}")
                    for k, why in cp.ignore.items():
                        lines.append(f"          {k:<40} ignored ({why})")
        if self.violations:
            lines.append(f"  Coverage violations: {len(self.violations)}")
            lines += ["    " + v for v in self.violations[:20]]
        return "\n".join(lines)

    def markdown(self) -> str:
        h, t = self.covered()
        md = [f"### Functional coverage: {self.percent():.1f}% ({h}/{t} bins)", "",
              "| Covergroup | Coverage | Bins | Holes |", "|---|---:|---:|---|"]
        for g in self.groups.values():
            gh, gt = g.covered()
            holes = [f"`{cp.name}:{x}`" for cp in g.points.values() for x in cp.holes()]
            pct = 100.0 * gh / gt if gt else 100.0
            md.append(f"| {g.name} | {pct:.1f}% | {gh}/{gt} | {' '.join(holes[:8]) or '-'} |")
        if self.violations:
            md += ["", f"**Coverage violations ({len(self.violations)}):**", ""]
            md += [f"- {v}" for v in self.violations[:20]]
        return "\n".join(md)
