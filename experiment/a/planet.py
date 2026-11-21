#!/usr/bin/env python3
"""planet.py — AGENT A's half of THE BALLOON ON A FOREIGN PLANET.

You (agent B, b/pilot.py) pilot a balloon through my hidden atmosphere.
I own the physics and the true wind/thermal field; I publish honest but
sparse telemetry through two JSON files. No sockets, no locks.

File protocol (interface v2, pinned in log message 4):
  telemetry.json  written by me, atomic (tmp+os.replace):
    {"from":"a","tick":int,"alt_m":f3,"vspeed_mps":f3,"wind_hint":f2,
     "band":[70,80],"streak":int,"ticks_left":int,"status":str}
  command.json    written by you, atomic:
    {"from":"b","tick":N,"action":"up"|"down"|"hold","power":0..3}
    power must be a JSON integer (booleans are not integers here); a
    command whose tick or "from" is wrong is ignored until it times out.
  I consume command N to produce telemetry N+1. Telemetry 0 is the
  start state; it is written BEFORE any command is read. By default I
  delete a stale command.json on serve start (--stale-ok skips this).
  I ignore any command.json whose tick != expected or from != "b".

Physics (the published contract, constants exact):
  dt = 0.5 s, 120 ticks (telemetry 0..120). Band [70,80] m.
  Win   = 12 consecutive ticks with alt inside band, all earned:
          streak starts at 0 at tick 0 regardless of start altitude
          (v2.1: no freebie; tick 0's altitude never counts as tick 1
          of the streak). Win earliest possible tick is 12.
  Crash = alt <= 0.
  Timeout = 120 commands used without a win.
  Vertical: dv = (-0.4 + burn - 0.1*v + thermal) * dt, v clamp [-6,6],
  burn = +0.25*power (up) / -0.25*power (down) / 0 (hold), so thrust
  saturates at +-0.75 m/s^2.
  The thermal term is the hidden part of my half: a deterministic,
  bounded (|w| <= 0.8 m/s worst case over seed x tick x altitude;
  measured max 0.759) vertical air current that varies with altitude
  and time. It is real physics, not a lie: it always enters the
  published equation above exactly as written, same seed = same field.
  wind_hint is the HORIZONTAL wind + U(-0.8,+0.8) noise, deterministic
  from (seed, tick); barometer and vspeed exact to 3dp.

CLI:
  python3 a/planet.py --serve  [--seed N] [--dir PATH]
  python3 a/planet.py --selftest [--seed N] [--moves "u3 d2 h0 ..."]
    --selftest runs the same physics on a canned move string
    (tokens: u|d|h + one optional power digit 0-3, malformed tokens
    e.g. "u12" are rejected), repeated to fill 120 ticks, and prints a
    trace to stdout. Writes no protocol files.

Difficulty v2.4 (LOCKED, agreed messages 6-7, acceptance measured by both
sides): start 40.0 m, streak 0 at tick 0, bound |w| <= 0.8 m/s. Acceptance
at 40 m over 50 seeds: canned hold-0 and up-3 each win <15% (measured:
0%, 2% by A's independent check, 0%, 1% by B's study.py); observing pilot
>85% (measured: 94% A's check, 100% B's pilot). Any amp change needs
B's written OK and a fresh joint re-measure.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

DT = 0.5
TICKS = 120
GRAVITY = 0.4
POWER = 0.25
DRAG = 0.1
BAND_LO, BAND_HI = 70.0, 80.0
WIN_STREAK = 12
V_MIN, V_MAX = -6.0, 6.0
START_ALT = 40.0  # below the band: the pilot must climb into it
NOISE = 0.8
POLL_HZ = 20
PARTNER_TIMEOUT_S = 30.0

TELEMETRY = "telemetry.json"
COMMAND = "command.json"


# --------------------------------------------------------------------------
# Deterministic PRNG: mulberry32


def rng_stream(seed: int):
    state = seed & 0xFFFFFFFF

    def nxt() -> float:
        nonlocal state
        state = (state + 0x6D2B79F5) & 0xFFFFFFFF
        t = state
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t ^= t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 2**32

    return nxt


class Planet:
    """Hidden atmosphere + balloon physics. Deterministic in (seed, tick)."""

    def __init__(self, seed: int):
        self.seed = seed
        rng = rng_stream(seed)
        # Hidden thermal field: vertical air velocity w(alt, t).
        # Two smooth modes. Bound |w| <= 0.8 m/s (v2.4, LOCKED): gravity
        # 0.4 and max thrust 0.75 stay the published contract, so the field
        # is fightable but hidden; quantised burns make hovering the skill.
        # Acceptance (msg 6 items 4-6), measured with a/difficulty_check.py
        # (independent observer controller, not B's): 40 m start, 50 seeds,
        # hold0 0%, up1 0%, up3 2% (bar <15%), observing pilot 94% (bar
        # >85%). Do not touch these amps again without B's written OK.
        self.t_amp1 = 0.28 + 0.32 * rng()    # 0.28..0.60 (global mode)
        self.t_amp2 = 0.12 + 0.08 * rng()    # 0.12..0.20 (traveling mode)
        self.t_len = 40.0 + 35.0 * rng()     # altitude wavelength, m
        self.t_per = 30.0 + 55.0 * rng()     # time period, s
        self.w_amp1 = 2.0 + 1.5 * rng()
        self.w_len = 30.0 + 30.0 * rng()
        self.w_p1 = 2 * math.pi * rng()
        self.w_amp2 = 1.0 + 1.0 * rng()
        self.w_per = 20.0 + 25.0 * rng()
        self.w_p2 = 2 * math.pi * rng()
        self.t_p1, self.t_p2 = 2 * math.pi * rng(), 2 * math.pi * rng()
        self.t_len2 = self.t_len / 2.7
        self.t_per2 = self.t_per / 3.1
        self.t_p3, self.t_p4 = 2 * math.pi * rng(), 2 * math.pi * rng()
        self.t_drift = 0.5 * rng()           # slow phase drift, rad/tick
        # Horizontal wind (only this is hinted): shear layers + drift.
        # Balloon state
        self.tick = 0
        self.alt = START_ALT
        self.v = 0.0
        self.streak = 0  # no freebie: streak only counts earned in-band ticks
        self.status = "running"

    # -- hidden field ------------------------------------------------------
    def thermal(self, tick: int, alt: float) -> float:
        t = tick * DT
        ph1 = self.t_p1 + self.t_drift * tick
        w1 = self.t_amp1 * math.sin(2 * math.pi * alt / self.t_len + ph1) \
             * math.cos(2 * math.pi * t / self.t_per + self.t_p2)
        w2 = self.t_amp2 * math.sin(2 * math.pi * alt / self.t_len2 + self.t_p3) \
             * math.sin(2 * math.pi * t / self.t_per2 + self.t_p4)
        return w1 + w2

    def true_wind(self, tick: int, alt: float) -> float:
        t = tick * DT
        u1 = self.w_amp1 * math.sin(2 * math.pi * alt / self.w_len + self.w_p1)
        u2 = self.w_amp2 * math.sin(2 * math.pi * t / self.w_per + self.w_p2)
        return u1 + u2

    def wind_hint(self, tick: int) -> float:
        rng = rng_stream((self.seed * 1000003 + tick * 2654435761) & 0xFFFFFFFF)
        return self.true_wind(tick, self.alt) + (rng() * 2 - 1) * NOISE

    # -- published constants ----------------------------------------------
    def burn(self, action: str, power: int) -> float:
        if action == "up":
            return POWER * power
        if action == "down":
            return -POWER * power
        return 0.0

    # -- one step ----------------------------------------------------------
    def step(self, action: str, power: int) -> dict:
        """Apply command for the current tick, produce next tick's telemetry.
        Raises RuntimeError on win/crash abuse (caller checks status)."""
        th = self.thermal(self.tick, self.alt)
        self.last_thermal = th
        accel = -GRAVITY + self.burn(action, power) - DRAG * self.v + th
        self.v = max(V_MIN, min(V_MAX, self.v + accel * DT))
        self.alt = self.alt + self.v * DT
        self.tick += 1
        if BAND_LO <= self.alt <= BAND_HI:
            self.streak += 1
        else:
            self.streak = 0
        if self.alt <= 0.0:
            self.status = "crashed"
        elif self.streak >= WIN_STREAK:
            self.status = "win"
        elif self.tick >= TICKS:
            self.status = "timeout"
        return self.telemetry()

    def telemetry(self) -> dict:
        return {
            "from": "a",
            "tick": self.tick,
            "alt_m": round(self.alt, 3),
            "vspeed_mps": round(self.v, 3),
            "wind_hint": round(self.wind_hint(self.tick), 2),
            "band": [BAND_LO, BAND_HI],
            "streak": self.streak,
            "ticks_left": TICKS - self.tick,
            "status": self.status,
        }


# --------------------------------------------------------------------------
# Protocol helpers


def write_atomic(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, separators=(",", ":")) + "\n")
    os.replace(tmp, path)


def read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def valid_command(cmd, expect_tick: int) -> bool:
    return (
        isinstance(cmd, dict)
        and cmd.get("from") == "b"
        and type(cmd.get("tick")) is int
        and cmd.get("tick") == expect_tick
        and cmd.get("action") in ("up", "down", "hold")
        and type(cmd.get("power")) is int
        and 0 <= cmd["power"] <= 3
    )


def serve(seed: int, directory: Path, stale_ok: bool = False) -> int:
    directory.mkdir(parents=True, exist_ok=True)
    cmd_path = directory / COMMAND
    tel_path = directory / TELEMETRY
    # Kill any stale command file from an earlier run so we cannot
    # mistake an old tick 0 for this run's. --stale-ok skips this for
    # partners that pre-write command 0 before we boot (then only the
    # tick number and from-field validate the handshake).
    if not stale_ok:
        try:
            cmd_path.unlink()
        except OSError:
            pass

    planet = Planet(seed)
    stderr = sys.stderr
    write_atomic(tel_path, planet.telemetry())
    print(f"[planet] seed={seed} start alt={START_ALT} (band "
          f"[{BAND_LO},{BAND_HI}], streak starts 0)", file=stderr)

    deadline_tick = 0
    while planet.status == "running" and planet.tick < TICKS:
        want = planet.tick  # command N feeds telemetry N+1
        deadline = time.monotonic() + PARTNER_TIMEOUT_S
        cmd = None
        while time.monotonic() < deadline:
            c = read_json(cmd_path)
            if valid_command(c, want):
                cmd = c
                break
            time.sleep(1.0 / POLL_HZ)
        if cmd is None:
            print(f"[planet] FATAL: no valid command for tick {want} "
                  f"within {PARTNER_TIMEOUT_S}s — is b/pilot.py alive?",
                  file=stderr)
            return 2
        planet.step(cmd["action"], cmd["power"])
        write_atomic(tel_path, planet.telemetry())
        if planet.status != "running":
            break

    if planet.status == "running":  # pragma: no cover (loop guarantees)
        planet.status = "timeout"
        write_atomic(tel_path, planet.telemetry())

    tel = read_json(tel_path) or {}
    print(f"[planet] done: status={tel.get('status')} "
          f"tick={tel.get('tick')} alt={tel.get('alt_m')} "
          f"streak={tel.get('streak')} seed={seed}", file=stderr)
    return 0


# --------------------------------------------------------------------------
# Selftest: canned moves, no files


def parse_moves(spec: str):
    moves = []
    for tok in spec.split() or ["h0"]:
        letter, rest = tok[0], tok[1:]
        if rest:
            if not rest.isdigit() or not 0 <= int(rest) <= 3:
                raise ValueError(
                    f"bad move token {tok!r}: power must be a single digit 0-3")
            power = int(rest)
        else:
            power = 0
        action = {"u": "up", "d": "down", "h": "hold"}.get(letter)
        if action is None:
            raise ValueError(f"bad move token {tok!r} (use u|d|h + 0-3)")
        moves.append((action, power))
    return moves or [("hold", 0)]


def selftest(seed: int, moves_spec: str) -> None:
    moves = parse_moves(moves_spec)
    p = Planet(seed)
    print(f"selftest seed={seed} moves={moves_spec!r} "
          f"start alt={p.alt} band=[{BAND_LO},{BAND_HI}]")
    print("tick action power    alt_m   v_ms  hint  thermal streak status")
    print(f"{p.tick:>4} {'init':>6} {0:>5} {p.alt:>8.3f} {p.v:>6.3f} "
          f"{p.wind_hint(0):>6.2f} {p.thermal(0, p.alt):>7.3f} "
          f"{p.streak:>6} {p.status}")
    while p.status == "running" and p.tick < TICKS:
        action, power = moves[min(p.tick, len(moves) - 1)]
        p.step(action, power)
        print(f"{p.tick:>4} {action:>6} {power:>5} {p.alt:>8.3f} {p.v:>6.3f} "
              f"{p.wind_hint(p.tick):>6.2f} "
              f"{p.last_thermal:>7.3f} "
              f"{p.streak:>6} {p.status}")
    print(f"RESULT {p.status} tick={p.tick} alt={p.alt:.3f} "
          f"v={p.v:.3f} streak={p.streak}")


def main() -> int:
    ap = argparse.ArgumentParser(description="planet: hidden atmosphere (A)")
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--dir", default=".", help="protocol file directory")
    ap.add_argument("--moves", default="h0", help="canned moves for selftest")
    ap.add_argument("--stale-ok", action="store_true",
                    help="do NOT delete a pre-existing command.json on boot")
    args = ap.parse_args()
    if args.selftest:
        try:
            selftest(args.seed, args.moves)
        except ValueError as e:
            ap.error(f"--moves: {e}")
        return 0
    if args.serve:
        return serve(args.seed, Path(args.dir), stale_ok=args.stale_ok)
    ap.error("choose --serve or --selftest")


if __name__ == "__main__":
    sys.exit(main())
