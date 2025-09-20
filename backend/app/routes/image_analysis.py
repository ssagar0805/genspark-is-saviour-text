# backend/app/routes/image_analysis.py

from fastapi import APIRouter, HTTPException
from app.services.image_service import analyze_image
from app.models import Result

router = APIRouter()

@router.post("/analyze/image", response_model=Result)
async def analyze_image_route(payload: dict):
    """
    Endpoint for analyzing images.
    Expects JSON: { "image_base64": "<base64string>", "language": "en" }
    """
    try:
        image_base64 = payload.get("image_base64")
        language = payload.get("language", "en")

        if not image_base64:
            raise HTTPException(status_code=400, detail="image_base64 is required")

        result = await analyze_image(image_base64, language)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
