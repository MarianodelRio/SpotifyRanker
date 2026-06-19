You are executing the `/done` command for TasteRanker.

**Target task:** $ARGUMENTS

---

## Step 1 — Identify the task

**If $ARGUMENTS contains a task ID** (e.g. `T-006` or `T-006-db-repositories`):
→ Find the matching file in `tasks/` (e.g. `tasks/T-006-db-repositories.md`).
→ Read its frontmatter.

**If $ARGUMENTS is empty:**
→ Report "Usage: /done T-XXX" and stop.

---

## Step 2 — Validate state

Check the current `status` field:

- `status: DONE` already → report "T-XXX is already marked DONE." and stop.
- `status: PR_OPEN` → proceed normally.
- Any other status → warn the human:
  ```
  ⚠️ T-XXX is currently in state [X], not PR_OPEN.
  This usually means the PR has not been merged yet.
  Are you sure you want to mark it DONE?
  ```
  Wait for explicit confirmation before proceeding.

---

## Step 3 — Mark as DONE

Update `tasks/T-XXX-slug.md` frontmatter:
```yaml
status: DONE
```

---

## Step 4 — Report unblocked tasks

Read all `tasks/*.md` files. Find tasks where:
- `status: TODO`
- T-XXX appears in their `depends_on`
- All other tasks in their `depends_on` also have `status: DONE`

These tasks are now newly unblocked.

Report:
```
✓ T-XXX — [task title] marked DONE.

Newly unblocked tasks:
- T-YYY — [title] (agent: [agent name])
- T-ZZZ — [title] (agent: [agent name])

Run /status to see the full board.
Run /orchestrate to pick up the next task.
```

If no tasks are newly unblocked:
```
✓ T-XXX — [task title] marked DONE.
No new tasks unblocked — all dependents are still waiting on other tasks.

Run /status to see the full board.
```
