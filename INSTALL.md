# Installing PRISM Plugin for Resolve Team

This guide is for Resolve team members to install the PRISM Development System plugin in Claude Code.

## Prerequisites

- Claude Code installed
- Access to Resolve GitHub organization (resolve-io/.prism)

## Installation Steps

### Option 1: Via Marketplace (Recommended)

1. Open Claude Code
2. Add the PRISM marketplace by typing:
   ```
   /plugin marketplace add resolve-io/.prism
   ```
3. Install the plugin:
   ```
   /plugin install prism-devtools
   ```
   Or use the interactive menu: `/plugin` → Browse Plugins → Install prism-devtools
4. Restart Claude Code

The plugin will be installed and automatically activated.

### Option 2: Manual Clone (For Development)

If you want to modify the plugin or test changes:

```bash
# Clone to Claude Code plugins directory
cd ~/.claude-code/plugins  # macOS/Linux
# or: cd %APPDATA%/ClaudeCode/plugins  # Windows

git clone https://github.com/resolve-io/.prism.git prism-devtools
```

Then restart Claude Code.

## Verification

After installation, verify the plugin is active:

1. Type `/` in Claude Code - you should see PRISM commands:
   - `/architect`
   - `/dev`
   - `/qa`
   - `/po`
   - `/sm`
   - `/peer`
   - `/support`

2. Or check Settings → Plugins and confirm "prism-devtools" is listed and enabled

## Jira Integration (Optional)

To enable Jira integration with Resolve's Atlassian instance:

1. Copy `.env.example` to `.env` in the plugin directory
2. Get your Jira API token: https://id.atlassian.com/manage-profile/security/api-tokens
3. Edit `.env`:
   ```
   JIRA_EMAIL=your.email@resolve.io
   JIRA_API_TOKEN=your-api-token-here
   ```

The plugin is pre-configured for Resolve's Jira:
- Base URL: `https://resolvesys.atlassian.net`
- Default Project: `PLAT`

## Usage

### Slash Commands

Invoke specialized agents:
```
/architect    # System architecture and design
/dev          # Development with TDD workflow
/qa           # Quality assurance and testing
/po           # Product owner and requirements
/sm           # Story sizing and planning
/peer         # Code review and mentoring
/support      # Issue validation and support
```

### Auto-Activation

Skills automatically activate based on context:
- Mention "design architecture" → Architect skill loads
- Mention "implement story" → Dev skill loads
- Mention "validate issue" → Support skill loads

### Jira Context

When configured, agents automatically detect and fetch Jira issues:
```
User: "Let's work on PLAT-123"
Agent: *Automatically fetches PLAT-123 context and displays issue details*
```

## Troubleshooting

### Plugin Not Found
- Ensure you have access to the resolve-io GitHub organization
- Try authenticating GitHub CLI: `gh auth login`

### Commands Not Showing
- Restart Claude Code after installation
- Check Settings → Plugins to confirm plugin is enabled

### Jira Not Working
- Verify `.env` file is in the plugin directory (not the repository root)
- Confirm your API token is valid
- Check JIRA_EMAIL matches your Atlassian account

## Updates

To update the plugin:

**If installed via Git:**
- Settings → Plugins → Find "prism-devtools" → Click Update

**If manually cloned:**
```bash
cd ~/.claude-code/plugins/prism-devtools  # or Windows path
git pull origin main
```

Then restart Claude Code.

## Support

- **Issues**: https://github.com/resolve-io/.prism/issues
- **Documentation**: See README.md and docs/ directory
- **Internal**: Ask in #engineering Slack channel

---

**Version**: 1.0.0
**Repository**: https://github.com/resolve-io/.prism
