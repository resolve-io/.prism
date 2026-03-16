STORY DRAFTING: Create Next Story

## Understanding the System (DO THIS FIRST)
1. Your prompt includes a ## System Context section with relevant
   architecture, similar past stories, and known constraints. Read it carefully.
2. For deeper understanding: /brain search "topic you need"
   - Requirements: /brain search "requirements for user authentication"
   - Architecture context: /brain search "architecture decisions for data model"
   - Design decisions: /brain search "design decisions and technical constraints"
3. THEN Glob for epic and architecture docs as fallback

## Skills
IMPORTANT: Before drafting manually, check Available Skills above and invoke any relevant skill — skills encode project-specific story formats, AC patterns, and acceptance criteria conventions that general drafting won't apply automatically. Invoking a skill first saves rework.

Steps:
1. Glob for epic and architecture docs: docs/*.md, docs/epics/*.md
2. Read requirements and technical constraints
3. Draft story with YAML frontmatter (status, size, epic link)
4. Write acceptance criteria in Given/When/Then format
5. Break into tasks sized 1-3 days each
6. Save to docs/stories/ directory


