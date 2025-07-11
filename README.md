# Dionisselami.github.io

This repository contains a comprehensive Twitter bot system with cookie-based authentication and intelligent engagement features.

## Twitter Bot System

### Overview

The Twitter bot system is a sophisticated automation tool that engages with Twitter content using cookie-based authentication instead of API keys. It simulates natural human behavior patterns while maintaining safety and respecting rate limits.

### Key Features

- **🔐 Cookie-Based Authentication**: No API keys required - uses browser cookies for authentication
- **🎯 Smart Tweet Discovery**: Finds tweets using weighted random selection and engagement metrics
- **⚡ Natural Behavior Simulation**: Variable delays, human-like scrolling, and realistic engagement patterns
- **🛡️ Advanced Safety Features**: Rate limiting, error handling, CAPTCHA detection, and account protection
- **📊 Comprehensive Logging**: Detailed activity logging and performance metrics
- **⚙️ Easy Configuration**: All settings in a single configuration file

### Quick Start

1. **Installation**
   ```bash
   cd twitter_bot
   pip install -r requirements.txt
   ```

2. **Configuration**
   ```bash
   cp example_config.py config.py
   # Edit config.py with your settings
   ```

3. **Run the Bot**
   ```bash
   python twitter_bot.py
   ```

### Project Structure

```
twitter_bot/
├── __init__.py              # Package initialization
├── twitter_bot.py          # Main bot orchestration
├── config.py               # Configuration settings
├── cookie_manager.py       # Cookie-based authentication
├── rate_limiter.py         # Smart rate limiting
├── tweet_finder.py         # Tweet discovery engine
├── engagement_engine.py    # Engagement actions (like, reply, retweet)
├── utils.py                # Utility functions
├── requirements.txt        # Python dependencies
├── example_config.py       # Example configuration
└── README.md               # This file
```

### Core Components

#### 1. Cookie Manager
- Handles Twitter authentication using browser cookies
- Manages session persistence and renewal
- Supports automatic login with username/password
- Detects and handles CAPTCHA challenges

#### 2. Rate Limiter
- Implements conservative rate limits to avoid account suspension
- Simulates human-like activity patterns
- Tracks actions per hour/day with automatic resets
- Includes weekend mode with reduced activity

#### 3. Tweet Finder
- Searches for tweets using configurable queries
- Applies weighted random selection based on engagement metrics
- Filters tweets by age, engagement thresholds, and content
- Supports trending topics and hashtag searches

#### 4. Engagement Engine
- Performs likes, replies, and retweets with natural timing
- Uses contextual reply templates based on tweet content
- Simulates human typing patterns and click behavior
- Handles error recovery and CAPTCHA detection

### Configuration

The bot is highly configurable through the `config.py` file:

```python
# Rate limiting
MAX_ACTIONS_PER_HOUR = 12
MAX_ACTIONS_PER_DAY = 100

# Action probabilities
ACTION_PROBABILITIES = {
    "like": 0.7,      # 70% chance to like
    "reply": 0.3,     # 30% chance to reply
    "retweet": 0.2,   # 20% chance to retweet
}

# Search queries with weights
SEARCH_QUERIES = [
    ("python programming", 3),
    ("web development", 2),
    ("artificial intelligence", 3),
    # Add your topics here
]

# Reply templates
REPLY_TEMPLATES = [
    "Great insights! 👍",
    "Thanks for sharing! 🙏",
    "Really useful information! 💯",
    # Add your templates here
]
```

### Safety Features

- **Conservative Rate Limits**: Default limits are very conservative to protect accounts
- **Error Handling**: Comprehensive error recovery and logging
- **CAPTCHA Detection**: Automatic detection and handling of security challenges
- **Content Filtering**: Blocks engagement with sensitive or inappropriate content
- **Account Protection**: Avoids engaging with own content and suspicious accounts

### Usage Examples

#### Basic Usage
```python
from twitter_bot import TwitterBot

# Create and run bot with default configuration
bot = TwitterBot()
bot.run()
```

#### Custom Configuration
```python
from twitter_bot import TwitterBot

# Custom configuration
config = {
    'rate_limits': {
        'max_actions_per_hour': 5,  # Very conservative
        'max_actions_per_day': 30,
    },
    'behavior': {
        'action_probabilities': {
            'like': 0.8,
            'reply': 0.1,
            'retweet': 0.1,
        }
    }
}

bot = TwitterBot(config)
bot.run()
```

#### Monitoring and Control
```python
from twitter_bot import TwitterBot
import threading
import time

bot = TwitterBot()

# Run bot in a separate thread
bot_thread = threading.Thread(target=bot.run)
bot_thread.start()

# Monitor bot status
while bot.running:
    status = bot.get_status()
    print(f"Cycles completed: {status['statistics']['cycles_completed']}")
    time.sleep(300)  # Check every 5 minutes

# Stop the bot
bot.stop()
bot_thread.join()
```

### Advanced Features

#### Engagement Scoring
The bot uses sophisticated engagement scoring to select the best tweets:

```python
def get_engagement_score(tweet_data):
    likes = tweet_data.get('likes', 0)
    replies = tweet_data.get('replies', 0)
    retweets = tweet_data.get('retweets', 0)
    
    # Weighted scoring
    score = (likes * 0.3 + replies * 0.4 + retweets * 0.2)
    return min(1.0, score / 100)  # Normalize to 0-1
```

#### Contextual Replies
The bot can generate contextual replies based on tweet content:

```python
CONTEXTUAL_REPLIES = {
    "python": [
        "Python is amazing! 🐍",
        "Love Python! 💻",
    ],
    "javascript": [
        "JavaScript is so powerful! ⚡",
        "Great JS content! 🌐",
    ],
}
```

#### Human-Like Behavior
The bot simulates natural human behavior patterns:

- Variable delays between actions (1-10 minutes)
- Random scrolling and mouse movements
- Realistic typing patterns with pauses
- Activity patterns that vary by time of day
- Reduced activity during weekends

### Monitoring and Logging

The bot provides comprehensive monitoring:

```
2024-01-01 10:00:00 - TwitterBot - INFO - Starting bot cycle...
2024-01-01 10:00:05 - TweetFinder - INFO - Found 15 tweets for query: python programming
2024-01-01 10:00:10 - EngagementEngine - INFO - Successfully liked tweet: 1234567890
2024-01-01 10:00:15 - RateLimiter - INFO - Rate limits - Hourly: 1/12, Daily: 1/100
```

### Troubleshooting

#### Common Issues

1. **Authentication Failures**
   - Check username/password in config
   - Clear cookie file and retry
   - Verify account is not locked

2. **Rate Limit Errors**
   - Reduce action limits in config
   - Increase delays between actions
   - Check for account restrictions

3. **Element Not Found Errors**
   - Twitter may have changed their interface
   - Update selectors in code
   - Check if account is suspended

#### Debug Mode
```python
# Enable debug logging
LOG_LEVEL = "DEBUG"

# Disable headless mode to see browser
HEADLESS_MODE = False
```

### Security Considerations

- **Account Safety**: Always use test accounts initially
- **Rate Limiting**: Start with very conservative limits
- **Content Filtering**: Avoid controversial or sensitive topics
- **Terms of Service**: Respect Twitter's automation policies
- **Cookie Security**: Keep cookie files secure and private

### Contributing

This bot system is designed to be educational and demonstrate automation concepts. Please use responsibly and in accordance with Twitter's terms of service.

### License

This project is for educational purposes. Please review Twitter's terms of service before using any automation tools.

### Disclaimer

This software is provided for educational purposes only. Users are responsible for ensuring compliance with Twitter's terms of service and applicable laws. The authors are not responsible for any account suspensions or other consequences resulting from the use of this software.

---

## Website

This repository also hosts a GitHub Pages website at [dionisselami.me](https://dionisselami.me).