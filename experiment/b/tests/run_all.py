#!/usr/bin/env python3
"""tests/run_all.py — one entry point for all of B's checks.

    python3 b/tests/run_all.py

Each check prints PASS/FAIL and the script exits non-zero if anything failed.
Nothing here writes to a/.
"""

from __future__ import annotations

import subprocess
import time
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PILOT = ROOT / "b" / "pilot.py"
REPLAY = ROOT / "b" / "tests" / "replay.py"
STUDY = ROOT / "b" / "tests" / "study.py"
FAKE = ROOT / "b" / "tests" / "fake_planet.py"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}{'  — ' + detail if detail else ''}")


def run(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, timeout=300, **kw)


def main() -> int:
    # 1. the demo wins end to end against A's real planet
    with tempfile.TemporaryDirectory() as td:
        p = run([sys.executable, str(PILOT), "--quiet", "--dir", td])
    ok = p.returncode == 0 and "status=win" in p.stdout
    detail = ""
    for line in p.stdout.splitlines():
        if "status=" in line:
            detail = line.strip()
    check("demo wins against a/planet.py", ok, detail)

    # 2. A's protocol is deterministic and schema-clean
    p = run([sys.executable, str(REPLAY)])
    check("a/ determinism + v2 schema", p.returncode == 0,
          next((l.strip() for l in p.stdout.splitlines()
                if "determinism" in l), ""))

    # 3. the game is not winnable by doing nothing (the whole point)
    p = run([sys.executable, str(STUDY), "--seeds", "20"])
    line40 = next((l for l in p.stdout.splitlines() if l.strip().startswith("40 ")), "")
    cols = [c.strip() for c in line40.split("|")[1:]] if line40 else []
    naive_ok = bool(cols) and all(c.startswith("0/20") or c.startswith("1/20")
                                  for c in cols[:3])
    pilot_ok = bool(cols) and cols[3].startswith("20/20")
    check("naive policies lose at 40 m", naive_ok, line40.strip())
    check("pilot wins at 40 m", pilot_ok, "")

    # 4. the pilot is not tuned to A's field: it also flies my harsher planet
    wins = 0
    for seed in (1, 2, 3):
        with tempfile.TemporaryDirectory() as td:
            env = {"BALLOON_PLANET": str(FAKE)}
            p = run([sys.executable, str(PILOT), "--quiet", "--seed", str(seed),
                     "--dir", td], env={**__import__("os").environ, **env})
        wins += "status=win" in p.stdout
    check("pilot wins on an independent planet", wins == 3, f"{wins}/3")

    # 5. --attach flies a planet it did not spawn, and does not delete its files
    with tempfile.TemporaryDirectory() as td:
        planet = subprocess.Popen(
            [sys.executable, str(ROOT / "a" / "planet.py"), "--serve",
             "--seed", "1234", "--dir", td],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.8)
        p = run([sys.executable, str(PILOT), "--attach", "--dir", td, "--quiet"])
        planet.wait(timeout=30)
    check("--attach flies an already-serving planet", "status=win" in p.stdout,
          next((l.strip() for l in p.stdout.splitlines() if "status=" in l), ""))
    with tempfile.TemporaryDirectory() as td:
        p = run([sys.executable, str(PILOT), "--attach", "--dir", td, "--quiet"])
    check("--attach with no planet -> exit 2", p.returncode == 2,
          p.stderr.strip().splitlines()[0] if p.stderr.strip() else "")

    # 6. failure paths are loud, not hangs
    p = run([sys.executable, str(PILOT), "--quiet"], env={
        **__import__("os").environ, "BALLOON_PLANET": "/nonexistent/planet.py"})
    check("missing planet half -> exit 2", p.returncode == 2,
          p.stderr.strip().splitlines()[-1] if p.stderr.strip() else "")

    # 7. A rejects malformed commands and reports it in one line
    p = run([sys.executable, str(ROOT / "a" / "planet.py"), "--selftest",
             "--moves", "u12"])
    one_line = p.returncode != 0 and "Traceback" not in p.stderr
    check("a/ rejects malformed --moves cleanly", one_line,
          p.stderr.strip().splitlines()[-1] if p.stderr.strip() else "")

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
