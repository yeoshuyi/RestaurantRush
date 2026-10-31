"""Covergroup registry.

A stage module defines builders decorated with @covergroup(stage=N). A builder
gets (db, spec) and returns a sampler(ctx) -> None.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from ..coverage import CoverageDB
from ..monitor import Transcript
from ..spec import StageSpec
from ..timeline import Timeline

_MODULES = ("stage1", "stage2", "stage3")

Builder = Callable[[CoverageDB, StageSpec], Callable[["SampleCtx"], None]]
_REGISTRY: List[Tuple[int, Builder]] = []


@dataclass
class SampleCtx:
    spec: StageSpec
    tr: Transcript
    tl: Timeline
    stim: Optional[object]  # rrdv.stimulus.Stimulus
    eof: bool


def covergroup(stage: int):
    def deco(fn: Builder) -> Builder:
        _REGISTRY.append((stage, fn))
        return fn
    return deco


def build_db(spec: StageSpec) -> Tuple[CoverageDB, List[Callable[[SampleCtx], None]]]:
    for m in _MODULES:
        importlib.import_module(f"{__name__}.{m}")
    db = CoverageDB()
    samplers = [fn(db, spec) for stage, fn in _REGISTRY if stage <= spec.stage]
    return db, samplers


def sample_all(samplers, ctx: SampleCtx) -> None:
    for s in samplers:
        s(ctx)
