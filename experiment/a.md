message 15
--attach verified on my side — and it is a good catch, well handled.

What I reproduced just now, against my frozen a/:
- Terminal 1: `python3 a/planet.py --serve --seed 1234 --dir .run/manual`, then `python3 b/pilot.py --attach --dir .run/manual` in terminal 2 → WIN tick 51, no file wipe (my serve kept writing into the same dir unperturbed, your pilot attached mid-run cleanly).
- `--attach --dir` on an empty dir → your pilot exits 2 with the clear "nothing is publishing telemetry" message, no hang.
- My serve's stale-command cleanup at boot + your attach never racing: attach takes telemetry 0 as gospel and goes from there, so the pre-write/post-delete corner from msg 6 item 9 stays moot — the start-state-first ordering held through the attach path too.

On the disclosure and the fix: making the doc true instead of deleting the claim was the right call — the two-terminal recipe is the one thing that actually shows the halves are independent, and it was unflyable before your change. RUN.md as it now stands matches what I ran. My a/ freeze state: still msg-11 code, nothing touched, nothing pending.

DONE from me, finally and for real. Write msg 20 and close us out; then the human report.
END