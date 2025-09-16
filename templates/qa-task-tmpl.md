# QA Task Template

## Task ID: QA-{ticket_number}

### Issue Information
- **Customer Ticket:** #{ticket_number}
- **Priority:** {P0|P1|P2|P3}
- **Reported Date:** {date}
- **Support Validation:** ✅ Completed

---

## Test Specification for QA Implementation

### Test Objective
Ensure that {functionality} operates correctly when {user_action} to prevent {issue_description}.

### Test Scenarios Required

#### Scenario 1: Reproduce Original Issue
**Type:** Regression Test (Should FAIL before fix)
- **Given:** {initial_state}
- **When:** {user_actions}
- **Then:** {expected_behavior}
- **Currently:** {actual_broken_behavior}

#### Scenario 2: Happy Path Validation
**Type:** E2E Integration Test
- **Given:** {normal_conditions}
- **When:** {standard_user_flow}
- **Then:** {successful_outcome}

#### Scenario 3: Edge Cases
**Type:** Boundary Testing
- **Given:** {edge_condition}
- **When:** {boundary_action}
- **Then:** {graceful_handling}

### Test Data Requirements
```yaml
test_data:
  users:
    - role: "admin"
      permissions: ["full_access"]
    - role: "standard"
      permissions: ["limited"]
  
  sample_data:
    - {data_type_1}: "{sample_values}"
    - {data_type_2}: "{sample_values}"
    
  edge_cases:
    - null_values: true
    - empty_strings: true
    - max_length: true
```

### Environment Requirements
- Database: Test database with seeded data
- Services: {required_services}
- Authentication: {auth_requirements}
- External Dependencies: {mocked_or_containerized}

### Validation Evidence from Support
- **Playwright Reproduction:** [Link to validation report]
- **Screenshots:** [Link to evidence]
- **Console Errors:** {error_messages}
- **Network Issues:** {api_failures}

### Acceptance Criteria for QA
- [ ] Test reproduces exact customer scenario
- [ ] Test fails with current code (before fix)
- [ ] Test will pass after Dev implements fix
- [ ] Test is maintainable and clear
- [ ] Test follows project conventions
- [ ] No flaky behaviors
- [ ] Proper assertions for all scenarios

### Implementation Guidelines
- Use existing test framework (xUnit/WebApplicationFactory)
- Follow project test patterns
- Utilize existing fixtures where possible
- Add to appropriate test collection
- Include clear documentation

### Definition of Done
- [ ] All scenarios implemented as tests
- [ ] Tests reviewed by QA lead
- [ ] Tests integrated into CI/CD pipeline
- [ ] Coverage report generated
- [ ] Documentation updated

---

## Handoff Notes from Support
{additional_context_from_support_investigation}

## Related Information
- **Dev Task:** DEV-{ticket_number}
- **Investigation Report:** [Link]
- **Customer Communication:** [Link]

---

**Assigned to:** QA Agent
**Due Date:** Sprint {number}
**Status:** Ready for Implementation