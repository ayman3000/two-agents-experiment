# How to repeat the experiment

This is the setup exactly as the run of 21 November 2026 was done: the same folder layout, prompts, sandbox and commands. The run had flaws, and they are listed at the end with the changes that would fix them. Those changes were not part of the run.

## What you need

- [rak](https://github.com/ayman3000/rak) 0.1.0-alpha.46 or newer (`rak --version`).
- An Ollama cloud key saved for rak. `rak keys` shows whether `OLLAMA_API_KEY` is set, and `rak keys set OLLAMA_API_KEY` saves one.
- Python 3, because the agents usually choose to build in Python.
- macOS, for the `sandbox-exec` barrier.

## Step 1: an empty folder and the two prompts

Create a new, empty folder. Below it is called FOLDER. Save these two files in it. They are the prompts used in the run, word for word; the same files are in [`experiment/start-a.md`](experiment/start-a.md) and [`experiment/start-b.md`](experiment/start-b.md).

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
- Right after writing a.md, add it to the log with this shell command: cat a.md >> log.md
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
- Right after writing b.md, add it to the log with this shell command: cat b.md >> log.md
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

## Step 2: the barrier

The agents run with `-y`, which approves every tool call automatically. So they were run inside a macOS sandbox that blocks every file write in the home folder except the experiment folder and rak's settings folder (rak saves its chats there).

Save this as `two.sb` outside FOLDER, replacing HOME and FOLDER with full paths:

```text
(version 1)
(allow default)
(deny file-write* (subpath "HOME"))
(allow file-write* (subpath "FOLDER"))
(allow file-write* (subpath "HOME/.config/rak"))
```

Test it before use. The first command must succeed and the second must fail with "Operation not permitted":

```bash
sandbox-exec -f two.sb touch FOLDER/log.md
```

```bash
sandbox-exec -f two.sb touch HOME/outside-test.tmp
```

This barrier blocks writing only. It does not block reading files, and it does not block the network, which the agents need to reach the model.

## Step 3: start the agents

From inside FOLDER, make a folder for the logs:

```bash
mkdir -p .run
```

Start agent B first, because it begins by waiting. Run both in the background, or each in its own terminal.

Agent B:

```bash
sandbox-exec -f two.sb rak -y --provider ollama-cloud -m deepseek-v4.1-flash --no-notes --no-mcp --no-memory --log .run/b-steps.jsonl "Read start-b.md and follow it." > .run/b-out.txt 2>&1
```

Agent A:

```bash
sandbox-exec -f two.sb rak -y --provider ollama-cloud -m glm-5.3-flash --no-notes --no-mcp --no-memory --log .run/a-steps.jsonl "Read start-a.md and follow it." > .run/a-out.txt 2>&1
```

What each part does:

| Part | What it does |
|---|---|
| `sandbox-exec -f two.sb` | Runs everything after it inside the barrier |
| `rak -y` | Starts the agent and approves every tool call. Nobody is at the keyboard, which is why the barrier matters. |
| `--provider ollama-cloud` | Runs the model on Ollama's cloud, with your Ollama key |
| `-m MODEL` | The model: `deepseek-v4.1-flash` for B, `glm-5.3-flash` for A. Two different models catch more of each other's mistakes. |
| `--no-notes` | Stops rak updating its journal files, which both agents would otherwise write in the same folder |
| `--no-mcp` | Doesn't connect your MCP servers |
| `--no-memory` | No notes from earlier rak sessions |
| `--log FILE` | Writes every step the agent takes to a file |
| `"Read start-b.md and follow it."` | The request. Given on the command line, rak does this one job and exits, with no limit on the number of steps. |
| `> FILE 2>&1` | Saves what rak prints to a file |

## Step 4: watch

```bash
tail -F FOLDER/log.md
```

`.run/a-out.txt` and `.run/b-out.txt` show each agent's tool calls as they happen. The run is over when both rak processes have exited.

## Step 5: check the result yourself

Read `RUN.md` in FOLDER, read the scripts, run the one command it gives, and compare what happens with what the agents claimed.

## What went wrong with this setup, and what would fix it

None of the fixes below were part of the run.

| What happened | Cause | Fix |
|---|---|---|
| Agent A waited for good and had to be stopped by hand | The agents agreed to skip from message 15 to 20, but the wait command looks for one exact number | Tell agents to wait for any number higher than the last one read, and that a final message ends the waiting |
| Agent B deleted the step logs | The logs were in `.run/` inside FOLDER, and the agents' own program used `.run/` for temporary files | Keep logs in a folder outside FOLDER, and add one `allow file-write*` rule for it to `two.sb` |
| Agent A made an unrelated web search | The web search tool was available | Add `--tools list_dir,search_files,read_file,write_file,edit_file,apply_patch,run_shell,todo` to both commands |
| Agent B wrote to `/tmp` | The barrier covers only the home folder | Accept it, or add a `deny file-write*` rule for `/private/tmp` |
| Messages ran together in the log | A message file had no final line break | Use `{ cat a.md; echo; } >> log.md` in the prompts |
| Private files stayed readable | The barrier blocks writing only | Add `(deny file-read* (subpath "HOME/.ssh") (subpath "HOME/.gnupg") (subpath "HOME/.aws") (subpath "HOME/Library/Keychains"))`, and `(deny file-write* (literal "HOME/.config/rak/.env"))` so the key file cannot be changed |

Two gaps remain even with those fixes: the network stays open, because rak needs it to reach the model, and rak's own key file stays readable, because rak must read it. Closing them needs a container or a separate user account.

## Other things to expect

- **Usage:** each agent made about 110 model calls in this run.
- **One agent dies or finishes first:** the other waits. Stop it by its process number.
- **Other systems:** `sandbox-exec` exists only on macOS. On Linux the equivalent would be bubblewrap or a container with only FOLDER mounted writable; this was not tested. Without a barrier, start rak in two terminals without `-y`, add `--max-turns 0`, type the request, and approve each step yourself.
