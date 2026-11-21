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
