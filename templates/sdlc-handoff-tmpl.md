# SDLC Handoff Template

## Handoff Package: Issue #{ticket_number}

### Executive Summary
- **Issue Type:** {Bug|Performance|Security|Feature}
- **Priority:** {P0|P1|P2|P3}
- **Status:** ✅ Validated → 📋 Ready for SDLC
- **Target Resolution:** Sprint {number}

---

## Issue Lifecycle Tracking

### ✅ Support Phase (COMPLETE)
- [x] Customer issue reported
- [x] Issue validated via Playwright
- [x] Root cause investigated
- [x] Impact assessment completed
- [x] Documentation prepared

### 📋 Development Phase (PENDING)
- [ ] DEV-{ticket}: Fix implementation
- [ ] Code review completed
- [ ] Unit tests updated
- [ ] Documentation updated

### 🧪 QA Phase (PENDING)
- [ ] QA-{ticket}: Test creation
- [ ] Test validates issue
- [ ] Fix verification
- [ ] Regression testing

### 🚀 Deployment Phase (PENDING)
- [ ] Staging deployment
- [ ] Production deployment
- [ ] Post-deployment verification
- [ ] Customer notification

---

## Complete Issue Documentation

### Customer Report
```yaml
reporter: "{customer_id}"
date_reported: "{date}"
severity_reported: "{customer_severity}"
description: |
  {original_customer_description}
business_impact: |
  {how_this_affects_their_business}
```

### Validation Results
```yaml
validation_method: "Playwright Automation"
reproduction_rate: "{100%|Intermittent}"
evidence:
  screenshots: "[Link to screenshots]"
  console_errors: "[Link to logs]"
  network_traces: "[Link to traces]"
  playwright_script: "[Link to validation code]"
reproduction_steps:
  1. {step_1}
  2. {step_2}
  3. {step_3}
```

### Root Cause Analysis
```yaml
identified_cause: "{root_cause_description}"
affected_component: "{service/module}"
introduced_in: "{version/date}"
code_location: "{file:line}"
investigation_notes: |
  {additional_investigation_details}
```

---

## Task Assignments

### Development Task
- **ID:** DEV-{ticket_number}
- **Assigned:** Dev Agent
- **Status:** Ready
- **Deliverables:**
  - Fix implementation
  - Code review
  - Unit test updates
- **Specification:** [Link to dev task]

### QA Task
- **ID:** QA-{ticket_number}
- **Assigned:** QA Agent
- **Status:** Ready
- **Deliverables:**
  - E2E test creation
  - Fix validation
  - Regression testing
- **Specification:** [Link to QA task]

### DevOps Requirements
- **Deployment Window:** {scheduled_time}
- **Rollback Plan:** {strategy}
- **Monitoring:** {metrics_to_watch}

---

## Risk & Priority Matrix

### Risk Assessment
| Factor | Level | Mitigation |
|--------|-------|------------|
| Customer Impact | {High/Med/Low} | {mitigation_strategy} |
| Technical Complexity | {High/Med/Low} | {mitigation_strategy} |
| Regression Risk | {High/Med/Low} | {mitigation_strategy} |
| Deployment Risk | {High/Med/Low} | {mitigation_strategy} |

### Priority Justification
- **Business Priority:** {reason}
- **Technical Priority:** {reason}
- **Customer Priority:** {reason}

---

## Communication Plan

### Internal Communications
```yaml
dev_team:
  channel: "#dev-team"
  message: "New {priority} fix required for {component}"
  action: "Review and estimate"
  
qa_team:
  channel: "#qa-team"
  message: "Test spec ready for {ticket}"
  action: "Plan test implementation"
  
leadership:
  channel: "#leadership"
  message: "Customer issue {ticket} in pipeline"
  action: "Monitor SLA compliance"
```

### Customer Communications
```yaml
initial_response:
  sent: "{timestamp}"
  message: "Issue confirmed and escalated to engineering"
  
progress_update:
  schedule: "{daily|weekly}"
  next_update: "{date}"
  
resolution_notice:
  target_date: "{date}"
  message_template: "Fix deployed and verified"
```

---

## Success Metrics

### SLA Tracking
- **Target Resolution:** {sla_time}
- **Current Status:** {on_track|at_risk|delayed}
- **Time Elapsed:** {hours/days}

### Quality Gates
- [ ] Support validation complete
- [ ] Dev implementation complete
- [ ] QA verification complete
- [ ] Staging validation complete
- [ ] Production deployment successful
- [ ] Customer confirmation received

---

## Escalation Information

### Escalation Triggers
- P0 unresolved after 2 hours
- P1 unassigned after 4 hours
- Customer executive escalation
- SLA breach imminent

### Escalation Contacts
1. **Level 1:** Team Lead - {contact}
2. **Level 2:** Engineering Manager - {contact}
3. **Level 3:** Director - {contact}
4. **Level 4:** VP/C-Level - {contact}

---

## References & Links

### Documentation
- Original Ticket: [#{ticket_number}]({link})
- Validation Report: [{link}]
- Investigation Notes: [{link}]
- Dev Task: [DEV-{ticket}]({link})
- QA Task: [QA-{ticket}]({link})

### Related Issues
- Similar Issues: {linked_tickets}
- Dependencies: {blocking_tickets}
- Follow-up Items: {future_work}

---

**Handoff Completed By:** Support Agent
**Handoff Date:** {timestamp}
**SDLC Owner:** Dev & QA Teams
**Status:** 🚦 In SDLC Pipeline