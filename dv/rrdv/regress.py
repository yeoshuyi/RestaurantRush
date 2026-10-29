"""Regression: run directed + random tests, check, sample coverage, report."""

from __future__ import annotations

import json
import os
import random
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from . import assertions, monitor, scoreboard, timeline
from .coverage import CoverageDB
from .covergroups import SampleCtx, build_db, sample_all
from .driver import JavaDUT, RunResult
from .model import run_script
from .spec import StageSpec
from .stimulus import PROFILES, Stimulus, generate

# Deterministic profile mix for random seeds (seed % len).
PROFILE_MIX = (["random"] * 7 + ["chaos"] * 5 + ["lazy"] * 3 + ["mostly_greedy"] * 3 + ["greedy"] * 2)


@dataclass
class TestResult:
    name: str
    seed: int
    profile: str
    passed: bool
    errors: List[str] = field(default_factory=list)
    outcome: str = ""
    seconds: float = 0.0
    cov: Optional[CoverageDB] = None


def check(spec: StageSpec, stim: Stimulus, run: RunResult, strict: bool = True) -> TestResult:
    t0 = time.time()
    exp = run_script(spec, stim.text)
    exp_tr = monitor.parse(exp.text)
    act_tr = monitor.parse(run.stdout)
    tl = timeline.build(act_tr)
    errors = scoreboard.compare(exp_tr, act_tr, exp.text, run.stdout, strict=strict)
    errors += assertions.check_all(assertions.Ctx(spec, act_tr, tl, run, run.stdout, exp.eof))
    if stim.expect and (act_tr.result is None or act_tr.result.outcome != stim.expect):
        errors.append(f"DIRECTED expected {stim.expect}, got {act_tr.result.outcome if act_tr.result else None}")
    if stim.expect_fn is not None:
        try:
            errors += [f"DIRECTED {m}" for m in stim.expect_fn(act_tr)]
        except Exception as e:  # a broken DUT can break a check's assumptions; report, don't crash
            errors.append(f"DIRECTED check raised {type(e).__name__}: {e}")
    db, samplers = build_db(spec)
    sample_all(samplers, SampleCtx(spec, act_tr, tl, stim, exp.eof))
    errors += db.violations
    outcome = act_tr.result.outcome if act_tr.result else ("EOF" if exp.eof else "NONE")
    return TestResult(stim.name, stim.seed, stim.profile, not errors, errors, outcome, time.time() - t0, db)


def run_one(dut: JavaDUT, spec: StageSpec, stim: Stimulus, strict: bool = True) -> TestResult:
    t0 = time.time()
    run = dut.run(stim.text)
    res = check(spec, stim, run, strict)
    res.seconds = time.time() - t0
    res._run = run  # type: ignore[attr-defined]
    return res


def save_failure(out: Path, stim: Stimulus, res: TestResult, spec: StageSpec) -> Path:
    d = out / "failures" / res.name
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "input.txt", "w", encoding="utf-8", newline="") as f:
        f.write(stim.text)
    if stim.annotated:
        (d / "input_annotated.txt").write_text(stim.annotated, encoding="utf-8")
    (d / "expected.txt").write_text(run_script(spec, stim.text).text, encoding="utf-8")
    run = getattr(res, "_run", None)
    if run is not None:
        (d / "actual.txt").write_text(run.stdout, encoding="utf-8")
        if run.stderr:
            (d / "stderr.txt").write_text(run.stderr, encoding="utf-8")
    (d / "errors.txt").write_text("\n".join(res.errors) + "\n", encoding="utf-8")
    return d


def write_junit(path: Path, results: List[TestResult]) -> None:
    suite = ET.Element("testsuite", name="rrdv", tests=str(len(results)),
                       failures=str(sum(not r.passed for r in results)))
    for r in results:
        tc = ET.SubElement(suite, "testcase", classname=f"rrdv.{r.profile}", name=r.name, time=f"{r.seconds:.3f}")
        if not r.passed:
            fl = ET.SubElement(tc, "failure", message=r.errors[0][:200] if r.errors else "failed")
            fl.text = "\n".join(r.errors)
    ET.ElementTree(suite).write(str(path), encoding="utf-8", xml_declaration=True)


def build_plan(spec: StageSpec, repo: Path, seeds: int, seed_base: int, directed: bool = True,
               profile: Optional[str] = None) -> List[Stimulus]:
    from .sequences import all_directed
    plan: List[Stimulus] = all_directed(spec, repo) if directed else []
    for seed in range(seed_base, seed_base + seeds):
        prof = profile or PROFILE_MIX[seed % len(PROFILE_MIX)]
        plan.append(generate(spec, seed, prof))
    return plan


def regress(dut: JavaDUT, spec: StageSpec, plan: List[Stimulus], out: Path, jobs: int = 0,
            strict: bool = True, min_cov: float = 100.0, verbose: bool = False) -> int:
    out.mkdir(parents=True, exist_ok=True)
    jobs = jobs or min(8, (os.cpu_count() or 2))
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        results = list(ex.map(lambda s: run_one(dut, spec, s, strict), plan))

    total_db, _ = build_db(spec)
    for r in results:
        total_db.merge(r.cov)
    failures = [r for r in results if not r.passed]
    for stim, r in zip(plan, results):
        if not r.passed:
            save_failure(out, stim, r, spec)

    total_db.write_json(out / "coverage.json")
    (out / "coverage.txt").write_text(total_db.text_report(verbose=True), encoding="utf-8")
    write_junit(out / "junit.xml", results)
    summary = {
        "stage": spec.stage, "tests": len(results), "failures": len(failures),
        "coverage_percent": round(total_db.percent(), 2), "min_cov": min_cov,
        "outcomes": {o: sum(1 for r in results if r.outcome == o) for o in sorted({r.outcome for r in results})},
        "failed": [{"name": r.name, "seed": r.seed, "profile": r.profile, "errors": r.errors[:5]} for r in failures],
        "seconds": round(time.time() - t0, 1),
    }
    (out / "results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    cov_ok = total_db.percent() + 1e-9 >= min_cov
    md = [f"## RestaurantRush DV - stage {spec.stage}", "",
          f"- Tests: **{len(results)}**, failures: **{len(failures)}**",
          f"- Outcomes: {summary['outcomes']}",
          f"- Coverage gate: {total_db.percent():.1f}% (min {min_cov}%) {'PASS' if cov_ok else 'FAIL'}", ""]
    if failures:
        md += ["### Failures", ""] + [f"- `{r.name}` ({r.profile}, seed {r.seed}): {r.errors[0][:200]}"
                                       for r in failures[:20]] + [""]
    md.append(total_db.markdown())
    (out / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as f:
            f.write("\n".join(md) + "\n")

    print(f"Ran {len(results)} tests in {summary['seconds']}s: {len(results) - len(failures)} passed, "
          f"{len(failures)} failed. Outcomes {summary['outcomes']}")
    for r in failures[:10]:
        print(f"  FAIL {r.name} ({r.profile}, seed {r.seed})")
        for e in r.errors[:3]:
            print("     " + e.splitlines()[0][:200])
    print(total_db.text_report(verbose=verbose))
    print(f"Artifacts in {out}")
    if failures:
        return 1
    if not cov_ok:
        print(f"Coverage {total_db.percent():.2f}% below gate {min_cov}%")
        return 2
    return 0


def random_seed_base() -> int:
    return random.SystemRandom().randint(1, 10 ** 6)


__all__ = ["PROFILES", "build_plan", "check", "regress", "run_one", "random_seed_base"]
