Read all files in `tasks/*.md`. Parse the frontmatter of each file to extract:
`id`, `phase`, `agent`, `depends_on`, `status`, `branch`, `pr`.

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
[All tasks with status: TODO where every task in depends_on has status: DONE]
[For each: ID, title, assigned agent, count of tasks it unblocks]
[Mark ⭐ tasks on the critical path:]
[Critical path: T-001→T-002→T-003→T-004→T-006→T-010→T-018→T-020→T-021→T-022→T-024→T-025→T-026]

### 🔴 Blocked
[All tasks with status: TODO where at least one task in depends_on is not DONE]
[For each: ID, title, blocked by: T-XXX (current status of blocker)]

---

## Summary

- Done: X / 34
- Phase 0: X/5 | Phase 1: X/11 | Phase 2: X/10 | Phase 3: X/4 | Phase 4: X/4
- Critical path: next task is T-XXX
- Can start in parallel right now: [list available tasks with non-overlapping agent assignments]

Keep it concise. No implementation. No code. Only what is in the task file frontmatter.
