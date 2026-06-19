First, fetch remote branches and extract which tasks are claimed:
```bash
git fetch origin
git branch -r | grep "origin/feature/T-"
```
Extract task IDs from branch names (e.g. `origin/feature/T-006-db-repositories` → T-006).

Read all files in `tasks/*.md`. Parse the frontmatter of each file to extract:
`id`, `phase`, `agent`, `depends_on`, `status`, `branch`, `pr`.

Cross-reference frontmatter with remote branches to detect stale states:
- Branch exists but frontmatter says `TODO` → ⚠️ stale (agent crashed before committing claim)
- Frontmatter says `IN_PROGRESS` but no remote branch exists → ⚠️ stale (agent crashed before push)
Show these in a separate **⚠️ Stale** section — do not count them as available or in-progress.

Then display the current project status in this format:

---

## Status Board — TasteRanker

### ✅ Done
[All tasks with status: DONE — ID, title from heading, PR link if available]

### 🔍 In Review (PR open)
[All tasks with status: PR_OPEN — ID, title, PR URL, assigned agent]

### 🛎 Ready for PR
[All tasks with status: READY_FOR_PR — ID, title, branch, assigned agent]
[For each: append "→ run /prepare-pr T-XXX to open PR"]

### 🔧 In Progress
[All tasks with status: IN_PROGRESS — ID, title, branch, assigned agent]

### 🟢 Available now (can be picked up)
[All tasks with status: TODO, all deps DONE, AND no remote branch origin/feature/T-XXX-* exists]
[For each: ID, title, assigned agent, count of tasks it unblocks]
[Mark ⭐ tasks on the critical path:]
[Critical path: T-001→T-002→T-003→T-004→T-006→T-010→T-018→T-020→T-021→T-022→T-024→T-025→T-026]

### 🔴 Blocked
[All tasks with status: TODO where at least one task in depends_on is not DONE]
[For each: ID, title, blocked by: T-XXX (current status of blocker)]

### ⚠️ Stale (needs human attention)
[Tasks where frontmatter and remote branch state are inconsistent]
[Branch exists but status: TODO → agent crashed before committing claim]
[status: IN_PROGRESS but no remote branch → agent crashed before push]
[For each: ID, title, inconsistency description, suggested fix]

---

## Summary

- Done: X / 34
- Phase 0: X/5 | Phase 1: X/11 | Phase 2: X/10 | Phase 3: X/4 | Phase 4: X/4
- Critical path: next task is T-XXX
- Can start in parallel right now: [list available tasks with non-overlapping agent assignments]

Keep it concise. No implementation. No code. Only what is in the task file frontmatter.
