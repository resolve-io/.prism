#!/usr/bin/env python3
"""
Jira Issue Fetcher - Fetch and format a single Jira issue.

Usage:
    python jira_fetch.py PLAT-123
    python jira_fetch.py PLAT-123 --format json
    python jira_fetch.py PLAT-123 --format markdown

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
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

# Configuration
JIRA_BASE_URL = "https://resolvesys.atlassian.net"
ENV_FILE_PATH = Path("C:/Dev/.prism/plugins/prism-devtools/.env")


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


def fetch_issue(issue_key: str) -> dict:
    """Fetch issue from Jira API."""
    email, token = get_credentials()

    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}"

    request = urllib.request.Request(url)
    request.add_header('Authorization', make_auth_header(email, token))
    request.add_header('Accept', 'application/json')

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else ''
        try:
            error_data = json.loads(error_body)
            error_msg = error_data.get('errorMessages', [str(e)])[0]
        except:
            error_msg = str(e)

        if e.code == 401:
            print(f"Error: Authentication failed. Check JIRA_EMAIL and JIRA_API_TOKEN.", file=sys.stderr)
        elif e.code == 403:
            print(f"Error: Access denied to {issue_key}. Check permissions.", file=sys.stderr)
        elif e.code == 404:
            print(f"Error: Issue {issue_key} not found.", file=sys.stderr)
        else:
            print(f"Error: {error_msg}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Network error - {e.reason}", file=sys.stderr)
        sys.exit(1)


def extract_text_from_adf(adf_content) -> str:
    """Extract plain text from Atlassian Document Format (ADF)."""
    if not adf_content:
        return ""

    if isinstance(adf_content, str):
        return adf_content

    def extract_from_node(node):
        if not isinstance(node, dict):
            return str(node) if node else ""

        text_parts = []

        if node.get('type') == 'text':
            text_parts.append(node.get('text', ''))

        for child in node.get('content', []):
            text_parts.append(extract_from_node(child))

        return ''.join(text_parts)

    return extract_from_node(adf_content)


def format_issue_json(data: dict) -> str:
    """Format issue as JSON."""
    fields = data.get('fields', {})

    result = {
        'key': data.get('key'),
        'type': fields.get('issuetype', {}).get('name'),
        'summary': fields.get('summary'),
        'status': fields.get('status', {}).get('name'),
        'priority': fields.get('priority', {}).get('name'),
        'assignee': (fields.get('assignee') or {}).get('displayName', 'Unassigned'),
        'reporter': (fields.get('reporter') or {}).get('displayName', 'Unknown'),
        'description': extract_text_from_adf(fields.get('description')),
        'labels': fields.get('labels', []),
        'components': [c.get('name') for c in fields.get('components', [])],
        'parent': fields.get('parent', {}).get('key'),
        'url': f"{JIRA_BASE_URL}/browse/{data.get('key')}"
    }

    return json.dumps(result, indent=2, ensure_ascii=False)


def format_issue_markdown(data: dict) -> str:
    """Format issue as Markdown."""
    fields = data.get('fields', {})
    key = data.get('key')

    issue_type = fields.get('issuetype', {}).get('name', 'Unknown')
    summary = fields.get('summary', 'No summary')
    status = fields.get('status', {}).get('name', 'Unknown')
    priority = fields.get('priority', {}).get('name', 'Unknown')
    assignee = (fields.get('assignee') or {}).get('displayName', 'Unassigned')
    reporter = (fields.get('reporter') or {}).get('displayName', 'Unknown')
    description = extract_text_from_adf(fields.get('description')) or 'No description'
    labels = fields.get('labels', [])
    components = [c.get('name') for c in fields.get('components', [])]
    parent = fields.get('parent', {}).get('key')

    lines = [
        f"## [{key}] {summary}",
        f"",
        f"**Link**: [{key}]({JIRA_BASE_URL}/browse/{key})",
        f"",
        f"### Details",
        f"- **Type**: {issue_type}",
        f"- **Status**: {status}",
        f"- **Priority**: {priority}",
        f"- **Assignee**: {assignee}",
        f"- **Reporter**: {reporter}",
    ]

    if parent:
        lines.append(f"- **Parent**: [{parent}]({JIRA_BASE_URL}/browse/{parent})")

    if labels:
        lines.append(f"- **Labels**: {', '.join(labels)}")

    if components:
        lines.append(f"- **Components**: {', '.join(components)}")

    lines.extend([
        f"",
        f"### Description",
        description[:2000] + ('...' if len(description) > 2000 else ''),
    ])

    # Extract acceptance criteria from description
    ac_match = re.search(r'(?:Acceptance Criteria|AC):\s*(.*?)(?=\n\n|\Z)', description, re.IGNORECASE | re.DOTALL)
    if ac_match:
        lines.extend([
            f"",
            f"### Acceptance Criteria",
            ac_match.group(1).strip()[:1000],
        ])

    # Recent comments
    comments = fields.get('comment', {}).get('comments', [])
    if comments:
        lines.extend([
            f"",
            f"### Recent Comments ({min(3, len(comments))} of {len(comments)})",
        ])
        for comment in comments[-3:]:
            author = (comment.get('author') or {}).get('displayName', 'Unknown')
            body = extract_text_from_adf(comment.get('body'))[:300]
            lines.append(f"- **{author}**: {body}")

    return '\n'.join(lines)


def validate_issue_key(key: str) -> bool:
    """Validate Jira issue key format."""
    return bool(re.match(r'^[A-Z]+-\d+$', key))


def main():
    parser = argparse.ArgumentParser(
        description='Fetch and format a Jira issue',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('issue_key', help='Jira issue key (e.g., PLAT-123)')
    parser.add_argument('--format', '-f', choices=['json', 'markdown'], default='markdown',
                       help='Output format (default: markdown)')

    args = parser.parse_args()

    # Validate issue key format
    issue_key = args.issue_key.upper()
    if not validate_issue_key(issue_key):
        print(f"Error: Invalid issue key format: {args.issue_key}", file=sys.stderr)
        print("Expected format: PROJECT-123 (e.g., PLAT-123)", file=sys.stderr)
        sys.exit(1)

    # Fetch and format
    data = fetch_issue(issue_key)

    if args.format == 'json':
        print(format_issue_json(data))
    else:
        print(format_issue_markdown(data))


if __name__ == '__main__':
    main()
