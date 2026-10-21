# Conductor answers template (`answers.md` on `notes/<topic>-answers`)

The conductor (a cloud session by default; it sees only git) answers a topic lead here. The lead reads it with `git fetch origin notes/<topic>-answers:refs/remotes/origin/notes/<topic>-answers && git show origin/notes/<topic>-answers:answers.md`. The lead cannot see local files, so anything it needs goes into this branch.

## answers.md structure

```
# Answers for <topic> (phase <phase>), <date UTC>
Answers to status of <status commit sha>.

## Answers
1. Q1 (<short restatement of the question>): <answer>. <Why, in one line.>
2. Q2 (...): <answer>.
(One numbered entry per question of "QUESTIONS FOR THE COORDINATOR", same numbers, none skipped. Unknown: say so and give the safest option.)

## Decisions
- <decision taken by the owner or the conductor, one line each, with the scope it covers>

## Dependencies from other topics
- <topic X> branch <branch> is ready at <sha>. Check: git fetch origin "<branch>:refs/remotes/origin/<branch>" && git log --oneline -1 origin/<branch>. Then rebase/continue as follows: <command or step>.
(Leads never talk to each other: this is the only way they learn about other topics.)

## Attached files
- reports/<name>.md : <what it is>. Read: git show origin/notes/<topic>-answers:reports/<name>.md
- mockups/<name>.png : <what it shows>. Read: git show origin/notes/<topic>-answers:mockups/<name>.png > /tmp/<name>.png
(Only files the lead actually needs. Text first; binaries only when indispensable, specific and small, never bulk folders: they stay in repo history forever. Answers are for owner decisions and evidence the cloud cannot see; predictable questions belong in the brief's DEFAULT DECISIONS.)

## Next phase instructions
- Continue / stop after this phase / hand over to a new lead (phase <next>): <instruction>.
- Orders for the remaining work: <ordered list>.
- Still forbidden: <list, e.g. PRs, merges, migrations, deploys>.
```

## Pushing answers with attachments (git plumbing, working tree untouched)

Append to the previous answers commit with `-p`, so history is kept (never `--force` on this branch). Write `${VAR}`, never `$VAR:` in zsh, and quote every variable. `--no-verify`: the pre-push hook checks the main checkout, unrelated to a notes ref.

```bash
B="notes/<topic>-answers"
# first answer: no remote branch yet, the fetch fails quietly and PARENT stays empty
git fetch origin "${B}:refs/remotes/origin/${B}" 2>/dev/null
PARENT=$(git rev-parse --verify -q "refs/remotes/origin/${B}")

# one blob per file
A=$(git hash-object -w answers.md)
R=$(git hash-object -w <local-report.md>)
M=$(git hash-object -w <local-mockup.png>)

# mktree rejects paths with a slash: build one subtree per directory, then the top tree
RT=$(printf "100644 blob %s\t<name>.md\n" "${R}" | git mktree)
MT=$(printf "100644 blob %s\t<name>.png\n" "${M}" | git mktree)
T=$(printf "100644 blob %s\tanswers.md\n040000 tree %s\treports\n040000 tree %s\tmockups\n" "${A}" "${RT}" "${MT}" | git mktree)

# explicit if/else: a "${PARENT:+-p ...}" expansion reaches git as ONE argument in zsh
MSG="docs(notes): answers <topic> <date>"
if [ -n "${PARENT}" ]; then
  C=$(echo "${MSG}" | git commit-tree "${T}" -p "${PARENT}")
else
  C=$(echo "${MSG}" | git commit-tree "${T}")
fi
# never push a refspec with an empty source: an empty ${C} deletes the remote branch
[ -n "${C}" ] && git cat-file -e "${C}^{commit}" || { echo "plumbing failed, nothing pushed"; exit 1; }
# destination written literally (not ${B}): the pack allow rule matches the command text, a variable never matches it
git push --no-verify origin "${C}:refs/heads/notes/<topic>-answers"
```

Rules:
- Only answer statuses of topics YOU launched (listed in your state.md). A push rejected by protection or rules: do not try other names; tell the user in French which ref was rejected and why.
- Never put secrets or `.env` content in answers or attachments (repo history keeps them forever).
- The new tree must contain every file still needed (a tree replaces the previous one): re-list the earlier attachments (rebuild each subtree), drop those no longer needed. Dropped files remain in history.
- Fast-forward push only. If it is rejected, `git fetch` again, rebuild the commit on the new tip.
- Check: `git ls-remote origin "refs/heads/${B}"` equals `${C}`, then `git show "${C}:answers.md" | head`.
- Large binaries: render at the size actually needed, one file per decision, no folders of exports.
