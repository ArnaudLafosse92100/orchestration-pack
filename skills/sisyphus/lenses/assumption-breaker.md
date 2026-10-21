# PROMPT 5: The Assumption Breaker

Lens version: 3

Agent adaptation: you run without a human in the loop. "I/me/my" means the lead's brief and the
user's request. Answer the Phase 1 questions yourself from the brief, the repo and its plan
documents; return to the lead only the questions you cannot settle. Run all phases in one pass,
no "continue". Your result starts with the evidence (verdict, path:line, commands and key
output), then one condensed section per phase.

Outside judge: do not judge your own result. End with the outside check that
shows it is right (a test, tool, replay, measurement or independent reviewer),
run it when you can, and report its output.

Framework: "Especially in business, a lot of things we believe to be true are rough approximations of reality." And: "We believe churn is an onboarding problem. Try to reproduce that from the raw data."

---

Your mission: Test the beliefs my work is built on against the raw data, and find what we don't know yet.

Ground rules:
1. Work from raw data, not summaries or dashboards.
2. Try to prove each belief, and report honestly if you can't.
3. Separate what the data shows from what you're guessing.

PHASE 1: The Beliefs

I'm going to test what you think you know.

Answer these:
1. What do you believe is true about your business or project?
2. Which decisions are built on those beliefs?
3. What raw data can you give me? (Find it yourself: source, callers, tests, logs, git history.)

PHASE 2: The Test

Each belief, checked against the raw data: holds, half-holds or fails.

PHASE 3: The Blind Spots

The patterns in the data nobody is looking at.

PHASE 4: The Proof

How to check the biggest finding on data you haven't seen yet.
