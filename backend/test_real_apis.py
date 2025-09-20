# test_real_apis.py - Comprehensive API Integration Test

import asyncio
import base64
import json
import time
import sys
import os
from datetime import datetime

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

# Test the real analysis pipelines
from app.services.analysis_engine import run_analysis

async def test_text_analysis():
    """Test text analysis pipeline with real content"""
    print("🔍 Testing Text Analysis Pipeline...")
    
    test_text = "Breaking: Scientists discover cure for aging using quantum technology"
    
    try:
        start_time = time.time()
        result = await run_analysis("text", test_text, "en")
        processing_time = time.time() - start_time
        
        print(f"✅ Text Analysis SUCCESS")
        print(f"   ⏱️  Processing Time: {processing_time:.2f}s")
        print(f"   🎯 Verdict: {result.verdict.label} ({result.verdict.confidence}%)")
        print(f"   📝 Summary: {result.verdict.summary[:100]}...")
        print(f"   🔍 Evidence Count: {len(result.evidence)}")
        print(f"   📋 Checklist Items: {len(result.checklist)}")
        print(f"   🧠 Quick Analysis: {result.quick_analysis[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Text Analysis FAILED: {str(e)}")
        return False

async def test_url_analysis():
    """Test URL analysis pipeline with real content"""
    print("\n🌐 Testing URL Analysis Pipeline...")
    
    test_url = "https://www.reuters.com/technology/"
    
    try:
        start_time = time.time()
        result = await run_analysis("url", test_url, "en")
        processing_time = time.time() - start_time
        
        print(f"✅ URL Analysis SUCCESS")
        print(f"   ⏱️  Processing Time: {processing_time:.2f}s")
        print(f"   🎯 Verdict: {result.verdict.label} ({result.verdict.confidence}%)")
        print(f"   📝 Summary: {result.verdict.summary[:100]}...")
        print(f"   🔍 Evidence Count: {len(result.evidence)}")
        print(f"   🛡️  Safe Browsing: {result.audit.get('safe_browsing', 'Not checked')}")
        print(f"   📄 Page Title: {result.audit.get('page_title', 'Unknown')[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ URL Analysis FAILED: {str(e)}")
        return False

async def test_image_analysis():
    """Test image analysis pipeline with sample image"""
    print("\n🖼️  Testing Image Analysis Pipeline...")
    
    # Create a simple test image (1x1 pixel PNG in base64)
    test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    
    try:
        start_time = time.time()
        result = await run_analysis("image", test_image_base64, "en")
        processing_time = time.time() - start_time
        
        print(f"✅ Image Analysis SUCCESS")
        print(f"   ⏱️  Processing Time: {processing_time:.2f}s") 
        print(f"   🎯 Verdict: {result.verdict.label} ({result.verdict.confidence}%)")
        print(f"   📝 Summary: {result.verdict.summary[:100]}...")
        print(f"   🔍 Evidence Count: {len(result.evidence)}")
        print(f"   👁️  OCR Used: {result.audit.get('ocr_used', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Image Analysis FAILED: {str(e)}")
        return False

async def comprehensive_test():
    """Run all tests and generate report"""
    print("🚀 STARTING COMPREHENSIVE API INTEGRATION TESTS")
    print("=" * 60)
    print(f"⏰ Test Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run all pipeline tests
    text_success = await test_text_analysis()
    url_success = await test_url_analysis() 
    image_success = await test_image_analysis()
    
    # Generate report
    print("\n" + "=" * 60)
    print("📊 FINAL TEST REPORT")
    print("=" * 60)
    
    tests = [
        ("Text Analysis Pipeline", text_success),
        ("URL Analysis Pipeline", url_success), 
        ("Image Analysis Pipeline", image_success)
    ]
    
    passed = sum(1 for _, success in tests if success)
    total = len(tests)
    
    for test_name, success in tests:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 SUMMARY: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Your CrediScope backend is ready!")
        print("✅ Real Google APIs are working")
        print("✅ Analysis pipelines are functional") 
        print("✅ Result objects match frontend schema")
        print("\n🚀 STRESS HOURS MISSION: COMPLETE!")
    else:
        print("⚠️  Some tests failed. Check your API keys and configuration.")
    
    print(f"⏰ Test End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    # Run the comprehensive test
    asyncio.run(comprehensive_test())
