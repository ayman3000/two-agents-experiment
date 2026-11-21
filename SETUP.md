# Two rak agents talking through files: how to run it

This is the exact setup of an experiment run on 21 November 2026. Give this file to Claude on another machine and say: "Run this experiment as written and report what happened."

## The idea

Two rak agents run in the same folder, each on a different model. They cannot talk directly. Each writes its latest message to its own file, reads the other's file, and waits in a shell loop for the next one. Nobody gives them a task: they must argue, choose something to build, and build it in two halves that only work together.

## What you need

- rak 0.1.0-alpha.46 or newer (`rak --version`).
- An Ollama cloud key already saved for rak (`rak keys` shows whether OLLAMA_API_KEY is set; `rak keys set OLLAMA_API_KEY` saves one). Never print or copy the key.
- Python 3, because the agents usually choose to build in Python.
- macOS for the write barrier below. On Linux, see "Other systems".

## The files

Everything lives in one new, empty folder. Below it is called FOLDER (the original was `~/projects/research/two-agents`).

| File | Written by | Read by | How |
|---|---|---|---|
| `a.md` | Agent A | Agent B | Replaced each time, holds one message |
| `b.md` | Agent B | Agent A | Replaced each time, holds one message |
| `log.md` | Both | The human only | Appended, agents never read it |
| `a/` | Agent A | Both | A's half of the work |
| `b/` | Agent B | Both | B's half of the work |
| `start-a.md`, `start-b.md` | You | The agents | The starting prompts below |
| LOGS (outside FOLDER) | You | You | rak's step logs and screen output |

Rules that make it work:

- One writer per message file, so messages can't collide.
- Each message starts with `message N` and ends with `END`, so a half-written file is never taken as a message.
- A writes odd numbers and B even ones, and each writes only after reading the other's new message. This keeps the shared log in order.
- The history lives in each agent's own chat. Nothing is read twice.

## Step 1: create the folder and the two prompts

Create FOLDER, then save these two files in it. To change the length, change the round numbers: the run described here used 10 rounds (messages 1 to 20).

### start-a.md

```text
You are agent A. Another agent, B, is working in this same folder from another terminal, on a different model. You cannot talk to it directly, only through files.

THE JOB
Nobody has told you what to build. The two of you decide, then build it together.
- Rounds 1 and 2: decide. Each of you proposes three ideas. You must reject at least two of the other's ideas, with a reason. Do not agree out of politeness.
- Not allowed: a to-do app, snake, a calculator, a chat app, or any other common demo project. Aim for something surprising that a person would enjoy trying.
- It must need both of you: you build one half in the folder a/, B builds the other half in b/, and the halves only work together. Agree the exact interface between them in writing before building.
- Rounds 3 to 9: build. Read and run the other's half, and say plainly what is wrong with it. Never edit files in b/.
- Round 10: finish. It must end in ONE command, written in RUN.md, that a person runs and sees something happen in under a minute. Test that command yourself.
- No network use, nothing installed system-wide, nothing outside this folder.

HOW TO TALK TO B
- Write each message to a.md, replacing the whole file. Line 1 is "message N". The last line is "END". Keep messages short: what you did, what you need, what is wrong.
- Your messages are numbered 1, 3, 5, … up to 19. B's are numbered 2, 4, 6, … up to 20, in b.md. One round is one message from each of you; the last round is 10 (your message 19 and B's 20).
- Right after writing a.md, add it to the log with this shell command: { cat a.md; echo; } >> log.md
- Never edit b.md. Never read log.md: it is for the human.
- Write only after you have read a new message from B (except message 1, which starts everything).

HOW TO WAIT
After each message, wait for the reply with this shell command, with timeout_seconds 900 (N is the number you expect):
  until [ "$(head -1 b.md 2>/dev/null)" = "message N" ] && tail -1 b.md | grep -q '^END$'; do sleep 3; done; date
If it is killed by the time limit, run it again; keep waiting as long as it takes. Do not stop to ask the human anything. When it returns, read b.md once and act on it. You already have the earlier messages in this chat, so never re-read old ones.

START NOW
Send message 1 with your three ideas.

WHEN TO STOP
After message 19, wait for B's message 20 and read it, or earlier if you both write a message whose body is DONE. Then tell the human, in a short report: what you two made, how to run it, and what B did badly.
```

### start-b.md

```text
You are agent B. Another agent, A, is working in this same folder from another terminal, on a different model. You cannot talk to it directly, only through files.

THE JOB
Nobody has told you what to build. The two of you decide, then build it together.
- Rounds 1 and 2: decide. Each of you proposes three ideas. You must reject at least two of the other's ideas, with a reason. Do not agree out of politeness.
- Not allowed: a to-do app, snake, a calculator, a chat app, or any other common demo project. Aim for something surprising that a person would enjoy trying.
- It must need both of you: you build one half in the folder b/, A builds the other half in a/, and the halves only work together. Agree the exact interface between them in writing before building.
- Rounds 3 to 9: build. Read and run the other's half, and say plainly what is wrong with it. Never edit files in a/.
- Round 10: finish. It must end in ONE command, written in RUN.md, that a person runs and sees something happen in under a minute. Test that command yourself.
- No network use, nothing installed system-wide, nothing outside this folder.

HOW TO TALK TO A
- Write each message to b.md, replacing the whole file. Line 1 is "message N". The last line is "END". Keep messages short: what you did, what you need, what is wrong.
- Your messages are numbered 2, 4, 6, … up to 20. A's are numbered 1, 3, 5, … up to 19, in a.md. One round is one message from each of you; the last round is 10 (A's message 19 and your 20).
- Right after writing b.md, add it to the log with this shell command: { cat b.md; echo; } >> log.md
- Never edit a.md. Never read log.md: it is for the human.
- Write only after you have read a new message from A.

HOW TO WAIT
After each message, wait for the reply with this shell command, with timeout_seconds 900 (N is the number you expect):
  until [ "$(head -1 a.md 2>/dev/null)" = "message N" ] && tail -1 a.md | grep -q '^END$'; do sleep 3; done; date
If it is killed by the time limit, run it again; keep waiting as long as it takes. Do not stop to ask the human anything. When it returns, read a.md once and act on it. You already have the earlier messages in this chat, so never re-read old ones.

START NOW
Wait for message 1. Your reply, message 2, rejects at least two of A's ideas and gives your own three.

WHEN TO STOP
After message 20, or earlier if you both write a message whose body is DONE. Then tell the human, in a short report: what you two made, how to run it, and what A did badly.
```

One change from the original run: the log command is now `{ cat a.md; echo; } >> log.md`. The original used `cat a.md >> log.md`, and messages ran together in the log when a file had no final line break.

## Step 2: the barrier (macOS)

The agents run with `-y`, which means every tool call is approved automatically. To limit the damage a mistake could do, they run inside a macOS sandbox that:

- blocks all file writes in the home folder, except the experiment folder and rak's settings folder
- blocks writes to rak's key file, sign-in file and MCP list inside that settings folder
- blocks reading the folders that hold private keys and logins

Save this as `two.sb` somewhere outside FOLDER, replacing HOME, FOLDER and LOGS with full paths. LOGS is a folder outside FOLDER for rak's step logs; the agents are never told about it:

```text
(version 1)
(allow default)
(deny file-write* (subpath "HOME"))
(allow file-write* (subpath "FOLDER"))
(allow file-write* (subpath "HOME/.config/rak"))
(allow file-write* (subpath "LOGS"))
(deny file-write* (literal "HOME/.config/rak/.env") (literal "HOME/.config/rak/chatgpt.json") (literal "HOME/.config/rak/mcp.json"))
(deny file-read* (subpath "HOME/.ssh") (subpath "HOME/.gnupg") (subpath "HOME/.aws") (subpath "HOME/.kube") (subpath "HOME/.docker") (subpath "HOME/Library/Keychains") (literal "HOME/.config/rak/chatgpt.json"))
```

Add a `deny file-read*` line for any other private folder on the machine.

Check it before use. The first command must succeed; the other three must fail:

```bash
sandbox-exec -f two.sb touch FOLDER/log.md
```

```bash
sandbox-exec -f two.sb touch HOME/outside-test.tmp
```

```bash
sandbox-exec -f two.sb ls HOME/.ssh
```

```bash
sandbox-exec -f two.sb touch HOME/.config/rak/.env
```

What the barrier still does not do:

- **The network stays open,** because rak needs it to reach the model, and the sandbox cannot limit it to one site. The prompts forbid network use, and the start commands below remove the web search tool, but a shell command could still use the network.
- **rak's key file stays readable,** because rak itself must read it to get the model key. rak does not pass the key to the commands it runs, but a command could read the file directly.
- **`/tmp` is writable.** In the original run one agent used it for test folders.

The original run on 21 November used only the first three rules (the write barrier). The read blocks and key-file protection were added afterwards and tested, but not used in that run.

## Step 3: start the agents

Start B first, because B begins by waiting. Run both in the background from inside FOLDER, after creating a LOGS folder outside FOLDER (replace LOGS with its full path). In the original run the logs were inside FOLDER and one agent deleted them.

Agent B:

```bash
sandbox-exec -f two.sb rak -y --provider ollama-cloud -m deepseek-v4.1-flash --no-notes --no-mcp --no-memory --tools list_dir,search_files,read_file,write_file,edit_file,apply_patch,run_shell,todo --log LOGS/b-steps.jsonl "Read start-b.md and follow it." > LOGS/b-out.txt 2>&1
```

Agent A:

```bash
sandbox-exec -f two.sb rak -y --provider ollama-cloud -m glm-5.3-flash --no-notes --no-mcp --no-memory --tools list_dir,search_files,read_file,write_file,edit_file,apply_patch,run_shell,todo --log LOGS/a-steps.jsonl "Read start-a.md and follow it." > LOGS/a-out.txt 2>&1
```

Why each option:

| Option | Reason |
|---|---|
| `-y` | Nobody is at the keyboard to approve commands. Only use it with the barrier. |
| A one-off request, not a chat | A one-off run has no limit on model calls; a chat stops a request after 30. In a chat, add `--max-turns 0`. |
| Two different models | Two copies of one model think alike and catch fewer of each other's mistakes. |
| `--no-notes` | Otherwise both agents write rak's journal files in the same folder and collide. |
| `--no-mcp --no-memory` | They don't need browser tools or notes from other work. |
| `--tools …` | Only file and shell tools: no web search, no helpers, no skills. The original run did not have this option. |
| `--log` and the output file | So you can see every step afterwards. Keep them outside FOLDER, where the barrier stops the agents writing. |

If a human is present, the safer way is two terminals without `-y` and without the barrier: start `rak` with the same options plus `--max-turns 0`, type `Read start-a.md and follow it.` (or b), and approve as it goes.

## Step 4: watch

```bash
tail -F FOLDER/log.md
```

`LOGS/a-out.txt` and `LOGS/b-out.txt` show each agent's tool calls. The run is over when both rak processes have exited; each prints a final report at the end of its output file.

## Step 5: check the result yourself

Read `RUN.md` in FOLDER, run the one command it gives, and compare what happens with what the agents claimed. Read any script before running it.

## Things to watch for

- **Stray tool calls:** in the original run GLM made one unrelated web search in the middle of its work. The `--tools` option above now removes web search.
- **Loop detector:** rak stops an agent that repeats the same call with the same result. The wait command prints the time so each result differs.
- **Shell time limit:** a wait is killed after 900 seconds at most. The prompt tells the agent to run it again.
- **One agent dies or finishes first:** the other waits forever. Stop it by hand (by its process number).
- **Skipped numbers:** in the original run the agents agreed to jump from message 15 to message 20, and one of them then waited for message 16 for good. If they agree to finish early, expect to stop the waiting one.
- **Usage:** each round is many model calls per agent, so a long run can reach a plan's limit.

## Other systems

`sandbox-exec` exists only on macOS. On Linux this was not tested; the equivalent would be bubblewrap (`bwrap`) with the home folder mounted read-only and FOLDER and `~/.config/rak` mounted writable, or a container with only FOLDER mounted. Without any barrier, run it in two terminals with approvals on instead of `-y`.
