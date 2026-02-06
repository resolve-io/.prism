# Target Repository Patterns

Common file patterns for different project types. Use these to quickly identify project structure and key files to read.

## Project Type Detection

### .NET Backend (`dotnet_backend`)

**Indicators:**
- `*.csproj` files present
- `Program.cs` entry point
- `appsettings.json` configuration

**Key Files:**
```yaml
entryPoints:
  - "**/Program.cs"
  - "**/Startup.cs"

configuration:
  - "**/appsettings.json"
  - "**/appsettings.*.json"
  - "**/*.csproj"

architecture:
  - "**/Controllers/**/*.cs"
  - "**/Services/**/*.cs"
  - "**/Models/**/*.cs"
  - "**/Data/**/*.cs"

tests:
  - "**/*Tests.cs"
  - "**/*Test.cs"
  - "**/Tests/**/*.cs"
```

**Read Order:**
1. `*.csproj` - Dependencies and project structure
2. `Program.cs` - Entry point and DI setup
3. `appsettings.json` - Configuration
4. `Controllers/` - API surface
5. `Services/` - Business logic

---

### React Frontend (`react_frontend`)

**Indicators:**
- `package.json` with `react` dependency
- `src/App.tsx` or `src/App.jsx`
- May have `vite.config.ts`, `webpack.config.js`, or CRA structure

**Key Files:**
```yaml
entryPoints:
  - "**/src/main.tsx"
  - "**/src/index.tsx"
  - "**/src/App.tsx"
  - "**/src/main.jsx"
  - "**/src/index.jsx"
  - "**/src/App.jsx"

configuration:
  - "package.json"
  - "tsconfig.json"
  - "**/vite.config.*"
  - "**/webpack.config.*"
  - "**/.env.example"
  - "**/tailwind.config.*"

architecture:
  - "**/src/components/**/*"
  - "**/src/pages/**/*"
  - "**/src/views/**/*"
  - "**/src/hooks/**/*"
  - "**/src/context/**/*"
  - "**/src/store/**/*"
  - "**/src/services/**/*"
  - "**/src/api/**/*"
  - "**/src/utils/**/*"
  - "**/src/types/**/*"

styles:
  - "**/src/styles/**/*"
  - "**/src/index.css"
  - "**/src/App.css"
  - "**/tailwind.config.*"

tests:
  - "**/*.test.tsx"
  - "**/*.test.ts"
  - "**/*.spec.tsx"
  - "**/*.spec.ts"
  - "**/__tests__/**/*"
```

**Read Order:**
1. `package.json` - Dependencies, scripts, React version
2. `vite.config.ts` or build config - Build setup
3. `src/main.tsx` or `src/index.tsx` - Entry point, providers
4. `src/App.tsx` - Root component, routing
5. `src/components/` - Reusable components
6. `src/pages/` or `src/views/` - Page components
7. `src/hooks/` - Custom hooks
8. `src/context/` or `src/store/` - State management
9. `src/services/` or `src/api/` - API integration

---

### Next.js (`nextjs_fullstack`)

**Indicators:**
- `package.json` with `next` dependency
- `next.config.js` or `next.config.mjs`
- `app/` or `pages/` directory structure

**Key Files:**
```yaml
entryPoints:
  - "**/app/layout.tsx"
  - "**/app/page.tsx"
  - "**/pages/_app.tsx"
  - "**/pages/index.tsx"

configuration:
  - "package.json"
  - "next.config.*"
  - "tsconfig.json"
  - "**/.env.example"
  - "**/tailwind.config.*"

architecture:
  - "**/app/**/*.tsx"
  - "**/pages/**/*.tsx"
  - "**/components/**/*"
  - "**/lib/**/*"
  - "**/hooks/**/*"
  - "**/api/**/*"

tests:
  - "**/*.test.tsx"
  - "**/*.spec.tsx"
  - "**/__tests__/**/*"
```

**Read Order:**
1. `package.json` - Dependencies and scripts
2. `next.config.js` - Next.js configuration
3. `app/layout.tsx` or `pages/_app.tsx` - Root layout
4. `app/page.tsx` or `pages/index.tsx` - Home page
5. `components/` - Shared components
6. `lib/` - Utilities and helpers
7. `api/` routes - Backend endpoints

---

### TypeScript/Node Backend (`typescript_backend`)

**Indicators:**
- `package.json` present
- `tsconfig.json` present
- Express, Fastify, NestJS backend (no React)

**Key Files:**
```yaml
entryPoints:
  - "**/src/index.ts"
  - "**/src/main.ts"
  - "**/src/app.ts"
  - "**/src/server.ts"

configuration:
  - "package.json"
  - "tsconfig.json"
  - "**/.env.example"

architecture:
  - "**/src/routes/**/*"
  - "**/src/controllers/**/*"
  - "**/src/services/**/*"
  - "**/src/models/**/*"
  - "**/src/middleware/**/*"

tests:
  - "**/*.test.ts"
  - "**/*.spec.ts"
  - "**/__tests__/**/*"
```

**Read Order:**
1. `package.json` - Dependencies and scripts
2. `tsconfig.json` - TypeScript configuration
3. Entry point (`src/index.ts`, `src/server.ts`)
4. `src/routes/` - API routes
5. `src/controllers/` - Request handlers
6. `src/services/` - Business logic

---

### Python Backend (`python_backend`)

**Indicators:**
- `requirements.txt` or `pyproject.toml`
- `main.py` or `app.py`
- May have `setup.py`, `setup.cfg`

**Key Files:**
```yaml
entryPoints:
  - "**/main.py"
  - "**/app.py"
  - "**/__main__.py"

configuration:
  - "requirements.txt"
  - "pyproject.toml"
  - "setup.py"
  - "setup.cfg"
  - "**/.env.example"

architecture:
  - "**/api/**/*.py"
  - "**/routes/**/*.py"
  - "**/models/**/*.py"
  - "**/services/**/*.py"
  - "**/core/**/*.py"

tests:
  - "**/test_*.py"
  - "**/*_test.py"
  - "**/tests/**/*.py"
```

**Read Order:**
1. `pyproject.toml` or `requirements.txt` - Dependencies
2. Entry point (`main.py`, `app.py`)
3. `api/` or `routes/` - API surface
4. `models/` - Data models
5. `services/` - Business logic

---

### Java Backend (`java_backend`)

**Indicators:**
- `pom.xml` (Maven) or `build.gradle` (Gradle)
- `src/main/java` structure
- `Application.java` entry point

**Key Files:**
```yaml
entryPoints:
  - "**/*Application.java"
  - "**/Main.java"

configuration:
  - "pom.xml"
  - "build.gradle"
  - "**/application.yml"
  - "**/application.properties"

architecture:
  - "**/controller/**/*.java"
  - "**/service/**/*.java"
  - "**/repository/**/*.java"
  - "**/model/**/*.java"
  - "**/entity/**/*.java"

tests:
  - "**/*Test.java"
  - "**/*Tests.java"
  - "**/test/**/*.java"
```

**Read Order:**
1. `pom.xml` or `build.gradle` - Dependencies
2. `Application.java` - Entry point
3. `application.yml` - Configuration
4. `controller/` - API surface
5. `service/` - Business logic

---

### Go Backend (`go_backend`)

**Indicators:**
- `go.mod` present
- `main.go` entry point
- `cmd/` directory structure

**Key Files:**
```yaml
entryPoints:
  - "**/main.go"
  - "**/cmd/**/main.go"

configuration:
  - "go.mod"
  - "go.sum"
  - "**/config/**/*.go"
  - "**/*.yaml"
  - "**/*.toml"

architecture:
  - "**/internal/**/*.go"
  - "**/pkg/**/*.go"
  - "**/api/**/*.go"
  - "**/handlers/**/*.go"

tests:
  - "**/*_test.go"
```

**Read Order:**
1. `go.mod` - Dependencies and module path
2. `main.go` or `cmd/*/main.go` - Entry point
3. `internal/` - Private packages
4. `pkg/` - Public packages
5. `api/` or `handlers/` - API surface

---

### Rust Backend (`rust_backend`)

**Indicators:**
- `Cargo.toml` present
- `src/main.rs` entry point
- `src/lib.rs` for libraries

**Key Files:**
```yaml
entryPoints:
  - "**/main.rs"
  - "**/lib.rs"

configuration:
  - "Cargo.toml"
  - "Cargo.lock"
  - "**/config/**/*.rs"

architecture:
  - "**/src/**/*.rs"
  - "**/api/**/*.rs"
  - "**/handlers/**/*.rs"
  - "**/models/**/*.rs"

tests:
  - "**/tests/**/*.rs"
  - "**/src/**/*_test.rs"
```

**Read Order:**
1. `Cargo.toml` - Dependencies and crate info
2. `src/main.rs` or `src/lib.rs` - Entry point
3. `src/` module structure
4. Key modules based on `mod` declarations

---

## Universal Patterns

### Documentation

Always check for:
```yaml
documentation:
  - "README.md"
  - "docs/**/*.md"
  - "CONTRIBUTING.md"
  - "ARCHITECTURE.md"
  - "docs/architecture/**/*.md"
```

### CI/CD

Understand build process:
```yaml
cicd:
  - ".github/workflows/**/*.yml"
  - ".gitlab-ci.yml"
  - "azure-pipelines.yml"
  - "Jenkinsfile"
  - "Dockerfile"
  - "docker-compose.yml"
```

### Configuration Management

Environment and secrets:
```yaml
config:
  - "**/.env.example"
  - "**/*.env.template"
  - "**/config/**/*"
  - "**/settings/**/*"
```

## Using Patterns

### With Glob Tool

**.NET Examples:**
```bash
# Find all entry points for .NET
Glob: "**/Program.cs"

# Find all configuration files
Glob: "**/appsettings*.json"

# Find all tests
Glob: "**/*Test*.cs"
```

**React/Frontend Examples:**
```bash
# Find all React components
Glob: "**/src/components/**/*.tsx"

# Find all hooks
Glob: "**/src/hooks/*.ts"

# Find all page components
Glob: "**/src/pages/**/*.tsx"

# Find entry points
Glob: "**/src/main.tsx"
Glob: "**/src/App.tsx"

# Find all tests
Glob: "**/*.test.tsx"
Glob: "**/__tests__/**/*"

# Find configuration
Glob: "**/vite.config.*"
Glob: "**/tailwind.config.*"
```

**Next.js Examples:**
```bash
# Find all page routes (App Router)
Glob: "**/app/**/page.tsx"

# Find all layouts
Glob: "**/app/**/layout.tsx"

# Find API routes
Glob: "**/app/api/**/*.ts"
Glob: "**/pages/api/**/*.ts"
```

### With Grep Tool

**.NET Examples:**
```bash
# Find service registrations
Grep: "AddScoped|AddSingleton|AddTransient"

# Find API endpoints
Grep: "\[HttpGet\]|\[HttpPost\]|\[Route\]"

# Find configuration usage
Grep: "IConfiguration|appsettings"
```

**React/Frontend Examples:**
```bash
# Find component definitions
Grep: "export (const|function|default)"

# Find React hooks usage
Grep: "use(State|Effect|Context|Memo|Callback|Ref)"

# Find API calls
Grep: "fetch\(|axios\.|useSWR|useQuery"

# Find route definitions
Grep: "<Route|createBrowserRouter|useNavigate"

# Find context providers
Grep: "createContext|useContext|Provider"

# Find Redux/Zustand stores
Grep: "createSlice|createStore|create\("
```

**Next.js Examples:**
```bash
# Find server components
Grep: "'use server'|\"use server\""

# Find client components
Grep: "'use client'|\"use client\""

# Find data fetching
Grep: "getServerSideProps|getStaticProps|fetch\("
```

## Pattern Selection Logic

```python
def suggest_patterns(detected_type: str) -> dict:
    patterns = PROJECT_PATTERNS.get(detected_type, {})
    return {
        "key_files": patterns.get("entryPoints", []) + patterns.get("configuration", []),
        "architecture_files": patterns.get("architecture", []),
        "test_files": patterns.get("tests", []),
        "read_order": patterns.get("read_order", [])
    }
```
