# Story Template

> Source: [Confluence - Story Template](https://resolvesys.atlassian.net/wiki/spaces/PLAT/pages/1826455553/Story+Template)

This template defines the standard structure for user stories in the PLAT project.

---

## User Story

The business goal is the reason for this story.

**Format Option 1 (User Story):**
> "As a [persona], I want to [action], so [reason]."

**Format Option 2 (Who/What/Why):**
- **Who:** [The user/persona affected]
- **What:** [The action or capability needed]
- **Why:** [The business value or reason]

---

## Acceptance Criteria

Acceptance criteria refer to a set of predefined requirements that must be met to mark a user story complete.

**Important:** Acceptance criteria should attempt to address any cross-cutting concerns such as:
- Metrics
- Security
- Performance
- Accessibility

**Example:**
> When the user clicks the login button, they receive a valid token.

**Format:** Use testable, measurable criteria:
- [ ] Given [context], when [action], then [expected result]
- [ ] ...

---

## Technical Details

Technical details will contain specific technical requirements related to the story:

- Frameworks
- Libraries
- APIs
- Dependencies
- Configuration requirements

---

## Design

Design will specify any architectural/design guidelines related to this story:

- Architectural diagrams
- UI mockups
- Sequence diagrams
- Data flow diagrams
- Component interactions

---

## Assumptions

Things that can be considered as truths in the context of working on the story.

**Example:**
> The user authentication token will be in JSON format.

List assumptions that:
- Reduce ambiguity
- Define scope boundaries
- Clarify dependencies on other systems/teams

---

## Test Cases

Test cases will outline the testing expectations of the story. Test cases can be very specific or generic depending on the context of the story.

**Categories to consider:**
- Unit tests
- Integration tests
- E2E tests
- Edge cases
- Error scenarios

---

## Template Usage

When creating a new story in Jira, include these sections in the Description field:

```
## User Story
As a [persona], I want to [action], so [reason].

## Acceptance Criteria
- [ ] [Criterion 1]
- [ ] [Criterion 2]

## Technical Details
- [Detail 1]
- [Detail 2]

## Design
[Links to diagrams, mockups, or design docs]

## Assumptions
- [Assumption 1]
- [Assumption 2]

## Test Cases
- [Test case 1]
- [Test case 2]
```
