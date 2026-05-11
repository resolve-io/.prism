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
