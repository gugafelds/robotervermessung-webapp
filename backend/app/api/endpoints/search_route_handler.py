# backend/app/api/endpoints/search_route_handler.py

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict
import logging
from ...database import get_db
from ...utils.multi_modal_searcher import MultiModalSearcher

logger = logging.getLogger(__name__)
router = APIRouter()


class SimilaritySearchResponse(BaseModel):
    """Response für Similarity Search"""
    target_id: str
    modes: List[str]
    weights: Dict[str, float]
    prefilter_enabled: bool
    results: List[Dict]
    metadata: Dict
    error: Optional[str] = None


@router.get("/similar/{target_id}")
async def search_similar_get(
        target_id: str,
        modes: Optional[str] = Query(None, description="Comma-separated: joint,position,orientation,velocity,acceleration,metadata"),
        joint_weight: float = Query(0.0, ge=0.0, le=1.0),
        position_weight: float = Query(1.0, ge=0.0, le=1.0),
        orientation_weight: float = Query(0.0, ge=0.0, le=1.0),
        velocity_weight: float = Query(0.0, ge=0.0, le=1.0),
        acceleration_weight: float = Query(0.0, ge=0.0, le=1.0),
        metadata_weight: float = Query(0.0, ge=0.0, le=1.0),
        limit: int = Query(10, ge=1, le=100),
        prefilter_features: Optional[str] = Query(
            None, 
            description="Comma-separated prefilter features: length,duration,movement_type,position_3d"
        ),
        conn=Depends(get_db)
):
    """
    GET Endpoint für schnelle Tests (gleiche Funktionalität wie POST)

    **Beispiel:**
```
    GET /search/similar/1760613717?joint_weight=0.5&position_weight=0.3&orientation_weight=0.2&limit=10&prefilter_features=length,duration
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
            'orientation': orientation_weight,
            'velocity': velocity_weight,
            'acceleration': acceleration_weight,
            'metadata': metadata_weight
        }

        prefilter_features_list = []
        
        
        if prefilter_features:
            prefilter_features_list = [f.strip() for f in prefilter_features.split(',')]
            
            # Validation
            allowed_features = {'length', 'duration', 'movement_type', 'position_3d', 'velocity_profile', 'acceleration_profile'}
            invalid_features = [f for f in prefilter_features_list if f not in allowed_features]

            if invalid_features:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid prefilter features: {invalid_features}. Allowed: {list(allowed_features)}"
                )

        searcher = MultiModalSearcher(conn)

        result = await searcher.search_similar(
            target_id=target_id,
            modes=mode_list,
            weights=weights,
            limit=limit,
            prefilter_features=prefilter_features_list
        )

        if result.get('error'):
            raise HTTPException(status_code=404, detail=result['error'])

        #logger.info(f"{result}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in similarity search: {e}")
        raise HTTPException(status_code=500, detail=str(e))