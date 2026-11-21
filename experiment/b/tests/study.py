#!/usr/bin/env python3
"""tests/study.py — difficulty study, read-only.

Runs agent A's planet CLASS (imported, never modified) against canned
policies AND against my own Pilot, over many seeds and several start
altitudes, to answer one question: does the game actually need a pilot?

Usage: python3 b/tests/study.py [--seeds 50]
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "b"))

from pilot import Pilot, BAND_LO, BAND_HI, TICKS  # noqa: E402


def load_planet_module():
    spec = importlib.util.spec_from_file_location("planet_a", ROOT / "a" / "planet.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fly(planet_cls, seed: int, start: float, policy: str):
    """Run one episode. policy = 'h0'|'u3'|'u1'|'pilot'. Returns (status, tick, streak_max)."""
    p = planet_cls(seed)
    p.alt = start
    p.streak = 1 if BAND_LO <= p.alt <= BAND_HI else 0
    pilot = Pilot() if policy == "pilot" else None
    prev = p.telemetry()
    smax = p.streak
    while p.status == "running" and p.tick < TICKS:
        if pilot is None:
            action, power = {"h0": ("hold", 0), "u1": ("up", 1),
                             "u3": ("up", 3)}[policy]
        else:
            action, power = pilot.decide(prev)
        nxt = p.step(action, power)
        if pilot is not None:
            pilot.note_step(prev, nxt, action, power)
        prev = nxt
        smax = max(smax, p.streak)
    return p.status, p.tick, smax


def study(planet_cls, seeds: int, starts: list[float]) -> None:
    policies = ["h0", "u1", "u3", "pilot"]
    print(f"{'start':>6} | " + " | ".join(f"{p:>12}" for p in policies))
    print("-" * (9 + 15 * len(policies)))
    for start in starts:
        row = []
        for pol in policies:
            wins = ticks = smax = 0
            for s in range(1, seeds + 1):
                status, tick, st = fly(planet_cls, s, start, pol)
                if status == "win":
                    wins += 1
                    ticks += tick
                smax += st
            avg = f"{ticks / wins:.0f}" if wins else "-"
            row.append(f"{wins:>2}/{seeds} w@{avg:<3}smax{smax // seeds:>2}")
        print(f"{start:>6.0f} | " + " | ".join(f"{c:>12}" for c in row))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=50)
    a = ap.parse_args()
    planet_cls = load_planet_module().Planet
    print("A's physics, naive canned policies vs my pilot.")
    print("w@N = wins, mean tick of the win. smax = mean best streak reached.")
    print()
    study(planet_cls, a.seeds, [72.0, 60.0, 40.0, 25.0, 10.0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
