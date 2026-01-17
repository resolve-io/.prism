# PRISM Commands

Slash commands for activating PRISM personas and workflows.

## Role Personas

| Command | Role | Description |
|---------|------|-------------|
| [`/sm`](./sm.md) | Story Master | Plan and size stories |
| [`/dev`](./dev.md) | Developer | Implement features with TDD |
| [`/qa`](./qa.md) | QA Engineer | Test design and quality gates |
| [`/po`](./po.md) | Product Owner | Requirements and backlog |
| [`/architect`](./architect.md) | Architect | System design and decisions |
| [`/support`](./support.md) | Support | Customer issue triage |

## Workflow Commands

| Command | Description |
|---------|-------------|
| [`/prism-loop`](./prism-loop.md) | Start TDD development cycle |
| [`/prism-status`](./prism-status.md) | Check current workflow state |
| [`/prism-approve`](./prism-approve.md) | Approve gate and advance |
| [`/prism-reject`](./prism-reject.md) | Reject and loop back |
| [`/cancel-prism`](./cancel-prism.md) | Cancel active workflow |

## Usage

```bash
/sm              # Activate Story Master persona
/dev story-001   # Activate Developer with story context
/qa story-001    # Activate QA for story review
```

---

**See Also:** [Documentation Index](../docs/index.md)
