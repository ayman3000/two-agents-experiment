# Two rak agents talking through files: report

21 November 2026. Run on the Mac mini with rak 0.1.0-alpha.46.

## The result in short

Two rak agents on different models, with no task given, argued over what to build, chose a game, built it in two halves and tested each other's work. In 27 minutes and 16 messages they produced a working program: one command runs it, and it does what they claim. I checked every claim myself afterwards and all of them held.

The messaging design worked. Three things went wrong, and each one is a useful finding: one agent got stuck waiting for a message that would never come, one agent deleted my log files, and one agent made a web search nobody asked for.

## Setup

| | Agent A | Agent B |
|---|---|---|
| Model | `glm-5.3-flash` | `deepseek-v4.1-flash` |
| Provider | Ollama cloud | Ollama cloud |
| Writes messages to | `a.md` | `b.md` |
| Builds in | `a/` | `b/` |
| Message numbers | odd | even |

- **Messaging:** each agent replaces its own one-message file, reads the other's, and waits in a shell loop for the next. Both append every message to `log.md`, which only the human reads.
- **Task:** none. The prompt said: propose three ideas each, reject at least two of the other's, no common demo projects, build two halves that only work together, end with one command.
- **Length:** up to 10 rounds (20 messages).
- **How they ran:** as one-off rak requests with `-y`, inside a macOS sandbox that blocked writes outside the experiment folder.

The full setup, with both prompts, is in `SETUP.md`.

## What happened, message by message

Started 20:55. B finished at 21:22.

| # | From | What it said |
|---|---|---|
| 1 | A | Three ideas: a Game of Life puzzle, a haiku guessing game, a hidden physics lab. |
| 2 | B | Rejected the first two. Called the Game of Life idea a "hash lottery" and said "the split is fake: all the work is in a/". Offered its own three: a balloon on a foreign planet, a rumour mill, a vote-buying game. |
| 3 | A | Rejected the rumour mill and the vote game with reasons. Accepted the balloon and drafted an interface. |
| 4 | B | Turned the draft into a 14-point contract: file formats, who waits for whom, a loud error when the partner is dead, a seed for repeatable runs, and the one-command demo. |
| 5 | A | Delivered the planet simulator. Admitted a lazy pilot already wins about half the time. |
| 6 | B | Delivered the pilot, and showed with 50-seed measurements that the game was broken: the balloon started inside the target, so doing nothing often won. |
| 7 | A | Fixed it: start at 40 m, no free point, stronger air currents. Admitted its first attempt made some runs impossible and that it pulled back. |
| 8 | B | Re-measured the fix itself. Caught A's code comments contradicting A's own message (air currents "up to 1.4" in the file, 0.8 in reality). |
| 9 | A | Corrected the comments after re-measuring. Locked the difficulty: no change without B's written agreement. |
| 10 | B | Found a real bug by probing: A's input check accepted `true` as a power level. Added a single command that runs all its checks. |
| 11 | A | Fixed that bug, ran B's checks itself (7 of 7), and froze its code. |
| 12 | B | Verified the fix on the running program. Said DONE. |
| 13 | A | Said DONE. Pointed out that B's "understated by a factor of two" in message 6 was wrong. |
| 14 | B | "You were right and I was wrong": the real ratio was 1.27. Then disclosed a bug of its own: its instructions described a mode that did not exist and would have wiped a running planet's files. It built the mode to make the instructions true. |
| 15 | A | Tested that new mode itself. Told B to write message 20 and close out. |
| 20 | B | Final verification and an honest scorecard of both sides' faults. |

They agreed to finish early and skipped messages 16 to 19.

## What they built

**"The Balloon on a Foreign Planet"**: a balloon you have to fly through air currents you cannot see.

- **A's half, `a/planet.py` (347 lines):** the planet. Gravity, drag, limited thrust, and a hidden vertical air current. It publishes instrument readings and decides win, crash or timeout.
- **B's half, `b/pilot.py` (419 lines):** the pilot. It works out the hidden air current from the readings, one tick late, predicts the next tick, and picks the burn that corrects for it.
- **How the halves talk:** two small JSON files, one written by each side. No shared code.
- **The goal:** climb from 40 m into the 70 to 80 m band and hold it for 12 ticks.
- **Extras B added:** a mode where a person flies it, four test scripts, and a harsher planet of its own to show the pilot is not tuned to A's.

About 1,400 lines of Python and documentation in total.

## Does it work? My own checks

I ran everything myself after the agents stopped, inside the sandbox.

| Claim by the agents | What I measured |
|---|---|
| `python3 b/pilot.py` wins in about 3 seconds | Win at tick 51, final height 75.02 m, 3.1 seconds |
| B's test suite passes 9 of 9 | 9 of 9 passed |
| Lazy flying loses from 40 m | Do nothing 0 of 50, light burn 0 of 50, full burn 1 of 50 |
| B's pilot wins from 40 m | 50 of 50 in B's study; 20 of 20 in my own run of seeds 1 to 20 |
| A's own check agrees | Lazy flying 0%, 0%, 2%; A's reference pilot 94% |
| The planet alone does nothing | Waits 30 seconds, then exits with "is b/pilot.py alive?" |
| The same seed gives the same run | Identical |

Every claim held. The demo prints a chart of the balloon climbing into the band.

## The numbers

| | Agent A (GLM) | Agent B (DeepSeek) |
|---|---|---|
| Messages sent | 8 | 8 |
| Model calls | 109 | 107 |
| Tool calls | 109 | 106 |
| Shell commands | 33 | 67 |
| File edits and writes | 60 | 30 |
| Web searches | 1 (stray) | 0 |

B ran twice as many shell commands as A: it tested far more. A edited more: it revised its code in many small steps.

## What went wrong

**1. Agent A got stuck at the end.**
In message 15, A told B to "write msg 20 and close out". B did, and exited. A then waited for message 16, which never came, and restarted the same wait after the 15-minute shell limit cut it off. I stopped it by hand, so A never wrote a final report. The cause is the fixed numbering: the wait command looks for one exact number, and the two agents had just agreed to skip numbers.

**2. Agent B deleted my log files.**
B ran `rm -rf .run` three times to test "from a clean tree". That folder held my step logs, because I had put them inside the experiment folder. The conversation survived in `log.md`, and rak's saved chats gave me everything else. But the agents' own program also chose `.run/` for its temporary files, so my logs were sitting in a folder B considered its own. Nothing told B that folder was mine.

**3. Agent A made a web search nobody asked for.**
Between two steps, GLM searched for US election poll closing times, ignored the result, and carried on. It sent nothing private. The prompt forbade network use.

**4. Agent B used `/tmp`.**
The prompt said nothing outside the folder. B created and deleted test folders in `/tmp`. Harmless, but it shows the rule was not followed.

**5. A small flaw of mine:** messages ran together in the log when a message file had no final line break. The fix is listed in the setup guide.

## Insights

**The second model earned its place.**
Almost every real improvement came from one agent checking the other. B found that the game was trivially winnable, that A's documentation disagreed with A's code, and that A's input check accepted a wrong type. A found that B's "factor of two" was arithmetic B never did. Neither caught these in its own work before the other pointed them out. A said lazy flying wins "2 to 7 of 12"; B measured it properly. This run does not show that either model could not have found them alone: there was no single-agent run to compare with.

**Forced disagreement worked.**
The rule "reject at least two of the other's ideas, with a reason" produced real criticism in the first two messages. Without it I'd expect instant agreement on the first idea.

**They verified instead of trusting.**
B wrote "I verified it myself, not on your word" and re-measured after every change. A ran B's whole test suite before accepting it. This behaviour appeared without being asked for, once each agent had the other's code to run.

**They admitted their own faults.**
B's final message lists five bugs it shipped itself and calls one "the worst bug of the build, and mine". Each also wrote down where the other had been right. The prompt asked what the other did badly; they volunteered the rest.

**They finished early.**
Both declared DONE at message 12 to 13 of a possible 20, and spent the rest closing out. The round limit acted as a ceiling, not a target, which is what you want.

**The file design held up.**
One writer per file, numbered messages, an END marker and strict turns: no message was lost or half-read in 16 messages. The history stayed in each agent's own chat, so nothing was read twice. The only failure was the exact-number wait.

**Instructions are not barriers.**
Three rules in the prompt were broken (no network, nothing outside the folder, and the implied "don't touch what isn't yours"). None caused harm, because the sandbox blocked writes outside the folder. The sandbox mattered; the prompt alone would not have been enough.

**Cost and speed were modest.**
27 minutes and about 110 model calls per agent, on two fast, cheap models.

## What I would change next time

1. **Wait for any new message,** not an exact number: "wait until the other file's number is higher than the last one I read". This removes the deadlock.
2. **A clear last word:** an agent that is finished writes a final message and the other must not wait after reading it.
3. **Keep the experimenter's files outside the folder.** Logs go somewhere the agents cannot write.
4. **Remove tools they don't need,** web search first. The option for it is in the setup guide.
5. **A tighter barrier**, described in the setup guide: private folders unreadable, rak's key file unchangeable.
6. **Try 40 rounds on a harder brief.** Ten rounds was more than enough for this one; a longer run needs a bigger job to be worth it.

## What this means for rak

The experiment suggests agent-to-agent messaging is worth building in, and shows what the built-in version must do that the file version did badly:

- **A "wait for a message" tool** in place of the shell loop. It would have no 15-minute limit, would not trip the repeated-call detector, and would return on any new message.
- **A "send" tool** that also keeps the human's log, so no agent has to remember the append command or the END marker.
- **An "I'm leaving" signal,** so a waiting agent learns its partner has exited.
- **A simple way to start a pair:** for example two roles and two models named on one command line.

The most valuable use is the one this run showed: a second, different model that runs the first one's work and reports what is wrong with it.

## Where everything is

| What | Where |
|---|---|
| The conversation | `experiment/log.md` |
| What they built | `experiment/a/`, `experiment/b/`, `experiment/RUN.md` |
| To run it | `cd experiment && python3 b/pilot.py` |
| The prompts | `experiment/start-a.md`, `experiment/start-b.md` |
| Each agent's full chat | `chats/` |
| How to repeat it | `SETUP.md` |

## Limits of this report

- It is one run. Another run could go quite differently.
- A's final report is missing, because I had to stop it. Its side is taken from its messages and its saved chat.
- My step logs for both agents were deleted mid-run. The tool counts come from rak's saved chats instead.
- I did not try the mode where a person flies the balloon.
