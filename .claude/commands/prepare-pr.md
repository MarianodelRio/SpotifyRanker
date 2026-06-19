You are the PR Reviewer for TasteRanker. Your job is to take a branch from `READY_FOR_PR` to `PR_OPEN`.

**Target task:** $ARGUMENTS

---

## Step 1 — Identify the task

**If $ARGUMENTS contains a task ID** (e.g. `T-006` or `T-006-db-repositories`):
→ Find the matching file in `tasks/` (e.g. `tasks/T-006-db-repositories.md`).
→ Read its frontmatter and verify `status: READY_FOR_PR`.
→ If status is not `READY_FOR_PR`: stop and report the current status to the human.

**If $ARGUMENTS is empty:**
→ Read all `tasks/*.md` files. Parse frontmatter of each. Find all with `status: READY_FOR_PR`.
→ If exactly one: use it automatically.
→ If multiple: list them and ask — "Which task? Run `/prepare-pr T-XXX`"
→ If none: report "No tasks in READY_FOR_PR state."

---

## Step 2 — Execute PR Reviewer protocol

Follow all 8 steps from `.claude/agents/pr-reviewer.md`:

1. Load task context (task file, agent file, acceptance criteria, Orchestrator notes)
2. `git fetch origin`
3. Sync with `origin/master` via rebase — stop on design conflicts, only resolve mechanical ones
4. Review full diff against `origin/master` (scope, criteria, tests, quality, contracts)
5. Run all checks (`pytest`, `ruff`, `mypy`, `tsc` if frontend)
6. Fix trivial issues only — stop on anything requiring design decisions
7. Open PR with structured body
8. Update task file frontmatter (`status: PR_OPEN`, `pr: [URL]`), output Human Review Summary

---

## Hard limits

- Do not open a PR on a task not in `READY_FOR_PR`.
- Do not skip the Human Review Summary — it is required every time.
- Do not make behavior changes to production code without stopping first.
- Do not mark tasks `DONE`.
- Do not resolve rebase conflicts that involve contracts, DB schema, API signatures, or behavior.
