# Review Checklist

Comprehensive review criteria for peer code reviews.

## Architecture & Design
- [ ] Changes fit existing architecture
- [ ] Component boundaries respected
- [ ] Design patterns used correctly
- [ ] Dependencies managed appropriately
- [ ] No circular dependencies

## Code Quality
- [ ] Clean Code principles followed
- [ ] SOLID principles applied
- [ ] Clear, descriptive naming
- [ ] Functions small and focused
- [ ] Low cyclomatic complexity

## Duplication
- [ ] No duplicated code
- [ ] Common logic extracted
- [ ] Utilities reused where appropriate
- [ ] No reinvented wheels

## Test Coverage
- [ ] All new code tested
- [ ] Edge cases covered
- [ ] Error paths tested
- [ ] Integration tests present
- [ ] Tests follow AAA pattern (Arrange-Act-Assert)

## PRISM Compliance
- [ ] Predictability: Structured, measurable
- [ ] Resilience: Error handling, tests
- [ ] Intentionality: Clear, purposeful
- [ ] Sustainability: Maintainable
- [ ] Maintainability: Clean boundaries

## Technical Debt
- [ ] No new technical debt introduced
- [ ] Existing debt addressed if touched
- [ ] TODOs have tickets
- [ ] Workarounds documented

## Documentation
- [ ] Complex logic commented
- [ ] Public APIs documented
- [ ] README updated if needed
- [ ] Architecture docs current
