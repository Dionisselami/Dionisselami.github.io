"""
Twitter Bot Package

A comprehensive Twitter bot system with cookie-based authentication,
intelligent tweet discovery, and natural engagement patterns.

Features:
- Cookie-based authentication (no API keys required)
- Weighted random tweet selection
- Smart rate limiting with human-like behavior
- Natural engagement simulation
- Comprehensive error handling and logging
- Easy configuration management

Usage:
    from twitter_bot import TwitterBot
    
    bot = TwitterBot()
    bot.run()

Or run directly:
    python -m twitter_bot.twitter_bot
"""

__version__ = "1.0.0"
__author__ = "Twitter Bot System"
__email__ = "contact@example.com"
__description__ = "Comprehensive Twitter bot with cookie-based authentication"

# Import main classes for easy access
from .twitter_bot import TwitterBot
from .config import CONFIG
from .cookie_manager import CookieManager
from .rate_limiter import RateLimiter
from .tweet_finder import TweetFinder
from .engagement_engine import EngagementEngine

# Import utility functions
from .utils import (
    setup_logging,
    load_json_file,
    save_json_file,
    human_like_delay,
    get_current_timestamp,
    format_duration,
)

__all__ = [
    'TwitterBot',
    'CONFIG',
    'CookieManager',
    'RateLimiter',
    'TweetFinder',
    'EngagementEngine',
    'setup_logging',
    'load_json_file',
    'save_json_file',
    'human_like_delay',
    'get_current_timestamp',
    'format_duration',
]

# Package metadata
__package_info__ = {
    'name': 'twitter_bot',
    'version': __version__,
    'author': __author__,
    'email': __email__,
    'description': __description__,
    'features': [
        'Cookie-based authentication',
        'Intelligent tweet discovery',
        'Natural behavior simulation',
        'Smart rate limiting',
        'Comprehensive logging',
        'Easy configuration',
    ],
    'requirements': [
        'selenium>=4.15.0',
        'requests>=2.31.0',
        'beautifulsoup4>=4.12.2',
        'numpy>=1.24.3',
        'psutil>=5.9.5',
    ],
}