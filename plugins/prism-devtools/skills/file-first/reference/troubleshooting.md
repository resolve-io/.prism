# Troubleshooting File-First Approach

Common issues and solutions when using file-first patterns.

## Issue: Can't Find Files

### Symptom
Glob patterns return no results, or wrong files.

### Solutions

1. **Check path separators**
   ```bash
   # Windows paths need forward slashes in Glob
   ✅ Glob: "src/components/**/*.tsx"
   ❌ Glob: "src\components\**\*.tsx"
   ```

2. **Check working directory**
   ```bash
   # Verify where you're searching from
   pwd
   # Then use relative patterns from that location
   ```

3. **Broaden the pattern**
   ```bash
   # Too specific
   Glob: "src/features/auth/components/LoginForm.tsx"

   # Start broader
   Glob: "**/*Login*.tsx"
   ```

4. **Check case sensitivity**
   ```bash
   # Windows is case-insensitive, but patterns might not be
   Glob: "**/program.cs"  # May miss Program.cs on some systems
   Glob: "**/[Pp]rogram.cs"  # Case-insensitive pattern
   ```

---

## Issue: Too Many Files Found

### Symptom
Glob returns hundreds of files, overwhelming context.

### Solutions

1. **Exclude directories**
   ```bash
   # Exclude common noise
   Glob: "**/*.ts" --exclude "node_modules,dist,build"
   ```

2. **Be more specific**
   ```bash
   # Instead of
   Glob: "**/*.cs"

   # Use
   Glob: "src/Services/**/*.cs"
   ```

3. **Use multiple targeted globs**
   ```bash
   # Better than one broad glob
   Glob: "src/Controllers/*.cs"
   Glob: "src/Services/*.cs"
   # Read each category separately
   ```

---

## Issue: Grep Returns No Results

### Symptom
Searching for known text returns nothing.

### Solutions

1. **Check regex escaping**
   ```bash
   # Literal braces need escaping
   ✅ Grep: "interface\\{\\}"  # Finds interface{}
   ❌ Grep: "interface{}"      # Regex syntax error
   ```

2. **Check case sensitivity**
   ```bash
   # Use -i flag for case-insensitive
   Grep: "controller" -i  # Finds Controller, CONTROLLER, etc.
   ```

3. **Simplify the pattern**
   ```bash
   # Complex pattern
   Grep: "public\s+async\s+Task<.*>\s+\w+\("

   # Simpler (then refine)
   Grep: "async Task"
   ```

4. **Check file type filtering**
   ```bash
   # May be filtering too aggressively
   Grep: "pattern" --type cs  # Only .cs files
   Grep: "pattern"            # All files
   ```

---

## Issue: Context Too Large

### Symptom
Token limit reached, can't load all needed files.

### Solutions

1. **Use line limits**
   ```python
   # Read specific portions
   Read("file.cs", offset=100, limit=50)  # Lines 100-150
   ```

2. **Read only what you need**
   ```python
   # Instead of full file
   Read("LargeFile.cs")

   # Find the section first
   Grep: "public class UserService"  # Get line number
   Read("LargeFile.cs", offset=245, limit=100)  # Read that class
   ```

3. **Use the story's File List**
   - Story File List should be curated for the task
   - Trust it over broad searches

4. **Incremental loading**
   - Don't load everything upfront
   - Load as needed based on discoveries

---

## Issue: Wrong Project Type Detected

### Symptom
`analyze_codebase.py` detects wrong project type.

### Solutions

1. **Check root directory**
   - Run from repo root, not subdirectory
   - Multi-project repos may confuse detection

2. **Manual override**
   ```bash
   # Force project type
   python analyze_codebase.py /path/to/repo --type dotnet_backend
   ```

3. **Check for hybrid projects**
   - Frontend + Backend in same repo
   - Run analyzer on subdirectories separately

---

## Issue: Missing Architecture Documentation

### Symptom
Expected architecture docs don't exist.

### Solutions

1. **Use initialize-architecture skill**
   ```
   Run: /prism-devtools:initialize-architecture
   # Creates all required architecture docs
   ```

2. **Create from codebase analysis**
   ```
   Run: /prism-devtools:document-project
   # Generates documentation from actual code
   ```

3. **Work without docs (carefully)**
   - Read entry points and config directly
   - Build understanding from code
   - Document findings as you go

---

## Issue: Stale Context

### Symptom
AI references outdated information about files.

### Solutions

1. **Always re-read in new sessions**
   - Never trust remembered file contents
   - Fresh reads each session

2. **Re-read after writes**
   ```python
   # After editing
   Write("file.cs", content)

   # Verify the write
   Read("file.cs")
   ```

3. **Watch for "I remember..." statements**
   - If you catch yourself saying this, re-read instead
   - Memory of file contents is unreliable

---

## Issue: Can't Understand Codebase Structure

### Symptom
Files found but relationships unclear.

### Solutions

1. **Read entry point first**
   ```python
   # .NET
   Read("Program.cs")  # See DI registrations

   # Node
   Read("package.json")  # See scripts and entry
   Read("index.ts")      # See bootstrapping
   ```

2. **Follow imports/dependencies**
   ```python
   # Read a file
   Read("UserController.cs")
   # See: using App.Services.UserService

   # Follow the dependency
   Read("Services/UserService.cs")
   ```

3. **Use source-tree.md if available**
   ```python
   Read("docs/architecture/source-tree.md")
   # Shows directory structure with explanations
   ```

---

## Issue: Scripts Fail to Run

### Symptom
`analyze_codebase.py` or `validate_file_first.py` errors.

### Solutions

1. **Check Python version**
   ```bash
   python --version  # Needs Python 3.7+
   ```

2. **Check dependencies**
   ```bash
   # Scripts should be self-contained
   # If imports fail, check for missing packages
   pip install pathlib  # Example
   ```

3. **Check path formatting**
   ```bash
   # Windows vs Unix paths
   python analyze_codebase.py "C:/Dev/myproject"  # Use forward slashes
   ```

4. **Run from correct directory**
   ```bash
   # Run from skills/file-first/scripts/
   cd "C:/Dev/.prism/plugins/prism-devtools/skills/file-first/scripts"
   python analyze_codebase.py /path/to/repo
   ```

---

## Quick Diagnostics

### Check Your Context

```
Questions to ask:
1. What's the current working directory?
2. What project type is this?
3. What files have I actually read (not assumed)?
4. Is my context from this session or memory?
5. What does the story File List say?
```

### Verify File-First Compliance

```
Checklist:
[ ] Am I reading files directly (not relying on summaries)?
[ ] Am I citing sources for claims about code?
[ ] Did I re-read files this session (not from memory)?
[ ] Am I using Glob/Grep (not guessing paths)?
[ ] Is my context fresh (not stale)?
```

### When to Escalate

If these issues persist:
1. Check if repo structure is non-standard
2. Consider if project is too large for file-first
3. Discuss with user about best approach
4. Document the issue for future reference
