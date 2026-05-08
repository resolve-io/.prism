#!/usr/bin/env python3
"""
prism-enrich.py — Phase 2 semantic enrichment for Prism Brain.

Scans C# and TypeScript source files and infers cross-file relationships
that AST cannot see:
  - MediatR dispatch:  mediator.Send(new TCommand) -> IRequestHandler<TCommand>
  - MassTransit msgs:  IConsumer<TMsg> <-> IBus.Publish<TMsg> / endpoint.Send<TMsg>
  - DI registrations:  services.AddScoped<IFoo, Foo>() and convention Foo : IFoo
  - Stored procs:      ExecuteStoredProcedure("sp_name") -> matching .sql file
  - Angular TS DI:     constructor(private svc: FooService) -> FooService class
  - HTTP cross-repo:   Angular service name stem -> matching C# controller

Writes synthetic enrichment documents into Prism (under enrichment/ namespace)
and rebuilds the graph.  Existing enrichment docs are overwritten on each run
(idempotent).  Structural source docs are never touched.

Usage:
    python prism-enrich.py --repos D:/dev/repo1 D:/dev/repo2
    python prism-enrich.py --repos D:/dev/repo1 --dry-run
    python prism-enrich.py --repos D:/dev/repo1 --patterns mediatR mt ts_di http_route
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class InferredEdge:
    kind: str           # mediatR | masstransit | di | sproc | ts_di | http_route
    from_entity: str    # caller / publisher / interface / TS class
    to_entity: str      # handler / consumer / implementation / sql file / C# controller
    from_file: str      # repo-relative path
    to_file: str        # repo-relative path (may be empty if target not found)
    detail: str = ""    # human-readable context


@dataclass
class RepoCatalog:
    """Indices built during the scan pass, used during the inference pass."""
    # MediatR: TRequest -> [(handler_class, file)]
    mediatR_handlers: dict = field(default_factory=lambda: defaultdict(list))
    # MassTransit: TMsg -> [(consumer_class, file)]
    mt_consumers: dict = field(default_factory=lambda: defaultdict(list))
    # DI: IFoo -> [(impl_class, file)]
    di_impls: dict = field(default_factory=lambda: defaultdict(list))
    # Stored procs: sp_name -> [sql_file]
    sql_procs: dict = field(default_factory=lambda: defaultdict(list))
    # TypeScript services: class_name -> [(file, has_http)]
    ts_services: dict = field(default_factory=lambda: defaultdict(list))
    # C# controllers: stem_lowercase -> [(controller_class, route_prefix, file)]
    cs_controllers: dict = field(default_factory=lambda: defaultdict(list))


# ---------------------------------------------------------------------------
# Regex patterns — C#
# ---------------------------------------------------------------------------

# MediatR — handler declaration: class FooHandler : IRequestHandler<FooCommand, ...>
RE_MEDIATR_HANDLER = re.compile(
    r'class\s+(\w+)\s*[:<][^{]*IRequestHandler\s*<\s*(\w+)'
)
# MediatR — dispatch call: _mediator.Send(new FooCommand / mediator.Send<FooCommand>
RE_MEDIATR_SEND = re.compile(
    r'(?:_mediator|mediator|Mediator)\s*\.\s*Send(?:Async)?\s*[<(]\s*(?:new\s+)?(\w+)'
)

# MassTransit — consumer: class FooConsumer : IConsumer<FooMessage>
RE_MT_CONSUMER = re.compile(
    r'class\s+(\w+)\s*[:<][^{]*IConsumer\s*<\s*(\w+)'
)
# MassTransit — publish/send: _bus.Publish<FooEvent> / endpoint.Send<FooMessage>
RE_MT_PUBLISH = re.compile(
    r'(?:_bus|bus|_endpoint|endpoint|publishEndpoint|_publishEndpoint)'
    r'\s*\.\s*(?:Publish|Send)(?:Async)?\s*<\s*(\w+)'
)

# DI — explicit registration: services.AddScoped<IFoo, Foo>() style
RE_DI_EXPLICIT = re.compile(
    r'\.Add(?:Scoped|Singleton|Transient)\s*<\s*(\w+)\s*,\s*(\w+)\s*>'
)
# DI — lambda via GetRequiredService: AddScoped<IFoo>(sp => sp.GetRequiredService<Foo>())
RE_DI_LAMBDA_GRS = re.compile(
    r'\.Add(?:Scoped|Singleton|Transient)\s*<\s*(I\w+)\s*>\s*\([^)]*GetRequiredService\s*<\s*(\w+)\s*>'
)
# DI — lambda via new: AddScoped<IFoo>(_ => new Foo(...)) or (sp => new Foo(...))
RE_DI_LAMBDA_NEW = re.compile(
    r'\.Add(?:Scoped|Singleton|Transient)\s*<\s*(I\w+)\s*>\s*\([^)]*=>\s*new\s+(\w+)\s*[(\[]'
)
# DI — convention: class Foo : IFoo (interface name = "I" + class name)
RE_CLASS_IFACE = re.compile(
    r'class\s+(\w+)\s*[:<][^{]*\b(I\w+)\b'
)

# Stored procedures — ExecuteStoredProcedure("sp_name", ...) and variants
RE_SPROC_CALL = re.compile(
    r'ExecuteStoredProcedure\w*\s*\(\s*"([^"]+)"'
)
# SP name in .sql file: CREATE PROCEDURE [dbo].[sp_name] or CREATE PROC sp_name
RE_SQL_PROC_DEF = re.compile(
    r'CREATE\s+(?:OR\s+ALTER\s+)?(?:PROCEDURE|PROC)\s+(?:\[?\w+\]?\.)?\[?(\w+)\]?',
    re.IGNORECASE,
)

# C# controller class name
RE_CS_CONTROLLER_CLASS = re.compile(r'class\s+(\w+Controller)\s*[:<]')
# C# route prefix/attribute on class or method (RoutePrefix = Web API 2, Route = ASP.NET Core)
RE_CS_ROUTE_PREFIX = re.compile(
    r'\[Route(?:Prefix)?\s*\(\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Regex patterns — TypeScript / Angular
# ---------------------------------------------------------------------------

# Angular class declaration (export class, abstract class)
RE_TS_CLASS = re.compile(r'(?:export\s+)?(?:abstract\s+)?class\s+(\w+)')

# Angular constructor injection parameter: private|public|protected [readonly] name: Type
# Also matches @Inject(...) decorated params
RE_TS_INJECT_PARAM = re.compile(
    r'(?:@\w+(?:\([^)]*\))?\s+)*(?:private|public|protected|readonly)\s+\w+\s*:\s*(\w+)'
)

# Angular HTTP call: this.http.get/post/... or this.httpUtils.get/post/...
RE_TS_HTTP = re.compile(
    r'(?:this\._?http(?:Utils|Client)?|this\._?httpUtils)\s*\.\s*'
    r'(?:get|post|put|patch|delete)\s*[<(]',
    re.IGNORECASE,
)

# Angular framework types to exclude from DI edges (not our app services)
_TS_FRAMEWORK_TYPES = frozenset({
    'HttpClient', 'Router', 'ActivatedRoute', 'ActivatedRouteSnapshot',
    'Renderer2', 'NgZone', 'ChangeDetectorRef', 'ElementRef', 'ViewContainerRef',
    'ComponentFactoryResolver', 'Injector', 'ApplicationRef', 'NgModuleRef',
    'FormBuilder', 'FormGroup', 'FormControl', 'FormArray',
    'MatDialog', 'MatSnackBar', 'MatDialogRef',
    'TranslateService', 'Store', 'Actions',
    'Title', 'Meta', 'DomSanitizer', 'DOCUMENT', 'Document',
    'string', 'number', 'boolean', 'any', 'void', 'never', 'object',
    'Observable', 'Subject', 'BehaviorSubject', 'ReplaySubject',
    'EventEmitter', 'QueryList',
})


# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------

_CS_SQL_EXTS = {'.cs', '.sql'}
_TS_EXTS = {'.ts'}
_ALL_EXTS = _CS_SQL_EXTS | _TS_EXTS
_TS_SKIP_SUFFIXES = ('.spec.ts', '.d.ts', '.module.ts')


def get_repo_files(repo_path: Path) -> list[Path]:
    try:
        result = subprocess.run(
            ['git', 'ls-files'],
            cwd=repo_path, capture_output=True, text=True, check=True,
        )
        files = []
        for line in result.stdout.splitlines():
            p = repo_path / line
            if p.suffix not in _ALL_EXTS or not p.exists():
                continue
            if p.suffix == '.ts' and any(p.name.endswith(s) for s in _TS_SKIP_SUFFIXES):
                continue
            files.append(p)
        return files
    except subprocess.CalledProcessError:
        files = []
        for p in repo_path.rglob('*'):
            if p.suffix not in _ALL_EXTS:
                continue
            if any(skip in p.parts for skip in {'bin', 'obj', 'node_modules', '.angular'}):
                continue
            if p.suffix == '.ts' and any(p.name.endswith(s) for s in _TS_SKIP_SUFFIXES):
                continue
            files.append(p)
        return files


# ---------------------------------------------------------------------------
# Catalog-building pass (first pass — builds indices)
# ---------------------------------------------------------------------------

def build_catalog(files: list[Path], repo_root: Path, repo_name: str, catalog: RepoCatalog) -> None:
    for f in files:
        # Store paths as repo_name/rel so cross-repo references are unambiguous
        rel = f'{repo_name}/{f.relative_to(repo_root).as_posix()}'
        try:
            text = f.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue

        if f.suffix == '.cs':
            for m in RE_MEDIATR_HANDLER.finditer(text):
                catalog.mediatR_handlers[m.group(2)].append((m.group(1), rel))
            for m in RE_MT_CONSUMER.finditer(text):
                catalog.mt_consumers[m.group(2)].append((m.group(1), rel))
            for m in RE_DI_EXPLICIT.finditer(text):
                catalog.di_impls[m.group(1)].append((m.group(2), rel))
            for m in RE_CLASS_IFACE.finditer(text):
                class_name, iface = m.group(1), m.group(2)
                if iface == f'I{class_name}':
                    catalog.di_impls[iface].append((class_name, rel))
            # Catalog controllers for cross-repo HTTP edge matching
            for m in RE_CS_CONTROLLER_CLASS.finditer(text):
                ctrl = m.group(1)
                stem = ctrl[:-len('Controller')].lower()
                prefix_m = RE_CS_ROUTE_PREFIX.search(text)
                prefix = prefix_m.group(1) if prefix_m else ''
                catalog.cs_controllers[stem].append((ctrl, prefix, rel))

        elif f.suffix == '.sql':
            for m in RE_SQL_PROC_DEF.finditer(text):
                catalog.sql_procs[m.group(1).lower()].append(rel)

        elif f.suffix == '.ts':
            classes = RE_TS_CLASS.findall(text)
            has_http = bool(RE_TS_HTTP.search(text))
            for cls in classes:
                catalog.ts_services[cls].append((rel, has_http))


# ---------------------------------------------------------------------------
# Inference pass (second pass — emit edges)
# ---------------------------------------------------------------------------

def infer_edges(
    files: list[Path],
    repo_root: Path,
    repo_name: str,
    catalog: RepoCatalog,
    enabled: set[str],
) -> list[InferredEdge]:
    edges: list[InferredEdge] = []

    for f in files:
        from_file = f'{repo_name}/{f.relative_to(repo_root).as_posix()}'
        try:
            text = f.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue

        # ── C# patterns ──────────────────────────────────────────────────────

        if f.suffix == '.cs':
            if 'mediatR' in enabled:
                for m in RE_MEDIATR_SEND.finditer(text):
                    req_type = m.group(1)
                    for handler_class, handler_file in catalog.mediatR_handlers.get(req_type, []):
                        edges.append(InferredEdge(
                            kind='mediatR',
                            from_entity=req_type,
                            to_entity=handler_class,
                            from_file=from_file,
                            to_file=handler_file,
                            detail=f'mediator.Send dispatches {req_type} to {handler_class}',
                        ))

            if 'mt' in enabled:
                for m in RE_MT_PUBLISH.finditer(text):
                    msg_type = m.group(1)
                    for consumer_class, consumer_file in catalog.mt_consumers.get(msg_type, []):
                        edges.append(InferredEdge(
                            kind='masstransit',
                            from_entity=msg_type,
                            to_entity=consumer_class,
                            from_file=from_file,
                            to_file=consumer_file,
                            detail=f'Published {msg_type} is consumed by {consumer_class}',
                        ))

            if 'di' in enabled:
                for m in RE_DI_EXPLICIT.finditer(text):
                    iface, impl = m.group(1), m.group(2)
                    if iface == impl:
                        continue
                    edges.append(InferredEdge(
                        kind='di',
                        from_entity=iface,
                        to_entity=impl,
                        from_file=from_file,
                        to_file='',
                        detail=f'DI: {iface} resolved as {impl}',
                    ))
                for m in RE_DI_LAMBDA_GRS.finditer(text):
                    iface, impl = m.group(1), m.group(2)
                    edges.append(InferredEdge(
                        kind='di',
                        from_entity=iface,
                        to_entity=impl,
                        from_file=from_file,
                        to_file='',
                        detail=f'DI lambda: {iface} resolved via GetRequiredService<{impl}>',
                    ))
                for m in RE_DI_LAMBDA_NEW.finditer(text):
                    iface, impl = m.group(1), m.group(2)
                    edges.append(InferredEdge(
                        kind='di',
                        from_entity=iface,
                        to_entity=impl,
                        from_file=from_file,
                        to_file='',
                        detail=f'DI lambda: {iface} resolved via new {impl}(...)',
                    ))

            if 'sproc' in enabled:
                for m in RE_SPROC_CALL.finditer(text):
                    sp_name = m.group(1)
                    sql_files = catalog.sql_procs.get(sp_name.lower(), [])
                    edges.append(InferredEdge(
                        kind='sproc',
                        from_entity=sp_name,
                        to_entity=sql_files[0] if sql_files else sp_name,
                        from_file=from_file,
                        to_file=sql_files[0] if sql_files else '',
                        detail=(
                            f'Calls stored procedure {sp_name}'
                            + (f', defined in {sql_files[0]}' if sql_files else ' (SQL file not found)')
                        ),
                    ))

        # ── TypeScript / Angular patterns ─────────────────────────────────────

        elif f.suffix == '.ts':
            classes_in_file = RE_TS_CLASS.findall(text)
            source_class = classes_in_file[0] if classes_in_file else ''

            if 'ts_di' in enabled and source_class:
                for m in RE_TS_INJECT_PARAM.finditer(text):
                    injected_type = m.group(1)
                    if injected_type in _TS_FRAMEWORK_TYPES:
                        continue
                    # Only emit edge if the injected type is a known service in the catalog
                    targets = catalog.ts_services.get(injected_type, [])
                    if targets:
                        for (target_file, _) in targets:
                            if target_file == from_file:
                                continue  # skip self
                            edges.append(InferredEdge(
                                kind='ts_di',
                                from_entity=source_class,
                                to_entity=injected_type,
                                from_file=from_file,
                                to_file=target_file,
                                detail=f'Angular DI: {source_class} injects {injected_type}',
                            ))

            if 'http_route' in enabled and source_class and RE_TS_HTTP.search(text):
                # Name-stem matching: WorkflowService -> "workflow" -> WorkflowController
                stem = source_class.lower()
                for suffix in ('service', 'apiservice', 'client', 'apiclient'):
                    if stem.endswith(suffix):
                        stem = stem[:-len(suffix)]
                        break
                if stem:
                    matched = catalog.cs_controllers.get(stem, [])
                    for (ctrl_class, route_prefix, ctrl_file) in matched:
                        edges.append(InferredEdge(
                            kind='http_route',
                            from_entity=source_class,
                            to_entity=ctrl_class,
                            from_file=from_file,
                            to_file=ctrl_file,
                            detail=(
                                f'HTTP client: {source_class} likely calls {ctrl_class}'
                                + (f' ({route_prefix})' if route_prefix else '')
                                + ' [name-stem match, medium confidence]'
                            ),
                        ))

    return edges


# ---------------------------------------------------------------------------
# Document generation
# ---------------------------------------------------------------------------

def edges_to_documents(edges: list[InferredEdge]) -> dict[str, str]:
    """
    Group edges by (kind, from_file) and produce one enrichment doc per group.
    Returns {prism_path: content}.
    """
    groups: dict[tuple, list[InferredEdge]] = defaultdict(list)
    for e in edges:
        groups[(e.kind, e.from_file)].append(e)

    docs: dict[str, str] = {}
    for (kind, from_file), group in groups.items():
        slug = from_file.replace('/', '_').replace('\\', '_').replace('.', '_')
        prism_path = f'enrichment/{kind}/{slug}.md'

        # deduplicate by (from_entity, to_entity) within this doc
        seen_edges: set[tuple] = set()
        deduped = []
        for e in group:
            key = (e.from_entity, e.to_entity)
            if key not in seen_edges:
                seen_edges.add(key)
                deduped.append(e)
        group = deduped

        lines = [
            f'# Inferred relationships - {kind} - {from_file}',
            '',
            f'Source file: `{from_file}`',
            f'Pattern: {kind}',
            '',
            '## Edges',
            '',
        ]
        for e in group:
            lines.append(f'- **{e.from_entity}** -> **{e.to_entity}**')
            lines.append(f'  - {e.detail}')
            if e.to_file:
                lines.append(f'  - Target: `{e.to_file}`')
            lines.append('')

        lines += [
            '## Entity index',
            '',
            '(Listed so graph traversal can discover this document from either end)',
            '',
        ]
        seen: set[str] = set()
        for e in group:
            for name in (e.from_entity, e.to_entity):
                if name and name not in seen:
                    lines.append(f'- `{name}`')
                    seen.add(name)

        docs[prism_path] = '\n'.join(lines)

    return docs


# ---------------------------------------------------------------------------
# Prism helpers
# ---------------------------------------------------------------------------

def prism_refresh(files_map: dict[str, str], skip_graph: bool, mcp_server: str) -> None:
    import time
    url = _get_mcp_url(mcp_server)
    if not url:
        print(f'  [error] prism_refresh: could not resolve URL for "{mcp_server}"', file=sys.stderr)
        return
    args = {'files': files_map, 'domain': 'architecture', 'skip_graph': skip_graph}
    for attempt in range(1, 4):
        result, err = _call_mcp_http(url, 'prism_refresh', args, timeout=600)
        if result is not None:
            return
        if attempt < 3:
            print(f'  [retry {attempt}/3] {err}, retrying...', file=sys.stderr)
            time.sleep(2 * attempt)
        else:
            print(f'  [error] prism_refresh: {err}', file=sys.stderr)
            return


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
    and concurrent persistent sessions (e.g. claude-code's MCP) can starve the new
    handshake into SERVER_CONNECTION_FAILED timeouts. Direct HTTP avoids the handshake.

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
        # MCP wraps tool errors in {isError: true, content: [...]}; some
        # gating paths return isError=false but include an "error" key in
        # the JSON content. Treat both as failures so callers see a real
        # error rather than a silent success with empty defaults.
        if result.get('isError') or (isinstance(payload, dict) and 'error' in payload):
            err_msg = payload.get('error') if isinstance(payload, dict) else text
            return None, str(err_msg)
        return payload, None
    except req.exceptions.Timeout:
        return None, f'timed out after {timeout}s'
    except req.exceptions.RequestException as e:
        return None, str(e)


def graph_rebuild(mcp_server: str) -> None:
    url = _get_mcp_url(mcp_server)
    if not url:
        print(f'  [error] graph_rebuild: could not resolve URL for server "{mcp_server}"', file=sys.stderr)
        return
    print('  (direct HTTP, timeout=3600s)')
    data, err = _call_mcp_http(url, 'graph_rebuild', {}, timeout=3600)
    if data is None:
        print(f'  [error] graph_rebuild: {err}', file=sys.stderr)
        return
    if '_text' in data:
        print(f'  graph_rebuild: {data["_text"]}')
        return
    print(
        f'  nodes={data.get("nodes", 0)}  '
        f'edges={data.get("edges", 0)}  '
        f'communities={data.get("communities", 0)}'
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ALL_PATTERNS = {'mediatR', 'mt', 'di', 'sproc', 'ts_di', 'http_route'}


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Phase 2 semantic enrichment for Prism Brain.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--repos', nargs='+', metavar='PATH', required=True)
    parser.add_argument('--dry-run', action='store_true',
                        help='Print findings without writing to Prism')
    parser.add_argument('--patterns', nargs='+', metavar='PATTERN',
                        choices=list(ALL_PATTERNS), default=list(ALL_PATTERNS),
                        help=f'Patterns to run (default: all). Choices: {ALL_PATTERNS}')
    parser.add_argument('--batch-size', type=int, default=50, metavar='N')
    parser.add_argument('--mcp-server', default='prism', metavar='NAME')
    args = parser.parse_args()

    enabled = set(args.patterns)
    repos = [Path(r) for r in args.repos]

    # Pass 1: collect files and build a single shared catalog across ALL repos.
    # This is what enables cross-repo edge inference (e.g. publisher in
    # express-scheduler, consumer in express-web-api).
    catalog = RepoCatalog()
    repo_file_map: list[tuple[Path, list[Path]]] = []

    print('Pass 1: building shared catalog...')
    for repo in repos:
        if not repo.exists():
            print(f'  [skip] {repo} not found')
            continue
        files = get_repo_files(repo)
        repo_file_map.append((repo, files))
        build_catalog(files, repo, repo.name, catalog)
        ts_count = sum(1 for f in files if f.suffix == '.ts')
        cs_count = sum(1 for f in files if f.suffix == '.cs')
        print(f'  {repo.name}: {cs_count} cs, {ts_count} ts files')

    print(
        f'\nShared catalog: '
        f'{sum(len(v) for v in catalog.mediatR_handlers.values())} mediatR handlers, '
        f'{sum(len(v) for v in catalog.mt_consumers.values())} MT consumers, '
        f'{sum(len(v) for v in catalog.di_impls.values())} DI impls, '
        f'{sum(len(v) for v in catalog.sql_procs.values())} SQL procs, '
        f'{sum(len(v) for v in catalog.ts_services.values())} TS services, '
        f'{sum(len(v) for v in catalog.cs_controllers.values())} CS controllers'
    )

    # Pass 2: infer edges in each repo against the shared catalog.
    all_edges: list[InferredEdge] = []
    print('\nPass 2: inferring edges...')
    for repo, files in repo_file_map:
        edges = infer_edges(files, repo, repo.name, catalog, enabled)
        print(f'  {repo.name}: {len(edges)} edges')
        all_edges.extend(edges)

    print(f'\nTotal edges: {len(all_edges)}')
    if not all_edges:
        print('Nothing to enrich.')
        return

    docs = edges_to_documents(all_edges)
    print(f'Enrichment documents: {len(docs)}')

    if args.dry_run:
        by_kind: dict[str, int] = defaultdict(int)
        for e in all_edges:
            by_kind[e.kind] += 1
        print('\nEdge breakdown (dry run -- nothing written):')
        for kind, count in sorted(by_kind.items()):
            print(f'  {kind}: {count}')
        print('\nSample documents:')
        for i, (path, content) in enumerate(list(docs.items())[:3]):
            print(f'\n--- {path} ---')
            print(content[:600])
            if i == 2 and len(docs) > 3:
                print(f'  ... ({len(docs) - 3} more documents)')
        return

    # Write enrichment docs to Prism
    doc_items = list(docs.items())
    batches = [doc_items[i:i + args.batch_size] for i in range(0, len(doc_items), args.batch_size)]
    written = 0
    for i, batch in enumerate(batches):
        files_map = dict(batch)
        written += len(files_map)
        pct = written * 100 // len(doc_items)
        print(f'  batch {i + 1}/{len(batches)}  ({pct}%  {written}/{len(doc_items)} docs)', end='\r')
        prism_refresh(files_map, skip_graph=True, mcp_server=args.mcp_server)

    print()
    print('Rebuilding graph...')
    graph_rebuild(args.mcp_server)
    print('Done.')


if __name__ == '__main__':
    main()
