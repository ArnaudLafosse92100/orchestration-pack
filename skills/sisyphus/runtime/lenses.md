# Lenses (the user's seven prompts, `SKILL_DIR/lenses/*.md`)

A lens is one of the user's seven phased prompts (derived from Felix Rieseberg's "How to be
more ambitious"), kept close to the original with a minimal agent adaptation at its top and
no role-play opener; `deeper-brief` is the author's own prompt verbatim. You activate a lens
by naming it in a brief: "Apply `<absolute SKILL_DIR>/lenses/<lens>.md`". The agent reads the
file and returns the evidence first, then one condensed section per phase (see Result format
below). A lens you apply yourself (`deeper-brief`, `heist-crew`, or any lens in Hephaestus
mode): read the file and run its phases before acting.

Lenses are part of the routing, not an option: whenever a trigger below holds, the brief names
the lens. Never for a pure location query, a single mechanical edit or a pure conversational
answer.

| Lens (prompt) | Who applies it | Trigger |
| --- | --- | --- |
| `goal-beyond-goal` (1) | `metis` (Prometheus: you, at interview start) | the request names a task but not the outcome it serves; any resume of interrupted work |
| `three-decisions` (2) | `ultrabrain` or `oracle` | several open choices compete and the user must decide; a plan or checkpoint has to end in decisions |
| `experts-toolkit` (3) | every implementation executor (`hephaestus`, `deep`, `bug-hunt`, `ultrabrain`, `refactor-safe`, `visual-engineering`) | any code change beyond a mechanical edit |
| `unreasonable-goal` (4) | `artistry` or `ultrabrain` | only when the user asks for an ambitious target (moonshot, 10x, "unreasonable"); never by default |
| `assumption-breaker` (5) | `metis` or `oracle` before the work; the `bug-hunt` verifier after it | the work rests on beliefs from status docs, plans or earlier agents' reports ("done", "wired", "covered", "caused by"); every resume; before every lane merge; every verification of an implementer's claims |
| `deeper-brief` (6) | you, on your own draft brief | every consequential brief (implementation, review, root cause, decision) before you send it |
| `heist-crew` (7) | you, when composing a wave or a team | multi-disciplinary work whose crew is not obvious from the routing table; its adversary maps to `arch-review` or `momus` |

Outside judge (applies to every lens): never accept a lens result on the agent's own
judgment. It must end with an outside check (test, tool, replay, measurement or independent
reviewer) and its output.

Result format: a lens result starts with the evidence the lead needs (verdict, `path:line`,
commands run with their key output), then the phase sections, condensed. No phase restates the
brief.

Versions: each lens file carries a `Lens version: N` line, and checkpoints name `lens@N`. When a
lens file changes while agents that read it are still running, tell them with `SendMessage` to
re-read it.

In every checkpoint, name the lens each brief carries (or "no lens: <reason>").
