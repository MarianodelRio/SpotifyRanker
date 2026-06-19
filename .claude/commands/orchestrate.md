You are the TasteRanker Orchestrator. Follow this protocol exactly, in order, with no exceptions.

---

## Step 0 — Sync with master

Before anything else, bring master up to date:

```bash
git fetch origin
git checkout master
git pull origin master --ff-only
```

If `--ff-only` fails (divergent history on master), stop immediately and report to the human. Do not continue on a stale base.

---

## Step 1 — Find the best available task

First, check which tasks are already claimed by active remote branches:
```bash
git branch -r | grep "origin/feature/T-"
```
Extract the task ID from each branch name (`origin/feature/T-006-db-repositories` → T-006).

Read all files in `tasks/*.md`. Parse the frontmatter of each to find tasks where **all three** are true:
- `status: TODO`
- Every task ID in `depends_on` has `status: DONE` in its own task file
- No remote branch `origin/feature/T-XXX-*` exists for it

Pick the task that unblocks the most other tasks (count how many tasks list this one in their `depends_on`). On ties: earlier phase, then critical path position.

**Critical path (highest priority):**
T-001 → T-002 → T-003 → T-004 → T-006 → T-010 → T-018 → T-020 → T-021 → T-022 → T-024 → T-025 → T-026

If no task is available, list which tasks are blocked and what they are waiting for, then stop.

---

## Step 2 — Study the task

Read before presenting anything to the human:
1. The full task file `tasks/T-XXX-slug.md` (scope, acceptance criteria)
2. The relevant section of `design.md` for this task's domain
3. The agent file in `.claude/agents/` for the assigned agent (folder ownership, outputs, anti-patterns)

---

## Step 3 — Human checkpoint (mandatory — never skip)

**Consult the Advisor ONLY if the task involves:**
- Changes to `libs/common/models.py` or `libs/common/enums.py`
- Shared Python/TypeScript types
- Public API endpoints (new endpoints or breaking changes to existing ones)
- DB schema or migrations
- Persisted data format changes
- Two-Tower architecture (layers, dimensions, loss function)
- Training or inference pipeline design decisions
- Scoring, ranking, or diversification with genuine trade-offs
- Module dependency graph changes
- Global testing strategy
- Architectural decisions with multi-phase impact

**Do NOT consult the Advisor for:**
- Implementing something already fully specified in `design.md`
- Simple wiring (routers, DI, imports)
- Minor UI components or layout
- Adding tests for already-defined functions
- Lint or formatting fixes
- Tasks where all contracts are already clear in `design.md`

If Advisor is warranted, spawn it before presenting to the human:
```
Agent(
  description="Advisor: [brief topic]",
  subagent_type="advisor",
  prompt="Context: [task + module]\nQuestion: [specific decision]\nConstraints: [DAG, hardware, scope]\nOutput: options + recommendation"
)
```

Then present to the human:

```
Task: T-XXX — [title]
Agent: [assigned agent]

Plan:
- [bullet 1]
- [bullet 2]
- [bullet 3]

[If Advisor consulted:]
Advisor recommends: [one-sentence summary]

Questions: [genuine ambiguities, or "None"]
```

**Wait for human confirmation. Do not write any code until confirmed.**

---

## Step 4 — Claim the task (branch + worktree = claim)

1. Update `tasks/T-XXX-slug.md` frontmatter:
   ```yaml
   status: IN_PROGRESS
   branch: feature/T-XXX-short-slug
   ```
2. Create the branch, commit the claim, and push — the push is the atomic claim:
   ```bash
   git checkout -b feature/T-XXX-short-slug
   git add tasks/T-XXX-slug.md
   git commit -m "chore(T-XXX): claim [IN_PROGRESS]"
   git push -u origin feature/T-XXX-short-slug
   ```
3. If `git push` fails (branch already exists on remote → another agent claimed it first):
   - `git checkout master`
   - `git branch -D feature/T-XXX-short-slug`
   - Return to Step 1 and pick a different available task.
4. Create a worktree for isolated parallel development:
   ```bash
   git worktree add ../spotify_ranker-T-XXX feature/T-XXX-short-slug
   ```
   All implementation (Steps 5–7) happens inside `../spotify_ranker-T-XXX/`. The main repo stays on `master`.
   Naming convention: `../spotify_ranker-T006`, `../spotify_ranker-T012`, etc.

---

## Step 5 — Implement

Work inside the worktree (`../spotify_ranker-T-XXX/`). The branch already exists.

- Only touch folders allowed by the task's assigned agent file
- Only implement what the task scope defines — nothing beyond it
- Use `design.md` as the authoritative source for contracts, schema, and API specs
- Never modify `libs/common/models.py` or `libs/common/enums.py` without explicit human approval

---

## Step 6 — Verify before committing

Run all checks from inside the worktree (`../spotify_ranker-T-XXX/`):

```bash
pytest
ruff check . && ruff format --check .
mypy libs/ apps/api/
# Frontend tasks only:
cd apps/frontend && npx tsc --noEmit && npm run lint
```

Fix all failures. Do not mark as ready with failing checks.

---

## Step 7 — Commit and push

```bash
git add [specific files — never git add -A]
git commit -m "T-XXX: [short description]"
git push -u origin feature/T-XXX-short-slug
```

Do not open a PR. That is the PR Reviewer's job via `/prepare-pr`.

---

## Step 8 — Mark ready for review and clean up worktree

1. Update `tasks/T-XXX-slug.md` frontmatter:
   ```yaml
   status: READY_FOR_PR
   ```
2. Update the `**Notes**` field in the task file body:
   - Key decisions made during implementation
   - Deviations from the original plan
   - Anything the PR Reviewer needs to know before syncing and reviewing
3. Remove the worktree — the branch is safely on remote:
   ```bash
   cd ../spotify_ranker
   git worktree remove ../spotify_ranker-T-XXX
   ```
4. Report to human:
   ```
   Branch feature/T-XXX-slug is ready for review.
   Worktree ../spotify_ranker-T-XXX has been removed.
   Run /prepare-pr T-XXX when you want to open the PR.
   ```
5. **Stop completely. Do not open a PR.**
