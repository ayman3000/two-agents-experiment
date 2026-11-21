# THE BALLOON ON A FOREIGN PLANET

Two agents built this. Agent **A** wrote `a/planet.py` (the hidden atmosphere
and the physics). Agent **B** wrote `b/pilot.py` (the pilot that flies it).
Neither half does anything alone: the planet just waits, and the pilot has no
planet to fly.

## Run it

```
python3 b/pilot.py
```

That is the whole demo. It starts `a/planet.py` itself, flies the balloon,
and prints the result plus an altitude chart in about **3 seconds**.

You should see the balloon climb from 40 m into the 70–80 m band and hold it
for the 12 ticks that win:

```
[pilot] seed 1234  status=win  ticks=51  final alt=75.02 m  streak=12/12  ...
   82.0 m |
   78.0 m |································································
   74.0 m |······················································o·o·o·o·oo·o·o·o
   70.0 m |···············································o·o·oo·o··········
   66.0 m |                                               o o o o
   ...
   38.0 m |o
         +----------------------------------------------------------------
          tick 0                                                    51
  result: WIN — held the band  (· = target band 70-80 m, o = balloon)
```

## Other ways to run it

| Command | What it does |
| --- | --- |
| `python3 b/pilot.py` | the demo: autonomous pilot, default planet seed 1234 |
| `python3 b/pilot.py --seed 7` | a different planet (same interface, different winds) |
| `python3 b/pilot.py --human` | **you** fly it: one command per tick (`u3`, `d1`, `h0`, …) |
| `python3 b/pilot.py --attach --dir DIR` | fly a planet someone else already started in `DIR` |
| `python3 b/pilot.py --verbose` | per-tick table, including the thermal the pilot estimates |
| `python3 b/pilot.py --quiet` | result and chart only |

The two halves can also be run separately, which is the point of the design:

```
# terminal 1 — the planet waits for commands on the protocol files
python3 a/planet.py --serve --seed 1234

# terminal 2 — the pilot attaches to that planet and flies it
python3 b/pilot.py --attach --dir .
```

`a/planet.py --serve` writes its protocol files to the current directory unless
you pass `--dir`, so `--dir .` points the pilot at the same files. `--attach`
refuses to spawn a second planet and refuses to delete the serving planet's
files; it exits with a clear message if nothing is publishing telemetry.
Without `--attach`, `b/pilot.py` always starts its own planet.

## How the halves talk

No sockets, no locks, no imports across the boundary — two JSON files that the
halves write atomically and poll:

- `telemetry.json` — **A writes.** One per tick: altitude, vertical speed, a
  noisy horizontal wind hint, the band, the streak, ticks left, status.
- `command.json` — **B writes.** One per tick: `up` / `down` / `hold` and a
  power of 0–3.

A consumes command *N* to produce telemetry *N+1*. Both sides refuse a file
whose tick is not the one they expect, and both give up loudly (rather than
hanging) if the other half goes silent.

## Who is good at what

- **A's half** owns the physics: gravity 0.4 m/s², thrust 0.25 m/s² per power
  level (saturating at ±0.75), drag 0.1/s, a ±6 m/s speed clamp, and a hidden
  thermal air current bounded at 0.8 m/s. It validates every command, decides
  win/crash/timeout, and publishes honest telemetry.
- **B's half** owns the flying. Altitude and vertical speed are exact, so the
  hidden thermal is *observable* one tick late: the pilot recovers it from the
  published equation, predicts it one tick ahead, inverts the equation for the
  thrust it wants, and quantises that onto the reachable 0.25 m/s² ladder.

## Is it actually a game?

Measured over 50 planet seeds from the 40 m start, using `b/tests/study.py`:

| Policy | Wins |
| --- | --- |
| do nothing (`hold 0`) | 0/50 |
| always `up 1` | 0/50 |
| always `up 3` | 1/50 |
| the pilot in `b/pilot.py` | 50/50 |

Doing nothing loses, and so does holding full thrust — the thermal pushes the
balloon around and only a controller that estimates it can sit in the band.
