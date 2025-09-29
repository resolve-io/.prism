# PRISM Anti-Patterns Guide

## Overview
This guide documents common anti-patterns to avoid in PRISM development. Understanding what NOT to do is as important as knowing best practices.

## Code Anti-Patterns

### 1. God Object/Class
**Problem**: A class that knows too much or does too much.

❌ **Bad Example**:
```javascript
class AppManager {
  constructor() {
    this.database = new Database();
    this.auth = new Auth();
    this.email = new EmailService();
    this.cache = new Cache();
    this.logger = new Logger();
  }

  registerUser(data) { /* ... */ }
  sendEmail(to, subject, body) { /* ... */ }
  queryDatabase(query) { /* ... */ }
  authenticate(credentials) { /* ... */ }
  logEvent(event) { /* ... */ }
  cacheData(key, value) { /* ... */ }
  processPayment(amount) { /* ... */ }
  generateReport(type) { /* ... */ }
}
```

✅ **Better Approach**: Separate concerns into focused services.

### 2. Spaghetti Code
**Problem**: Code with complex and tangled control structure.

❌ **Bad Example**:
```javascript
function processData(data) {
  if (data) {
    if (data.type === 'A') {
      if (data.status === 'active') {
        if (data.value > 100) {
          // process A
          if (data.priority === 'high') {
            // more nested logic
          }
        }
      }
    } else if (data.type === 'B') {
      // similar deep nesting
    }
  }
}
```

✅ **Better Approach**: Use early returns and extract functions.

### 3. Copy-Paste Programming
**Problem**: Duplicating code instead of creating reusable functions.

❌ **Bad Example**:
```javascript
function sendWelcomeEmail(user) {
  const template = loadTemplate('welcome');
  const html = renderTemplate(template, user);
  const subject = 'Welcome!';
  sendEmail(user.email, subject, html);
  logEmail('welcome', user.email);
}

function sendPasswordResetEmail(user) {
  const template = loadTemplate('password-reset');
  const html = renderTemplate(template, user);
  const subject = 'Password Reset';
  sendEmail(user.email, subject, html);
  logEmail('password-reset', user.email);
}
```

✅ **Better Approach**: Extract common functionality.

### 4. Magic Numbers/Strings
**Problem**: Using hard-coded literals without explanation.

❌ **Bad Example**:
```javascript
if (user.age >= 18 && user.score > 75) {
  applyDiscount(order, 0.15);
}

if (status === 'ACT' || status === 'PND') {
  process();
}
```

✅ **Better Approach**: Use named constants.

### 5. Callback Hell
**Problem**: Deeply nested callbacks making code hard to read.

❌ **Bad Example**:
```javascript
getData(function(a) {
  getMoreData(a, function(b) {
    getMoreData(b, function(c) {
      getMoreData(c, function(d) {
        getMoreData(d, function(e) {
          console.log(e);
        });
      });
    });
  });
});
```

✅ **Better Approach**: Use async/await or promises.

## Error Handling Anti-Patterns

### 1. Swallowing Exceptions
**Problem**: Catching exceptions without proper handling.

❌ **Bad Example**:
```javascript
try {
  riskyOperation();
} catch (error) {
  // Silent fail - very bad!
}
```

✅ **Better Approach**: Always handle or rethrow errors appropriately.

### 2. Generic Error Messages
**Problem**: Providing vague error messages that don't help debugging.

❌ **Bad Example**:
```javascript
throw new Error('An error occurred');
throw new Error('Invalid input');
```

✅ **Better Approach**: Provide specific, actionable error messages.

### 3. Using Exceptions for Control Flow
**Problem**: Using try-catch for normal program flow.

❌ **Bad Example**:
```javascript
function findUser(id) {
  try {
    return database.getUser(id);
  } catch (error) {
    return null; // Using exception to indicate "not found"
  }
}
```

✅ **Better Approach**: Use return values or specific methods.

## Database Anti-Patterns

### 1. N+1 Query Problem
**Problem**: Making multiple database queries in a loop.

❌ **Bad Example**:
```javascript
const users = await db.query('SELECT * FROM users');
for (const user of users) {
  user.orders = await db.query('SELECT * FROM orders WHERE user_id = ?', user.id);
}
```

✅ **Better Approach**: Use joins or batch queries.

### 2. SQL Injection Vulnerability
**Problem**: Concatenating user input directly into SQL queries.

❌ **Bad Example**:
```javascript
const query = `SELECT * FROM users WHERE email = '${userEmail}'`;
db.query(query);
```

✅ **Better Approach**: Use parameterized queries.

### 3. Missing Indexes
**Problem**: Querying columns without proper indexes.

❌ **Bad Example**:
```sql
-- Querying without index on email column
SELECT * FROM users WHERE email = 'user@example.com';
```

✅ **Better Approach**: Add indexes for frequently queried columns.

## API Design Anti-Patterns

### 1. Inconsistent Naming
**Problem**: Using different naming conventions across endpoints.

❌ **Bad Example**:
```
GET /getUsers
POST /create-product
PUT /Order/Update
DELETE /remove_item
```

✅ **Better Approach**: Use consistent RESTful conventions.

### 2. Chatty API
**Problem**: Requiring multiple API calls for a single operation.

❌ **Bad Example**:
```javascript
// Need 4 API calls to get complete user data
const user = await api.get('/user/123');
const profile = await api.get('/profile/123');
const preferences = await api.get('/preferences/123');
const permissions = await api.get('/permissions/123');
```

✅ **Better Approach**: Design endpoints that return complete data.

### 3. Breaking Changes Without Versioning
**Problem**: Changing API contract without versioning.

❌ **Bad Example**:
```javascript
// Original
{ "name": "John Doe" }

// Changed without version (breaks clients)
{ "fullName": "John Doe" }
```

✅ **Better Approach**: Use API versioning.

## Testing Anti-Patterns

### 1. No Tests
**Problem**: Writing code without any tests.

❌ **Bad Example**:
```javascript
// Complex business logic with zero tests
function calculatePricing(order) {
  // 100 lines of untested logic
}
```

✅ **Better Approach**: Write tests for all critical paths.

### 2. Testing Implementation Instead of Behavior
**Problem**: Tests that break when refactoring despite behavior being unchanged.

❌ **Bad Example**:
```javascript
it('should call internal method', () => {
  const spy = jest.spyOn(service, '_internalMethod');
  service.publicMethod();
  expect(spy).toHaveBeenCalled();
});
```

✅ **Better Approach**: Test public interfaces and outcomes.

### 3. Fragile Tests
**Problem**: Tests that break easily due to unrelated changes.

❌ **Bad Example**:
```javascript
it('should render correctly', () => {
  const html = component.render();
  expect(html).toBe('<div class="container"><span>Text</span></div>');
});
```

✅ **Better Approach**: Test specific aspects, not entire output.

## Performance Anti-Patterns

### 1. Premature Optimization
**Problem**: Optimizing before identifying actual bottlenecks.

❌ **Bad Example**:
```javascript
// Over-engineered for a rarely-used feature
class SuperOptimizedCache {
  // 200 lines of complex caching logic
  // for data that's accessed once per day
}
```

✅ **Better Approach**: Profile first, optimize what matters.

### 2. Memory Leaks
**Problem**: Not cleaning up resources properly.

❌ **Bad Example**:
```javascript
const cache = {};
function addToCache(key, value) {
  cache[key] = value; // Never removed
}
```

✅ **Better Approach**: Implement cleanup and limits.

### 3. Blocking the Event Loop
**Problem**: CPU-intensive operations blocking async operations.

❌ **Bad Example**:
```javascript
app.get('/compute', (req, res) => {
  // Blocks all other requests
  const result = heavyComputation();
  res.send(result);
});
```

✅ **Better Approach**: Use worker threads or async processing.

## Security Anti-Patterns

### 1. Hardcoded Credentials
**Problem**: Embedding secrets in source code.

❌ **Bad Example**:
```javascript
const API_KEY = 'sk-1234567890abcdef';
const DB_PASSWORD = 'admin123';
```

✅ **Better Approach**: Use environment variables.

### 2. Trusting Client Input
**Problem**: Not validating data from clients.

❌ **Bad Example**:
```javascript
app.post('/transfer', (req, res) => {
  // Trusting amount from client
  transferMoney(req.body.from, req.body.to, req.body.amount);
});
```

✅ **Better Approach**: Validate and authorize all operations server-side.

### 3. Logging Sensitive Data
**Problem**: Writing sensitive information to logs.

❌ **Bad Example**:
```javascript
logger.info('User login', {
  username: user.email,
  password: user.password,
  creditCard: user.ccNumber
});
```

✅ **Better Approach**: Sanitize logs and never log sensitive data.

## Architecture Anti-Patterns

### 1. Big Ball of Mud
**Problem**: System with no clear structure or boundaries.

❌ **Bad Example**:
- No clear separation of concerns
- Everything depends on everything
- No modules or layers
- Changes ripple throughout system

✅ **Better Approach**: Define clear architecture and boundaries.

### 2. Vendor Lock-in
**Problem**: Tight coupling to specific vendor implementations.

❌ **Bad Example**:
```javascript
// Directly using AWS SDK throughout codebase
import AWS from 'aws-sdk';
class UserService {
  async saveUser(user) {
    const s3 = new AWS.S3();
    await s3.putObject(/*...*/).promise();
  }
}
```

✅ **Better Approach**: Abstract vendor-specific code behind interfaces.

### 3. Reinventing the Wheel
**Problem**: Creating custom solutions for solved problems.

❌ **Bad Example**:
```javascript
// Custom date parsing instead of using a library
function parseDate(dateString) {
  // 100 lines of buggy date parsing
}
```

✅ **Better Approach**: Use well-tested libraries for common tasks.

## How to Identify Anti-Patterns

### Code Smells to Watch For:
- Methods longer than 20-30 lines
- Classes with more than 5-7 methods
- Deep nesting (>3 levels)
- Duplicate code blocks
- Long parameter lists (>3-4 parameters)
- Comments explaining complex code
- Dead code
- Large commits
- Frequent bugs in the same area

### Questions to Ask:
1. Is this code easy to understand?
2. Can I unit test this easily?
3. Will changes ripple through the system?
4. Am I repeating myself?
5. Is this the simplest solution?
6. Are there established patterns for this?

## Prevention Strategies

1. **Code Reviews**: Catch anti-patterns before merging
2. **Automated Linting**: Detect common issues automatically
3. **Refactoring**: Regularly improve code structure
4. **Education**: Share knowledge about patterns and anti-patterns
5. **Metrics**: Track code complexity and technical debt
6. **Documentation**: Document decisions and patterns used

---
*PRISM Anti-Patterns Guide - Learn from Common Mistakes*