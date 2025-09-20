# backend/app/services/url_service.py

from app.services.analysis_engine import analyze_url_pipeline
from app.models import Result

async def analyze_url(url: str, language: str = "en") -> Result:
    """
    Wrapper around analysis_engine for URL analysis.
    Returns a Result object formatted for frontend.
    """
    return await analyze_url_pipeline(url, language)
