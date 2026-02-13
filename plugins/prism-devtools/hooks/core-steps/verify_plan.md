PLAN VERIFICATION: Check Story Coverage Against Requirements

Steps:
1. Read the original prompt/requirements from workflow context below
2. Read the story file just drafted
3. Extract every distinct requirement from the prompt
4. For each requirement, find the AC(s) that cover it
5. Write a ## Plan Coverage section in the story with:
   | # | Requirement | AC(s) | Status |
   Each must be COVERED, PARTIAL, or MISSING
6. If any are MISSING: add new ACs and tasks to cover them
7. If any are PARTIAL: expand existing ACs to fully cover
8. Final coverage must have zero MISSING items

CRITICAL: The stop hook validates that the Plan Coverage section exists
and contains zero MISSING items. Do NOT stop until all requirements are COVERED.
