#!/usr/bin/env python3
"""
Test runner for the voice agent test suite.
"""

import asyncio
import sys
import subprocess
from pathlib import Path
from loguru import logger

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


async def run_comprehensive_tests():
    """Run the comprehensive test suite."""
    logger.info("🧪 Running comprehensive voice agent tests...")
    
    try:
        # Run the comprehensive test suite
        result = subprocess.run([
            sys.executable, 
            str(Path(__file__).parent / "test_voice_agent.py")
        ], capture_output=True, text=True)
        
        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        logger.error(f"Error running comprehensive tests: {e}")
        return False


async def run_interactive_quick_test():
    """Run the quick interactive test."""
    logger.info("⚡ Running quick interactive test...")
    
    try:
        # Run the quick test mode
        result = subprocess.run([
            sys.executable, 
            str(Path(__file__).parent / "test_interactive.py"),
            "--mode", "quick"
        ], capture_output=True, text=True)
        
        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        logger.error(f"Error running interactive test: {e}")
        return False


async def run_all_tests():
    """Run all tests in sequence."""
    logger.info("🧪 VOICE AGENT TEST SUITE")
    logger.info("=" * 60)
    
    tests = [
        ("Comprehensive Test Suite", run_comprehensive_tests),
        ("Interactive Quick Test", run_interactive_quick_test),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n🔬 Running {test_name}...")
        try:
            result = await test_func()
            results[test_name] = result
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test_name}: {status}")
        except Exception as e:
            logger.error(f"{test_name}: ❌ ERROR - {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📋 TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"  {test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests PASSED!")
        logger.info("\n🚀 Voice Agent is ready for production!")
        return True
    else:
        logger.info("❌ Some tests FAILED!")
        logger.info("\n💡 Check individual test outputs above for details")
        return False


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> - <level>{message}</level>"
    )
    
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)