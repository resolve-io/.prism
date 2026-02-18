# Code Review Persistence

**After completing ANY pull request code review, ALWAYS persist detailed findings in TWO locations.**

This applies when using:
- `code-review:code-review` skill
- `pr-review-toolkit:review-pr` skill
- Manual PR review (via Task agents or direct analysis)
- Any other PR review workflow

**Trigger:** Completing a PR review and providing results to the user → MUST persist before finishing.

## 1. GitHub PR Review (Conversations - Require Resolution)

After completing the review, post findings as **review comments that create conversations** the developer must resolve before merging.

### Step 1: Post Line-Specific Review Comments

For each critical or important issue, create a **review comment on the specific line**:

```bash
# Get the HEAD commit SHA first
HEAD_SHA=$(gh pr view {PR_NUMBER} --json headRefOid -q '.headRefOid')

# Post a review comment on a specific line (creates a conversation)
gh api repos/{OWNER}/{REPO}/pulls/{PR_NUMBER}/comments \
  -f body="**[{SEVERITY}]** {Issue description}

{Detailed explanation of the issue}

**Suggested fix:**
\`\`\`
{code suggestion if applicable}
\`\`\`" \
  -f commit_id="$HEAD_SHA" \
  -f path="{file/path.ts}" \
  -f line={LINE_NUMBER}
```

### Step 2: Submit Formal Review

After posting all line-specific comments, submit a formal review:

```bash
# If critical issues found → Request Changes
gh pr review {PR_NUMBER} --request-changes --body "$(cat <<'EOF'
### Code Review - Detailed Analysis

**PR Summary:** [Brief description]

#### Issues Reviewed (X total, Y met 80+ confidence threshold)

| Issue | File:Line | Confidence | Severity | Verdict |
|-------|-----------|------------|----------|---------|
| [Issue description] | `path:123` | [Score] | Critical/Important/Suggestion | [Why flagged/filtered] |
...

#### Review Methodology
[Description of multi-agent process]

🤖 Generated with Claude Code
EOF
)"

# If only suggestions or no issues → Comment (no blocking)
gh pr review {PR_NUMBER} --comment --body "..."
```

### Review Submission Logic

| Condition | Review Type | Effect |
|-----------|-------------|--------|
| Critical issues (80+ confidence) | `--request-changes` | Blocks merge until resolved |
| Important issues only | `--request-changes` | Blocks merge until resolved |
| Suggestions only | `--comment` | Non-blocking feedback |
| No issues found | `--comment` | Confirms review completed |

### Why Conversations Matter

- **Conversations require resolution** - Developer must address each before merge (if branch protection enabled)
- **Line-specific context** - Comments appear directly on the relevant code
- **Audit trail** - Each conversation shows resolution status
- **Blocks premature merge** - `--request-changes` prevents merge until re-reviewed

## Workflow

1. Complete code review process (eligibility check, agents, scoring)
2. **ALWAYS** post detailed analysis comment to PR (see format above) - this applies regardless of whether issues were found or filtered

**CRITICAL: The detailed comment format is REQUIRED even when no issues meet the 80+ threshold.** The table should show ALL issues that were reviewed and why each was filtered. This provides transparency into the review process.

## Why This Matters

- Provides transparency into review decisions
- Creates audit trail for filtered issues
- Allows learning from false positive patterns
