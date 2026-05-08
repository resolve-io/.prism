#!/usr/bin/env python3
"""
prism-scan.py — Bulk-ingest source files from one or more repos into Prism Brain.

Walks each repo using `git ls-files` (respects .gitignore) and pushes file
contents to Prism via mcp-cli in batches, then triggers a single graph rebuild.

Usage:
    python prism-scan.py [--repos path1 path2 ...] [--batch-size N]

If --repos is omitted, the DEFAULT_REPOS list is used (project-specific).
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

INCLUDE_EXTENSIONS = {
    # C# / .NET
    '.cs', '.csproj', '.sln', '.props', '.targets',
    # TypeScript / JavaScript
    '.ts', '.tsx', '.js', '.jsx', '.mjs',
    # Python
    '.py',
    # Docs / config
    '.md', '.txt', '.json', '.yaml', '.yml', '.toml',
    # SQL / HTML / styles
    '.sql', '.html', '.css', '.scss',
    # Shell
    '.sh', '.bash',
    # XML / config
    '.xml', '.config',
}

MAX_FILE_SIZE = 200_000  # 200 KB — skips minified/generated files

# Dirs to skip when falling back to os.walk (non-git repos)
SKIP_DIRS = {
    'node_modules', 'bin', 'obj', '.git', '__pycache__',
    '.vs', 'graphify-out', 'dist', 'build', '.angular',
}


def get_repo_files(repo_path: Path) -> list[Path]:
    """Return eligible source files from a repo, respecting .gitignore."""
    try:
        result = subprocess.run(
            ['git', 'ls-files'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        files = []
        for line in result.stdout.splitlines():
            p = repo_path / line
            if p.suffix in INCLUDE_EXTENSIONS:
                try:
                    if p.stat().st_size <= MAX_FILE_SIZE:
                        files.append(p)
                except OSError:
                    pass
        return files
    except subprocess.CalledProcessError:
        print(f"  [warn] not a git repo, walking without gitignore: {repo_path}", file=sys.stderr)
        return _walk_files(repo_path)


def _walk_files(repo_path: Path) -> list[Path]:
    files = []
    for root, dirs, filenames in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in filenames:
            p = Path(root) / f
            if p.suffix in INCLUDE_EXTENSIONS:
                try:
                    if p.stat().st_size <= MAX_FILE_SIZE:
                        files.append(p)
                except OSError:
                    pass
    return files


def _get_mcp_url(mcp_server: str) -> str | None:
    """Resolve the HTTP URL for a named MCP server.

    Reads .mcp.json directly (cwd, then ancestors) rather than spawning
    `mcp-cli info`, which itself has to talk to the server and can fail
    transiently against servers that close sockets aggressively.

    Appends `tool_profile=all` because pipeline calls (prism_refresh,
    graph_rebuild) live in the maintenance profile, not the default
    `interactive` profile served to agent sessions.
    """
    from pathlib import Path
    cwd = Path.cwd()
    for d in (cwd, *cwd.parents):
        cfg_path = d / '.mcp.json'
        if cfg_path.is_file():
            try:
                cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
                server = cfg.get('mcpServers', {}).get(mcp_server)
                if isinstance(server, dict) and server.get('url'):
                    url = server['url']
                    sep = '&' if '?' in url else '?'
                    if 'tool_profile=' not in url:
                        url = f'{url}{sep}tool_profile=all'
                    return url
            except (json.JSONDecodeError, OSError):
                pass
    return None


def _call_mcp_http(url: str, tool_name: str, arguments: dict, timeout: int = 600) -> tuple[dict | None, str | None]:
    """Direct JSON-RPC tools/call over HTTP, bypassing mcp-cli's per-call session handshake.

    Why: spawning `mcp-cli call` for every refresh creates a new MCP session per call,
    and concurrent persistent sessions can starve the new handshake into timeouts.

    Returns (result_dict, None) on success, (None, error_message) on failure.
    """
    import requests as req
    payload = {
        'jsonrpc': '2.0',
        'id': '1',
        'method': 'tools/call',
        'params': {'name': tool_name, 'arguments': arguments},
    }
    try:
        resp = req.post(
            url, json=payload,
            headers={'Accept': 'application/json, text/event-stream'},
            timeout=timeout, stream=True,
        )
        resp.raise_for_status()
        result_data = None
        for line in resp.iter_lines(decode_unicode=True):
            if line.startswith('data: '):
                result_data = json.loads(line[6:])
                break
        if result_data is None:
            return None, 'empty response'
        if 'error' in result_data:
            return None, str(result_data['error'])
        result = result_data.get('result', {})
        content = result.get('content', [])
        text = content[0].get('text', '') if content else ''
        try:
            payload = json.loads(text) if text else {}
        except json.JSONDecodeError:
            return {'_text': text}, None
        if result.get('isError') or (isinstance(payload, dict) and 'error' in payload):
            err_msg = payload.get('error') if isinstance(payload, dict) else text
            return None, str(err_msg)
        return payload, None
    except req.exceptions.Timeout:
        return None, f'timed out after {timeout}s'
    except req.exceptions.RequestException as e:
        return None, str(e)


def prism_refresh(files_map: dict[str, str], skip_graph: bool, mcp_server: str, retries: int = 3) -> None:
    import time
    url = _get_mcp_url(mcp_server)
    if not url:
        print(f'  [error] prism_refresh: could not resolve URL for "{mcp_server}"', file=sys.stderr)
        return
    args = {'files': files_map, 'domain': 'code', 'skip_graph': skip_graph}
    for attempt in range(1, retries + 1):
        result, err = _call_mcp_http(url, 'prism_refresh', args, timeout=600)
        if result is not None:
            return
        if attempt < retries:
            print(f"  [retry {attempt}/{retries}] {err}, retrying...", file=sys.stderr)
            time.sleep(2 * attempt)
        else:
            print(f"  [error] prism_refresh: {err}", file=sys.stderr)
            return


def graph_rebuild(mcp_server: str) -> None:
    url = _get_mcp_url(mcp_server)
    if not url:
        print(f'  [error] graph_rebuild: could not resolve URL for "{mcp_server}"', file=sys.stderr)
        return
    print('  (direct HTTP, timeout=3600s)')
    data, err = _call_mcp_http(url, 'graph_rebuild', {}, timeout=3600)
    if data is None:
        print(f"  [error] graph_rebuild: {err}", file=sys.stderr)
        return
    if '_text' in data:
        print(f"  graph_rebuild: {data['_text']}")
        return
    print(
        f"  nodes={data.get('nodes', 0)}  "
        f"edges={data.get('edges', 0)}  "
        f"communities={data.get('communities', 0)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Bulk-ingest source repos into Prism Brain.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--repos', nargs='+', metavar='PATH', required=True,
                        help='Repo root paths to scan (one or more)')
    parser.add_argument('--batch-size', type=int, default=20, metavar='N',
                        help='Files per prism_refresh call (default: 20)')
    parser.add_argument('--mcp-server', default='prism', metavar='NAME',
                        help='mcp-cli server name for Prism (default: prism)')
    args = parser.parse_args()

    repos = [Path(r) for r in args.repos]

    # Collect (prism_path, abs_path) pairs across all repos
    all_files: list[tuple[str, Path]] = []
    for repo in repos:
        if not repo.exists():
            print(f"[skip] {repo} not found")
            continue
        files = get_repo_files(repo)
        for f in files:
            prism_path = f"{repo.name}/{f.relative_to(repo).as_posix()}"
            all_files.append((prism_path, f))
        print(f"{repo.name}: {len(files)} files")

    total = len(all_files)
    print(f"\nTotal: {total} files across {len([r for r in repos if r.exists()])} repos")
    if total == 0:
        print("Nothing to ingest.")
        return

    batches = [all_files[i:i + args.batch_size] for i in range(0, total, args.batch_size)]
    ingested = 0

    for i, batch in enumerate(batches):
        files_map: dict[str, str] = {}
        for prism_path, abs_path in batch:
            try:
                files_map[prism_path] = abs_path.read_text(encoding='utf-8', errors='replace')
            except OSError as e:
                print(f"  [skip] {prism_path}: {e}", file=sys.stderr)

        ingested += len(files_map)
        pct = ingested * 100 // total
        print(f"  batch {i + 1}/{len(batches)}  ({pct}%  {ingested}/{total} files)", end='\r')
        prism_refresh(files_map, skip_graph=True, mcp_server=args.mcp_server)

    print()  # clear \r line
    print("Rebuilding graph...")
    graph_rebuild(args.mcp_server)
    print("Done.")


if __name__ == '__main__':
    main()
