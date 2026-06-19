# Parallel Development — TasteRanker

## Task-Per-Branch Model

Each task in `task.md` gets its own branch: `feature/T-XXX-short-slug`. Branches are short-lived — the goal is to open a PR quickly and merge, not accumulate long-running branches.

Multiple orchestrators can run in parallel on different tasks simultaneously, as long as:
- Their tasks have no overlapping folder ownership
- Both tasks have all dependencies marked `DONE` in `task.md`

See `task.md` for the full dependency graph and execution order.

---

## Folder Isolation

Each agent owns exclusive folders. The only shared artifacts are:

| Shared artifact | Who can write | Rule |
|----------------|--------------|------|
| `libs/common/models.py` | Architect only | Frozen after T-002. No agent touches without explicit human approval. |
| `libs/common/enums.py` | Architect only | Same as models.py |
| `db/models.py` | Data Agent | Schema changes require migration. Ask before altering existing columns. |
| `apps/api/main.py` | Backend/API Agent | Router registration only. |
| `pyproject.toml` | Architect → then any agent | Agents append their deps. Merge conflicts resolved linearly. |

Two agents must never edit the same file simultaneously. If you are about to edit a file that another orchestrator could be touching, check the Status Board first.

---

## How to Avoid Merge Conflicts

### Append-only pattern
When multiple agents may need to touch the same file (e.g., `pyproject.toml`, `apps/api/main.py`), use the append-only pattern: add new content at the bottom or in a new section. Conflicts are resolved by manual merge at integration time — they are always straightforward.

### Import discipline
Follow the DAG strictly. If `libs/candidates/` needs something from `libs/profile/`, it imports from `libs.common.models` (the shared contract), not from `libs.profile.builder`. Cross-module imports above `common/` level are architecture violations that will cause test failures.

### No shared mutable state
All modules are stateless — they receive inputs and return outputs. No global state means no race conditions or conflict points between parallel branches.

---

## Integration Verification

After merging any PR to `main`, run the full check before starting the next merge:

```bash
pytest                             # all tests pass
ruff check .                       # no lint errors
mypy libs/ apps/api/               # no type errors
cd apps/frontend && npx tsc --noEmit  # no frontend type errors
```

If a check fails after a merge, stop and fix it before proceeding. A broken `main` blocks all parallel work.

---

## How to Check That a Task's Dependencies Are Truly Done

Before picking a task, verify that its dependencies are not just marked `DONE` in `task.md` but are actually merged into `main`:

```bash
git log --oneline main | head -20   # see what's merged
git diff main..HEAD                 # what your branch adds
```

If a dependency PR is in `PR_OPEN` state but not yet merged, wait or coordinate with the human to merge it first.
