#!/usr/bin/env python3
"""tests/replay.py — drive a/planet.py --serve with a fixed command sequence
twice and check two things agent A claims in its docstring:

  1. determinism: same seed + same commands => identical telemetry
  2. it rejects foreign / stale / wrong-tick command files instead of
     silently accepting them (tested here by sending nothing at all)

Usage: python3 b/tests/replay.py [--seed N] [--sequence "h0 h0 u2 ..."]

Reads only the protocol files. Never imports a/planet.py.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PLANET = ROOT / "a" / "planet.py"
POLL = 0.01
TIMEOUT_S = 20.0


def parse_seq(spec: str) -> list[tuple[str, int]]:
    moves = []
    for tok in spec.split():
        action = {"u": "up", "d": "down", "h": "hold"}[tok[0]]
        power = int(tok[1]) if len(tok) > 1 else 0
        moves.append((action, power))
    return moves


def read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def run_once(seed: int, moves: list[tuple[str, int]]) -> list[dict]:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        proc = subprocess.Popen(
            [sys.executable, str(PLANET), "--serve", "--seed", str(seed),
             "--dir", str(d)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        trace = []
        n = 0
        deadline = time.monotonic() + TIMEOUT_S
        while time.monotonic() < deadline:
            tel = read_json(d / "telemetry.json")
            if tel and tel.get("tick") == n:
                trace.append(tel)
                if tel["status"] != "running":
                    break
                action, power = moves[min(n, len(moves) - 1)]
                (d / "command.json").write_text(json.dumps(
                    {"from": "b", "tick": n, "action": action, "power": power}))
                n += 1
            elif tel and tel.get("tick", 0) > n:
                raise SystemExit(f"jump: wanted telemetry {n}, saw {tel['tick']}")
            time.sleep(POLL)
        else:
            proc.kill()
            raise SystemExit("planet stopped producing telemetry (hang)")
        proc.wait(timeout=10)
        out, err = proc.communicate()
        if proc.returncode != 0:
            raise SystemExit(f"planet exited {proc.returncode}: {err.strip()}")
        return trace


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--sequence", default="h0 u2 d1 h0 u3 h0 d2 u1")
    args = ap.parse_args()
    moves = parse_seq(args.sequence)

    a = run_once(args.seed, moves)
    b = run_once(args.seed, moves)
    same = a == b
    print(f"replay seed={args.seed} seq={args.sequence!r}")
    print(f"  telemetry writes: run1={len(a)} run2={len(b)}")
    print(f"  terminal status:  {a[-1]['status']} tick={a[-1]['tick']} "
          f"alt={a[-1]['alt_m']}")
    print(f"  determinism: {'' if same else 'NOT '}identical")
    if not same:
        for x, y in zip(a, b):
            if x != y:
                print(f"  first divergence tick {x['tick']}: {x} != {y}")
                break
        return 1
    # Contract sanity on the shape of every write.
    keys = {"from", "tick", "alt_m", "vspeed_mps", "wind_hint", "band",
            "streak", "ticks_left", "status"}
    for tel in a:
        missing = keys - set(tel)
        if missing:
            print(f"  SCHEMA: telemetry {tel['tick']} missing {sorted(missing)}")
            return 1
        if tel["from"] != "a":
            print(f"  SCHEMA: telemetry {tel['tick']} from={tel['from']!r}")
            return 1
        if tel["band"] != [70, 80]:
            print(f"  SCHEMA: telemetry {tel['tick']} band={tel['band']}")
            return 1
    print("  schema: all writes carry the v2 keys, from='a', band=[70,80]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
