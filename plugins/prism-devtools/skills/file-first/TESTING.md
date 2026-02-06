# Testing the File-First Skill

## Quick Test Commands

### 1. Test Project Type Detection

Run the analyzer against any repository:

```bash
# Basic usage (markdown output)
python "C:/Dev/.prism/plugins/prism-devtools/skills/file-first/scripts/analyze_codebase.py" "C:/path/to/repo"

# JSON output for programmatic use
python "C:/Dev/.prism/plugins/prism-devtools/skills/file-first/scripts/analyze_codebase.py" "C:/path/to/repo" --format json

# Force a specific project type
python "C:/Dev/.prism/plugins/prism-devtools/skills/file-first/scripts/analyze_codebase.py" "C:/path/to/repo" --type react_frontend
```

### 2. Test Story Validation

Run the validator against a story file:

```bash
# Basic usage
python "C:/Dev/.prism/plugins/prism-devtools/skills/file-first/scripts/validate_file_first.py" --story "C:/path/to/story.md"

# JSON output
python "C:/Dev/.prism/plugins/prism-devtools/skills/file-first/scripts/validate_file_first.py" --story "C:/path/to/story.md" --format json
```

---

## Expected Detection Results

| Repository Type | Expected `project_type` | Key Files Found |
|-----------------|------------------------|-----------------|
| React + Vite | `react_frontend` | `package.json`, `vite.config.ts`, `src/App.tsx` |
| React + CRA | `react_frontend` | `package.json`, `src/App.tsx` |
| Next.js | `nextjs_fullstack` | `package.json`, `next.config.js`, `app/` or `pages/` |
| .NET API | `dotnet_backend` | `*.csproj`, `Program.cs`, `appsettings.json` |
| Express/Node | `typescript_backend` | `package.json`, `tsconfig.json`, `src/index.ts` |
| Python Flask/FastAPI | `python_backend` | `requirements.txt`, `main.py` |

---

## Manual Testing Checklist

### Test 1: React Project Detection

1. Navigate to a React project (with `react` in package.json)
2. Run: `python analyze_codebase.py /path/to/react-project`
3. Verify:
   - [ ] `project_type` is `react_frontend`
   - [ ] `key_files.entry_points` includes `src/App.tsx` or `src/main.tsx`
   - [ ] `key_files.configuration` includes `package.json`, `vite.config.*`
   - [ ] `suggested_read_order` starts with package.json

### Test 2: .NET Project Detection

1. Navigate to a .NET project (with `*.csproj` files)
2. Run: `python analyze_codebase.py /path/to/dotnet-project`
3. Verify:
   - [ ] `project_type` is `dotnet_backend`
   - [ ] `key_files.entry_points` includes `Program.cs`
   - [ ] `key_files.configuration` includes `appsettings.json`

### Test 3: Next.js Detection (should NOT be React)

1. Navigate to a Next.js project (has `next.config.js`)
2. Run: `python analyze_codebase.py /path/to/nextjs-project`
3. Verify:
   - [ ] `project_type` is `nextjs_fullstack` (NOT `react_frontend`)
   - [ ] `key_files.entry_points` includes `app/layout.tsx` or `pages/_app.tsx`

### Test 4: Story Validation

1. Find a completed story file with File List and Debug Log
2. Run: `python validate_file_first.py --story /path/to/story.md`
3. Verify:
   - [ ] Score reflects presence/absence of source citations
   - [ ] File List check passes if section exists with files
   - [ ] Architecture references detected if present

---

## Testing in Claude Code

### Test Skill Activation

Say any of these phrases to Claude Code to trigger the skill:

- "analyze this codebase"
- "what files should I read"
- "load context for this repo"
- "file-first approach"
- "understand the project structure"

### Verify Agent Principles

After activating a PRISM persona (`/dev`, `/qa`, `/sm`), check that `file_first_principles` appear in the persona's behavior:

1. Activate: `/dev`
2. Ask: "What are your file-first principles?"
3. Should list principles like:
   - Read source files directly
   - Story file is SINGLE SOURCE OF TRUTH
   - Use Read/Glob/Grep tools
   - Cite sources with `[Source: path]`

---

## Creating Test Fixtures

To create minimal test fixtures for automated testing:

### React Fixture (`fixtures/react-app/`)

```
fixtures/react-app/
├── package.json          # Must contain "react"
├── tsconfig.json
├── vite.config.ts
└── src/
    ├── main.tsx
    └── App.tsx
```

**package.json content:**
```json
{
  "name": "test-react-app",
  "dependencies": {
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  }
}
```

### .NET Fixture (`fixtures/dotnet-api/`)

```
fixtures/dotnet-api/
├── MyApi.csproj
├── Program.cs
├── appsettings.json
└── Controllers/
    └── WeatherController.cs
```

### Next.js Fixture (`fixtures/nextjs-app/`)

```
fixtures/nextjs-app/
├── package.json          # Must contain "next"
├── next.config.js
├── tsconfig.json
└── app/
    ├── layout.tsx
    └── page.tsx
```

---

## Troubleshooting Tests

### "unknown" project type returned

- Check if required files exist at repo root
- For React: Verify `package.json` contains the string "react"
- Try `--format json` to see detection scores

### Wrong project type detected

- Check detection scores in JSON output
- Higher score = more confident match
- React vs Next.js: Next.js has `next.config.js` exclude rule

### Script errors

- Ensure Python 3.7+ is installed
- Run from correct directory
- Use forward slashes in paths even on Windows

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (or PASS/NEEDS_REVIEW for validator) |
| 1 | Error (file not found, invalid args) |
| 2 | FAIL status (validator only) |
