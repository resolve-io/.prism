# PRISM Coding Standards Reference

## Overview
This document defines the coding standards and conventions for PRISM-based development. All code must adhere to these standards to ensure consistency, maintainability, and quality.

## General Principles

### PRISM Core Values
- **Predictability**: Code behavior should be obvious and consistent
- **Resilience**: Handle errors gracefully and recover when possible
- **Intentionality**: Every line of code should have a clear purpose
- **Sustainability**: Write code that can be maintained long-term
- **Maintainability**: Keep complexity manageable and code modular

## Naming Conventions

### Variables
- Use camelCase for variables: `userName`, `orderCount`
- Use UPPER_SNAKE_CASE for constants: `MAX_RETRIES`, `API_BASE_URL`
- Boolean variables should start with is/has/can: `isActive`, `hasPermission`

### Functions
- Use camelCase for functions: `calculateTotal()`, `getUserById()`
- Use verbs that describe the action: `fetchData()`, not `data()`
- Keep names descriptive but concise

### Classes
- Use PascalCase for classes: `UserService`, `OrderController`
- Use nouns that describe the entity or service

### Files
- Use kebab-case for file names: `user-service.js`, `order-controller.ts`
- Test files should end with `.test` or `.spec`
- Configuration files should be clearly named: `database.config.js`

## Code Organization

### File Structure
```
src/
├── components/     # UI components
├── services/       # Business logic
├── models/         # Data models
├── utils/          # Utility functions
├── types/          # Type definitions
└── tests/          # Test files
```

### Module Structure
- One export per file for major components
- Group related functionality together
- Keep files under 300 lines when possible
- Extract complex logic into separate functions

## Documentation

### Comments
- Write self-documenting code that needs minimal comments
- Use comments to explain "why" not "what"
- Document complex algorithms or business logic
- Keep comments up-to-date with code changes

### JSDoc/TypeDoc
```javascript
/**
 * Calculates the total price including tax
 * @param {number} price - Base price
 * @param {number} taxRate - Tax rate as decimal
 * @returns {number} Total price with tax
 */
function calculateTotal(price, taxRate) {
  return price * (1 + taxRate);
}
```

## Error Handling

### Try-Catch Blocks
```javascript
try {
  const result = await riskyOperation();
  return result;
} catch (error) {
  logger.error('Operation failed', error);
  throw new CustomError('Operation failed', error);
}
```

### Error Messages
- Provide clear, actionable error messages
- Include relevant context
- Log errors appropriately
- Never expose sensitive information

## Testing Standards

### Test Coverage
- Minimum 80% code coverage
- 100% coverage for critical paths
- Test edge cases and error conditions

### Test Structure
```javascript
describe('UserService', () => {
  describe('getUserById', () => {
    it('should return user when ID exists', () => {
      // Arrange
      const userId = '123';

      // Act
      const user = userService.getUserById(userId);

      // Assert
      expect(user).toBeDefined();
      expect(user.id).toBe(userId);
    });
  });
});
```

## Security Standards

### Input Validation
- Always validate and sanitize user input
- Use parameterized queries for database operations
- Implement proper authentication and authorization
- Validate at every layer (defense in depth)

### Credential Management
- **Environment Variables**: Store all credentials in environment variables, never hardcode
- **Local Storage**: Use `.env` files for local development (automatically gitignored)
- **No Hardcoded Secrets**: No API tokens, passwords, or keys in source code
- **Personal Tokens**: Use personal API tokens, not shared accounts
- **Token Security**: Never embed credentials in URLs (prevents logging exposure)

### Configuration Security
```yaml
# ✅ Good: Use environment variable placeholders
api:
  token: ${API_TOKEN}

# ❌ Bad: Never hardcode credentials
api:
  token: "sk-1234567890abcdef"
```

### Sensitive Data Handling
- Never log sensitive information (passwords, tokens, PII)
- Encrypt sensitive data at rest and in transit
- Keep credentials out of chat messages and screenshots
- Never commit `.env` files to version control

### Gitignore Essentials
Ensure these patterns are in `.gitignore`:
```
.env
.env.local
.env.*.local
*.local.yaml
*.local.json
**/credentials.*
**/secrets.*
```

### User Control & Permissions
- Request minimal necessary permissions
- Allow users to audit permissions via `/permissions` command
- Respect user approval for network requests
- Document what data is accessed and why

## Performance Guidelines

### Optimization
- Optimize for readability first, then performance
- Profile before optimizing
- Cache expensive operations appropriately
- Use pagination for large datasets

### Async Operations
- Use async/await over callbacks
- Handle promise rejections properly
- Avoid blocking operations

## Version Control

### Commit Messages
- Use conventional commits format
- Keep messages clear and concise
- Reference issue numbers when applicable

### Branch Naming
- feature/description
- bugfix/description
- hotfix/description

## Code Review Checklist
- [ ] Follows naming conventions
- [ ] Properly documented
- [ ] Includes tests
- [ ] Handles errors appropriately
- [ ] No security vulnerabilities
- [ ] Performance considerations addressed
- [ ] No code duplication
- [ ] Follows PRISM principles

---
*PRISM Coding Standards - Ensuring Quality Through Consistency*