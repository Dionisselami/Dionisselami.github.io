"""
Example configuration file for Twitter bot.
Copy this file to config.py and modify the settings as needed.
"""

import os

# ========== AUTHENTICATION SETTINGS ==========
# Twitter login credentials
TWITTER_USERNAME = "your_twitter_username"
TWITTER_PASSWORD = "your_twitter_password"

# Cookie management
COOKIE_FILE = "twitter_cookies.json"
COOKIE_REFRESH_INTERVAL = 3600  # 1 hour

# ========== RATE LIMITING SETTINGS ==========
# Conservative limits (adjust based on your needs)
MAX_ACTIONS_PER_HOUR = 8    # Very conservative
MAX_ACTIONS_PER_DAY = 50    # Very conservative
MAX_LIKES_PER_HOUR = 6
MAX_REPLIES_PER_HOUR = 2
MAX_RETWEETS_PER_HOUR = 1

# ========== BEHAVIOR SETTINGS ==========
# Action probabilities (0.0 to 1.0)
ACTION_PROBABILITIES = {
    "like": 0.8,      # 80% chance to like
    "reply": 0.2,     # 20% chance to reply
    "retweet": 0.1,   # 10% chance to retweet
}

# Delay ranges (in seconds)
DELAY_BETWEEN_ACTIONS = (120, 300)     # 2-5 minutes
DELAY_BETWEEN_SEARCHES = (600, 1200)   # 10-20 minutes
DELAY_AFTER_ERROR = (1800, 3600)      # 30-60 minutes

# ========== SEARCH SETTINGS ==========
# Search queries with weights
SEARCH_QUERIES = [
    # Tech and programming
    ("python programming", 3),
    ("web development", 2),
    ("javascript", 2),
    ("artificial intelligence", 3),
    ("machine learning", 2),
    ("data science", 2),
    ("coding", 2),
    ("software development", 2),
    ("tech news", 1),
    ("startup", 1),
    
    # Add your own topics here
    ("your topic", 1),
    ("another topic", 2),
]

# Tweet engagement criteria
MIN_LIKES_THRESHOLD = 5
MAX_LIKES_THRESHOLD = 5000  # Avoid viral tweets
MIN_REPLIES_THRESHOLD = 0
MAX_REPLIES_THRESHOLD = 50
TWEET_AGE_LIMIT_HOURS = 12  # Only engage with recent tweets

# ========== REPLY SETTINGS ==========
# Reply templates
REPLY_TEMPLATES = [
    "Great insights! 👍",
    "Thanks for sharing! 🙏",
    "Really useful information! 💯",
    "Interesting perspective! 🤔",
    "Well explained! 👏",
    "This is helpful! ✅",
    "Love this! ❤️",
    "Great work! 🚀",
    "Exactly what I needed! 🎯",
    "Thanks for the tip! 💡",
]

# Contextual replies (optional)
CONTEXTUAL_REPLIES = {
    "python": [
        "Python is amazing! 🐍",
        "Love Python! 💻",
        "Python makes everything easier! 🚀",
    ],
    "javascript": [
        "JavaScript is so powerful! ⚡",
        "Great JS content! 🌐",
        "JavaScript rocks! 💪",
    ],
    "ai": [
        "AI is fascinating! 🤖",
        "The future is AI! 🚀",
        "Great AI insights! 🧠",
    ],
}

# ========== BROWSER SETTINGS ==========
BROWSER_TYPE = "chrome"  # or "firefox"
HEADLESS_MODE = True     # Set to False to see browser (for testing)
BROWSER_TIMEOUT = 30

# ========== SAFETY SETTINGS ==========
# Content filtering
BLOCKED_KEYWORDS = [
    "spam", "scam", "crypto", "bitcoin", "investment",
    "money", "rich", "trading", "forex", "winner",
    "congratulations", "prize", "lottery", "casino"
]

# Account safety
AVOID_OWN_CONTENT = True
AVOID_SENSITIVE_CONTENT = True
CAPTCHA_DETECTION = True
MAX_CONSECUTIVE_ERRORS = 3
ERROR_COOLDOWN_MINUTES = 60

# ========== RUNTIME SETTINGS ==========
RUN_CONTINUOUSLY = True
RUN_DURATION_HOURS = 12      # If not continuous
PAUSE_BETWEEN_CYCLES = 3600  # 1 hour between cycles
ENABLE_WEEKEND_MODE = True
WEEKEND_ACTIVITY_REDUCTION = 0.3  # 30% activity on weekends

# ========== LOGGING SETTINGS ==========
LOG_FILE = "twitter_bot.log"
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ========== ADVANCED SETTINGS ==========
# Enable experimental features
ENABLE_SMART_REPLIES = True
ENABLE_ENGAGEMENT_SCORING = True
ENABLE_TREND_FOLLOWING = True

# Monitoring
ENABLE_MONITORING = True
ALERT_ON_ERRORS = True
HEALTH_CHECK_INTERVAL = 1800  # 30 minutes

# ========== USAGE EXAMPLES ==========
"""
BEGINNER SETUP:
- Set very conservative limits (low actions per hour)
- Use simple reply templates
- Enable all safety features
- Start with headless mode disabled to watch the bot

INTERMEDIATE SETUP:
- Increase action limits gradually
- Add more search queries
- Use contextual replies
- Enable trend following

ADVANCED SETUP:
- Fine-tune engagement scoring
- Add custom reply logic
- Implement advanced filtering
- Use monitoring and alerts

SAFETY TIPS:
1. Always start with very low limits
2. Monitor your account for any issues
3. Use realistic human-like delays
4. Avoid engaging with controversial content
5. Respect Twitter's terms of service
6. Consider using a test account first
"""

# ========== ENVIRONMENT VARIABLES ==========
"""
You can also set these values using environment variables:

export TWITTER_USERNAME="your_username"
export TWITTER_PASSWORD="your_password"
export TWITTER_BOT_LOG_LEVEL="INFO"
export TWITTER_BOT_HEADLESS="true"
export TWITTER_BOT_MAX_ACTIONS_PER_HOUR="8"

The bot will use environment variables if they exist,
otherwise it will use the values defined in this file.
"""