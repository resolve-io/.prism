# PSP Size Categories

Standard PSP size categories calibrated over time:

| Category | Hours | Days | When to Use |
|----------|-------|------|-------------|
| **VS** | 0.5-2 | <0.5 | Trivial changes, config updates |
| **S** | 2-4 | 0.5-1 | Simple features, clear path |
| **M** | 4-8 | 1 | Standard feature, well-understood |
| **L** | 8-16 | 1-2 | Complex feature, some unknowns |
| **VL** | 16-24 | 2-3 | Very complex, maximum story size |
| **TOO LARGE** | >24 | >3 | SPLIT REQUIRED |

**Note**: Categories calibrated over time based on actual team velocity.

## Decomposition Principles

- Each story 1-3 days of work (based on PSP data)
- Stories independently valuable and testable
- Maintain architectural boundaries in splits
- Size consistency more important than time boxes

## PSP Sizing Process

- PROBE estimation for every story
- Size categories with historical calibration
- Track actual time to refine definitions
- Identify when epics need re-decomposition
- Flag stories >8 points for splitting
