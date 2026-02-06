#!/usr/bin/env python3
"""
Analyze a codebase to detect project type and suggest key files to read.

Usage:
    python analyze_codebase.py /path/to/repo
    python analyze_codebase.py /path/to/repo --format json
    python analyze_codebase.py /path/to/repo --type dotnet_backend  # Force type
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Project type detection patterns
PROJECT_INDICATORS = {
    "dotnet_aspire": {
        "required": ["**/*.csproj"],
        "required_any": ["**/*.AppHost/*.csproj", "**/AppHost/*.csproj", "**/*AppHost.csproj"],
        "optional": ["**/*.ServiceDefaults/*.csproj", "**/ServiceDefaults/*.csproj", "*.sln"],
        "weight": 0
    },
    "dotnet_backend": {
        "required": ["**/*.csproj"],
        "optional": ["**/Program.cs", "**/appsettings.json", "**/Startup.cs", "*.sln"],
        "weight": 0
    },
    "react_frontend": {
        "required": ["package.json"],
        "required_content": {"package.json": "react"},
        "optional": ["src/App.tsx", "src/App.jsx", "vite.config.ts", "src/main.tsx", "src/index.tsx"],
        "exclude": ["next.config.js", "next.config.mjs"],
        "weight": 0
    },
    "nextjs_fullstack": {
        "required": ["package.json"],
        "required_any": ["next.config.js", "next.config.mjs", "next.config.ts"],
        "optional": ["app/layout.tsx", "pages/_app.tsx", "app/page.tsx"],
        "weight": 0
    },
    "typescript_backend": {
        "required": ["package.json", "tsconfig.json"],
        "exclude": ["src/App.tsx", "src/App.jsx", "next.config.js"],
        "optional": ["src/index.ts", "src/server.ts", "src/app.ts"],
        "weight": 0
    },
    "javascript_fullstack": {
        "required": ["package.json"],
        "exclude": ["tsconfig.json"],
        "optional": ["index.js", "src/index.js"],
        "weight": 0
    },
    "python_backend": {
        "required_any": ["requirements.txt", "pyproject.toml", "setup.py"],
        "optional": ["main.py", "app.py", "__main__.py"],
        "weight": 0
    },
    "java_backend": {
        "required_any": ["pom.xml", "build.gradle"],
        "optional": ["src/main/java", "Application.java"],
        "weight": 0
    },
    "go_backend": {
        "required": ["go.mod"],
        "optional": ["main.go", "cmd/"],
        "weight": 0
    },
    "rust_backend": {
        "required": ["Cargo.toml"],
        "optional": ["src/main.rs", "src/lib.rs"],
        "weight": 0
    }
}


# Key files by project type
KEY_FILES = {
    "dotnet_aspire": {
        "entry_points": ["**/*.AppHost/Program.cs", "**/AppHost/Program.cs"],
        "configuration": ["**/*.AppHost/appsettings.json", "**/appsettings.json", "**/*.csproj", "*.sln"],
        "orchestration": ["**/*.AppHost/*.cs", "**/AppHost/*.cs"],
        "service_defaults": ["**/*.ServiceDefaults/*.cs", "**/ServiceDefaults/*.cs"],
        "services": ["**/*.Api/Program.cs", "**/*.Gui/Program.cs", "**/*.MigrationService/Program.cs"],
        "docs": ["README.md", "docs/**/*.md"]
    },
    "dotnet_backend": {
        "entry_points": ["**/Program.cs", "**/Startup.cs"],
        "configuration": ["**/appsettings.json", "**/appsettings.*.json", "**/*.csproj"],
        "architecture": ["**/Controllers/**/*.cs", "**/Services/**/*.cs"],
        "docs": ["README.md", "docs/**/*.md"]
    },
    "react_frontend": {
        "entry_points": ["**/src/main.tsx", "**/src/index.tsx", "**/src/App.tsx", "**/src/main.jsx", "**/src/index.jsx"],
        "configuration": ["package.json", "tsconfig.json", "**/vite.config.*", "**/tailwind.config.*"],
        "architecture": ["**/src/components/**/*", "**/src/pages/**/*", "**/src/hooks/**/*", "**/src/context/**/*", "**/src/store/**/*"],
        "styles": ["**/src/styles/**/*", "**/src/index.css", "**/src/App.css"],
        "docs": ["README.md", "docs/**/*.md"]
    },
    "nextjs_fullstack": {
        "entry_points": ["**/app/layout.tsx", "**/app/page.tsx", "**/pages/_app.tsx", "**/pages/index.tsx"],
        "configuration": ["package.json", "next.config.*", "tsconfig.json", "**/tailwind.config.*"],
        "architecture": ["**/app/**/*.tsx", "**/pages/**/*.tsx", "**/components/**/*", "**/lib/**/*"],
        "docs": ["README.md", "docs/**/*.md"]
    },
    "typescript_backend": {
        "entry_points": ["**/src/index.ts", "**/src/main.ts", "**/src/server.ts", "**/src/app.ts"],
        "configuration": ["package.json", "tsconfig.json"],
        "architecture": ["**/src/routes/**/*", "**/src/controllers/**/*", "**/src/services/**/*"],
        "docs": ["README.md", "docs/**/*.md"]
    },
    "javascript_fullstack": {
        "entry_points": ["**/index.js", "**/main.js", "**/app.js"],
        "configuration": ["package.json", "**/config/**/*"],
        "architecture": ["**/src/**/*.js"],
        "docs": ["README.md", "docs/**/*.md"]
    },
    "python_backend": {
        "entry_points": ["**/main.py", "**/app.py", "**/__main__.py"],
        "configuration": ["requirements.txt", "pyproject.toml", "setup.py"],
        "architecture": ["**/api/**/*.py", "**/routes/**/*.py", "**/models/**/*.py"],
        "docs": ["README.md", "docs/**/*.md"]
    },
    "java_backend": {
        "entry_points": ["**/*Application.java", "**/Main.java"],
        "configuration": ["pom.xml", "build.gradle", "**/application.yml"],
        "architecture": ["**/controller/**/*.java", "**/service/**/*.java"],
        "docs": ["README.md", "docs/**/*.md"]
    },
    "go_backend": {
        "entry_points": ["**/main.go", "**/cmd/**/main.go"],
        "configuration": ["go.mod", "go.sum"],
        "architecture": ["**/internal/**/*.go", "**/pkg/**/*.go"],
        "docs": ["README.md", "docs/**/*.md"]
    },
    "rust_backend": {
        "entry_points": ["**/main.rs", "**/lib.rs"],
        "configuration": ["Cargo.toml"],
        "architecture": ["**/src/**/*.rs"],
        "docs": ["README.md", "docs/**/*.md"]
    }
}


# Suggested read order by project type
READ_ORDER = {
    "dotnet_aspire": [
        "1. *.sln - Solution structure and projects",
        "2. *.AppHost/Program.cs - Orchestration entry point, service registration",
        "3. *.AppHost/appsettings.json - Aspire configuration",
        "4. *.ServiceDefaults/ - Shared service configuration (telemetry, health checks)",
        "5. Individual service projects (*.Api, *.Gui, etc.) - Service implementations",
        "6. docs/architecture/*.md - Design decisions"
    ],
    "dotnet_backend": [
        "1. *.csproj - Dependencies and project structure",
        "2. Program.cs - Entry point and DI setup",
        "3. appsettings.json - Configuration",
        "4. docs/architecture/*.md - Design decisions",
        "5. Controllers/ - API surface",
        "6. Services/ - Business logic"
    ],
    "react_frontend": [
        "1. package.json - Dependencies, scripts, React version",
        "2. vite.config.ts or build config - Build setup",
        "3. src/main.tsx or src/index.tsx - Entry point, providers",
        "4. src/App.tsx - Root component, routing",
        "5. src/components/ - Reusable components",
        "6. src/pages/ or src/views/ - Page components",
        "7. src/hooks/ - Custom hooks",
        "8. src/context/ or src/store/ - State management",
        "9. src/services/ or src/api/ - API integration"
    ],
    "nextjs_fullstack": [
        "1. package.json - Dependencies and scripts",
        "2. next.config.js - Next.js configuration",
        "3. app/layout.tsx or pages/_app.tsx - Root layout",
        "4. app/page.tsx or pages/index.tsx - Home page",
        "5. components/ - Shared components",
        "6. lib/ - Utilities and helpers",
        "7. api/ routes - Backend endpoints"
    ],
    "typescript_backend": [
        "1. package.json - Dependencies and scripts",
        "2. tsconfig.json - TypeScript configuration",
        "3. Entry point (src/index.ts, src/server.ts)",
        "4. src/routes/ - API routes",
        "5. src/controllers/ - Request handlers",
        "6. src/services/ - Business logic"
    ],
    "python_backend": [
        "1. pyproject.toml or requirements.txt - Dependencies",
        "2. main.py or app.py - Entry point",
        "3. docs/architecture/*.md - Design decisions",
        "4. api/ or routes/ - API surface",
        "5. models/ - Data models",
        "6. services/ - Business logic"
    ],
    "java_backend": [
        "1. pom.xml or build.gradle - Dependencies",
        "2. Application.java - Entry point",
        "3. application.yml - Configuration",
        "4. docs/architecture/*.md - Design decisions",
        "5. controller/ - API surface",
        "6. service/ - Business logic"
    ],
    "go_backend": [
        "1. go.mod - Dependencies and module path",
        "2. main.go or cmd/*/main.go - Entry point",
        "3. docs/architecture/*.md - Design decisions",
        "4. internal/ - Private packages",
        "5. pkg/ - Public packages"
    ],
    "rust_backend": [
        "1. Cargo.toml - Dependencies and crate info",
        "2. src/main.rs or src/lib.rs - Entry point",
        "3. docs/architecture/*.md - Design decisions",
        "4. src/ module structure"
    ]
}


def glob_match(root: Path, pattern: str) -> List[Path]:
    """Simple glob matching from root directory."""
    return list(root.glob(pattern))


def check_file_contains(repo_path: Path, filename: str, content: str) -> bool:
    """Check if a file contains specific content."""
    matches = glob_match(repo_path, filename)
    for match in matches:
        try:
            file_content = match.read_text(encoding="utf-8")
            if content in file_content:
                return True
        except Exception:
            pass
    return False


def detect_project_type(repo_path: Path) -> Tuple[str, Dict]:
    """Detect project type based on file indicators."""
    scores = {}

    for project_type, indicators in PROJECT_INDICATORS.items():
        score = 0

        # Check required files
        if "required" in indicators:
            all_found = True
            for pattern in indicators["required"]:
                if not glob_match(repo_path, pattern):
                    all_found = False
                    break
            if all_found:
                score += 10
            else:
                continue  # Skip this type if required files missing

        # Check required_any (at least one must exist)
        if "required_any" in indicators:
            any_found = False
            for pattern in indicators["required_any"]:
                if glob_match(repo_path, pattern):
                    any_found = True
                    break
            if any_found:
                score += 10
            else:
                continue

        # Check required_content (file must contain specific text)
        if "required_content" in indicators:
            content_found = True
            for filename, content in indicators["required_content"].items():
                if not check_file_contains(repo_path, filename, content):
                    content_found = False
                    break
            if content_found:
                score += 15  # Higher weight for content match
            else:
                continue

        # Check exclude patterns
        if "exclude" in indicators:
            excluded = False
            for pattern in indicators["exclude"]:
                if glob_match(repo_path, pattern):
                    excluded = True
                    break
            if excluded:
                continue

        # Check optional files
        if "optional" in indicators:
            for pattern in indicators["optional"]:
                if glob_match(repo_path, pattern):
                    score += 2

        scores[project_type] = score

    if not scores:
        return "unknown", {}

    best_type = max(scores.keys(), key=lambda k: scores[k])
    return best_type, scores


def find_existing_files(repo_path: Path, patterns: List[str]) -> List[str]:
    """Find files that actually exist matching the patterns."""
    found = []
    for pattern in patterns:
        matches = glob_match(repo_path, pattern)
        for match in matches[:5]:  # Limit results
            rel_path = match.relative_to(repo_path)
            found.append(str(rel_path).replace("\\", "/"))
    return found


def analyze_codebase(repo_path: str, force_type: Optional[str] = None) -> Dict:
    """Analyze codebase and return analysis results."""
    path = Path(repo_path).resolve()

    if not path.exists():
        return {"error": f"Path does not exist: {repo_path}"}

    if not path.is_dir():
        return {"error": f"Path is not a directory: {repo_path}"}

    # Detect or use forced project type
    if force_type:
        project_type = force_type
        detection_scores = {"forced": force_type}
    else:
        project_type, detection_scores = detect_project_type(path)

    # Get key files for this project type
    key_files_patterns = KEY_FILES.get(project_type, KEY_FILES.get("typescript_fullstack", {}))

    # Find actual existing files
    found_files = {}
    for category, patterns in key_files_patterns.items():
        found_files[category] = find_existing_files(path, patterns)

    # Build result
    result = {
        "repo_path": str(path),
        "project_type": project_type,
        "detection_scores": detection_scores,
        "key_files": found_files,
        "suggested_read_order": READ_ORDER.get(project_type, []),
        "architecture_files": found_files.get("docs", []) + [
            "docs/architecture/coding-standards.md",
            "docs/architecture/tech-stack.md",
            "docs/architecture/source-tree.md"
        ]
    }

    return result


def format_markdown(result: Dict) -> str:
    """Format result as markdown."""
    if "error" in result:
        return f"Error: {result['error']}"

    lines = [
        f"# Codebase Analysis: {result['repo_path']}",
        "",
        f"**Project Type:** `{result['project_type']}`",
        "",
        "## Key Files Found",
        ""
    ]

    for category, files in result.get("key_files", {}).items():
        lines.append(f"### {category.replace('_', ' ').title()}")
        if files:
            for f in files:
                lines.append(f"- `{f}`")
        else:
            lines.append("- *(none found)*")
        lines.append("")

    lines.append("## Suggested Read Order")
    lines.append("")
    for step in result.get("suggested_read_order", []):
        lines.append(f"- {step}")

    lines.append("")
    lines.append("## Architecture Files to Check")
    lines.append("")
    for f in result.get("architecture_files", []):
        lines.append(f"- `{f}`")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze a codebase to detect project type and key files."
    )
    parser.add_argument(
        "repo_path",
        help="Path to the repository root"
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format (default: markdown)"
    )
    parser.add_argument(
        "--type",
        dest="force_type",
        choices=list(PROJECT_INDICATORS.keys()),
        help="Force a specific project type"
    )

    args = parser.parse_args()

    result = analyze_codebase(args.repo_path, args.force_type)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(format_markdown(result))


if __name__ == "__main__":
    main()
