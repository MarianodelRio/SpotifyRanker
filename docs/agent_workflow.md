# Agent Workflow — TasteRanker

This document defines the execution model and available development modes.

---

## Primary Workflow — Orchestrator Loop

All implementation work flows through the Orchestrator. See `.claude/agents/orchestrator.md` for the full protocol.

**Task lifecycle:** `TODO → IN_PROGRESS → READY_FOR_PR → PR_OPEN → DONE`

**Summary:**
1. Sync main (`git fetch origin && git pull --ff-only`) — never start on a stale base
2. Read all `tasks/*.md` frontmatter — find tasks where `status: TODO` and all deps are `DONE`
3. Pick the highest-priority available task (maximize unblocked tasks, prefer critical path)
4. Study the task and present a **mandatory human checkpoint** before writing any code
5. After human approval: create branch `feature/T-XXX-slug`, implement, verify, push
6. Update `tasks/T-XXX-slug.md` frontmatter: `status: READY_FOR_PR` — inform human, stop
7. Human decides when to open PR: runs `/prepare-pr T-XXX` → PR Reviewer syncs with main, validates scope and criteria, runs checks, opens PR, outputs Human Review Summary → `status: PR_OPEN`
8. Human reviews summary + PR on GitHub, merges → updates `status: DONE` in task file

Multiple chats can run the Orchestrator in parallel on different tasks simultaneously.

---

## Specialized Modes

These modes handle situations that fall outside the main task-per-branch flow.

### Exploration Mode

**When to use:** The problem is unclear, the design space is open, or you need to evaluate options before committing to an approach. Not needed for tasks already defined in `tasks/`.

**Agents involved:** Architect Agent (leads), domain specialist (optional, read-only)

**Output:**
- Two or more concrete options with trade-offs
- A recommendation with justification
- An ADR in `docs/adr/` if the decision has architectural impact
- No production code

**Example prompt:**
```
[EXPLORATION] How should TasteRanker handle Spotify token expiry during a long import?
Do not write code. Output: options, trade-offs, recommendation, ADR draft if needed.
```

---

### Planning Mode

**When to use:** Before adding a task to `tasks/` that doesn't have a clear implementation path. Turns a feature idea into a concrete, scoped task definition.

**Agents involved:** Planner Agent (leads), Architect Agent (validates contracts)

**Output:**
- Proposed task definition as a new `tasks/T-XXX-slug.md` file (description, acceptance criteria, deps)
- Interface definitions (function signatures, model fields)
- Test plan
- Risks and open questions
- No production code

**Example prompt:**
```
[PLANNING] Plan the evaluation metrics feature (Phase 4).
Output: proposed task definition for task.md, interface definitions, test plan, risks.
No implementation code.
```

---

### Integration Mode

**When to use:** After multiple PRs merge to `master` and a Phase milestone needs to be verified end-to-end.

**Agents involved:** Architect Agent (leads), Reviewer Agent

**Output:**
- All module boundaries verified (no DAG violations)
- Full test suite passes
- TypeScript types consistent with Pydantic models
- Any integration bugs fixed

**Example prompt:**
```
[INTEGRATION] Verify Phase 1 is complete and consistent.
Check: no circular imports, pytest passes, ruff+mypy clean, tsc clean.
Verify E2E flow: login → import → Mi música → play → like.
Report: PASS or list specific failures.
```

---

### Hardening Mode

**When to use:** Before a demo or milestone. Polish and safety pass across all merged code.

**Agents involved:** Reviewer Agent (leads), Testing Agent

**Output:**
- Edge cases handled
- All linting/type checks clean
- README and docs up to date
- Known limitations documented

**Example prompt:**
```
[HARDENING] Prepare for Phase 2 demo.
Review all modules for unhandled edge cases (empty library, no model trained, API failures).
Ensure pytest, ruff, mypy, tsc all pass with zero warnings.
Update README with current setup steps.
```

---

## Agent Coordination Rules

1. **One agent per folder.** Two agents must never edit the same file simultaneously.
2. **Contracts first.** No agent writes module code until `libs/common/models.py` is finalized.
3. **Tests travel with code.** A feature PR without tests is not complete.
4. **Docs travel with code.** API or scoring changes must update the relevant doc in the same PR.
5. **Ask before touching protected files.** `libs/common/models.py`, `libs/common/enums.py`, `db/models.py`.
6. **Report blockers.** If an agent needs a change in another agent's territory, open a discussion — never edit the file directly.

---

## Agent File Index

| Agent | File | Primary Folders | Model |
|-------|------|-----------------|-------|
| Orchestrator | `.claude/agents/orchestrator.md` | All (per task assignment) | claude-sonnet-4-6 |
| PR Reviewer | `.claude/agents/pr-reviewer.md` | READY_FOR_PR tasks only; trivial fixes in authorized folders | claude-sonnet-4-6 |
| Architect | `.claude/agents/architect.md` | `libs/common/` (write), all (read) | claude-sonnet-4-6 |
| Planner | `.claude/agents/planner.md` | Read-only | claude-sonnet-4-6 |
| Backend/API | `.claude/agents/backend-api.md` | `apps/api/`, `libs/spotify/` | claude-sonnet-4-6 |
| Domain Core | `.claude/agents/domain-core.md` | `libs/profile/`, `libs/candidates/`, `libs/playlist/` | claude-sonnet-4-6 |
| ML/Ranking | `.claude/agents/recommendation-ranking.md` | `libs/ml/`, `libs/ranker/`, `models_store/` | claude-sonnet-4-6 |
| Data | `.claude/agents/data-persistence.md` | `db/`, `libs/feedback/` | claude-sonnet-4-6 |
| Frontend | `.claude/agents/frontend.md` | `apps/frontend/` | claude-sonnet-4-6 |
| Testing | `.claude/agents/testing.md` | `tests/` | claude-sonnet-4-6 |
| Reviewer | `.claude/agents/reviewer.md` | Read-only (Integration/Hardening Mode) | claude-sonnet-4-6 |
| Docs | `.claude/agents/docs.md` | `docs/`, `README.md` | claude-sonnet-4-6 |
| DevOps | `.claude/agents/devops.md` | `.github/`, `scripts/`, config files | claude-sonnet-4-6 |
| **Advisor** | `.claude/agents/advisor.md` | Read-only (all), write `docs/adr/` only | **claude-opus-4-8** |

---

## Skills

Skills are invoked via `/skill-name` in the Claude Code CLI or IDE extensions. They are defined as markdown files in `.claude/commands/`.

| Skill | File | Description |
|-------|------|-------------|
| `/orchestrate` | `.claude/commands/orchestrate.md` | Sync main → pick task → human checkpoint → implement → push → mark `READY_FOR_PR` |
| `/prepare-pr [T-XXX]` | `.claude/commands/prepare-pr.md` | Sync branch with master, validate scope and criteria, run checks, open PR, output Human Review Summary |
| `/status` | `.claude/commands/status.md` | Display current status aggregated from all `tasks/*.md` frontmatter |
| `/explore` | `.claude/commands/explore.md` | Design exploration — evaluate options before writing code. Invokes Advisor for architectural questions. |

**Usage:**
- `/orchestrate` — start when you want to implement a task. Syncs main, finds the best available task, consults Advisor if needed, presents a plan for your approval, implements, and stops at `READY_FOR_PR`.
- `/prepare-pr T-XXX` — when you're ready to open a PR for a `READY_FOR_PR` task. The PR Reviewer syncs the branch, validates everything, opens the PR, and gives you a Human Review Summary.
- `/status` — check what's done, in progress, ready for PR, available, or blocked at any point.
- `/explore [topic]` — explore a design question before starting a task or when facing a non-obvious decision mid-implementation.
