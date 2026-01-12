# PRISM Peer Review Checklist

## Pre-Review Setup
- [ ] Pull latest changes from main branch
- [ ] Identify all modified files in the changeset
- [ ] Load story file if reviewing story implementation
- [ ] Verify build passes locally

## Code Quality Review

### PRISM Principles Adherence
- [ ] **Predictability**: Code follows established patterns and conventions
- [ ] **Resilience**: Error handling is comprehensive and graceful
- [ ] **Intentionality**: Code purpose is clear and well-documented
- [ ] **Sustainability**: Implementation supports long-term maintenance
- [ ] **Maintainability**: Code structure enables easy modifications

### Architecture Alignment
- [ ] Changes align with existing architecture patterns
- [ ] No architectural violations or anti-patterns introduced
- [ ] Proper separation of concerns maintained
- [ ] Dependencies are appropriate and minimal

### Code Duplication Check
- [ ] No copy-pasted code without justification
- [ ] Common functionality properly abstracted
- [ ] DRY principle followed appropriately
- [ ] Existing utilities/helpers reused where possible

### Testing Coverage
- [ ] All new functionality has corresponding tests
- [ ] Edge cases are tested
- [ ] Test names clearly describe what is being tested
- [ ] Tests follow AAA pattern (Arrange, Act, Assert)
- [ ] No tests are skipped without justification

### Security Review
- [ ] No hardcoded secrets or credentials
- [ ] Input validation present where needed
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] Authentication/authorization properly implemented

### Performance Considerations
- [ ] No obvious performance bottlenecks
- [ ] Database queries are optimized
- [ ] No unnecessary loops or iterations
- [ ] Resource cleanup handled properly
- [ ] Caching used appropriately

## Documentation Review
- [ ] Code comments explain "why" not "what"
- [ ] Complex logic is documented
- [ ] API documentation updated if applicable
- [ ] README updated if needed
- [ ] Change log updated

## Best Practices
- [ ] Naming conventions followed
- [ ] SOLID principles applied
- [ ] Clean Code principles followed
- [ ] No commented-out code left
- [ ] No debug/console statements left
- [ ] Proper error messages for users

## Final Checks
- [ ] All automated checks pass
- [ ] Manual testing completed
- [ ] Breaking changes documented
- [ ] Backwards compatibility maintained or migration provided
- [ ] Ready for production deployment

## Review Decision
- [ ] **APPROVED** - Ready to merge
- [ ] **APPROVED WITH SUGGESTIONS** - Minor improvements recommended
- [ ] **NEEDS CHANGES** - Must address issues before approval
- [ ] **REJECTED** - Major rework required

## Review Notes
_Document specific findings, suggestions, and action items here_

---
*PRISM Peer Review Checklist - Ensuring Quality Through Systematic Review*