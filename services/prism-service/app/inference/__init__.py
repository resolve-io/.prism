"""v5.1 Understand-Anything inference layer.

All `claude -p` subprocesses, the filesystem job queue, the
source-pinning service, the content-addressable artifact cache, and
the analyzer-orchestrating UnderstandEngine live here.

INV-1 (no API key, ever): every subprocess that ends up invoking
`claude` MUST go through `claude_cli.invoke()` so the env-strip
contract is enforced in exactly one place.
"""
