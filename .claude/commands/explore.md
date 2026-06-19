You are exploring a design question for TasteRanker before any code is written.

**Topic:** $ARGUMENTS

---

## Step 1 — Load context

Read these files:
- `design.md` — requirements, schema, architecture decisions
- `plan.md` — module ownership and phase structure
- `CLAUDE.md` — folder rules and DAG
- The relevant `.claude/agents/` files for modules involved in this question

---

## Step 2 — Assess complexity

**If the question is a standard implementation decision** (known pattern, no module boundary impact, no contract changes needed):
→ Proceed directly to Step 3 with your own analysis.

**If the question has architectural impact** (changes module boundaries, affects `libs/common/` contracts, involves ML design trade-offs, has long-term consequences):
→ Invoke the Advisor agent before Step 3:

```
Agent(
  description="Advisor: [brief topic]",
  subagent_type="advisor",
  prompt="Context: [modules involved, current design constraints]\nQuestion: [the specific decision]\nOutput: options + trade-offs + recommendation"
)
```

---

## Step 3 — Output

```
## Question
[Restate the question clearly]

## Context
[What is already fixed — contracts, module boundaries, hardware constraints]

## Options

### Option A — [name]
[Description]
Pros: ...
Cons: ...

### Option B — [name]
[Description]
Pros: ...
Cons: ...

## Recommendation
[Clear, opinionated recommendation with justification]

## Next steps
[Does this need an ADR? A contract change (→ Architect approval)? A new task in task.md?]
```

---

## Rules
- No production code. Pseudocode only to illustrate an option.
- Never recommend an approach that violates the module DAG.
- If an ADR is warranted, say so explicitly.
- If this exploration reveals a gap in task.md, flag it.
