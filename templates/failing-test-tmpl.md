<!-- Powered by PRISM™ Core -->

# Failing Test: {Issue Title}

## Issue ID: {ISSUE-XXX}
## Priority: {P0|P1|P2|P3}
## Status: Reproduces Consistently
## Date Validated: {YYYY-MM-DD}

## Test Objective

Verify that {specific functionality} works correctly when {conditions}.

**Currently FAILS:** {Brief description of the bug}

## Environment & Prerequisites

### Environment
- Platform: {staging|production|local}
- Browser: {Chrome 120|Firefox 119|Safari 17}
- API Version: {version}
- Feature Flags: {list any required flags}

### User Requirements
- Role: {admin|user|guest}
- Permissions: {specific permissions needed}
- Account State: {trial|paid|enterprise}

### Data Requirements
```yaml
required_records:
  - Record Type: {User|Product|Order}
    State: {active|pending|archived}
    Properties:
      - {field}: {value}
      - {field}: {value}
```

## Steps to Reproduce

| Step | Action | Element/Selector | Expected | Actual | Pass/Fail |
|------|--------|-----------------|----------|--------|-----------|
| 1 | Navigate to {URL} | - | Page loads | Page loads | ✅ |
| 2 | Click {button} | `#button-id` | Modal opens | Modal opens | ✅ |
| 3 | Enter "{value}" | `input[name='field']` | Accepts input | Accepts input | ✅ |
| 4 | Submit form | `button[type='submit']` | Success message | **ERROR** | ❌ |

### Failure Point
- **Step:** 4
- **Expected:** Form submits successfully, shows confirmation
- **Actual:** Form submission fails with error: "{exact error message}"

## Error Details

### Console Error
```javascript
Uncaught TypeError: Cannot read property 'x' of undefined
    at FileName.js:123:45
    at processResponse (api.js:456:12)
```

### Network Response
```json
{
  "status": 500,
  "error": "Internal Server Error",
  "message": "Database connection timeout",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Stack Trace
```
Error: Database connection timeout
    at Connection.timeout (db.js:234:15)
    at async PaymentController.process (payment.js:89:20)
    at async handleRequest (middleware.js:45:12)
```

## Test Assertions (for QA Implementation)

### Primary Assertion (Currently Fails)
```javascript
// This should PASS but currently FAILS
expect(successMessage).toBeVisible();
expect(successMessage).toHaveText('Payment processed successfully');
```

### Supporting Assertions
```javascript
// API response check
expect(response.status).toBe(200); // FAILS: returns 500

// Database check  
expect(paymentRecord).toBeDefined(); // FAILS: record not created

// UI state check
expect(errorBanner).not.toBeVisible(); // FAILS: error shown
```

## Visual Evidence

### Before Action (Working State)
[Screenshot placeholder - form ready for submission]

### After Action (Failed State)
[Screenshot placeholder - error message displayed]

### Expected Result (Mock)
[Screenshot placeholder - success message that should appear]

## Impact Analysis

### User Impact
- Severity: {Critical|High|Medium|Low}
- Users Affected: {percentage or count}
- Workaround Available: {Yes with steps|No}

### Business Impact
- Revenue Impact: {blocking purchases|degraded experience|cosmetic}
- Customer Complaints: {number} reports
- SLA Violation: {Yes|No}

## Related Information

### Similar Issues
- {ISSUE-YYY}: {Similar title - resolved/open}
- {ISSUE-ZZZ}: {Related issue - may have same root cause}

### Affected Components
- Frontend: {ComponentName.jsx}
- Backend: {ControllerName.cs}
- Database: {table_name}
- External Service: {ServiceName API}

## Definition of Done

### For Development
- [ ] Can reproduce the issue locally
- [ ] Root cause identified
- [ ] Fix implemented
- [ ] This test passes after fix
- [ ] No regression in related areas

### For QA
- [ ] Automated test created from this spec
- [ ] Test fails before fix (confirms reproduction)
- [ ] Test passes after fix applied
- [ ] Added to regression suite
- [ ] Edge cases covered

### For Support
- [ ] Customer notified of investigation
- [ ] Workaround provided if available
- [ ] Fix verified in staging
- [ ] Customer confirms resolution

## Notes

### Investigation Notes
{Any additional context from root cause investigation}

### Workaround (if available)
{Steps customer can take to avoid the issue temporarily}

### Fix Suggestions
{Potential approaches to fix based on investigation}

---

**Created by:** Support Agent
**Validated with:** Playwright-MCP
**Handoff to:** Dev Team (fix) & QA Team (test automation)