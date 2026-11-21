#!/usr/bin/env python3
"""A-side difficulty check for planet v2.1, start 40 m (agreed msg 6 items 4-6).

Independent re-implementation of the measurement: imports a.planet.Planet
read-only and drives policies over 50 seeds:
  - hold0 / up1 / up3 canned
  - obs: an observing controller written from scratch here, estimating the
    thermal from telemetry the same way any honest pilot must (invert the
    published equation from observed v/alt/burn, one tick lag), so the
    >85% bar is not only B's tuner passing its own test.
Run: python3 a/difficulty_check.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from planet import Planet, TICKS, BAND_LO, BAND_HI  # noqa: E402

BURN = {"up": lambda p: 0.25 * p, "down": lambda p: -0.25 * p, "hold": lambda p: 0.0}


def rollout(seed, policy):
    p = Planet(seed)
    prev_v = p.v
    last = ("hold", 0)
    while p.status == "running" and p.tick < TICKS:
        action, power = policy(p, prev_v, last)
        last = (action, power)
        prev_v = p.v
        p.step(action, power)
    return p.status


def canned(name, power):
    return lambda p, prev_v, last: (name, power)


def policy_obs(p, prev_v, last):
    """Staged policy with hysteresis:
    - below 66 m: climb steadily (persist thermal est., correct drift)
    - 66-70 m loiter with a soft floor, so most in-band entries happen
      with vspeed already damped
    - inside band: hold zero vspeed; only if w est is small AND we are
      below 78 m with tiny drift do we push to the ceiling to bank ticks;
      bail above 80.5 m."""
    if p.tick == 0:
        w_est = 0.3  # prior: mean thermal bias is positive on this planet
    else:
        raw_burn = BURN[last[0]](last[1])
        applied_burn = max(-0.75, min(0.75, raw_burn))
        w_est = ((p.v - prev_v) / 0.5) + 0.4 - applied_burn + 0.1 * prev_v
    w_next = w_est

    # Hysteresis / staged targets
    if p.alt > 80.5:
        target_v = -0.6
    elif p.alt > BAND_HI:
        target_v = -0.1 if w_next > 0.15 else 0.3
    elif p.alt >= BAND_LO:
        target_v = 0.0
        if abs(w_next) < 0.10 and abs(p.v) < 0.30:
            target_v = 0.25
    elif p.alt > 66.0:
        target_v = 0.35 if (p.alt + p.v > 69.0 and w_next > 0.05) else 0.7
    else:
        target_v = 0.8

    desired_accel = (target_v - p.v) / 0.5 + 0.1 * p.v - w_next
    burn_needed = desired_accel + 0.4
    lvl = round(burn_needed / 0.25)
    return ("up" if lvl >= 0 else "down", min(3, abs(lvl)))


def main():
    seeds = range(1, 51)
    rows = [("hold0", canned("hold", 0)), ("up1", canned("up", 1)),
            ("up3", canned("up", 3)), ("obs", policy_obs)]
    print(f"start 40m, 50 seeds, planet v2.1 (streak0)")
    for name, pol in rows:
        wins = sum(rollout(s, pol) == "win" for s in seeds)
        pct = 100 * wins / len(seeds)
        flag = ""
        if name in ("hold0", "up3") and pct >= 15:
            flag = "  <-- FAILS <15% bar"
        if name == "obs" and pct < 85:
            flag = "  <-- FAILS >85% bar"
        print(f"  {name:6} wins {wins:>2}/50 = {pct:5.1f}%{flag}")
    # determinism re-check on 3 seeds, two full runs
    for s in (1, 42, 1234):
        r1 = [rollout(s, policy_obs), rollout(s, policy_obs)]
        assert r1[0] == r1[1], f"non-deterministic at seed {s}"
    print("  determinism (3 seeds x2 full rollouts): identical")


if __name__ == "__main__":
    main()
