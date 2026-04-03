import time
from fastapi import APIRouter, Depends, File, UploadFile, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.middleware.auth import get_current_admin
from app.models.search_log import SearchLog
from ai.search import search_tile

router = APIRouter(prefix="/api/search", tags=["Visual Search"])

@router.post("/image")
async def search_by_image(
    file: UploadFile = File(...),
    top_k: int = Query(5, ge=1, le=10),
    material_id: Optional[int] = Query(None),
    color_family_id: Optional[int] = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=100.0),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin)
):
    start_time = time.time()

    # Read uploaded image bytes
    image_bytes = await file.read()

    # Run visual search
    results = search_tile(
        image_input     = image_bytes,
        db              = db,
        top_k           = top_k,
        min_confidence  = min_confidence / 100,  # convert % to 0-1
        material_id     = material_id,
        color_family_id = color_family_id
    )

    response_time_ms = int((time.time() - start_time) * 1000)

    # Log the search
    top_match = results[0] if results else None
    log = SearchLog(
        matched_tile_id  = top_match["tile_id"] if top_match else None,
        confidence       = top_match["confidence"] / 100 if top_match else None,
        response_time_ms = response_time_ms,
        status           = (
            "matched"        if top_match and top_match["confidence"] >= 75
            else "low_confidence" if top_match
            else "no_match"
        )
    )
    db.add(log)
    db.commit()

    return {
        "results":         results,
        "total_found":     len(results),
        "response_time_ms": response_time_ms,
        "status":          log.status
    }

@router.get("/history")
def search_history(
    limit: int = Query(50),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin)
):
    logs = db.query(SearchLog)\
             .order_by(SearchLog.searched_at.desc())\
             .limit(limit).all()
    return logs