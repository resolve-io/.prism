# PRISM Test Framework

This document combines the test levels framework and test priorities matrix to guide comprehensive test strategy design.

## Overview

The PRISM test framework helps determine:
1. **What level to test** (Unit, Integration, E2E)
2. **How much to test** (Priority: P0, P1, P2, P3)
3. **How to organize tests** (Naming, structure, execution)

## Test Levels Framework

### Purpose

Choose the appropriate test level to achieve efficient coverage without redundancy.

### Core Principle

**Test at the lowest appropriate level, then escalate when necessary.**

- ✅ **Unit tests** are fast and pinpoint issues → Prefer when possible
- ✅ **Integration tests** verify interactions → Use when units must work together
- ✅ **E2E tests** validate user experience → Reserve for critical journeys

### Test Level Decision Matrix

| **Test This**  | **Level** | **Why** |
|----------------|-----------|---------|
| Pure function | Unit | No external dependencies, fast, deterministic |
| Business logic | Unit | Core logic isolated from infrastructure |
| Calculation/algorithm | Unit | Mathematical operations, data transformations |
| Validation rules | Unit | Input validation, business rules |
| Data transformation | Unit | Mapping, serialization, formatting |
| Component interaction | Integration | Multiple units working together |
| Database operations | Integration | Persistence layer, transactions |
| API endpoints | Integration | Request/response handling, validation |
| Service integration | Integration | External service calls, message queues |
| Authentication flow | Integration | Multiple components (user, token, session) |
| Critical user journey | E2E | Revenue-impacting, compliance, security |
| Multi-step workflow | E2E | Spanning multiple services/pages |
| Cross-system flow | E2E | Multiple systems interacting |
| User experience validation | E2E | UI behavior, accessibility, UX |

### Unit Tests

**Characteristics:**
- Fast execution (<10ms per test)
- No external dependencies
- Deterministic (same input = same output)
- Test single function/class

**Use For:**
- Pure functions
- Business logic
- Calculations and algorithms
- Validation rules
- Data transformations

**Example:**
```python
# ✅ GOOD - Unit test for pure function
def test_calculate_discount():
    price = 100
    discount_percent = 20
    result = calculate_discount(price, discount_percent)
    assert result == 80

# Calculate function
def calculate_discount(price, discount_percent):
    return price * (1 - discount_percent / 100)
```

**Anti-Pattern:**
```python
# ❌ BAD - Unit test with external dependency
def test_get_user():
    user = User.objects.get(id=1)  # Database call!
    assert user.email == "test@example.com"
```

### Integration Tests

**Characteristics:**
- Moderate execution time (100ms-1s per test)
- May use test databases or containers
- Test multiple components together
- Verify boundaries and contracts

**Use For:**
- Component interactions
- Database operations and transactions
- API endpoints (request → response)
- Service integrations
- Message queue operations
- File system operations

**Example:**
```python
# ✅ GOOD - Integration test with database
def test_create_user_persists_to_database():
    user_service = UserService(database=test_db)
    user = user_service.create_user("test@example.com", "password123")

    # Verify persisted to database
    retrieved = test_db.query(User).filter_by(id=user.id).first()
    assert retrieved.email == "test@example.com"
    assert retrieved.password_hash is not None
```

**Anti-Pattern:**
```python
# ❌ BAD - Testing mock behavior
def test_create_user():
    mock_db = Mock()
    user_service = UserService(database=mock_db)
    user_service.create_user("test@example.com", "password123")

    # Testing that mock was called, not real behavior!
    mock_db.insert.assert_called_once()
```

### End-to-End Tests

**Characteristics:**
- Slow execution (5-30s per test)
- Requires full environment setup
- Tests complete workflows
- Most realistic, but most expensive

**Use For:**
- Critical user journeys (login, checkout, payment)
- Cross-system workflows
- Compliance requirements
- Revenue-impacting features
- Security-critical paths

**Example:**
```javascript
// ✅ GOOD - E2E test for critical journey
test('user can complete checkout and make payment', async ({ page }) => {
  // Login
  await page.goto('/login');
  await page.fill('[name="email"]', 'test@example.com');
  await page.fill('[name="password"]', 'password123');
  await page.click('button[type="submit"]');

  // Add item to cart
  await page.goto('/products/123');
  await page.click('button:has-text("Add to Cart")');

  // Checkout
  await page.goto('/cart');
  await page.click('button:has-text("Checkout")');

  // Payment
  await page.fill('[name="cardNumber"]', '4242424242424242');
  await page.fill('[name="expiry"]', '12/25');
  await page.fill('[name="cvc"]', '123');
  await page.click('button:has-text("Pay Now")');

  // Verify success
  await expect(page.locator('text=Order Confirmed')).toBeVisible();
});
```

**Anti-Pattern:**
```javascript
// ❌ BAD - E2E test for simple validation
test('email validation shows error', async ({ page }) => {
  await page.goto('/register');
  await page.fill('[name="email"]', 'invalid-email');
  await page.click('button[type="submit"]');
  await expect(page.locator('text=Invalid email')).toBeVisible();
});
// This should be a unit test of validation logic!
```

### Duplicate Coverage Guard

**Avoid testing the same thing at multiple levels.**

Each level should verify different aspects:
- **Unit**: Logic correctness
- **Integration**: Component interaction
- **E2E**: User experience

**Example - Payment Processing:**

```
✅ GOOD Coverage Strategy:

Unit Tests:
- Calculate payment amount with tax
- Validate card number format
- Generate transaction ID

Integration Tests:
- Payment service processes transaction
- Database records transaction
- Stripe API receives correct payload

E2E Tests:
- User completes checkout with test card
- Order confirmation displayed
- Email receipt sent

❌ BAD - Testing same thing at multiple levels:

Unit Test:
- Validate card number format ✓

Integration Test:
- Validate card number format ✗ (duplicate!)

E2E Test:
- Validate card number format ✗ (duplicate!)
```

### Test Naming Convention

**Pattern:** `test_{component}_{scenario}`

**Examples:**
- `test_user_creation_with_valid_email()`
- `test_payment_processing_with_insufficient_funds()`
- `test_cart_total_calculation_with_multiple_items()`

**Test IDs:** `{EPIC}.{STORY}-{LEVEL}-{SEQ}`
- Example: `1.3-UNIT-001`, `1.3-INT-002`, `1.3-E2E-001`

---

## Test Priorities Matrix

### Purpose

Determine how much testing is needed based on business risk.

### Priority Levels

#### P0 - Critical

**Criteria:**
- Revenue-impacting features
- Security paths (authentication, authorization, payments)
- Data integrity operations
- Compliance requirements (GDPR, PCI, HIPAA)

**Coverage Requirements:**
- >90% unit test coverage
- >80% integration test coverage
- All critical E2E paths covered
- Edge cases thoroughly tested
- Performance validated

**Examples:**
- User authentication and authorization
- Payment processing and billing
- Data encryption and security
- Regulatory compliance workflows
- Financial calculations

**Test Scenario:**
```python
# P0 - Payment processing
def test_payment_processing_with_valid_card():
    # Critical: Must work perfectly
    payment = process_payment(
        amount=99.99,
        card="4242424242424242",
        cvv="123"
    )
    assert payment.status == "success"
    assert payment.amount == 99.99

def test_payment_processing_with_declined_card():
    # Critical: Must handle failures gracefully
    payment = process_payment(
        amount=99.99,
        card="4000000000000002",  # Decline test card
        cvv="123"
    )
    assert payment.status == "declined"
    assert payment.error_message == "Card was declined"

def test_payment_processing_with_insufficient_funds():
    # Critical edge case
    ...

def test_payment_idempotency():
    # Critical: Prevent duplicate charges
    ...

def test_payment_concurrent_requests():
    # Critical: Race condition safety
    ...
```

#### P1 - High

**Criteria:**
- Core user journeys
- Frequently used features
- Complex business logic
- Important integrations

**Coverage Requirements:**
- Primary happy paths covered
- Key error scenarios tested
- Basic performance checks
- Integration points validated

**Examples:**
- User profile management
- Product search and filtering
- Shopping cart operations
- Email notifications
- Report generation

**Test Scenario:**
```python
# P1 - Product search
def test_product_search_returns_matching_results():
    # Happy path
    results = search_products("laptop")
    assert len(results) > 0
    assert all("laptop" in r.name.lower() for r in results)

def test_product_search_with_no_results():
    # Common error scenario
    results = search_products("nonexistent-product-xyz")
    assert len(results) == 0

def test_product_search_pagination():
    # Common use case
    page1 = search_products("laptop", page=1, size=20)
    page2 = search_products("laptop", page=2, size=20)
    assert len(page1) == 20
    assert page1[0].id != page2[0].id
```

#### P2 - Medium

**Criteria:**
- Secondary features
- Admin functionality
- Reporting and analytics
- Less frequently used features

**Coverage Requirements:**
- Happy path coverage sufficient
- Basic error handling tested
- Manual testing acceptable for edge cases

**Examples:**
- Admin dashboards
- User settings pages
- Export to CSV features
- Audit logs
- System configuration

**Test Scenario:**
```python
# P2 - Export to CSV
def test_export_users_to_csv():
    # Happy path only
    csv_data = export_users_to_csv()
    assert "email,name,created_at" in csv_data
    assert "test@example.com" in csv_data

def test_export_empty_users_to_csv():
    # Basic error handling
    csv_data = export_users_to_csv(filters={"no_results": True})
    assert csv_data == "email,name,created_at\n"
```

#### P3 - Low

**Criteria:**
- Rarely used features
- Cosmetic improvements
- Nice-to-have functionality
- Internal tools

**Coverage Requirements:**
- Smoke tests only
- Manual testing relied upon
- Minimal automated coverage

**Examples:**
- Theme customization
- Advanced filters rarely used
- Easter eggs
- Developer tools
- Experimental features

**Test Scenario:**
```python
# P3 - Theme selection
def test_user_can_select_theme():
    # Smoke test only
    user = User.objects.get(id=1)
    user.set_theme("dark")
    assert user.theme == "dark"
# That's it - manual testing for the rest
```

### Priority Adjustment Factors

**Increase Priority When:**
- Feature affects >50% of users
- Complex implementation (high bug risk)
- External dependency involved
- Regulatory implications
- Financial impact

**Decrease Priority When:**
- Feature flag in place (can disable)
- Gradual rollout planned
- Strong monitoring available
- Easy rollback
- Low user impact

### Execution Strategy

**Sequential Execution for Fast Feedback:**

1. **P0 Unit tests** (fail fast on critical logic)
2. **P0 Integration tests** (fail fast on critical interactions)
3. **P0 E2E tests** (verify critical journeys)
4. **P1 tests in order** (unit → integration → E2E)
5. **P2 tests** (if time permits)
6. **P3 tests** (if all above pass and time available)

**CI/CD Integration:**
```yaml
# Example GitHub Actions workflow
jobs:
  test-p0:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -m "p0 and unit"  # Fast, critical
      - run: pytest -m "p0 and integration"
      - run: playwright test --grep "@p0"
    # If P0 fails, stop immediately

  test-p1:
    needs: test-p0
    runs-on: ubuntu-latest
    steps:
      - run: pytest -m "p1"
      - run: playwright test --grep "@p1"
    # Continue even if P1 has failures

  test-p2-p3:
    needs: test-p1
    runs-on: ubuntu-latest
    steps:
      - run: pytest -m "p2 or p3"
    # Optional, may skip if time constrained
```

---

## Complete Test Strategy Template

### For Each Story

**1. Map Acceptance Criteria to Test Levels**

| AC | Description | Unit | Integration | E2E | Priority |
|----|-------------|------|-------------|-----|----------|
| AC1 | User can register | Validation logic | API endpoint | Full registration flow | P0 |
| AC2 | Email confirmation sent | Email formatting | Email service integration | - | P1 |
| AC3 | Duplicate email rejected | Validation logic | Database constraint | Error displayed | P1 |

**2. Design Test Scenarios**

For each cell in the matrix:

```yaml
scenario:
  id: "1.3-UNIT-001"
  ac: "AC1"
  priority: "P0"
  level: "unit"
  description: "Validate email format is correct"
  test_case: |
    def test_email_validation_accepts_valid_format():
        assert is_valid_email("test@example.com") is True

    def test_email_validation_rejects_invalid_format():
        assert is_valid_email("invalid-email") is False
```

**3. Validate Coverage**

- [ ] Every AC has at least one test
- [ ] No duplicate coverage across levels
- [ ] P0 has >90% unit, >80% integration, all critical E2E
- [ ] P1 has happy path + key errors
- [ ] Test IDs follow naming convention
- [ ] Scenarios are atomic and independent

**4. Document Test Design**

Output: `docs/qa/assessments/{epic}.{story}-test-design-{YYYYMMDD}.md`

---

## Best Practices

### Test Quality Standards

✅ **DO:**
- Write tests before implementation (TDD)
- Use dynamic waiting, not sleep
- Make tests stateless and parallel-safe
- Clean up test data automatically
- Keep assertions in tests, not helpers
- Test behavior, not implementation
- Use appropriate test level for scenario
- Assign priority based on business risk

❌ **DON'T:**
- Test mock behavior instead of real code
- Add test-only methods to production code
- Share state between tests
- Use hard-coded delays
- Test same thing at multiple levels
- Skip tests for "later"
- Over-test low-priority features
- Under-test critical paths

### Risk-Based Prioritization

**Formula:** Risk Score = Probability × Impact

- **Probability:** 1 (rare) to 9 (certain)
- **Impact:** 1 (minor) to 9 (critical)

**Scoring:**
- 1-9: Low risk (P2-P3)
- 10-29: Medium risk (P1-P2)
- 30-54: High risk (P0-P1)
- 55+: Critical risk (P0, may require design changes)

### Brownfield Testing

**Enhanced Requirements for Legacy Code:**
- ✅ ALWAYS run risk assessment first (`@qa *risk`)
- ✅ Design regression test strategy (`@qa *design`)
- ✅ Test all integration points
- ✅ Validate backward compatibility
- ✅ Performance benchmarks (before/after)
- ✅ Gradual rollout with monitoring

**Brownfield Test Additions:**
- Regression tests for untouched legacy code
- Integration tests for new/old boundaries
- Contract tests for API compatibility
- Performance tests to detect degradation

---

## Quick Reference

### Test Level Selection

**Pure logic** → Unit
**Multiple components** → Integration
**User journey** → E2E

### Priority Selection

**Revenue/Security/Compliance** → P0
**Core features** → P1
**Secondary features** → P2
**Rarely used** → P3

### Coverage Targets

**P0:** >90% unit, >80% integration, all E2E
**P1:** Happy path + key errors
**P2:** Happy path + basic errors
**P3:** Smoke only

### Test ID Format

`{EPIC}.{STORY}-{LEVEL}-{SEQ}`

Examples: `1.3-UNIT-001`, `2.5-INT-012`, `3.1-E2E-003`

---

**Last Updated**: 2025-10-22
