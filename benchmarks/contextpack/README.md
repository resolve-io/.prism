# PRISM context-pack benchmark

Scores the MCP `context_bundle` payload that an agent receives before work.

This is not a retrieval benchmark. It is a deterministic context-management
gate for the PRISM persona system:

- correct canonical persona dispatch
- correct role card and response template
- required MCP-first rules present
- relevant Brain, Memory, and Task context included in the right channel
- unrelated noise and other personas' role-specific context excluded
- asset digests stable across repeated calls

Run fast in-process:

```bash
python benchmarks/contextpack/run.py
```

Run against the isolated bench MCP service:

```bash
python benchmarks/contextpack/run.py --mcp-url http://localhost:18081/mcp/
```

Results are written to `benchmarks/results/contextpack/`.
