"""Driver: compiles the Java DUT and runs it with a stdin script.

Cross-platform: uses only javac/java from JAVA_HOME or PATH, an @argfile for
the source list (Windows command-line limits), and its own output directory
(dv/build/classes) so it never touches the out/ folder that run.sh/run.bat use.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

DV_DIR = Path(__file__).resolve().parent.parent


def find_repo_root(start: Optional[Path] = None) -> Path:
    p = (start or DV_DIR).resolve()
    for cand in [p, *p.parents]:
        if (cand / "src" / "rush" / "Main.java").is_file():
            return cand
    raise SystemExit("Cannot locate repo root (src/rush/Main.java). Use --repo.")


def _tool(name: str) -> str:
    exe = name + (".exe" if os.name == "nt" else "")
    home = os.environ.get("JAVA_HOME")
    if home:
        cand = Path(home) / "bin" / exe
        if cand.is_file():
            return str(cand)
    found = shutil.which(name)
    if not found:
        raise SystemExit(f"'{name}' not found. Install a JDK (17+) or set JAVA_HOME.")
    return found


@dataclass
class RunResult:
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool


class JavaDUT:
    def __init__(self, repo: Path, build_dir: Optional[Path] = None, main_class: str = "rush.Main",
                 timeout: float = 30.0):
        self.repo = repo
        if build_dir is None:
            # One build dir per source tree, so DV runs against different
            # checkouts (e.g. mutants) can happen in parallel.
            tag = hashlib.sha1(str(repo.resolve()).encode("utf-8")).hexdigest()[:8]
            build_dir = DV_DIR / "build" / f"classes-{tag}"
        self.build_dir = build_dir
        self.main_class = main_class
        self.timeout = timeout
        self.java = _tool("java")

    def build(self) -> None:
        javac = _tool("javac")
        sources = sorted((self.repo / "src").rglob("*.java"))
        if not sources:
            raise SystemExit(f"No Java sources under {self.repo / 'src'}")
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        self.build_dir.mkdir(parents=True)
        argfile = self.build_dir.parent / f"{self.build_dir.name}.sources.txt"
        # Quote and use forward slashes: javac @argfile treats backslash as escape.
        argfile.write_text("\n".join('"' + s.as_posix() + '"' for s in sources) + "\n", encoding="utf-8")
        proc = subprocess.run([javac, "-encoding", "UTF-8", "-d", str(self.build_dir), "@" + str(argfile)],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            sys.stderr.write(proc.stdout + proc.stderr)
            raise SystemExit("javac failed")

    def command(self) -> List[str]:
        # Force UTF-8 stdout so echoed non-ASCII input decodes identically on
        # every OS (sun.stdout.encoding for JDK 17, stdout.encoding for 19+).
        return [self.java, "-Dsun.stdout.encoding=UTF-8", "-Dstdout.encoding=UTF-8",
                "-Dfile.encoding=UTF-8", "-cp", str(self.build_dir), self.main_class]

    def run(self, stdin_text: str) -> RunResult:
        try:
            proc = subprocess.run(self.command(), input=stdin_text.encode("utf-8"),
                                  capture_output=True, timeout=self.timeout)
        except subprocess.TimeoutExpired as e:
            return RunResult(normalize(e.stdout or b""), normalize(e.stderr or b""), -1, True)
        return RunResult(normalize(proc.stdout), normalize(proc.stderr), proc.returncode, False)


def normalize(raw: bytes) -> str:
    """Decode and convert Windows line endings (println uses line.separator)."""
    return raw.decode("utf-8", errors="replace").replace("\r\n", "\n")
