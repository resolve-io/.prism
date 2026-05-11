from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_SERVICE_ROOT = _HERE.parent.parent.parent
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))


def test_node_hierarchy_uses_leiden_community_as_l0():
    from app.services.graph_service import compute_node_hierarchy

    hierarchy = compute_node_hierarchy(
        "services/prism-service/app/ui/graph_page.py",
        fallback_community=42,
    )

    assert hierarchy == {
        "l0": "comm:42",
        "l1": "comm:42/prism-service",
        "l2": "comm:42/prism-service/ui",
    }


def test_node_hierarchy_preserves_path_fallback_without_community():
    from app.services.graph_service import compute_node_hierarchy

    hierarchy = compute_node_hierarchy(
        "services/prism-service/app/ui/graph_page.py",
        fallback_community=None,
    )

    assert hierarchy == {
        "l0": "prism-service",
        "l1": "prism-service/ui",
        "l2": "prism-service/ui",
    }


def test_architectural_layer_inference_prefers_semantic_roles():
    from app.services.graph_service import infer_architectural_layer

    assert infer_architectural_layer("app/ui/graph_page.py") == "ui"
    assert infer_architectural_layer("app/mcp/server.py") == "api"
    assert infer_architectural_layer("app/services/graph_service.py") == "service"
    assert infer_architectural_layer("app/models/memory.py") == "data"
    assert infer_architectural_layer("tests/unit/test_graph.py") == "test"
