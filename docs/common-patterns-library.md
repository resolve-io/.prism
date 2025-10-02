# PRISM Common Patterns Library

## Overview
This library documents common design patterns and solutions used in PRISM development. These patterns have been proven effective and should be reused where appropriate.

## Architectural Patterns

### 1. Repository Pattern
**Purpose**: Abstract data access logic and provide a more object-oriented view of the persistence layer.

```javascript
class UserRepository {
  constructor(database) {
    this.db = database;
  }

  async findById(id) {
    return this.db.query('SELECT * FROM users WHERE id = ?', [id]);
  }

  async save(user) {
    if (user.id) {
      return this.update(user);
    }
    return this.create(user);
  }
}
```

### 2. Service Layer Pattern
**Purpose**: Encapsulate business logic and coordinate between multiple repositories.

```javascript
class UserService {
  constructor(userRepo, emailService) {
    this.userRepo = userRepo;
    this.emailService = emailService;
  }

  async registerUser(userData) {
    const user = await this.userRepo.save(userData);
    await this.emailService.sendWelcome(user.email);
    return user;
  }
}
```

### 3. Factory Pattern
**Purpose**: Create objects without specifying their concrete classes.

```javascript
class NotificationFactory {
  static create(type, data) {
    switch(type) {
      case 'email':
        return new EmailNotification(data);
      case 'sms':
        return new SMSNotification(data);
      case 'push':
        return new PushNotification(data);
      default:
        throw new Error(`Unknown notification type: ${type}`);
    }
  }
}
```

## Error Handling Patterns

### 1. Custom Error Classes
```javascript
class ValidationError extends Error {
  constructor(field, message) {
    super(message);
    this.name = 'ValidationError';
    this.field = field;
  }
}

class AuthenticationError extends Error {
  constructor(message = 'Authentication failed') {
    super(message);
    this.name = 'AuthenticationError';
  }
}
```

### 2. Error Middleware Pattern
```javascript
function errorHandler(err, req, res, next) {
  logger.error(err);

  if (err instanceof ValidationError) {
    return res.status(400).json({
      error: 'Validation failed',
      field: err.field,
      message: err.message
    });
  }

  if (err instanceof AuthenticationError) {
    return res.status(401).json({
      error: 'Authentication required',
      message: err.message
    });
  }

  res.status(500).json({
    error: 'Internal server error',
    message: 'An unexpected error occurred'
  });
}
```

## Async Patterns

### 1. Promise Chain with Error Handling
```javascript
function processOrder(orderId) {
  return fetchOrder(orderId)
    .then(validateOrder)
    .then(calculatePricing)
    .then(applyDiscounts)
    .then(processPayment)
    .then(sendConfirmation)
    .catch(error => {
      logger.error('Order processing failed', error);
      throw new OrderProcessingError(error.message);
    });
}
```

### 2. Async/Await with Try-Catch
```javascript
async function processOrderAsync(orderId) {
  try {
    const order = await fetchOrder(orderId);
    const validated = await validateOrder(order);
    const priced = await calculatePricing(validated);
    const discounted = await applyDiscounts(priced);
    const payment = await processPayment(discounted);
    await sendConfirmation(payment);
    return payment;
  } catch (error) {
    logger.error('Order processing failed', error);
    throw new OrderProcessingError(error.message);
  }
}
```

### 3. Parallel Processing
```javascript
async function fetchUserData(userId) {
  const [profile, preferences, orders] = await Promise.all([
    fetchUserProfile(userId),
    fetchUserPreferences(userId),
    fetchUserOrders(userId)
  ]);

  return {
    profile,
    preferences,
    orders
  };
}
```

## Validation Patterns

### 1. Schema Validation
```javascript
const userSchema = {
  email: {
    required: true,
    type: 'email',
    maxLength: 255
  },
  age: {
    required: false,
    type: 'number',
    min: 0,
    max: 120
  },
  role: {
    required: true,
    enum: ['user', 'admin', 'moderator']
  }
};

function validateUser(data) {
  return validate(data, userSchema);
}
```

### 2. Builder Pattern for Complex Objects
```javascript
class QueryBuilder {
  constructor() {
    this.query = {};
  }

  select(fields) {
    this.query.select = fields;
    return this;
  }

  where(conditions) {
    this.query.where = conditions;
    return this;
  }

  orderBy(field, direction = 'asc') {
    this.query.orderBy = { field, direction };
    return this;
  }

  limit(count) {
    this.query.limit = count;
    return this;
  }

  build() {
    return this.query;
  }
}

// Usage
const query = new QueryBuilder()
  .select(['id', 'name'])
  .where({ active: true })
  .orderBy('createdAt', 'desc')
  .limit(10)
  .build();
```

## Caching Patterns

### 1. Simple Memory Cache
```javascript
class MemoryCache {
  constructor(ttl = 3600000) { // 1 hour default
    this.cache = new Map();
    this.ttl = ttl;
  }

  set(key, value, customTtl) {
    const ttl = customTtl || this.ttl;
    const expiry = Date.now() + ttl;
    this.cache.set(key, { value, expiry });
  }

  get(key) {
    const item = this.cache.get(key);
    if (!item) return null;

    if (Date.now() > item.expiry) {
      this.cache.delete(key);
      return null;
    }

    return item.value;
  }
}
```

### 2. Cache-Aside Pattern
```javascript
class CachedUserService {
  constructor(userRepo, cache) {
    this.userRepo = userRepo;
    this.cache = cache;
  }

  async getUser(id) {
    const cacheKey = `user:${id}`;

    // Check cache
    const cached = this.cache.get(cacheKey);
    if (cached) return cached;

    // Fetch from database
    const user = await this.userRepo.findById(id);

    // Update cache
    if (user) {
      this.cache.set(cacheKey, user);
    }

    return user;
  }
}
```

## State Management Patterns

### 1. State Machine
```javascript
class OrderStateMachine {
  static states = {
    PENDING: 'pending',
    PROCESSING: 'processing',
    SHIPPED: 'shipped',
    DELIVERED: 'delivered',
    CANCELLED: 'cancelled'
  };

  static transitions = {
    [this.states.PENDING]: [this.states.PROCESSING, this.states.CANCELLED],
    [this.states.PROCESSING]: [this.states.SHIPPED, this.states.CANCELLED],
    [this.states.SHIPPED]: [this.states.DELIVERED],
    [this.states.DELIVERED]: [],
    [this.states.CANCELLED]: []
  };

  static canTransition(from, to) {
    return this.transitions[from]?.includes(to) || false;
  }
}
```

## Testing Patterns

### 1. Test Data Builders
```javascript
class UserBuilder {
  constructor() {
    this.user = {
      id: '123',
      email: 'test@example.com',
      name: 'Test User',
      role: 'user'
    };
  }

  withId(id) {
    this.user.id = id;
    return this;
  }

  withEmail(email) {
    this.user.email = email;
    return this;
  }

  withRole(role) {
    this.user.role = role;
    return this;
  }

  build() {
    return { ...this.user };
  }
}

// Usage in tests
const adminUser = new UserBuilder()
  .withRole('admin')
  .withEmail('admin@example.com')
  .build();
```

### 2. Mock Factory
```javascript
function createMockDatabase() {
  return {
    query: jest.fn(),
    insert: jest.fn(),
    update: jest.fn(),
    delete: jest.fn()
  };
}

function createMockEmailService() {
  return {
    sendWelcome: jest.fn().mockResolvedValue(true),
    sendPasswordReset: jest.fn().mockResolvedValue(true)
  };
}
```

## Security Patterns

### 1. Input Sanitization
```javascript
function sanitizeInput(input) {
  if (typeof input !== 'string') return input;

  return input
    .replace(/[<>]/g, '') // Remove angle brackets
    .replace(/javascript:/gi, '') // Remove javascript protocol
    .trim();
}
```

### 2. Rate Limiting
```javascript
class RateLimiter {
  constructor(maxRequests = 100, windowMs = 60000) {
    this.maxRequests = maxRequests;
    this.windowMs = windowMs;
    this.requests = new Map();
  }

  isAllowed(identifier) {
    const now = Date.now();
    const requests = this.requests.get(identifier) || [];

    // Filter out old requests
    const recent = requests.filter(time => now - time < this.windowMs);

    if (recent.length >= this.maxRequests) {
      return false;
    }

    recent.push(now);
    this.requests.set(identifier, recent);
    return true;
  }
}
```

---
*PRISM Common Patterns Library - Proven Solutions for Common Problems*