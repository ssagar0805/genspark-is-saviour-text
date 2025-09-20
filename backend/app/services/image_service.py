# backend/app/services/image_service.py

from app.services.analysis_engine import analyze_image_pipeline
from app.models import Result

async def analyze_image(image_base64: str, language: str = "en") -> Result:
    """
    Wrapper around analysis_engine for image analysis.
    Returns a Result object formatted for frontend.
    """
    return await analyze_image_pipeline(image_base64, language)
