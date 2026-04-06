---
name: story-decomposition
description: Break down large stories into optimally-sized stories (1-3 days) using PSP measurement discipline.
---

# Story Decomposition

Breaks large stories into 1-3 day slices by identifying architectural, functional, or technical boundaries.

## Steps

1. Load story context and historical sizing data from `estimation-history.yaml`
2. Identify natural split boundaries (architectural, functional, technical, or temporal)
3. Create story candidates with scope, value statement, and initial sizing
4. Apply PROBE estimation; split stories >24h, combine stories <4h
5. Sequence stories by dependencies and generate decomposition report

For detailed instructions, see [instructions.md](reference/instructions.md).
