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


def test_node_hierarchy_collapses_orphan_communities_under_external():
    from app.services.graph_service import compute_node_hierarchy

    hierarchy = compute_node_hierarchy(None, fallback_community=1530)

    assert hierarchy == {
        "l0": "external",
        "l1": "external/comm:1530",
        "l2": "external/comm:1530",
    }


def test_node_hierarchy_treats_bcl_like_symbols_as_external():
    from app.services.graph_service import compute_node_hierarchy

    hierarchy = compute_node_hierarchy("System.String", fallback_community=629)

    assert hierarchy == {
        "l0": "external",
        "l1": "external/comm:629",
        "l2": "external/comm:629",
    }


def test_node_hierarchy_uses_external_without_source_or_community():
    from app.services.graph_service import compute_node_hierarchy

    hierarchy = compute_node_hierarchy(None, fallback_community=None)

    assert hierarchy == {
        "l0": "external",
        "l1": "external",
        "l2": "external",
    }


def test_architectural_layer_inference_prefers_semantic_roles():
    from app.services.graph_service import infer_architectural_layer

    assert infer_architectural_layer("app/ui/graph_page.py") == "ui"
    assert infer_architectural_layer("app/mcp/server.py") == "api"
    assert infer_architectural_layer("app/services/graph_service.py") == "service"
    assert infer_architectural_layer("app/models/memory.py") == "data"
    assert infer_architectural_layer("tests/unit/test_graph.py") == "test"


def test_architectural_layer_inference_handles_csharp_conventions():
    from app.services.graph_service import infer_architectural_layer

    assert infer_architectural_layer("src/Shop.Api/Controllers/OrdersController.cs") == "api"
    assert infer_architectural_layer("src/Shop.Application/Handlers/CreateOrderHandler.cs") == "service"
    assert infer_architectural_layer("src/Shop.Infrastructure/Repositories/OrderRepository.cs") == "data"
    assert infer_architectural_layer("src/Shop.Domain/Entities/Order.cs") == "domain"
    assert infer_architectural_layer("src/Shop.Web/Components/CartView.razor.cs") == "ui"
    assert infer_architectural_layer("tests/Shop.Tests/OrderTests.cs") == "test"
    assert infer_architectural_layer("src/Shop.Api/Program.cs") == "config"


def test_csharp_viewer_labels_strip_ast_member_dot():
    from app.services.graph_service import display_label_for_graph_node

    assert display_label_for_graph_node(".Bar()", "src/Shop.Api/Controllers/OrdersController.cs") == "Bar()"
    assert display_label_for_graph_node(".Bar()", "src/widget.ts") == ".Bar()"


def test_graph_viewer_rolls_csharp_methods_up_to_owner_type():
    from app.ui.graph_page import _collapse_visual_graph

    raw_nodes = [
        {
            "id": "basenode_basenode",
            "label": "BaseNode",
            "source_file": "src/Core/BaseNode.cs",
            "file_type": "class",
            "community": 7,
        },
        {
            "id": "basenode_basenode_tostring",
            "label": ".ToString()",
            "source_file": "src/Core/BaseNode.cs",
            "file_type": "method",
            "community": 7,
        },
    ]

    nodes, edges = _collapse_visual_graph(raw_nodes, [])

    assert edges == []
    assert len(nodes) == 1
    assert nodes[0]["label"] == "BaseNode"
    assert nodes[0]["visual_kind"] == "type"
    assert nodes[0]["member_count"] == 2
    assert {symbol["label"] for symbol in nodes[0]["symbols"]} == {
        "BaseNode",
        "ToString()",
    }


def test_graph_viewer_rolls_typescript_symbols_up_to_file():
    from app.ui.graph_page import _collapse_visual_graph

    raw_nodes = [
        {
            "id": "dynamic_form_service_notifybeforesave",
            "label": ".notifyBeforeSave()",
            "source_file": "src/app/dynamic-form-service.ts",
            "file_type": "method",
            "community": 3,
        },
        {
            "id": "dynamic_form_service_validate",
            "label": "validate()",
            "source_file": "src/app/dynamic-form-service.ts",
            "file_type": "function",
            "community": 3,
        },
    ]

    nodes, _edges = _collapse_visual_graph(raw_nodes, [])

    assert len(nodes) == 1
    assert nodes[0]["label"] == "dynamic-form-service"
    assert nodes[0]["visual_kind"] == "file"
    assert nodes[0]["member_count"] == 2


def test_graph_viewer_aggregates_edges_between_visual_leaves():
    from app.ui.graph_page import _collapse_visual_graph

    raw_nodes = [
        {
            "id": "orderhandler_orderhandler",
            "label": "OrderHandler",
            "source_file": "src/App/OrderHandler.cs",
            "file_type": "class",
            "community": 1,
        },
        {
            "id": "orderhandler_orderhandler_handle",
            "label": ".Handle()",
            "source_file": "src/App/OrderHandler.cs",
            "file_type": "method",
            "community": 1,
        },
        {
            "id": "orders_component_save",
            "label": "save()",
            "source_file": "src/app/orders.component.ts",
            "file_type": "method",
            "community": 2,
        },
    ]
    raw_edges = [
        {"source": "orderhandler_orderhandler", "target": "orders_component_save", "relation": "calls"},
        {"source": "orderhandler_orderhandler_handle", "target": "orders_component_save", "relation": "calls"},
    ]

    nodes, edges = _collapse_visual_graph(raw_nodes, raw_edges)

    assert len(nodes) == 2
    assert len(edges) == 1
    assert edges[0]["aggregate_count"] == 2
    assert edges[0]["source"].startswith("type::")
    assert edges[0]["target"].startswith("file::")


def test_graph_viewer_keeps_orphan_nodes_visible_at_l0():
    from app.ui.graph_page import _collapse_visual_graph

    raw_nodes = [
        {
            "id": "system_string_length",
            "label": "Length",
            "file_type": "property",
        },
    ]

    nodes, _edges = _collapse_visual_graph(raw_nodes, [])

    assert len(nodes) == 1
    assert nodes[0]["l0"] == "external"
    assert nodes[0]["l1"] == "external"
    assert nodes[0]["l2"] == "external"


def test_node_hierarchy_skips_unity_wrapper_dirs():
    from app.services.graph_service import compute_node_hierarchy

    hierarchy = compute_node_hierarchy(
        "Assets/Scripts/Gameplay/PlayerController.cs",
        fallback_community=7,
    )

    assert hierarchy == {
        "l0": "comm:7",
        "l1": "comm:7/Gameplay",
        "l2": "comm:7/Gameplay",
    }


def test_node_hierarchy_prefers_dotnet_project_regions():
    from app.services.graph_service import compute_node_hierarchy

    hierarchy = compute_node_hierarchy(
        "repo/src/Commerce/Shop.Api/Controllers/OrdersController.cs",
        fallback_community=9,
    )

    assert hierarchy == {
        "l0": "comm:9",
        "l1": "comm:9/Shop.Api",
        "l2": "comm:9/Shop.Api/Controllers",
    }


def test_node_hierarchy_skips_dotnet_feature_wrapper():
    from app.services.graph_service import compute_node_hierarchy

    hierarchy = compute_node_hierarchy(
        "repo/src/Commerce/Shop.Application/Features/Orders/CreateOrderHandler.cs",
        fallback_community=9,
    )

    assert hierarchy == {
        "l0": "comm:9",
        "l1": "comm:9/Shop.Application",
        "l2": "comm:9/Shop.Application/Orders",
    }


def test_node_hierarchy_uses_dotnet_project_without_community():
    from app.services.graph_service import compute_node_hierarchy

    hierarchy = compute_node_hierarchy(
        "src/Inventory/Inventory.Infrastructure/Persistence/AppDbContext.cs",
        fallback_community=None,
    )

    assert hierarchy == {
        "l0": "Inventory.Infrastructure",
        "l1": "Inventory.Infrastructure/Persistence",
        "l2": "Inventory.Infrastructure/Persistence",
    }


def test_dotnet_community_prefix_labels_use_project_and_feature():
    from app.services.graph_service import _path_prefix_label

    nodes = [
        {
            "source_file":
                "repo/src/Commerce/Shop.Application/Features/Orders/CreateOrderHandler.cs"
        },
        {
            "source_file":
                "repo/src/Commerce/Shop.Application/Features/Orders/GetOrderHandler.cs"
        },
        {
            "source_file":
                "repo/src/Commerce/Shop.Application/Features/Orders/CancelOrderHandler.cs"
        },
    ]

    assert _path_prefix_label(nodes) == "shop application orders"


def test_csharp_files_are_indexable_and_graph_staged(tmp_path):
    from app.engines.brain_engine import Brain
    from app.services.graph_service import GraphService

    brain = Brain(
        brain_db=str(tmp_path / "brain.db"),
        graph_db=str(tmp_path / "graph.db"),
        scores_db=str(tmp_path / "scores.db"),
    )
    assert brain._should_index("src/Shop.Api/Controllers/OrdersController.cs")
    assert brain._should_index("src/Shop.Api/Shop.Api.csproj")
    assert brain._should_index("src/Shop.Web/Components/Cart.razor")

    graph_dir = tmp_path / "graph"
    svc = GraphService(
        project_data_dir=str(graph_dir),
        graph_db_path=str(graph_dir / "graph.db"),
    )
    assert svc.stage_doc("src/Shop.Api/Controllers/OrdersController.cs", "class OrdersController {}")
    assert svc.stage_doc("src/Shop.Api/Shop.Api.csproj", "<Project />")
    assert svc.stage_doc("src/Shop.Web/Components/Cart.razor", "@code {}")


def test_import_prunes_collapsed_csharp_unresolved_call_hubs(tmp_path):
    import sqlite3

    from app.engines.brain_engine import Brain
    from app.services.graph_service import GraphService

    graph_db = tmp_path / "graph.db"
    Brain(
        brain_db=str(tmp_path / "brain.db"),
        graph_db=str(graph_db),
        scores_db=str(tmp_path / "scores.db"),
    )
    svc = GraphService(
        project_data_dir=str(tmp_path / "graph"),
        graph_db_path=str(graph_db),
    )

    nodes = []
    links = []

    for i in range(10):
        nodes.append({
            "id": f"be_{i}",
            "label": ".Be()",
            "source_file": f"tests/Assertions{i}.cs",
            "source_location": "L10",
            "file_type": "method",
            "community": 1,
        })
    for i in range(10):
        nodes.append({
            "id": f"get_{i}",
            "label": ".GetById()",
            "source_file": f"src/Repo{i}.cs",
            "source_location": "L20",
            "file_type": "method",
            "community": 2,
        })

    for i in range(60):
        caller = f"be_caller_{i}"
        nodes.append({
            "id": caller,
            "label": f"BeCaller{i}",
            "source_file": f"tests/Caller{i}.cs",
            "source_location": "L30",
            "file_type": "method",
            "community": 1,
        })
        links.append({
            "source": caller,
            "target": "be_0",
            "relation": "calls",
            "source_file": f"tests/Caller{i}.cs",
        })

    nodes.append({
        "id": "be_local_caller",
        "label": "LocalBeCaller",
        "source_file": "tests/Assertions0.cs",
        "source_location": "L35",
        "file_type": "method",
        "community": 1,
    })
    links.append({
        "source": "be_local_caller",
        "target": "be_0",
        "relation": "calls",
        "source_file": "tests/Assertions0.cs",
    })

    for i in range(60):
        caller = f"get_caller_{i}"
        target = f"get_{i % 10}"
        nodes.append({
            "id": caller,
            "label": f"GetCaller{i}",
            "source_file": f"src/Service{i}.cs",
            "source_location": "L40",
            "file_type": "method",
            "community": 2,
        })
        links.append({
            "source": caller,
            "target": target,
            "relation": "calls",
            "source_file": f"src/Service{i}.cs",
        })

    result = svc._import_graph_json(
        {"nodes": nodes, "links": links},
        {"imported_entities": 0, "imported_relationships": 0},
    )

    assert result["pruned_unresolved_call_edges"] == 60
    assert result["imported_relationships"] == 61

    conn = sqlite3.connect(str(graph_db))
    try:
        be_nodes = conn.execute(
            "SELECT COUNT(*) FROM entities WHERE label = '.Be()'"
        ).fetchone()[0]
        assert be_nodes == 10

        rows = conn.execute(
            "SELECT e.label, COUNT(*) "
            "FROM relationships r "
            "JOIN entities e ON e.id = r.target_id "
            "GROUP BY e.label"
        ).fetchall()
        incoming_by_label = {label: count for label, count in rows}
    finally:
        conn.close()

    assert incoming_by_label[".Be()"] == 1
    assert incoming_by_label[".GetById()"] == 60


def test_safe_graphify_call_resolution_uses_phantoms_for_ambiguous_labels():
    from app.services.graph_service import (
        _merge_graphify_extractions_with_safe_calls,
    )

    per_file = [
        {
            "nodes": [
                {
                    "id": "caller_do",
                    "label": "Do()",
                    "file_type": "code",
                    "source_file": "src/Caller.cs",
                }
            ],
            "edges": [],
            "raw_calls": [
                {
                    "caller_nid": "caller_do",
                    "callee": "Be",
                    "source_file": "src/Caller.cs",
                    "source_location": "L12",
                }
            ],
        },
        {
            "nodes": [
                {
                    "id": "test_a_be",
                    "label": ".Be()",
                    "file_type": "code",
                    "source_file": "tests/A.cs",
                },
                {
                    "id": "test_b_be",
                    "label": ".Be()",
                    "file_type": "code",
                    "source_file": "tests/B.cs",
                },
            ],
            "edges": [],
            "raw_calls": [],
        },
    ]

    merged = _merge_graphify_extractions_with_safe_calls(per_file, [])

    phantom_nodes = [
        node for node in merged["nodes"]
        if node["id"].startswith("unresolved_call_be_")
    ]
    assert len(phantom_nodes) == 1
    assert phantom_nodes[0]["file_type"] == "unresolved_call"
    assert merged["ambiguous_call_phantoms"] == 1
    assert {
        (edge["source"], edge["target"], edge["confidence"])
        for edge in merged["edges"]
    } == {("caller_do", phantom_nodes[0]["id"], "AMBIGUOUS")}


def test_safe_graphify_call_resolution_preserves_unambiguous_calls():
    from app.services.graph_service import (
        _merge_graphify_extractions_with_safe_calls,
    )

    per_file = [
        {
            "nodes": [
                {
                    "id": "caller_do",
                    "label": "Do()",
                    "file_type": "code",
                    "source_file": "src/Caller.cs",
                },
                {
                    "id": "target_save",
                    "label": ".Save()",
                    "file_type": "code",
                    "source_file": "src/Repo.cs",
                },
            ],
            "edges": [],
            "raw_calls": [
                {
                    "caller_nid": "caller_do",
                    "callee": "Save",
                    "source_file": "src/Caller.cs",
                    "source_location": "L12",
                }
            ],
        }
    ]

    merged = _merge_graphify_extractions_with_safe_calls(per_file, [])

    assert merged["ambiguous_call_phantoms"] == 0
    assert {
        (edge["source"], edge["target"], edge["confidence"])
        for edge in merged["edges"]
    } == {("caller_do", "target_save", "INFERRED")}


def test_prism_detect_code_files_supplements_graphify_python_only_detection(tmp_path):
    from app.services.graph_service import _prism_detect_code_files

    root = tmp_path / "graphify-src"
    (root / "src").mkdir(parents=True)
    (root / "src" / "OrderHandler.cs").write_text("class OrderHandler {}", encoding="utf-8")
    (root / "web").mkdir()
    (root / "web" / "orders.component.tsx").write_text("export class Orders {}", encoding="utf-8")
    (root / "ai").mkdir()
    py_file = root / "ai" / "otel.py"
    py_file.write_text("def boot(): pass", encoding="utf-8")
    (root / "graphify-out").mkdir()
    (root / "graphify-out" / "stale.cs").write_text("class Stale {}", encoding="utf-8")

    files = _prism_detect_code_files(root, [py_file])
    rel = {p.relative_to(root).as_posix() for p in files}

    assert rel == {
        "ai/otel.py",
        "src/OrderHandler.cs",
        "web/orders.component.tsx",
    }


def test_prism_fallback_extracts_csharp_nodes_and_same_file_calls(tmp_path):
    from app.services.graph_service import (
        _extract_prism_fallback_graph,
        _merge_graphify_extractions_with_safe_calls,
    )

    root = tmp_path / "graphify-src"
    source = root / "src" / "OrderHandler.cs"
    source.parent.mkdir(parents=True)
    source.write_text(
        """
namespace Shop;
public class OrderHandler {
    public void Handle() { Save(); }
    public void Save() { }
}
""",
        encoding="utf-8",
    )

    extracted = _extract_prism_fallback_graph(source, root)
    labels = {node["label"] for node in extracted["nodes"]}

    assert {"OrderHandler", ".Handle()", ".Save()"}.issubset(labels)
    assert any(edge["relation"] == "contains" for edge in extracted["edges"])
    assert any(call["callee"] == "Save" for call in extracted["raw_calls"])

    merged = _merge_graphify_extractions_with_safe_calls([extracted], [source])
    label_by_id = {node["id"]: node["label"] for node in merged["nodes"]}
    assert (".Handle()", ".Save()", "INFERRED") in {
        (
            label_by_id[edge["source"]],
            label_by_id[edge["target"]],
            edge.get("confidence"),
        )
        for edge in merged["edges"]
        if edge["relation"] == "calls"
    }


def test_prism_fallback_extracts_typescript_nodes(tmp_path):
    from app.services.graph_service import _extract_prism_fallback_graph

    root = tmp_path / "graphify-src"
    source = root / "web" / "orders.component.ts"
    source.parent.mkdir(parents=True)
    source.write_text(
        """
export class OrdersComponent {
  load() { this.refresh(); }
  refresh() {}
}
export function makeOrder() { return new OrdersComponent(); }
""",
        encoding="utf-8",
    )

    extracted = _extract_prism_fallback_graph(source, root)
    labels = {node["label"] for node in extracted["nodes"]}

    assert "OrdersComponent" in labels
    assert "load()" in labels
    assert "refresh()" in labels
    assert any(call["callee"] == "refresh" for call in extracted["raw_calls"])
