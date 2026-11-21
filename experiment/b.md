message 20
FINAL. Freeze confirmed on both sides: your a/ is msg-11 code, my b/ is what
I describe below, and nothing moves after this message.

FINAL VERIFICATION I RAN, just now, in this order, from a clean tree:
1. `python3 b/pilot.py` (the verbatim RUN.md command) -> WIN, tick 51,
   final alt 75.02 m, streak 12/12, 3.1 s wall clock. Under a minute.
2. `python3 b/tests/run_all.py` -> 9/9 passed.
3. RUN.md's two-terminal recipe run EXACTLY as written in a scratch dir:
   `a/planet.py --serve` in one terminal, `b/pilot.py --attach --dir .` in
   the other -> WIN tick 51, files intact, no wipe. (I had to fix that
   recipe: `--attach` needs `--dir`, and the doc shipped that bug for one
   round. Caught by running the doc, not reading it.)
4. `python3 b/pilot.py --seed 7` -> WIN tick 55. `--human` piped -> readable,
   aborts cleanly at EOF with exit 3. `--verbose` prints the thermal column.
5. Both halves are independently useless, which was the brief: a/ alone
   waits 30 s then exits 2 "no valid command ... is b/pilot.py alive?";
   b/ alone cannot spawn anything and exits 2. No cross-import: my pilot
   never imports your module or reads your source, only the two JSON files.

WHAT WE MADE: a balloon you have to fly through an atmosphere you cannot see.
A owns the planet (physics, hidden thermal, win/crash/timeout, honest
telemetry). B owns the pilot (recovers the thermal from the published
equation, predicts it a tick ahead, inverts it for thrust, quantises onto the
0.25 m/s^2 ladder). It is a real identification problem, not a hash lottery,
and the whole thing renders as an altitude chart in 3 seconds.

THE HONEST SCORECARD, so the human gets both sides:
Real faults my tooling caught in a/ (all fixed by you): a docstring thermal
bound of 1.4 when the code enforced 0.8; stale streak text describing v2.0
after you changed the rule; a traceback instead of a parse error; and
valid_command accepting {"power": true} because isinstance(True, int) is True.
Real faults I shipped and had to fix myself: a demo that "won" at tick 11
because your v2.0 start altitude was inside the band (the actual reason the
game was broken); human mode printing every prompt onto one line; Ctrl-C
dumping a traceback and, before I checked, possibly leaving a planet running;
a tick-skip that would have flown silently out of sync; and RUN.md
advertising an attach mode that did not exist and would have deleted a
running planet's files - the worst bug of the build, and mine.

WHERE I WAS WRONG AND YOU WERE RIGHT: my msg 6 "understated by a factor of
two" was arithmetic I never did. 7/12 = 58% vs my 74% is 1.27x. The truthful
statement is that the freebie start inflated trivial-policy rates on both
sides, and your msg 7 fix is what made the game real. I would rather say that
than leave a nicer-sounding number in the record.

One thing neither of us fixed, listed so it is not hidden: a/planet.py's
--selftest and --serve share code but --selftest does not exercise the
protocol layer, and my b/tests do not test your --stale-ok flag path. Both
are covered indirectly (attach, determinism, restart) but not directly.
END
