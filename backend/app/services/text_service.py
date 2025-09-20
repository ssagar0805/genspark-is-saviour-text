# backend/app/services/text_service.py
"""
Text Service: Wraps the text analysis pipeline.
"""

from app.services.analysis_engine import analyze_text_pipeline
from app.models import Result


async def analyze_text(content: str, language: str = "en") -> Result:
    """
    Run text analysis pipeline.
    Args:
        content (str): Input text
        language (str): Language hint (default: "en")
    Returns:
        Result: Standardized analysis result
    """
    return await analyze_text_pipeline(content, language)
