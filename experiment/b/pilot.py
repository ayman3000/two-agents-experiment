#!/usr/bin/env python3
"""pilot.py — AGENT B's half of THE BALLOON ON A FOREIGN PLANET.

I am the pilot. Agent A's a/planet.py holds the hidden atmosphere and
writes telemetry.json; I read it and write command.json. Interface v2
(log message 4) is the contract; nothing here reads a/planet.py's source
or its internals, only the two protocol files.

What my half has to be good at
------------------------------
The published vertical equation is

    dv = (-0.4 + burn - 0.1*v + thermal) * dt

and barometer/vspeed are exact in telemetry, so the thermal term is
*observable* with one tick of lag:

    thermal = (v_N+1 - v_N)/dt + 0.4 - burn_N + 0.1*v_N

So the pilot (a) estimates the hidden thermal, (b) predicts it one tick
ahead, (c) inverts the equation for the burn that realises a desired
acceleration, and (d) quantises that burn onto the reachable ladder
0.25 m/s^2 x {0..3} up or down. Target: hold the band centre for the
12-tick streak.

CLI
---
    python3 b/pilot.py                  # the demo: spawns a/planet.py, flies it
    python3 b/pilot.py --seed 7         # same, different planet
    python3 b/pilot.py --dir /tmp/run   # protocol directory to use
    python3 b/pilot.py --human          # you fly it, one line per tick
    python3 b/pilot.py --quiet          # no per-tick log, just result + trace

Exit codes: 0 the run finished (win or loss), 2 the other half misbehaved.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ---- published contract constants (interface v2) --------------------------
DT = 0.5
TICKS = 120
GRAVITY = 0.4
POWER_STEP = 0.25
DRAG = 0.1
BAND_LO, BAND_HI = 70.0, 80.0
WIN_STREAK = 12
V_CLAMP = 6.0
POLL_HZ = 50              # contract floor is 20 Hz; faster only shortens latency
PARTNER_TIMEOUT_S = 30.0

TELEMETRY = "telemetry.json"
COMMAND = "command.json"

ROOT = Path(__file__).resolve().parent.parent
PLANET = Path(os.environ.get("BALLOON_PLANET", ROOT / "a" / "planet.py"))
RUN_ROOT = ROOT / ".run"

ALT_TARGET = 0.5 * (BAND_LO + BAND_HI)   # 75 m


# ---------------------------------------------------------------------------
# small helpers


def clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def burn_of(action: str, power: int) -> float:
    if action == "up":
        return POWER_STEP * power
    if action == "down":
        return -POWER_STEP * power
    return 0.0


def quantize(burn: float) -> tuple[str, int]:
    """Nearest reachable (action, power) on the 0.25 ladder, with deadband."""
    if abs(burn) < 0.125:
        return ("hold", 0)
    power = int(clamp(round(abs(burn) / POWER_STEP), 1, 3))
    return ("up" if burn > 0 else "down", power)


def write_atomic(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, separators=(",", ":")) + "\n")
    os.replace(tmp, path)


def read_telemetry(path: Path):
    """A telemetry dict written by a/, or None. Rejects anything malformed."""
    try:
        tel = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(tel, dict):
        return None
    if tel.get("from") != "a" or not isinstance(tel.get("tick"), int):
        return None
    for key in ("alt_m", "vspeed_mps", "wind_hint", "streak"):
        if not isinstance(tel.get(key), (int, float)):
            return None
    if tel.get("status") not in ("running", "win", "crashed", "timeout"):
        return None
    return tel


# ---------------------------------------------------------------------------
# The pilot brain: observable-thermal identification + inversion control


class Pilot:
    """Stateless-enough controller: feed it telemetry, get (action, power)."""

    def __init__(self):
        self.obs: list[tuple[int, float]] = []   # (tick, thermal estimate)
        self.last_pred = 0.0
        self.clamped_steps = 0
        self.target = ALT_TARGET                 # centre of the band I'm told about

    # -- identification ----------------------------------------------------
    def note_step(self, tel_prev: dict, tel_now: dict,
                  action: str, power: int) -> None:
        """Recover the thermal that acted between the two telemetry samples."""
        v0, v1 = tel_prev["vspeed_mps"], tel_now["vspeed_mps"]
        if abs(abs(v1) - V_CLAMP) < 1e-6:
            self.clamped_steps += 1        # v saturated: the inverse is unsafe
            return
        th = (v1 - v0) / DT + GRAVITY - burn_of(action, power) + DRAG * v0
        self.obs.append((tel_now["tick"], th))
        del self.obs[:-6]

    def predict_thermal(self) -> float:
        """One-tick-ahead thermal: persistence plus a damped linear trend."""
        if not self.obs:
            return 0.0
        t_last, th_last = self.obs[-1]
        trend = 0.0
        if len(self.obs) >= 2:
            t_prev, th_prev = self.obs[-2]
            step = max(1, t_last - t_prev)
            trend = (th_last - th_prev) / step
        self.last_pred = clamp(th_last + clamp(trend, -0.3, 0.3), -1.8, 1.8)
        return self.last_pred

    # -- control -----------------------------------------------------------
    def decide(self, tel: dict) -> tuple[str, int]:
        band = tel.get("band")
        if isinstance(band, list) and len(band) == 2:
            # The band is A's to publish; fly the middle of what it says.
            self.target = 0.5 * (band[0] + band[1])
        alt, v = tel["alt_m"], tel["vspeed_mps"]
        th = self.predict_thermal()
        err = self.target - alt
        v_des = clamp(1.4 * err, -2.0, 2.0)
        a_des = clamp(2.5 * (v_des - v), -0.9, 0.9)
        burn = a_des + GRAVITY + DRAG * v - th
        return quantize(burn)


# ---------------------------------------------------------------------------
# Rendering


def render_plot(alts: list[float], status: str, width: int = 96,
                rows: int = 12) -> str:
    """Altitude against tick, with the band shaded, as a terminal chart."""
    if not alts:
        return "(no telemetry)"
    lo = min(min(alts), BAND_LO)
    hi = max(max(alts), BAND_HI)
    pad = max(0.5, 0.05 * (hi - lo))
    lo, hi = lo - pad, hi + pad
    grid = [[" "] * width for _ in range(rows)]

    def row_of(alt: float) -> int:
        frac = (alt - lo) / (hi - lo)
        return int(clamp(round(frac * (rows - 1)), 0, rows - 1))

    for r in range(rows):
        alt = lo + (hi - lo) * r / (rows - 1)
        if BAND_LO <= alt <= BAND_HI:
            for c in range(width):
                grid[r][c] = "·"
    for i, alt in enumerate(alts):
        c = int(clamp(round(i * (width - 1) / max(1, len(alts) - 1)),
                      0, width - 1))
        grid[row_of(alt)][c] = "o"
    lines = []
    label_w = 9
    for r in range(rows - 1, -1, -1):
        alt = lo + (hi - lo) * r / (rows - 1)
        lines.append(f"{alt:>7.1f} m |{''.join(grid[r])}")
    lines.append(" " * label_w + "+" + "-" * width)
    lines.append(" " * label_w + " tick 0" + " " * (width - 13) + f"{len(alts) - 1} ")
    verdict = {"win": "WIN — held the band", "crashed": "CRASHED",
               "timeout": "OUT OF TIME — never held the band"}.get(status, status)
    lines.append(f"  result: {verdict}  (· = target band {BAND_LO:.0f}-"
                 f"{BAND_HI:.0f} m, o = balloon)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The protocol loop


class PartnerError(RuntimeError):
    pass


class HumanAbort(RuntimeError):
    """The human stopped giving commands (stdin closed). Not a partner fault."""


def wait_for_telemetry(path: Path, want_tick: int, proc, note: str) -> dict:
    deadline = time.monotonic() + PARTNER_TIMEOUT_S
    while time.monotonic() < deadline:
        tel = read_telemetry(path)
        if tel and tel["tick"] == want_tick:
            return tel
        if tel and tel["tick"] > want_tick:
            # A jumped a tick: it either ignored my command or double-stepped.
            # Waiting longer would silently fly a different run than I logged.
            raise PartnerError(
                f"a/planet.py skipped ahead: it published telemetry "
                f"{tel['tick']} while I was waiting for {want_tick} ({note}). "
                f"The run is out of sync; refusing to continue.")
        if proc is not None and proc.poll() is not None:
            time.sleep(0.2)                      # it may have written and exited
            tel = read_telemetry(path)
            if tel and tel["tick"] == want_tick:
                return tel
            raise PartnerError(
                f"a/planet.py exited (code {proc.returncode}) while I was "
                f"waiting for telemetry {want_tick} ({note}); its stderr is above")
        time.sleep(1.0 / POLL_HZ)
    raise PartnerError(
        f"no telemetry for tick {want_tick} from a/ within "
        f"{PARTNER_TIMEOUT_S:.0f}s ({note}) — the planet half is stuck or gone")


def ask_human(tel: dict) -> tuple[str, int]:
    while True:
        try:
            raw = input(f"tick {tel['tick']:>3}  alt {tel['alt_m']:7.2f} m  "
                        f"v {tel['vspeed_mps']:+5.2f}  streak {tel['streak']:>2}"
                        f"  [u|d|h + power 0-3, e.g. u2] > ").strip().lower()
        except EOFError:
            print()      # the prompt had no newline
            raise HumanAbort("no more commands on stdin")
        if not raw:
            raw = "h0"
        action = {"u": "up", "d": "down", "h": "hold"}.get(raw[0])
        if action is None:
            print("  use u (rise), d (drop) or h (hold), then a power 0-3",
                  file=sys.stderr)
            continue
        power = int(raw[1]) if len(raw) > 1 and raw[1].isdigit() else 0
        if not 0 <= power <= 3:
            print("  power must be 0-3", file=sys.stderr)
            continue
        return action, power


def fly(seed: int, run_dir: Path, human: bool, quiet: bool,
        verbose: bool = False, attach: bool = False) -> int:
    """Fly one run. attach=True uses a planet someone else already started."""
    if not attach and not PLANET.exists():
        print(f"[pilot] FATAL: cannot find the planet half at {PLANET}. "
              f"Both halves are needed: a/planet.py must exist.", file=sys.stderr)
        return 2

    run_dir.mkdir(parents=True, exist_ok=True)
    tel_path, cmd_path = run_dir / TELEMETRY, run_dir / COMMAND
    if attach:
        # A live planet owns this directory. Never delete its files, and let
        # it handle its own stale-command cleanup.
        if read_telemetry(tel_path) is None:
            print(f"[pilot] FATAL: --attach given but no planet half is "
                  f"publishing telemetry in {run_dir}. Start it first:\n"
                  f"  python3 a/planet.py --serve --dir {run_dir}",
                  file=sys.stderr)
            return 2
        child = None
        print(f"[pilot] attaching to the planet half already serving "
              f"{run_dir}", file=sys.stderr)
    else:
        for stale in (tel_path, cmd_path):        # stale files lie about ticks
            try:
                stale.unlink()
            except OSError:
                pass
        child = subprocess.Popen(
            [sys.executable, str(PLANET), "--serve", "--seed", str(seed),
             "--dir", str(run_dir)],
            stdout=subprocess.DEVNULL if quiet else None,
        )
        print(f"[pilot] seed {seed}: flying a/planet.py (pid {child.pid}), "
              f"protocol dir {run_dir}", file=sys.stderr)

    pilot = Pilot()
    alts: list[float] = []
    tel = None
    code = 0
    try:
        tel = wait_for_telemetry(tel_path, 0, child, "start state")
        alts.append(tel["alt_m"])
        if verbose:
            print(f"{'tick':>4} {'action':>6} {'power':>5} {'alt_m':>8} "
                  f"{'v_ms':>6} {'th_pred':>7} {'streak':>6} status")
            print(f"{tel['tick']:>4} {'init':>6} {0:>5} {tel['alt_m']:>8.3f} "
                  f"{tel['vspeed_mps']:>6.3f} {'-':>7} {tel['streak']:>6} "
                  f"{tel['status']}")
        while tel["status"] == "running":
            n = tel["tick"]
            if human:
                action, power = ask_human(tel)
                print(f"{action} {power}")
            else:
                action, power = pilot.decide(tel)
            write_atomic(cmd_path, {"from": "b", "tick": n,
                                    "action": action, "power": power})
            nxt = wait_for_telemetry(tel_path, n + 1, child,
                                     f"after my command {n}")
            pilot.note_step(tel, nxt, action, power)
            tel = nxt
            alts.append(tel["alt_m"])
            if verbose:
                print(f"{tel['tick']:>4} {action:>6} {power:>5} "
                      f"{tel['alt_m']:>8.3f} {tel['vspeed_mps']:>6.3f} "
                      f"{pilot.last_pred:>6.2f} {tel['streak']:>6} "
                      f"{tel['status']}")
            elif not quiet and not human:
                print(f"  tick {tel['tick']:>3}  alt {tel['alt_m']:7.2f}  "
                      f"v {tel['vspeed_mps']:+5.2f}  streak {tel['streak']:>2}  "
                      f"{action}{power}", file=sys.stderr)
    except PartnerError as exc:
        print(f"[pilot] FATAL: {exc}", file=sys.stderr)
        code = 2
    except HumanAbort as exc:
        # Not an error in the other half: the human just stopped flying.
        print(f"\n[pilot] you stopped flying ({exc}) — run aborted at tick "
              f"{tel['tick'] if tel else 0}", file=sys.stderr)
        code = 3
    finally:
        if child is not None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
            if code == 0 and child.returncode not in (0, -15):
                print(f"[pilot] note: planet exited with code "
                      f"{child.returncode}", file=sys.stderr)

    if code != 0:
        # The run did not complete: a chart of the first tick would suggest
        # it did. Say what went wrong and stop.
        return code

    if tel is not None:
        print()
        print(f"[pilot] seed {seed}  status={tel['status']}  "
              f"ticks={tel['tick']}  final alt={tel['alt_m']:.2f} m  "
              f"streak={tel['streak']}/{WIN_STREAK}  "
              f"thermals recovered={len(pilot.obs)}  "
              f"v-clamps={pilot.clamped_steps}")
        print(render_plot(alts, tel["status"]))
    return code


def main() -> int:
    ap = argparse.ArgumentParser(
        description="pilot: fly a balloon through agent A's hidden atmosphere")
    ap.add_argument("--seed", type=int, default=1234,
                    help="planet seed (default 1234)")
    ap.add_argument("--dir", default=None,
                    help="protocol directory (default .run/run-<pid>)")
    ap.add_argument("--human", action="store_true",
                    help="you fly it: one command per tick on stdin")
    ap.add_argument("--quiet", action="store_true",
                    help="no per-tick log; result and chart only")
    ap.add_argument("--verbose", action="store_true",
                    help="per-tick table with my thermal prediction")
    ap.add_argument("--keep", action="store_true",
                    help="keep the protocol directory after the run")
    ap.add_argument("--attach", action="store_true",
                    help="fly a planet half that is ALREADY serving --dir "
                         "(do not spawn one, do not delete its files)")
    args = ap.parse_args()
    if args.attach and not args.dir:
        ap.error("--attach needs --dir: point it at the serving planet's dir")
    run_dir = Path(args.dir) if args.dir else RUN_ROOT / f"run-{os.getpid()}"
    try:
        return fly(args.seed, run_dir, args.human, args.quiet, args.verbose,
                   args.attach)
    except KeyboardInterrupt:
        # Ctrl-C: fly() already terminated the planet half in its finally block.
        print("\n[pilot] interrupted — the planet half was stopped too",
              file=sys.stderr)
        return 130
    finally:
        if not args.keep and not args.dir:
            shutil.rmtree(run_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
