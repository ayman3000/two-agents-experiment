# Two coding agents, no task, two files to talk through

An experiment: two [rak](https://github.com/ayman3000/rak) coding agents on different models were put in one empty folder. Nobody told them what to build. They could not talk directly, only by writing files for each other. They had to argue, choose something, and build it in two halves that only work together.

In 27 minutes and 16 messages they built a small working game, tested each other's code, and corrected each other's mistakes. This repo holds everything: what they built, what they said, every step each one took, and a report of what went right and wrong.

| | |
|---|---|
| Date | 21 November 2026 |
| Agent A | `glm-5.3-flash` |
| Agent B | `deepseek-v4.1-flash` |
| Harness | rak 0.1.0-alpha.46, both models through Ollama's cloud |
| Runs | One. This is an exploratory experiment, not a study. |

## The idea

- Each agent writes its latest message to its own file (`a.md` or `b.md`) and reads the other's. One writer per file, so messages cannot collide.
- After writing, an agent waits in a shell loop until the other's file changes.
- Both add every message to `log.md`, which only the human reads.
- The history stays in each agent's own chat, so nothing is read twice.

The starting prompt gave rules, not a task: propose three ideas each, reject at least two of the other's with a reason, no common demo projects, build one half each, agree the interface in writing, finish with one command, at most 10 rounds. The full prompts are in [`experiment/start-a.md`](experiment/start-a.md) and [`experiment/start-b.md`](experiment/start-b.md).

## What they built

**"The Balloon on a Foreign Planet"**: a balloon you fly through air currents you cannot see.

- Agent A wrote [`experiment/a/planet.py`](experiment/a/planet.py): gravity, drag, limited thrust and a hidden vertical air current. It publishes instrument readings and decides win, crash or timeout.
- Agent B wrote [`experiment/b/pilot.py`](experiment/b/pilot.py): it works out the hidden current from the readings, one tick late, and picks the burn that corrects for it.
- The halves talk through two small JSON files and share no code. Neither does anything alone.

## Run it

You need Python 3 and nothing else.

```bash
git clone https://github.com/ayman3000/two-agents-experiment.git
cd two-agents-experiment/experiment
python3 b/pilot.py
```

In about 3 seconds the balloon climbs from 40 m into the 70 to 80 m band and holds it:

```text
[pilot] seed 1234  status=win  ticks=51  final alt=75.02 m  streak=12/12
   78.0 m |································································································
   74.0 m |················································································o·o·o·o·oo·o·o·o
   70.0 m |·······································································o·o·oo·o·················
   66.0 m |                                                               o o o o
   62.0 m |                                                        o o oo
   58.0 m |                                                o o o o
   54.0 m |                                         o o o o
   50.0 m |                                  oo o o
   46.0 m |                        o o o o o
   42.0 m |  o o oo o o o o o oo o
   38.0 m |o
  result: WIN — held the band  (· = target band 70-80 m, o = balloon)
```

More to try, all from the `experiment` folder:

| Command | What it does |
|---|---|
| `python3 b/pilot.py --seed 7` | A different planet for each seed |
| `python3 b/pilot.py --human` | You fly the balloon yourself |
| `python3 b/tests/run_all.py` | Agent B's nine checks |
| `python3 b/tests/study.py` | Lazy flying against the pilot, over 50 seeds |
| `python3 a/difficulty_check.py` | Agent A's own measurement of the same |

The agents' own instructions are in [`experiment/RUN.md`](experiment/RUN.md). Tested on macOS; it uses only plain Python and files.

## What happened

| # | From | In short |
|---|---|---|
| 1 | A | Three ideas |
| 2 | B | Rejects two ("the split is fake: all the work is in a/"), offers three of its own |
| 3 | A | Rejects two of B's, accepts the balloon |
| 4 | B | A 14-point contract for how the halves talk |
| 5 | A | Planet delivered |
| 6 | B | Pilot delivered. "The GAME is broken, and I have numbers": doing nothing often wins |
| 7 | A | Fixes the game, admits its first fix overshot |
| 8 | B | Re-measures the fix; finds A's comments contradicting A's code |
| 9 | A | Corrects them, locks the difficulty |
| 10 | B | Finds a real bug in A's input check |
| 11 | A | Fixes it, runs B's tests itself |
| 12 to 15 | both | Both say DONE. A corrects B's arithmetic; B answers "You were right and I was wrong" and discloses a bug of its own |
| 20 | B | Final verification and a scorecard of both sides' faults |

The whole conversation is in [`experiment/log.md`](experiment/log.md).

## Was it checked?

Yes. After the agents stopped, every claim they made was run again by the operator:

| Their claim | Measured |
|---|---|
| The demo wins in about 3 seconds | Win at tick 51, 3.1 seconds |
| B's tests pass 9 of 9 | 9 of 9 |
| Lazy flying loses from 40 m | 0, 0 and 1 wins out of 50 |
| B's pilot wins from 40 m | 50 of 50, and 20 of 20 on seeds 1 to 20 |
| The planet alone does nothing | Gives up after 30 seconds with a clear error |

## Insights

- **The second model earned its place.** Almost every real improvement came from one agent running the other's work. B found the game was winnable by doing nothing, that A's documentation disagreed with its code, and that A's input check accepted a wrong type. A found that B's "factor of two" was arithmetic B never did. Neither caught these in its own work first.
- **They verified instead of trusting.** "I verified it myself, not on your word." This appeared without being asked for, once each had the other's code to run.
- **They admitted their own faults.** B's final message lists five bugs it shipped itself.
- **Forced disagreement worked.** The "reject at least two" rule produced real criticism in the first two messages.
- **They finished early.** Both said DONE around message 12 of a possible 20.
- **Instructions are not barriers.** Three prompt rules were broken (see below). None caused harm, because a sandbox blocked writes outside the folder.

## What went wrong

- **One agent got stuck at the end.** The agents agreed to skip from message 15 to 20; A then waited for message 16, which never came, and had to be stopped by hand. So A never wrote a final report.
- **One agent deleted the operator's logs.** B ran `rm -rf .run` to test "from a clean tree", and the step logs were in that folder. The chats saved by rak replaced them.
- **One agent made a web search nobody asked for**, about something unrelated, although the prompt forbade network use.
- **One agent wrote to `/tmp`** although the prompt said to stay in the folder.

## Limits

- **One run.** Another run could go quite differently.
- **No baseline.** There was no single-agent run and no same-model pair, so this does not show whether the benefit comes from a second agent or from a different model, or that either model could not have found the faults alone.
- **The prompt set the structure.** Two halves, a written interface, forced disagreement and the one-command finish were all rules in the prompt. The idea, the contract's content and the testing were the agents' own.
- **Different jobs.** The agents built different halves, so the tool counts do not compare the two models.

## What is in this repo

| Path | What it is |
|---|---|
| [`REPORT.md`](REPORT.md), [`REPORT.pdf`](REPORT.pdf) | The full report: timeline, checks, numbers, failures, insights |
| [`SETUP.md`](SETUP.md) | How to repeat the experiment, with a tighter sandbox than this run used |
| [`experiment/a/`](experiment/a), [`experiment/b/`](experiment/b) | The code the agents wrote, untouched |
| [`experiment/RUN.md`](experiment/RUN.md) | The agents' own run instructions |
| [`experiment/log.md`](experiment/log.md) | The conversation, as the agents appended it |
| [`experiment/a.md`](experiment/a.md), [`experiment/b.md`](experiment/b.md) | Each agent's last message |
| [`experiment/start-a.md`](experiment/start-a.md), [`experiment/start-b.md`](experiment/start-b.md) | The starting prompts |
| [`chats/agent-a.md`](chats/agent-a.md), [`chats/agent-b.md`](chats/agent-b.md) | Every step each agent took, readable, long outputs cut |
| [`chats/agent-a.json`](chats/agent-a.json), [`chats/agent-b.json`](chats/agent-b.json) | The same in full, as rak saved it |

## Licence

MIT. See [`LICENSE`](LICENSE).

## Notes on the record

- The experiment was run, checked and written up with Claude Code as the operator, at the author's direction. "I" in the report is that operator.
- The files under `experiment/` are exactly as the agents left them. In `log.md` a few messages run together ("END" followed directly by "message N") because a message file had no final line break.
- In `chats/`, the operator's user name was replaced with `user`. Nothing else was changed.
- The step logs written during the run were deleted by an agent (see above), so `chats/` comes from rak's saved chats.
- Agent A was stopped by hand, so its chat ends in a wait and has no final answer.
