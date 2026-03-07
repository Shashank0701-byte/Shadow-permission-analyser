import traceback

from fastapi import APIRouter, HTTPException
from app.graph.queries import get_full_graph

router = APIRouter()


@router.get("/graph")
def get_graph():
    """Return the full permission graph for visualization."""
    try:
        return get_full_graph()
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))