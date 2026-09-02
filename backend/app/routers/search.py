import time
from fastapi import APIRouter, Depends, File, UploadFile, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.middleware.auth import get_current_admin
from app.models.search_log import SearchLog
from app.services.search_service import run_visual_search
from ai.gatekeeper import validate_tile_image

GATEKEEPER_REJECTION_MESSAGE = (
    "Please upload a valid marble, tile, or stone surface image."
)

router = APIRouter(prefix="/api/search", tags=["Visual Search"])

@router.post("/image")
async def search_by_image(
    file: UploadFile = File(...),
    top_k: int = Query(3, ge=1, le=10),
    material_id: Optional[int] = Query(None),
    color_family_id: Optional[int] = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=100.0),
    db: Session = Depends(get_db)
):
    try:
        start_time = time.time()

        # Read uploaded image bytes
        image_bytes = await file.read()

        gatekeeper_result = validate_tile_image(image_bytes)
        if not gatekeeper_result["is_tile"]:
            raise HTTPException(
                status_code=400,
                detail=GATEKEEPER_REJECTION_MESSAGE,
            )

        # Run visual search
        search_response = run_visual_search(
            db=db,
            image_bytes=image_bytes,
            top_k=top_k,
            min_confidence=min_confidence / 100,
            material_id=material_id,
            color_family_id=color_family_id
        )

        # Extract results and validation info
        results = search_response.get("results", [])
        validation = search_response.get("validation", {})
        error_msg = search_response.get("error", None)

        response_time_ms = int((time.time() - start_time) * 1000)

        # Check if image is not a tile
        if error_msg and not validation.get("is_tile", False):
            return {
                "results": [],
                "total_found": 0,
                "response_time_ms": response_time_ms,
                "status": "rejected_not_tile",
                "validation": validation,
                "error": error_msg
            }

        # Log the search
        top_match = results[0] if results else None
        log = SearchLog(
            query_image_url = "uploaded_image",
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
            "status":          log.status,
            "validation":      validation
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        import sys
        tb = traceback.format_exc()
        print(f"ERROR in search_by_image: {str(e)}", file=sys.stderr)
        print(tb, file=sys.stderr)
        sys.stderr.flush()
        raise HTTPException(status_code=500, detail={
            "message": "search image failed",
            "error": str(e),
            "traceback": tb,
            "hint": "restart backend and run seed_tiles.py if missing embeddings"
        })

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