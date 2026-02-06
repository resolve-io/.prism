#!/usr/bin/env python3
"""
Jira Issue Search - Search Jira issues using JQL.

Usage:
    python jira_search.py "project = PLAT AND type = Story"
    python jira_search.py "summary ~ '.NET'" --max 50
    python jira_search.py "assignee = currentUser()" --format json

Environment Variables (required):
    JIRA_EMAIL      - Your Atlassian account email
    JIRA_API_TOKEN  - Your Jira API token

Alternatively, credentials can be loaded from:
    C:/Dev/.prism/plugins/prism-devtools/.env
"""

import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

# Configuration
JIRA_BASE_URL = "https://resolvesys.atlassian.net"
ENV_FILE_PATH = Path("C:/Dev/.prism/plugins/prism-devtools/.env")
DEFAULT_FIELDS = ["key", "summary", "status", "issuetype", "assignee", "priority", "parent"]


def load_env_file(env_path: Path) -> dict:
    """Load environment variables from .env file."""
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
    return env_vars


def get_credentials() -> tuple:
    """Get Jira credentials from environment or .env file."""
    email = os.environ.get('JIRA_EMAIL')
    token = os.environ.get('JIRA_API_TOKEN')

    # Try loading from .env file if not in environment
    if not email or not token:
        env_vars = load_env_file(ENV_FILE_PATH)
        email = email or env_vars.get('JIRA_EMAIL')
        token = token or env_vars.get('JIRA_API_TOKEN')

    if not email or not token:
        print("Error: Jira credentials not configured.", file=sys.stderr)
        print("\nSet environment variables:", file=sys.stderr)
        print("  JIRA_EMAIL=your.email@resolve.io", file=sys.stderr)
        print("  JIRA_API_TOKEN=your_api_token", file=sys.stderr)
        print(f"\nOr create: {ENV_FILE_PATH}", file=sys.stderr)
        sys.exit(1)

    return email, token


def make_auth_header(email: str, token: str) -> str:
    """Create Basic Auth header value."""
    credentials = f"{email}:{token}"
    encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    return f"Basic {encoded}"


def search_issues(jql: str, max_results: int = 50, fields: list = None) -> dict:
    """Search Jira using JQL via POST request (new /search/jql endpoint)."""
    email, token = get_credentials()

    # Use the new /search/jql endpoint (required as of 2024)
    url = f"{JIRA_BASE_URL}/rest/api/3/search/jql"

    payload = {
        "jql": jql,
        "maxResults": max_results,
        "fields": fields or DEFAULT_FIELDS
    }

    data = json.dumps(payload).encode('utf-8')

    request = urllib.request.Request(url, data=data, method='POST')
    request.add_header('Authorization', make_auth_header(email, token))
    request.add_header('Content-Type', 'application/json')
    request.add_header('Accept', 'application/json')

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else ''
        try:
            error_data = json.loads(error_body)
            error_msgs = error_data.get('errorMessages', [])
            errors = error_data.get('errors', {})
            if error_msgs:
                error_msg = error_msgs[0]
            elif errors:
                error_msg = str(errors)
            else:
                error_msg = str(e)
        except:
            error_msg = str(e)

        if e.code == 400:
            print(f"Error: Invalid JQL query.", file=sys.stderr)
            print(f"JQL: {jql}", file=sys.stderr)
            print(f"Details: {error_msg}", file=sys.stderr)
        elif e.code == 401:
            print(f"Error: Authentication failed. Check JIRA_EMAIL and JIRA_API_TOKEN.", file=sys.stderr)
        elif e.code == 403:
            print(f"Error: Access denied. Check project permissions.", file=sys.stderr)
        else:
            print(f"Error: {error_msg}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Network error - {e.reason}", file=sys.stderr)
        sys.exit(1)


def format_results_json(data: dict) -> str:
    """Format search results as JSON."""
    issues = data.get('issues', [])
    result = {
        'total': data.get('total', 0),
        'count': len(issues),
        'issues': []
    }

    for issue in issues:
        fields = issue.get('fields', {})
        result['issues'].append({
            'key': issue.get('key'),
            'type': fields.get('issuetype', {}).get('name'),
            'summary': fields.get('summary'),
            'status': fields.get('status', {}).get('name'),
            'priority': fields.get('priority', {}).get('name'),
            'assignee': (fields.get('assignee') or {}).get('displayName', 'Unassigned'),
            'parent': fields.get('parent', {}).get('key'),
            'url': f"{JIRA_BASE_URL}/browse/{issue.get('key')}"
        })

    return json.dumps(result, indent=2, ensure_ascii=False)


def format_results_markdown(data: dict) -> str:
    """Format search results as Markdown."""
    issues = data.get('issues', [])
    total = data.get('total', 0)

    lines = [
        f"## Search Results ({len(issues)} of {total} issues)",
        ""
    ]

    if not issues:
        lines.append("No issues found matching the query.")
        return '\n'.join(lines)

    for issue in issues:
        fields = issue.get('fields', {})
        key = issue.get('key')
        issue_type = fields.get('issuetype', {}).get('name', 'Unknown')
        summary = fields.get('summary', 'No summary')
        status = fields.get('status', {}).get('name', 'Unknown')
        assignee = (fields.get('assignee') or {}).get('displayName', 'Unassigned')
        parent = fields.get('parent', {}).get('key')

        parent_str = f" (Parent: {parent})" if parent else ""
        lines.append(f"- **[{key}]({JIRA_BASE_URL}/browse/{key})** [{issue_type}] {summary}")
        lines.append(f"  - Status: {status} | Assignee: {assignee}{parent_str}")

    return '\n'.join(lines)


def format_results_table(data: dict) -> str:
    """Format search results as a simple table."""
    issues = data.get('issues', [])
    total = data.get('total', 0)

    lines = [
        f"Search Results: {len(issues)} of {total} issues",
        "",
        "| Key | Type | Summary | Status | Assignee |",
        "|-----|------|---------|--------|----------|"
    ]

    for issue in issues:
        fields = issue.get('fields', {})
        key = issue.get('key')
        issue_type = fields.get('issuetype', {}).get('name', '-')
        summary = (fields.get('summary', '-') or '-')[:50]
        if len(fields.get('summary', '')) > 50:
            summary += '...'
        status = fields.get('status', {}).get('name', '-')
        assignee = (fields.get('assignee') or {}).get('displayName', 'Unassigned')

        lines.append(f"| {key} | {issue_type} | {summary} | {status} | {assignee} |")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Search Jira issues using JQL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python jira_search.py "project = PLAT AND type = Story"
    python jira_search.py "summary ~ '.NET 10'"
    python jira_search.py "project = PLAT AND type = Bug AND status != Done"
    python jira_search.py "assignee = currentUser()" --max 100
    python jira_search.py "parent = PLAT-789" --format json

Common JQL operators:
    =, !=           Equal, not equal
    ~, !~           Contains, doesn't contain (text search)
    >, <, >=, <=    Comparisons
    IN, NOT IN      List membership
    AND, OR         Boolean operators
"""
    )
    parser.add_argument('jql', help='JQL query string')
    parser.add_argument('--max', '-m', type=int, default=50,
                       help='Maximum results (default: 50)')
    parser.add_argument('--format', '-f', choices=['json', 'markdown', 'table'], default='markdown',
                       help='Output format (default: markdown)')

    args = parser.parse_args()

    # Search
    data = search_issues(args.jql, max_results=args.max)

    # Format output
    if args.format == 'json':
        print(format_results_json(data))
    elif args.format == 'table':
        print(format_results_table(data))
    else:
        print(format_results_markdown(data))


if __name__ == '__main__':
    main()
