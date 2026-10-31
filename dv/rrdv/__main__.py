"""Command line: python -m rrdv <command> (run from dv/), or python dv/dv.py <command>."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .driver import DV_DIR, JavaDUT, find_repo_root
from .spec import get_stage
from .stimulus import PROFILES, Stimulus, generate


def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--stage", type=int, default=3)
    p.add_argument("--repo", type=Path, default=None, help="repo root (default: auto-detect)")
    p.add_argument("--no-build", action="store_true", help="reuse dv/build/classes")
    p.add_argument("--timeout", type=float, default=30.0)
    p.add_argument("--no-strict", action="store_true", help="skip full-transcript text diff")


def _dut(args) -> tuple:
    spec = get_stage(args.stage)
    repo = find_repo_root(args.repo)
    dut = JavaDUT(repo, main_class=spec.main_class, timeout=args.timeout)
    if not args.no_build:
        dut.build()
    return spec, repo, dut


def _report(res, stim: Stimulus, out: Path, spec) -> int:
    from .regress import save_failure
    print(f"{res.name}: {'PASS' if res.passed else 'FAIL'} outcome={res.outcome} ({res.seconds:.2f}s)")
    if not res.passed:
        for e in res.errors[:20]:
            print("  " + e)
        print(f"  artifacts: {save_failure(out, stim, res, spec)}")
    return 0 if res.passed else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="rrdv", description="RestaurantRush constrained-random DV")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("build", help="compile the Java DUT")
    _common(p)

    p = sub.add_parser("run", help="run one random test")
    _common(p)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--profile", choices=sorted(PROFILES), default="random")
    p.add_argument("--out", type=Path, default=DV_DIR / "out")
    p.add_argument("--dump", action="store_true", help="print the generated input script")

    p = sub.add_parser("regress", help="directed + N random seeds, coverage gate")
    _common(p)
    p.add_argument("--seeds", type=int, default=200)
    p.add_argument("--seed-base", type=str, default="1", help="int, or 'random'")
    p.add_argument("--profile", choices=sorted(PROFILES), default=None, help="force one profile")
    p.add_argument("--no-directed", action="store_true")
    p.add_argument("--jobs", type=int, default=0)
    p.add_argument("--min-cov", type=float, default=100.0)
    p.add_argument("--out", type=Path, default=DV_DIR / "out")
    p.add_argument("-v", "--verbose", action="store_true", help="print every bin")

    p = sub.add_parser("replay", help="check an input script (e.g. tests/stage1/victory.txt)")
    _common(p)
    p.add_argument("script", type=Path)
    p.add_argument("--expect", choices=["VICTORY", "DEFEAT"], default=None)
    p.add_argument("--out", type=Path, default=DV_DIR / "out")

    p = sub.add_parser("cov-report", help="pretty-print a coverage.json")
    p.add_argument("json", type=Path)

    args = ap.parse_args(argv)

    if args.cmd == "cov-report":
        import json
        data = json.loads(args.json.read_text(encoding="utf-8"))
        print(f"Coverage {data['percent']}%")
        for g, gd in data["groups"].items():
            print(f"  {g:<22} {gd['hit']}/{gd['total']}")
            for cp, cd in gd["points"].items():
                if cd["holes"]:
                    print(f"      {cp}: holes {cd['holes']}")
        return 0

    spec, repo, dut = _dut(args)
    strict = not args.no_strict

    if args.cmd == "build":
        print(f"Built {repo / 'src'} -> {dut.build_dir}")
        return 0

    from .regress import build_plan, random_seed_base, regress, run_one

    if args.cmd == "run":
        stim = generate(spec, args.seed, args.profile)
        if args.dump:
            sys.stdout.write(stim.annotated)
        res = run_one(dut, spec, stim, strict)
        print(res.cov.text_report())
        return _report(res, stim, args.out, spec)

    if args.cmd == "replay":
        stim = Stimulus(f"replay_{args.script.stem}", 0, "replay",
                        args.script.read_text(encoding="utf-8"), expect=args.expect)
        return _report(run_one(dut, spec, stim, strict), stim, args.out, spec)

    if args.cmd == "regress":
        base = random_seed_base() if args.seed_base == "random" else int(args.seed_base)
        print(f"Stage {spec.stage}: seeds {base}..{base + args.seeds - 1}")
        plan = build_plan(spec, repo, args.seeds, base, not args.no_directed, args.profile)
        return regress(dut, spec, plan, args.out, args.jobs, strict, args.min_cov, args.verbose)
    return 2


if __name__ == "__main__":
    sys.exit(main())
