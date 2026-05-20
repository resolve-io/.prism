"""Learning API — Layer-A quality rows + variant performance rankings."""

from fastapi import APIRouter, Query

from app.project_context import get_project
from app.services.learning_data import get_learning_rows, get_variant_performance

router = APIRouter()


@router.get("")
def overview(project: str = Query("default"), limit: int = Query(100, ge=1, le=500)) -> dict:
    ctx = get_project(project)
    scores_db = str(ctx._data_dir / "scores.db")
    return {
        "rows": get_learning_rows(scores_db, limit=limit),
        "variants": get_variant_performance(scores_db),
    }
