"""Regression guard: bench eval runners must strip any ``::<anything>``
chunk suffix from retrieved doc_ids before matching gold IDs.

Context: a stale matcher that only stripped ``::main`` once made the
multi-granular chunking change look like a 0.080 R@5 disaster when the
real result was 0.940 (see memory ``bench-eval-chunk-suffix-bug-2026``).
This test exists so the next person to extend doc_id formatting finds
out from a unit test, not a five-hour bench run.

Kept as a pure unit test (no container, no network) so it can run in
pre-commit in under a second.
"""

from pathlib import Path


def _strip_chunk_suffix(doc_id: str) -> str:
    if "::" in doc_id:
        return doc_id.split("::", 1)[0]
    return doc_id


_CASES = [
    # Legacy whole-file / prose.
    ("lme/q042/session_abc::main", "lme/q042/session_abc"),
    # Multi-granular variants emitted by Brain._chunk_source_file.
    ("lme/q042/session_abc::win_0", "lme/q042/session_abc"),
    ("lme/q042/session_abc::win_12", "lme/q042/session_abc"),
    ("src/foo.py::__file__", "src/foo.py"),
    ("src/foo.py::__module__", "src/foo.py"),
    ("src/foo.py::MyClass", "src/foo.py"),
    ("src/foo.py::_private_fn", "src/foo.py"),
    # No suffix must pass through unchanged.
    ("no_suffix_here", "no_suffix_here"),
    ("", ""),
]


def test_strip_chunk_suffix_handles_all_known_variants():
    for raw, expected in _CASES:
        got = _strip_chunk_suffix(raw)
        assert got == expected, f"{raw!r} -> {got!r}, expected {expected!r}"


def test_bench_runners_apply_canonical_stripping():
    """Both eval runners must use split('::', 1)[0] before matching.

    Catches the next person who copies the runner for a new dataset
    and re-introduces the ``::main``-only matcher.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    runners = [
        repo_root / "benchmarks" / "longmemeval" / "run.py",
        repo_root / "benchmarks" / "swebench" / "run.py",
    ]
    for path in runners:
        assert path.exists(), f"expected runner at {path}"
        src = path.read_text(encoding="utf-8")
        has_split = (
            'split("::", 1)[0]' in src or "split('::', 1)[0]" in src
        )
        assert has_split, (
            f"{path} does not apply the canonical ``split('::', 1)[0]`` "
            f"chunk-suffix stripping — see memory "
            f"bench-eval-chunk-suffix-bug-2026."
        )
