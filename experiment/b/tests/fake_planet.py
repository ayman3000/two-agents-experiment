#!/usr/bin/env python3
"""tests/fake_planet.py — MY OWN planet, for testing my pilot without waiting
on agent A. Same v2 wire protocol, same published equation and constants,
but a *different, harsher* hidden thermal field and a start altitude well
below the band. If my controller only works on A's gentle field, this finds
it before A does.

Deliberately independent: it does not import a/planet.py.

    python3 b/tests/fake_planet.py --serve --seed N --dir D
    python3 b/tests/fake_planet.py --run --seed N     # drive itself with a
                                                      # dumb "hold" policy
Options that A's half does not have, so I can stress my own controller:
    --thermal-amp F   scale on the hidden thermal (default 1.6)
    --start ALT       starting altitude (default 30, i.e. below the band)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

DT, TICKS, GRAVITY, POWER, DRAG = 0.5, 120, 0.4, 0.25, 0.1
BAND_LO, BAND_HI, WIN_STREAK = 70.0, 80.0, 12
V_MIN, V_MAX = -6.0, 6.0
POLL_HZ, PARTNER_TIMEOUT_S = 20.0, 20.0


def rng_stream(seed: int):
    state = (seed * 2654435761 + 1) & 0xFFFFFFFF

    def nxt() -> float:
        nonlocal state
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        return state / 2**32

    return nxt


class FakePlanet:
    def __init__(self, seed: int, start: float = 30.0, amp: float = 1.6):
        r = rng_stream(seed)
        self.seed, self.amp = seed, amp
        # A different shape of field from A's: three modes, faster, mean-free,
        # and one of them advected so it cannot be learned as f(alt) alone.
        self.a1, self.a2, self.a3 = amp * (0.5 + 0.3 * r()), amp * (0.3 + 0.3 * r()), amp * (0.2 + 0.2 * r())
        self.k1, self.k2, self.k3 = 0.11 + 0.08 * r(), 0.31 + 0.2 * r(), 0.07 + 0.05 * r()
        self.o1, self.o2, self.o3 = 6.28 * r(), 6.28 * r(), 6.28 * r()
        self.tick, self.alt, self.v = 0, start, 0.0
        self.streak = 1 if BAND_LO <= self.alt <= BAND_HI else 0
        self.status = "running"

    def thermal(self, tick: int, alt: float) -> float:
        t = tick * DT
        return (self.a1 * math.sin(self.k1 * alt + 0.9 * t + self.o1)
                + self.a2 * math.sin(self.k2 * alt - 1.1 * t + self.o2)
                + self.a3 * math.cos(self.k3 * alt + t + self.o3))

    def step(self, action: str, power: int) -> dict:
        burn = {"up": POWER * power, "down": -POWER * power}.get(action, 0.0)
        th = self.thermal(self.tick, self.alt)
        self.v = max(V_MIN, min(V_MAX, self.v + (-GRAVITY + burn - DRAG * self.v + th) * DT))
        self.alt += self.v * DT
        self.tick += 1
        self.streak = self.streak + 1 if BAND_LO <= self.alt <= BAND_HI else 0
        if self.alt <= 0.0:
            self.status = "crashed"
        elif self.streak >= WIN_STREAK:
            self.status = "win"
        elif self.tick >= TICKS:
            self.status = "timeout"
        return self.tel()

    def tel(self) -> dict:
        return {"from": "a", "tick": self.tick, "alt_m": round(self.alt, 3),
                "vspeed_mps": round(self.v, 3), "wind_hint": 0.0,
                "band": [BAND_LO, BAND_HI], "streak": self.streak,
                "ticks_left": TICKS - self.tick, "status": self.status}


def write_atomic(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, separators=(",", ":")) + "\n")
    os.replace(tmp, path)


def read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def valid(cmd, want: int) -> bool:
    return (isinstance(cmd, dict) and cmd.get("from") == "b"
            and cmd.get("tick") == want
            and cmd.get("action") in ("up", "down", "hold")
            and isinstance(cmd.get("power"), int) and 0 <= cmd["power"] <= 3)


def serve(seed: int, d: Path, start: float, amp: float) -> int:
    d.mkdir(parents=True, exist_ok=True)
    try:
        (d / "command.json").unlink()
    except OSError:
        pass
    p = FakePlanet(seed, start, amp)
    write_atomic(d / "telemetry.json", p.tel())
    while p.status == "running":
        want, cmd = p.tick, None
        deadline = time.monotonic() + PARTNER_TIMEOUT_S
        while time.monotonic() < deadline:
            c = read_json(d / "command.json")
            if valid(c, want):
                cmd = c
                break
            time.sleep(1.0 / POLL_HZ)
        if cmd is None:
            print(f"[fake] FATAL no command for tick {want}", file=sys.stderr)
            return 2
        write_atomic(d / "telemetry.json", p.step(cmd["action"], cmd["power"]))
    print(f"[fake] done status={p.status} tick={p.tick} alt={p.alt:.3f}",
          file=sys.stderr)
    return 0


def run(seed: int, start: float, amp: float) -> None:
    """Drive myself with a dumb policy: hold 0 below band, up 3 inside it."""
    p = FakePlanet(seed, start, amp)
    trace = [p.tel()]
    while p.status == "running":
        action, power = ("hold", 0) if p.alt < BAND_LO else ("up", 3)
        trace.append(p.step(action, power))
    print(f"fake seed={seed} start={start} amp={amp}: {p.status} "
          f"tick={p.tick} alt={p.alt:.3f}")
    for t in trace[:: max(1, len(trace) // 12)]:
        print(f"  tick {t['tick']:>3} alt {t['alt_m']:>8.3f} v {t['vspeed_mps']:>6.3f} "
              f"streak {t['streak']:>2} {t['status']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--dir", default=".")
    ap.add_argument("--start", type=float, default=30.0)
    ap.add_argument("--thermal-amp", type=float, default=1.6)
    a = ap.parse_args()
    if a.serve:
        return serve(a.seed, Path(a.dir), a.start, a.thermal_amp)
    if a.run:
        run(a.seed, a.start, a.thermal_amp)
        return 0
    ap.error("choose --serve or --run")


if __name__ == "__main__":
    sys.exit(main())
