# Dev Task Template

## Task ID: DEV-{ticket_number}

### Issue Information
- **Customer Ticket:** #{ticket_number}
- **Priority:** {P0|P1|P2|P3}
- **Severity:** {Critical|High|Medium|Low}
- **Support Validation:** ✅ Completed
- **Root Cause Investigation:** ✅ Completed

---

## Problem Statement

### Customer Impact
**What's Broken:** {user_facing_description}
**Business Impact:** {revenue/operational_impact}
**Affected Users:** {scope_and_count}
**Workaround:** {available_or_none}

### Technical Summary
**Root Cause:** {identified_root_cause}
**Component:** {affected_service_or_module}
**Introduced:** {version_or_date_if_known}
**Error Type:** {null_ref|timeout|logic|race_condition|other}

---

## Requirements for Fix

### Functional Requirements
1. {requirement_1}
2. {requirement_2}
3. {requirement_3}

### Non-Functional Requirements
- **Performance:** {response_time_requirements}
- **Security:** {validation_requirements}
- **Reliability:** {error_handling_requirements}
- **Compatibility:** {backward_compatibility_needs}

### Technical Constraints
- Minimal code changes preferred
- No breaking API changes
- Must be deployable without downtime
- Maintain existing behavior for unaffected flows

---

## Investigation Findings

### Evidence from Support
- **Validation Method:** Playwright automation
- **Reproduction Rate:** {percentage}
- **Error Messages:** 
  ```
  {error_message_1}
  {error_message_2}
  ```
- **Stack Trace:** {if_available}

### Affected Code Areas
Based on investigation, check these areas:
- File: `{file_path_1}`
  - Component: {component_name}
  - Suspected Issue: {issue_description}
  
- File: `{file_path_2}`
  - Component: {component_name}
  - Suspected Issue: {issue_description}

### Suggested Approach (Non-Prescriptive)
Support investigation suggests considering:
- {high_level_approach_1}
- {high_level_approach_2}

*Note: Dev agent determines actual implementation*

---

## Definition of Done

### Development Checklist
- [ ] Root cause addressed
- [ ] Fix implemented with minimal changes
- [ ] Unit tests updated/added
- [ ] Integration tests pass
- [ ] Code reviewed and approved
- [ ] Performance impact validated
- [ ] Documentation updated if needed

### Validation Requirements
- [ ] Original issue no longer reproduces
- [ ] QA test (created separately) passes
- [ ] No regression in existing functionality
- [ ] Performance metrics maintained
- [ ] Security scan passes (if applicable)

---

## Risk Assessment

### Change Risk: {Low|Medium|High}
- **Complexity:** {simple|moderate|complex}
- **Dependencies:** {isolated|some|many}
- **Testing Coverage:** {excellent|good|needs_improvement}

### Deployment Risk: {Low|Medium|High}
- **Rollback Plan:** {simple_revert|feature_flag|complex}
- **User Impact:** {transparent|minimal|visible}
- **Data Changes:** {none|backward_compatible|migration_needed}

---

## Testing Coordination

### QA Integration
- QA Task Created: QA-{ticket_number}
- Test Type: E2E Integration
- Test Status: Specification provided

### Testing Requirements
- Existing tests must continue to pass
- New QA test must pass post-fix
- Manual validation in staging required
- Performance benchmarks maintained

---

## Sprint Planning

### Effort Estimate
- **Story Points:** {1|2|3|5|8}
- **PROBE Size:** {very_small|small|medium|large|very_large}
  - 1 point = very_small (VS)
  - 2 points = small (S)
  - 3 points = medium (M)
  - 5 points = large (L)
  - 8 points = very_large (VL)
- **Time Estimate:** {hours_or_days}

### Dependencies
- [ ] QA test specification available
- [ ] Environment access confirmed
- [ ] Related tickets: {linked_issues}

### Timeline
- **Sprint:** {number}
- **Target Completion:** {date}
- **Customer Commitment:** {if_any}

---

## Communication

### Stakeholders
- Customer Support: Awaiting fix
- QA Team: Ready to test
- DevOps: Deployment planning needed
- Product: Monitoring issue

### Updates Required
- [ ] Ticket status updates
- [ ] Sprint board updates
- [ ] Team standup mention
- [ ] Customer communication (via Support)

---

**Assigned to:** Dev Agent
**Created by:** Support Agent
**Status:** Ready for Development

## Attachments
- [Validation Report]({link})
- [Screenshots]({link})
- [Investigation Details]({link})