# backend/app/services/analysis_engine.py
"""
Orchestration engine for CrediScope analysis pipeline.

Responsibilities:
- Translate input to English if needed
- Dispatch to text/url/image pipelines
- Collect signals from multiple APIs:
  - Google Cloud Translate (Translation)
  - Google Fact Check Tools (Fact checks)
  - Google Custom Search (evidence / reverse image lookup)
  - Wikipedia (context)
  - Perspective API (manipulative/toxic scoring)
  - Google Vision API (image OCR / metadata)
  - Safe Browsing API (URL threat checking)
  - Vertex/Gemini (LLM reasoning / structured output)
- Merge signals into a Result (app.models.Result)
"""

# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv()

import os
import time
import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from urllib.parse import quote as urlquote

import aiohttp

from app.models import (
    Result,
    Verdict,
    Evidence,
    EducationalChecklistItem,
    IntelligenceReport,
)

logger = logging.getLogger("analysis_engine")
logger.setLevel(os.getenv("LOGLEVEL", "INFO"))


# -------------------------
# Config from environment
# -------------------------
TRANSLATION_API_KEY = os.getenv("TRANSLATION_API_KEY")
CUSTOM_SEARCH_API_KEY = os.getenv("CUSTOM_SEARCH_API_KEY")
CUSTOM_SEARCH_CX = os.getenv("CUSTOM_SEARCH_CX")
FACTCHECK_API_KEY = os.getenv("FACT_CHECK_API_KEY") or os.getenv("FACTCHECK_API_KEY")
PERSPECTIVE_API_KEY = os.getenv("PERSPECTIVE_API_KEY")
VISION_API_KEY = os.getenv("VISION_API_KEY") or os.getenv("GOOGLE_VISION_API_KEY")
SAFE_BROWSING_API_KEY = os.getenv("SAFE_BROWSING_API_KEY")
VERTEX_API_KEY = os.getenv("VERTEX_API_KEY")
VERTEX_PROJECT = os.getenv("VERTEX_PROJECT")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
VERTEX_ENDPOINT_ID = os.getenv("VERTEX_ENDPOINT_ID")

HTTP_TIMEOUT = aiohttp.ClientTimeout(total=30)


# -----------------------
# Helper / External APIs
# -----------------------
async def detect_language(text: str) -> str:
    """Detect language using Google Translate REST (v2). Fall back to 'en'."""
    if not TRANSLATION_API_KEY:
        logger.debug("No TRANSLATION_API_KEY — default to 'en'")
        return "en"
    url = f"https://translation.googleapis.com/language/translate/v2/detect?key={TRANSLATION_API_KEY}"
    payload = {"q": text}
    try:
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.post(url, json=payload) as resp:
                j = await resp.json()
                detections = j.get("data", {}).get("detections", [])
                if detections and isinstance(detections[0], list) and detections[0]:
                    return detections[0][0].get("language", "en")
    except Exception:
        logger.exception("detect_language failed")
    return "en"


async def translate_text(text: str, target: str = "en") -> str:
    """Translate text -> target using Google Translate v2 REST. Return original on failure."""
    if not TRANSLATION_API_KEY:
        return text
    url = f"https://translation.googleapis.com/language/translate/v2?key={TRANSLATION_API_KEY}"
    payload = {"q": text, "target": target, "format": "text"}
    try:
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.post(url, json=payload) as resp:
                j = await resp.json()
                return j.get("data", {}).get("translations", [{}])[0].get("translatedText", text)
    except Exception:
        logger.exception("translate_text failed")
    return text

async def google_custom_search(query: str, num: int = 5) -> List[Dict[str, Any]]:
    """Return top search results using Google Custom Search API - hybrid OAuth2/API key approach."""
    
    # Method 1: Try OAuth2 first (your current implementation)
    try:
        from .oauth2_service import oauth2_service
        service = oauth2_service.get_custom_search_service()
        engine_id = os.getenv('CUSTOM_SEARCH_ENGINE_ID')
        
        if engine_id:
            result = service.cse().list(
                q=query,
                cx=engine_id,
                num=num
            ).execute()
            
            items = result.get("items", [])
            if items:  # If we got results, return them
                logger.info(f"OAuth2 Custom Search successful: {len(items)} results")
                return [
                    {
                        "title": it.get("title"),
                        "link": it.get("link"),
                        "snippet": it.get("snippet"),
                        "source": it.get("displayLink"),
                    }
                    for it in items
                ]
    except Exception as e:
        logger.warning(f"OAuth2 Custom Search failed, falling back to API key: {str(e)}")
    
    # Method 2: Fall back to API key method (original working approach)
    try:
        if not (CUSTOM_SEARCH_API_KEY and CUSTOM_SEARCH_CX):
            logger.debug("Custom Search not configured")
            return []
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {"key": CUSTOM_SEARCH_API_KEY, "cx": CUSTOM_SEARCH_CX, "q": query, "num": num}
        
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.get(url, params=params) as resp:
                j = await resp.json()
                items = j.get("items", [])
                logger.info(f"API key Custom Search successful: {len(items)} results")
                return [
                    {
                        "title": it.get("title"),
                        "link": it.get("link"),
                        "snippet": it.get("snippet"),
                        "source": it.get("displayLink"),
                    }
                    for it in items
                ]
    except Exception as e:
        logger.exception("Both OAuth2 and API key Custom Search failed")
        return []

async def wikipedia_lookup(query: str) -> Optional[Dict[str, Any]]:
    """Get short summary from Wikipedia."""
    try:
        safe_q = urlquote(query)
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{safe_q}"
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    j = await resp.json()
                    return {
                        "title": j.get("title"),
                        "extract": j.get("extract"),
                        "url": j.get("content_urls", {}).get("desktop", {}).get("page"),
                    }
    except Exception:
        logger.exception("wikipedia_lookup failed")
    return None


async def factcheck_search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Query Google Fact Check Tools API (claims:search)."""
    if not FACTCHECK_API_KEY:
        logger.debug("FactCheck API not configured")
        return []
    url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
    params = {"key": FACTCHECK_API_KEY, "query": query, "pageSize": top_k}
    try:
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.get(url, params=params) as resp:
                j = await resp.json()
                claims = j.get("claims", [])
                return [{"text": c.get("text"), "claimReview": c.get("claimReview", [])} for c in claims]
    except Exception:
        logger.exception("factcheck_search failed")
        return []


async def perspective_score(text: str) -> Dict[str, Any]:
    """Call Perspective API; returns attributeScores or empty dict."""
    if not PERSPECTIVE_API_KEY:
        logger.debug("Perspective API key not set")
        return {}
    url = "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze"
    payload = {
        "comment": {"text": text},
        "languages": ["en"],
        "requestedAttributes": {"TOXICITY": {}, "SEVERE_TOXICITY": {}, "INSULT": {}, "PROFANITY": {}},
    }
    params = {"key": PERSPECTIVE_API_KEY}
    try:
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.post(url, params=params, json=payload) as resp:
                j = await resp.json()
                return j.get("attributeScores", j)
    except Exception:
        logger.exception("perspective_score failed")
        return {}


async def safe_browsing_check(url_to_check: str) -> Dict[str, Any]:
    """Use Google Safe Browsing Lookup API to check URL threat. Returns raw response or empty."""
    if not SAFE_BROWSING_API_KEY:
        logger.debug("Safe Browsing not configured")
        return {}
    endpoint = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={SAFE_BROWSING_API_KEY}"
    body = {
        "client": {"clientId": "crediscope", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
            "platformTypes": ["ALL_PLATFORMS"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url_to_check}],
        },
    }
    try:
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.post(endpoint, json=body) as resp:
                j = await resp.json()
                return j
    except Exception:
        logger.exception("safe_browsing_check failed")
        return {}


async def vision_ocr_image_base64(image_base64: str) -> str:
    """OCR an image via Google Vision REST API. Return concatenated text or empty string."""
    if not VISION_API_KEY:
        logger.debug("Vision API not configured")
        return ""
    url = f"https://vision.googleapis.com/v1/images:annotate?key={VISION_API_KEY}"
    payload = {"requests": [{"image": {"content": image_base64}, "features": [{"type": "TEXT_DETECTION", "maxResults": 5}]}]}
    try:
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.post(url, json=payload) as resp:
                j = await resp.json()
                responses = j.get("responses", [])
                if responses:
                    annotations = responses[0].get("textAnnotations", [])
                    if annotations:
                        return annotations[0].get("description", "")
    except Exception:
        logger.exception("vision_ocr_image_base64 failed")
    return ""


# ---------------------------
# Vertex / Gemini LLM call
# ---------------------------
async def vertex_analyze(prompt: str, max_output_tokens: int = 512) -> Dict[str, Any]:
    """
    Call Vertex AI predict endpoint. Uses API key if present, otherwise expects ADC.
    Returns parsed JSON or fallback dict containing 'summary'.
    """
    if not (VERTEX_PROJECT and VERTEX_LOCATION and VERTEX_ENDPOINT_ID):
        logger.debug("Vertex not configured; returning fallback")
        return {"summary": (prompt[:800] + "...") if len(prompt) > 800 else prompt}

    base = f"https://{VERTEX_LOCATION}-aiplatform.googleapis.com/v1/projects/{VERTEX_PROJECT}/locations/{VERTEX_LOCATION}/endpoints/{VERTEX_ENDPOINT_ID}:predict"
    endpoint = base + (f"?key={VERTEX_API_KEY}" if VERTEX_API_KEY else "")
    headers = {"Content-Type": "application/json"}

    body = {
        "instances": [{"content": prompt}],
        "parameters": {"maxOutputTokens": max_output_tokens},
    }
    try:
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.post(endpoint, json=body, headers=headers) as resp:
                j = await resp.json()
                return j
    except Exception:
        logger.exception("vertex_analyze failed")
        return {"summary": prompt[:800]}


# ---------------------------
# Orchestrator helpers
# ---------------------------
async def _gather_evidence_and_checks(text: str) -> Dict[str, Any]:
    """
    Run parallel evidence retrieval and checks for a text claim.
    Returns consolidated dict with keys: fact_checks, search_results, wikipedia, perspective
    """
    tasks = [factcheck_search(text), google_custom_search(text, num=5), wikipedia_lookup(text), perspective_score(text)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    consolidated: Dict[str, Any] = {}
    consolidated["fact_checks"] = results[0] if not isinstance(results[0], Exception) else []
    consolidated["search_results"] = results[1] if not isinstance(results[1], Exception) else []
    consolidated["wikipedia"] = results[2] if not isinstance(results[2], Exception) else {}
    consolidated["perspective"] = results[3] if not isinstance(results[3], Exception) else {}
    return consolidated


# ---------------------------
# Pipelines: text / url / image
# ---------------------------
async def analyze_text_pipeline(original_text: str, language_hint: str = "en") -> Result:
    """
    Text pipeline:
     - detect/translate
     - evidence & signals
     - call LLM (Vertex/Gemini)
     - assemble Result according to app.models.Result
    """
    t0 = time.time()
    detected_lang = await detect_language(original_text)
    text = original_text
    if detected_lang and detected_lang != "en":
        text = await translate_text(original_text, target="en")

    signals = await _gather_evidence_and_checks(text)

    # Build LLM prompt with signals to request structured JSON
    prompt = (
        "You are an expert misinformation analyst. Given the CLAIM and EVIDENCE, "
        "produce JSON with keys: verdict_label (one of: ✅ Verified, ❌ False, ⚠️ Caution), "
        "confidence (0-100), quick_analysis (array of short bullets), evidence (array of {source, snippet, reliability}), "
        "checklist (array of {point, explanation}), intelligence (object with optional fields like political, financial, psychological, scientific, geopolitical, technical), "
        "summary (short plain text). Return only JSON.\n\n"
        f"CLAIM: {text}\n\n"
        "EVIDENCE (top search results):\n"
    )
    for it in (signals.get("search_results") or []):
        prompt += f"- {it.get('title')} ({it.get('link')}): {it.get('snippet')}\n"
    if signals.get("wikipedia"):
        prompt += f"\nWIKIPEDIA: {signals['wikipedia'].get('title')} — {signals['wikipedia'].get('extract')}\n"
    if signals.get("fact_checks"):
        prompt += "\nFACTCHECKS:\n"
        for fc in signals["fact_checks"]:
            prompt += f"- {fc.get('text')}\n"

    llm_output = await vertex_analyze(prompt, max_output_tokens=900)

    # Default fallbacks
    verdict_label = "⚠️ Caution"
    confidence_pct = 65
    quick_analysis_list: List[str] = []
    evidence_list: List[Dict[str, Any]] = []
    checklist_list: List[Dict[str, Any]] = []
    intelligence_sections: Dict[str, Any] = {}
    summary_text = ""

    # Try parse structured response from vertex
    try:
        if isinstance(llm_output, dict):
            # Common format: predictions -> list[0] with model payload
            if "predictions" in llm_output and isinstance(llm_output["predictions"], list) and llm_output["predictions"]:
                payload = llm_output["predictions"][0]
                # payload might already be dict or stringified JSON
                if isinstance(payload, dict):
                    verdict_label = payload.get("verdict_label") or payload.get("verdict") or verdict_label
                    confidence_pct = int(payload.get("confidence", confidence_pct))
                    quick_analysis_list = payload.get("quick_analysis", []) or payload.get("quick_analysis_text", []) or []
                    evidence_list = payload.get("evidence", []) or []
                    checklist_list = payload.get("checklist", []) or []
                    intelligence_sections = payload.get("intelligence", {}) or {}
                    summary_text = payload.get("summary", "") or ""
                else:
                    # payload could be a string — try to parse JSON
                    import json
                    try:
                        parsed = json.loads(payload)
                        verdict_label = parsed.get("verdict_label", verdict_label)
                        confidence_pct = int(parsed.get("confidence", confidence_pct))
                        quick_analysis_list = parsed.get("quick_analysis", []) or []
                        evidence_list = parsed.get("evidence", []) or []
                        checklist_list = parsed.get("checklist", []) or []
                        intelligence_sections = parsed.get("intelligence", {}) or {}
                        summary_text = parsed.get("summary", "") or ""
                    except Exception:
                        summary_text = str(payload)[:1500]
            elif "content" in llm_output:
                # Some endpoints return textual content fields
                summary_text = str(llm_output.get("content") or llm_output.get("summary") or "")
            elif "summary" in llm_output:
                summary_text = str(llm_output.get("summary", ""))
            else:
                # Attempt to extract any nested string field
                for k in ("output", "outputs", "result", "data"):
                    v = llm_output.get(k)
                    if v:
                        summary_text = str(v)[:1500]
                        break
        elif isinstance(llm_output, str):
            summary_text = llm_output[:1500]
    except Exception:
        logger.exception("Error parsing LLM output")

    # Heuristic fallback: if quick_analysis_list empty but we have summary_text, create a few bullets
    if not quick_analysis_list and summary_text:
        quick_analysis_list = [s.strip() for s in summary_text.split(".") if s.strip()][:4]

    # If no evidence_list from LLM, fallback to search results
    if not evidence_list and signals.get("search_results"):
        for sr in signals["search_results"][:5]:
            evidence_list.append({"source": sr.get("source") or sr.get("title"), "snippet": sr.get("snippet"), "reliability": 0.6})

    # Build Evidence objects
    evidence_objs: List[Evidence] = []
    for e in evidence_list:
        try:
            evidence_objs.append(Evidence(source=e.get("source", "unknown"), snippet=e.get("snippet", ""), reliability=float(e.get("reliability", 0.5))))
        except Exception:
            # defensive fallback convert to strings
            evidence_objs.append(Evidence(source=str(e.get("source", "unknown")), snippet=str(e.get("snippet", "")), reliability=0.5))

    # Build checklist objects
    checklist_objs: List[EducationalChecklistItem] = []
    if checklist_list:
        for item in checklist_list:
            if isinstance(item, dict):
                checklist_objs.append(EducationalChecklistItem(point=item.get("point", ""), explanation=item.get("explanation", "")))
            else:
                checklist_objs.append(EducationalChecklistItem(point=str(item), explanation=""))
    else:
        checklist_objs = [
            EducationalChecklistItem(point="Cross-check sources", explanation="Look for independent confirmation."),
            EducationalChecklistItem(point="Check date & context", explanation="Verify event time and location."),
        ]

    intelligence = IntelligenceReport(
        political=intelligence_sections.get("political") if isinstance(intelligence_sections, dict) else None,
        financial=intelligence_sections.get("financial") if isinstance(intelligence_sections, dict) else None,
        psychological=intelligence_sections.get("psychological") if isinstance(intelligence_sections, dict) else None,
        scientific=intelligence_sections.get("scientific") if isinstance(intelligence_sections, dict) else None,
        philosophical=intelligence_sections.get("philosophical") if isinstance(intelligence_sections, dict) else None,
        geopolitical=intelligence_sections.get("geopolitical") if isinstance(intelligence_sections, dict) else None,
        technical=intelligence_sections.get("technical") if isinstance(intelligence_sections, dict) else None,
    )

    # If factchecks exist, boost confidence and set "False"
    fc_hits = signals.get("fact_checks") or []
    if fc_hits:
        verdict_label = "❌ False"
        confidence_pct = max(confidence_pct, 85)

    # Compose quick_analysis string (frontend expects a string field)
    quick_analysis_text = "\n".join([f"- {b}" for b in quick_analysis_list]) if quick_analysis_list else (summary_text[:400] or "See evidence and full report")

    verdict = Verdict(label=verdict_label, confidence=int(confidence_pct), summary=(summary_text[:300] or quick_analysis_text[:200]))

    result = Result(
        input=original_text,
        domain=(signals.get("wikipedia") or {}).get("title", "General"),
        verdict=verdict,
        quick_analysis=quick_analysis_text,
        evidence=evidence_objs,
        checklist=checklist_objs,
        intelligence=intelligence,
        audit={
            "analysis_time": datetime.utcnow().isoformat(),
            "processing_time": f"{time.time() - t0:.2f}s",
            "detected_language": detected_lang,
            "fact_checks_found": len(fc_hits),
        },
    )
    return result


async def analyze_url_pipeline(url: str, language_hint: str = "en") -> Result:
    """
    URL pipeline:
     - fetch page
     - safe-browsing check
     - extract text -> run text pipeline
     - attach page metadata into audit
    """
    t0 = time.time()
    page_text = ""
    page_title = url
    safe_browsing_result = {}
    try:
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.get(url, timeout=HTTP_TIMEOUT) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    import re

                    m = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
                    page_title = m.group(1).strip() if m else url
                    page_text = re.sub("<[^<]+?>", "", html)[:8000]
    except Exception:
        logger.exception("Failed to fetch page")

    # Safe browsing check (if configured)
    try:
        safe_browsing_result = await safe_browsing_check(url)
    except Exception:
        logger.exception("safe_browsing_check failed in url pipeline")

    if page_text:
        result = await analyze_text_pipeline(page_text, language_hint)
        result.domain = "Web"
        # augment audit with page info and safe browsing
        result.audit["page_title"] = page_title
        if safe_browsing_result:
            result.audit["safe_browsing"] = safe_browsing_result
            # If unsafe, degrade verdict/confidence
            if safe_browsing_result.get("matches"):
                # mark as caution and reduce confidence
                result.verdict.label = "⚠️ Caution"
                result.verdict.confidence = min(95, max(30, result.verdict.confidence // 2))
    else:
        # fallback Result for unreachable page
        result = Result(
            input=url,
            domain="Web",
            verdict=Verdict(label="⚠️ Caution", confidence=50, summary="Unable to fetch page content"),
            quick_analysis="Could not fetch or parse page content for analysis",
            evidence=[],
            checklist=[EducationalChecklistItem(point="Fetch failed", explanation="Page could not be retrieved")],
            intelligence=IntelligenceReport(),
            audit={"analysis_time": datetime.utcnow().isoformat(), "processing_time": f"{time.time() - t0:.2f}s", "safe_browsing": safe_browsing_result},
        )
    return result


async def analyze_image_pipeline(image_base64: str, language_hint: str = "en") -> Result:
    """
    Image pipeline:
     - OCR via Vision API -> if text found run text pipeline
     - otherwise run LLM visual reasoning
    """
    t0 = time.time()
    ocr_text = await vision_ocr_image_base64(image_base64)

    if ocr_text:
        result = await analyze_text_pipeline(ocr_text, language_hint)
        result.domain = "Image"
        result.audit["ocr_used"] = True
    else:
        # Visual LLM prompt
        prompt = (
            "You are an expert image analyst. Describe likely origin, manipulation signals, metadata checks to run, "
            "and produce a JSON with keys verdict_label, confidence, quick_analysis (array), checklist (array), intelligence (object), summary."
        )
        llm_output = await vertex_analyze(prompt + f"\n\nImage base64 length: {len(image_base64)}", max_output_tokens=700)
        verdict_label = "⚠️ Caution"
        confidence = 50
        quick_analysis_list = []
        checklist_list = []
        intelligence_sections = {}
        summary_text = ""

        try:
            if isinstance(llm_output, dict) and "predictions" in llm_output and llm_output["predictions"]:
                payload = llm_output["predictions"][0]
                if isinstance(payload, dict):
                    verdict_label = payload.get("verdict_label", verdict_label)
                    confidence = int(payload.get("confidence", confidence))
                    quick_analysis_list = payload.get("quick_analysis", []) or []
                    checklist_list = payload.get("checklist", []) or []
                    intelligence_sections = payload.get("intelligence", {}) or {}
                    summary_text = payload.get("summary", "") or ""
                else:
                    import json
                    try:
                        parsed = json.loads(payload)
                        verdict_label = parsed.get("verdict_label", verdict_label)
                        confidence = int(parsed.get("confidence", confidence))
                        quick_analysis_list = parsed.get("quick_analysis", []) or []
                        checklist_list = parsed.get("checklist", []) or []
                        intelligence_sections = parsed.get("intelligence", {}) or {}
                        summary_text = parsed.get("summary", "") or ""
                    except Exception:
                        summary_text = str(payload)[:800]
            elif isinstance(llm_output, str):
                summary_text = llm_output[:800]
            elif isinstance(llm_output, dict) and "summary" in llm_output:
                summary_text = str(llm_output.get("summary"))
        except Exception:
            logger.exception("parsing vertex output for image")

        if not quick_analysis_list and summary_text:
            quick_analysis_list = [s.strip() for s in summary_text.split(".") if s.strip()][:4]

        evidence_objs = []
        checklist_objs = []
        for item in checklist_list:
            if isinstance(item, dict):
                checklist_objs.append(EducationalChecklistItem(point=item.get("point", ""), explanation=item.get("explanation", "")))
            else:
                checklist_objs.append(EducationalChecklistItem(point=str(item), explanation=""))

        intelligence = IntelligenceReport(
            political=intelligence_sections.get("political") if isinstance(intelligence_sections, dict) else None,
            financial=intelligence_sections.get("financial") if isinstance(intelligence_sections, dict) else None,
            psychological=intelligence_sections.get("psychological") if isinstance(intelligence_sections, dict) else None,
            scientific=intelligence_sections.get("scientific") if isinstance(intelligence_sections, dict) else None,
            philosophical=intelligence_sections.get("philosophical") if isinstance(intelligence_sections, dict) else None,
            geopolitical=intelligence_sections.get("geopolitical") if isinstance(intelligence_sections, dict) else None,
            technical=intelligence_sections.get("technical") if isinstance(intelligence_sections, dict) else None,
        )

        verdict = Verdict(label=verdict_label, confidence=int(confidence), summary=(summary_text or "Visual analysis"))

        result = Result(
            input="[image]",
            domain="Image",
            verdict=verdict,
            quick_analysis="\n".join([f"- {b}" for b in quick_analysis_list]) if quick_analysis_list else summary_text[:400],
            evidence=evidence_objs,
            checklist=checklist_objs or [EducationalChecklistItem(point="Reverse image search", explanation="Try reverse image search to find origins")],
            intelligence=intelligence,
            audit={"analysis_time": datetime.utcnow().isoformat(), "processing_time": f"{time.time() - t0:.2f}s"},
        )
    return result


# ---------------------------
# Unified entrypoint
# ---------------------------
async def run_analysis(content_type: str, content: str, language: str = "en") -> Result:
    """
    content_type: 'text' | 'url' | 'image'
    content: raw text / url / base64 image
    """
    if content_type == "text":
        return await analyze_text_pipeline(content, language)
    elif content_type == "url":
        return await analyze_url_pipeline(content, language)
    elif content_type == "image":
        return await analyze_image_pipeline(content, language)
    else:
        raise ValueError("Unsupported content_type")

async def force_google_indexing(urls_to_index: List[str]) -> bool:
    """Force Google to immediately index URLs using Google's Indexing API."""
    try:
        from google.oauth2 import service_account
        import json
        
        # Use your existing service account
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', './crediscopemain.json')
        
        # Create credentials for Indexing API
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/indexing']
        )
        
        indexing_service = build('indexing', 'v3', credentials=credentials)
        
        # Submit URLs for immediate indexing
        for url in urls_to_index:
            body = {
                'url': url,
                'type': 'URL_UPDATED'
            }
            indexing_service.urlNotifications().publish(body=body).execute()
            logger.info(f"Successfully submitted URL for indexing: {url}")
        
        return True
        
    except Exception as e:
        logger.error(f"Indexing API failed: {str(e)}")
        return False

async def google_custom_search(query: str, num: int = 5) -> List[Dict[str, Any]]:
    """Return top search results using Google Custom Search API - hybrid OAuth2/API key approach."""
    
    # Method 1: Try OAuth2 first
    try:
        from .oauth2_service import oauth2_service
        service = oauth2_service.get_custom_search_service()
        engine_id = os.getenv('CUSTOM_SEARCH_ENGINE_ID')
        
        if engine_id:
            result = service.cse().list(
                q=query,
                cx=engine_id,
                num=num
            ).execute()
            
            items = result.get("items", [])
            if items:  # If we got results, return them
                logger.info(f"OAuth2 Custom Search successful: {len(items)} results")
                return [
                    {
                        "title": it.get("title"),
                        "link": it.get("link"),
                        "snippet": it.get("snippet"),
                        "source": it.get("displayLink"),
                    }
                    for it in items
                ]
    except Exception as e:
        logger.warning(f"OAuth2 Custom Search failed, falling back to API key: {str(e)}")
    
    # Method 2: Fall back to API key method
    try:
        if not (CUSTOM_SEARCH_API_KEY and CUSTOM_SEARCH_CX):
            logger.debug("Custom Search not configured")
            return []
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {"key": CUSTOM_SEARCH_API_KEY, "cx": CUSTOM_SEARCH_CX, "q": query, "num": num}
        
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.get(url, params=params) as resp:
                j = await resp.json()
                items = j.get("items", [])
                logger.info(f"API key Custom Search successful: {len(items)} results")
                return [
                    {
                        "title": it.get("title"),
                        "link": it.get("link"),
                        "snippet": it.get("snippet"),
                        "source": it.get("displayLink"),
                    }
                    for it in items
                ]
    except Exception as e:
        logger.exception("Both OAuth2 and API key Custom Search failed")
        return []
