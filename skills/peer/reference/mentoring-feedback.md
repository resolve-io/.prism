# Mentoring Approach

## Educational Feedback Format

**Good feedback example:**
```
ISSUE: The `getUserData()` function is doing too much (fetching,
transforming, validating, logging).

WHY IT MATTERS: Violates Single Responsibility Principle (SOLID).
Hard to test, hard to reuse, hard to maintain.

SUGGESTION: Extract into smaller functions:
- fetchUserData()
- transformUserData()
- validateUserData()
- logUserAccess()

Then compose them in getUserData(). Each function now testable and
reusable independently.

REFERENCE: Clean Code, Chapter 3 - Functions should do one thing
```

**Poor feedback example:**
```
This function is bad. Refactor it.
```

## Mentoring Topics

Common areas for educational feedback:

- SOLID principles application
- Clean Code patterns
- Design patterns usage
- Test-driven development
- Refactoring techniques
- PRISM methodology
- Architecture patterns
- Performance optimization
