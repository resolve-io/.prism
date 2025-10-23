# Security Best Practices

This document outlines the security measures implemented in the PRISM plugin for Claude Code.

## Credential Management

### Environment Variables
All sensitive credentials are stored in environment variables, never hardcoded in source files:

```yaml
# core-config.yaml
jira:
  email: ${JIRA_EMAIL}      # Reads from environment
  token: ${JIRA_API_TOKEN}  # Reads from environment
```

### Local Storage Only
- Credentials are stored in your local `.env` file
- The `.env` file is automatically excluded via `.gitignore`
- Credentials never leave your local machine
- No credentials are transmitted to the plugin repository

### Setup Process
1. Copy `.env.example` to `.env` (gitignored)
2. Add your personal credentials to `.env`
3. The plugin reads credentials through `core-config.yaml` placeholders

## What's Protected

### Gitignored Files
The following files are automatically excluded from git:
```
.env
.env.local
.env.*.local
.jira-token
jira-config.local.yaml
*.local.yaml
*.local.json
```

### No Hardcoded Secrets
- No API tokens in source code
- No passwords in configuration files
- No credentials in documentation examples
- No embedded credentials in URLs

## Claude Code Security Features

### Permission-Based Architecture
Claude Code's permission system controls:
- Network requests to external APIs
- File access and modifications
- Command execution
- Credential access

### Encrypted Storage
- macOS: Credentials stored in encrypted Keychain
- All platforms: Secure credential storage per Claude Code standards

### User Control
- Users approve all network requests
- Users control credential access
- Users can audit permissions with `/permissions`
- Users can revoke access at any time

## Best Practices for Users

### Do's
✅ Store credentials in `.env` file
✅ Use personal API tokens (not shared accounts)
✅ Review permission requests before approving
✅ Keep credentials out of chat messages
✅ Audit permissions regularly with `/permissions`
✅ Use project-specific permissions for sensitive repos

### Don'ts
❌ Never commit `.env` file to git
❌ Never hardcode credentials in config files
❌ Never share `.env` file with others
❌ Never include credentials in screenshots or logs
❌ Never use production credentials in development

## Jira Integration Security

### Authentication Method
- Uses Jira REST API with Basic Authentication
- Credentials passed via secure Authorization headers
- No credentials embedded in URLs (prevents logging exposure)

### Read-Only Access
- Plugin only reads Jira data
- No write, update, or delete operations
- Minimal API surface area reduces risk

### User Consent
- Users must explicitly configure Jira integration
- Optional feature (disabled by default)
- Users control which issues are accessed

## Reporting Security Issues

If you discover a security vulnerability:

1. **Do NOT** open a public GitHub issue
2. Email security concerns to the maintainers
3. Include detailed reproduction steps
4. Allow reasonable time for fixes before disclosure

## Compliance

This plugin follows:
- Claude Code security guidelines
- Environment variable best practices
- Secure credential storage standards
- Permission-based access control patterns

## References

- [Claude Code Security Documentation](https://docs.claude.com/en/docs/claude-code/security)
- [Claude Code IAM Guide](https://docs.claude.com/en/docs/claude-code/iam)
- [Claude Code Network Configuration](https://docs.claude.com/en/docs/claude-code/network-config)

---

**Security is a shared responsibility.** This plugin provides secure defaults, but users must follow best practices for credential management and permission control.
