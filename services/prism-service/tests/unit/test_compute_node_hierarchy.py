"""Tests for compute_node_hierarchy — collapse orphan entities into 'external'.

Issue context: in projects with even 1-2% path-less entities (BCL types,
unresolved cross-repo references, graphify-synthetic nodes), the prior
per-community fallback scattered orphans across hundreds of singleton L0
buckets, fragmenting the L0 navigation surface. The fix routes all
path-less entities into a single 'external' L0, with the community ID
preserved at L1/L2 for drill-down.
"""

from __future__ import annotations

import sys
from pathlib import Path


_HERE = Path(__file__).resolve()
_SERVICE_ROOT = _HERE.parent.parent.parent
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))


from app.services.graph_service import compute_node_hierarchy  # noqa: E402


def test_path_based_l0_uses_first_segment() -> None:
    h = compute_node_hierarchy("actions.api/src/Foo/Bar.cs")
    assert h["l0"] == "actions.api"
    assert h["l1"] == "actions.api/Foo"  # 'src' stripped via _PATH_PREFIX_DROP
    assert h["l2"] == "actions.api/Foo"


def test_path_based_l1_l2_use_more_segments_when_available() -> None:
    h = compute_node_hierarchy("repo/area/sub/deep/leaf.cs")
    assert h["l0"] == "repo"
    assert h["l1"] == "repo/area"
    assert h["l2"] == "repo/area/sub"


def test_orphan_with_community_collapses_to_external_l0() -> None:
    h = compute_node_hierarchy(None, fallback_community=42)
    assert h["l0"] == "external"
    # Community ID preserved at L1/L2 so Leiden structure is still navigable
    assert h["l1"] == "external/comm:42"
    assert h["l2"] == "external/comm:42"


def test_orphans_across_many_communities_share_one_l0() -> None:
    # Regression for the L0-fragmentation bug: 440+ singleton L0s on
    # multi-repo platforms because each orphan was getting its own
    # comm:<id> bucket. With the collapse fix, every orphan lands in
    # the same L0 regardless of its community.
    l0s = {compute_node_hierarchy(None, fallback_community=c)["l0"]
           for c in range(500)}
    assert l0s == {"external"}


def test_orphan_without_community_returns_none_keys() -> None:
    h = compute_node_hierarchy(None, fallback_community=None)
    assert h == {"l0": None, "l1": None, "l2": None}


def test_empty_string_source_file_treated_as_orphan() -> None:
    h = compute_node_hierarchy("", fallback_community=7)
    assert h["l0"] == "external"


def test_windows_path_separators_normalized() -> None:
    h = compute_node_hierarchy("repo\\area\\file.cs")
    assert h["l0"] == "repo"
    assert h["l1"] == "repo/area"


def test_filename_dropped_before_segmenting() -> None:
    # Single-segment paths (just a filename) should fall back, not use
    # the bare filename as L0.
    h = compute_node_hierarchy("just_a_file.cs", fallback_community=99)
    assert h["l0"] == "external"
