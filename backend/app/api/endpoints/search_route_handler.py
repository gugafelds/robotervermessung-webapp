# backend/app/routers/search.py

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import logging
from ...database import get_db
from ...utils.multi_modal_searcher import MultiModalSearcher

logger = logging.getLogger(__name__)
router = APIRouter()


class SimilaritySearchRequest(BaseModel):
    """Request Body für Similarity Search"""
    target_id: str = Field(..., description="Target Bahn/Segment ID")
    modes: Optional[List[str]] = Field(
        None,
        description="Embedding modes: 'joint', 'position', 'orientation'"
    )
    weights: Optional[Dict[str, float]] = Field(
        None,
        description="Weights für RRF Fusion, z.B. {'joint': 0.5, 'position': 0.3, 'orientation': 0.2}"
    )
    use_prefilter: bool = Field(
        True,
        description="Pre-Filter aktivieren (empfohlen für Performance)"
    )
    prefilter_tolerance: float = Field(
        0.25,
        ge=0.1,
        le=1.0,
        description="Pre-Filter Tolerance (±Prozent), z.B. 0.25 = ±25%"
    )
    limit: int = Field(
        10,
        ge=1,
        le=100,
        description="Anzahl Ergebnisse"
    )


class SimilaritySearchResponse(BaseModel):
    """Response für Similarity Search"""
    target_id: str
    modes: List[str]
    weights: Dict[str, float]
    prefilter_enabled: bool
    results: List[Dict]
    metadata: Dict
    error: Optional[str] = None


@router.post("/similar", response_model=SimilaritySearchResponse)
async def search_similar(
        request: SimilaritySearchRequest,
        conn=Depends(get_db)
):
    """
    Multi-Modal Similarity Search mit Pre-Filter + RRF Fusion

    **Flow:**
    1. Pre-Filter basierend auf Features (duration, twist, accel)
    2. Shape Search mit Embeddings (joint, position, orientation)
    3. RRF Fusion mit user-definierten Gewichten

    **Beispiel:**
```json
    {
      "target_id": "1760613717",
      "modes": ["joint", "position", "orientation"],
      "weights": {
        "joint": 0.5,
        "position": 0.3,
        "orientation": 0.2
      },
      "use_prefilter": true,
      "prefilter_tolerance": 0.25,
      "limit": 10
    }
```
    """
    try:
        searcher = MultiModalSearcher(conn)

        result = await searcher.search_similar(
            target_id=request.target_id,
            modes=request.modes,
            weights=request.weights,
            use_prefilter=request.use_prefilter,
            prefilter_tolerance=request.prefilter_tolerance,
            limit=request.limit
        )

        if result.get('error'):
            raise HTTPException(status_code=404, detail=result['error'])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in similarity search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/similar/{target_id}")
async def search_similar_get(
        target_id: str,
        modes: Optional[str] = Query(None, description="Comma-separated: joint,position,orientation"),
        joint_weight: float = Query(0.0, ge=0.0, le=1.0),
        position_weight: float = Query(1.0, ge=0.0, le=1.0),
        orientation_weight: float = Query(0.0, ge=0.0, le=1.0),
        use_prefilter: bool = Query(True),
        prefilter_tolerance: float = Query(0.25, ge=0.1, le=1.0),
        bahn_limit: int = Query(10, ge=1, le=100),
        segment_limit: int = Query(10, ge=1, le=100),
        conn=Depends(get_db)
):
    """
    GET Endpoint für schnelle Tests (gleiche Funktionalität wie POST)

    **Beispiel:**
```
    GET /search/similar/1760613717?joint_weight=0.5&position_weight=0.3&orientation_weight=0.2&limit=10
```
    """
    try:
        # Parse modes
        mode_list = None
        if modes:
            mode_list = [m.strip() for m in modes.split(',')]

        # Build weights
        weights = {
            'joint': joint_weight,
            'position': position_weight,
            'orientation': orientation_weight
        }

        searcher = MultiModalSearcher(conn)

        result = await searcher.search_similar(
            target_id=target_id,
            modes=mode_list,
            weights=weights,
            use_prefilter=use_prefilter,
            prefilter_tolerance=prefilter_tolerance,
            bahn_limit=bahn_limit,
            segment_limit=segment_limit

        )

        if result.get('error'):
            raise HTTPException(status_code=404, detail=result['error'])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in similarity search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/similar/adaptive")
async def search_similar_adaptive(
        target_id: str,
        modes: Optional[List[str]] = None,
        weights: Optional[Dict[str, float]] = None,
        limit: int = Query(10, ge=1, le=100),
        conn=Depends(get_db)
):
    """
    ADAPTIVE Similarity Search

    Findet automatisch die beste Pre-Filter Strategie
    """
    try:
        searcher = MultiModalSearcher(conn)

        result = await searcher.search_adaptive(
            target_id=target_id,
            modes=modes,
            weights=weights,
            bahn_limit=limit,
            segment_limit=limit
        )

        if result.get('error'):
            raise HTTPException(status_code=404, detail=result['error'])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in adaptive search: {e}")
        raise HTTPException(status_code=500, detail=str(e))