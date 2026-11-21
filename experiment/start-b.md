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
