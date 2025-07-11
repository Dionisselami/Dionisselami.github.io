#!/usr/bin/env python3
"""
Test script for Twitter Bot components
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from twitter_bot.config import CONFIG
        print("✓ Config module imported successfully")
    except Exception as e:
        print(f"✗ Error importing config: {e}")
        return False
    
    try:
        from twitter_bot.utils import setup_logging, human_like_delay
        print("✓ Utils module imported successfully")
    except Exception as e:
        print(f"✗ Error importing utils: {e}")
        return False
    
    try:
        from twitter_bot.rate_limiter import RateLimiter
        print("✓ RateLimiter imported successfully")
    except Exception as e:
        print(f"✗ Error importing RateLimiter: {e}")
        return False
    
    # Test other modules (these require selenium)
    try:
        from twitter_bot.cookie_manager import CookieManager
        print("✓ CookieManager imported successfully")
    except ImportError as e:
        print(f"⚠ CookieManager requires selenium: {e}")
    except Exception as e:
        print(f"✗ Error importing CookieManager: {e}")
        return False
    
    try:
        from twitter_bot.tweet_finder import TweetFinder
        print("✓ TweetFinder imported successfully")
    except ImportError as e:
        print(f"⚠ TweetFinder requires selenium: {e}")
    except Exception as e:
        print(f"✗ Error importing TweetFinder: {e}")
        return False
    
    try:
        from twitter_bot.engagement_engine import EngagementEngine
        print("✓ EngagementEngine imported successfully")
    except ImportError as e:
        print(f"⚠ EngagementEngine requires selenium: {e}")
    except Exception as e:
        print(f"✗ Error importing EngagementEngine: {e}")
        return False
    
    try:
        from twitter_bot.twitter_bot import TwitterBot
        print("✓ TwitterBot imported successfully")
    except ImportError as e:
        print(f"⚠ TwitterBot requires selenium: {e}")
    except Exception as e:
        print(f"✗ Error importing TwitterBot: {e}")
        return False
    
    return True

def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        from twitter_bot.config import CONFIG, get_weighted_search_query
        
        # Test configuration structure
        required_sections = ['auth', 'rate_limits', 'behavior', 'search', 'replies']
        for section in required_sections:
            if section not in CONFIG:
                print(f"✗ Missing configuration section: {section}")
                return False
        
        print("✓ Configuration structure is valid")
        
        # Test search query function
        query = get_weighted_search_query()
        if query:
            print(f"✓ Search query function works: '{query}'")
        else:
            print("✗ Search query function failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing configuration: {e}")
        return False

def test_utils():
    """Test utility functions."""
    print("\nTesting utilities...")
    
    try:
        from twitter_bot.utils import (
            get_current_timestamp, format_duration, 
            parse_engagement_numbers, clean_tweet_text
        )
        
        # Test timestamp function
        timestamp = get_current_timestamp()
        if timestamp:
            print(f"✓ Timestamp function works: {timestamp}")
        else:
            print("✗ Timestamp function failed")
            return False
        
        # Test duration formatting
        duration = format_duration(3661)  # 1 hour, 1 minute, 1 second
        if "1h" in duration:
            print(f"✓ Duration formatting works: {duration}")
        else:
            print("✗ Duration formatting failed")
            return False
        
        # Test engagement number parsing
        likes = parse_engagement_numbers("1.5K")
        if likes == 1500:
            print("✓ Engagement number parsing works")
        else:
            print(f"✗ Engagement number parsing failed: {likes}")
            return False
        
        # Test text cleaning
        clean_text = clean_tweet_text("  Hello\n\nWorld  \t")
        if clean_text == "Hello World":
            print("✓ Text cleaning works")
        else:
            print(f"✗ Text cleaning failed: '{clean_text}'")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing utilities: {e}")
        return False

def test_rate_limiter():
    """Test rate limiter functionality."""
    print("\nTesting rate limiter...")
    
    try:
        from twitter_bot.rate_limiter import RateLimiter
        from twitter_bot.config import CONFIG
        
        # Create rate limiter
        limiter = RateLimiter(CONFIG)
        
        # Test basic functionality
        can_like = limiter.can_perform_action('like')
        print(f"✓ Can perform like action: {can_like}")
        
        # Test action recording
        limiter.record_action('like', True)
        print("✓ Action recording works")
        
        # Test statistics
        stats = limiter.get_statistics()
        if isinstance(stats, dict):
            print("✓ Statistics generation works")
        else:
            print("✗ Statistics generation failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing rate limiter: {e}")
        return False

def main():
    """Main test function."""
    print("Twitter Bot Test Suite")
    print("=" * 50)
    
    tests = [
        ("Import Tests", test_imports),
        ("Configuration Tests", test_config),
        ("Utility Tests", test_utils),
        ("Rate Limiter Tests", test_rate_limiter),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{test_name}")
        print("-" * len(test_name))
        
        try:
            if test_func():
                print(f"✓ {test_name} PASSED")
                passed += 1
            else:
                print(f"✗ {test_name} FAILED")
                failed += 1
        except Exception as e:
            print(f"✗ {test_name} ERROR: {e}")
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())