"""
Utility functions and helpers for the Twitter bot.
"""

import json
import random
import time
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

def setup_logging(log_file: str = "twitter_bot.log", 
                  log_level: str = "INFO",
                  log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                  max_size: int = 10 * 1024 * 1024,
                  backup_count: int = 5) -> None:
    """
    Set up logging configuration with rotation.
    
    Args:
        log_file: Path to log file
        log_level: Logging level
        log_format: Log message format
        max_size: Maximum log file size before rotation
        backup_count: Number of backup files to keep
    """
    from logging.handlers import RotatingFileHandler
    
    # Create logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create rotating file handler
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=max_size, 
        backupCount=backup_count
    )
    file_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(file_handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)
    
    logger.info(f"Logging initialized. Log file: {log_file}, Level: {log_level}")

def load_json_file(file_path: str, default: Any = None) -> Any:
    """
    Load JSON data from file with error handling.
    
    Args:
        file_path: Path to JSON file
        default: Default value if file doesn't exist or is invalid
        
    Returns:
        Loaded JSON data or default value
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.debug(f"Successfully loaded JSON from {file_path}")
        return data
    except FileNotFoundError:
        logger.debug(f"JSON file not found: {file_path}, returning default")
        return default
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
        return default
    except Exception as e:
        logger.error(f"Error loading JSON from {file_path}: {e}")
        return default

def save_json_file(file_path: str, data: Any) -> bool:
    """
    Save data to JSON file with error handling.
    
    Args:
        file_path: Path to JSON file
        data: Data to save
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.debug(f"Successfully saved JSON to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving JSON to {file_path}: {e}")
        return False

def random_delay(min_seconds: float, max_seconds: float) -> None:
    """
    Sleep for a random duration between min and max seconds.
    
    Args:
        min_seconds: Minimum sleep time
        max_seconds: Maximum sleep time
    """
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Random delay: {delay:.2f} seconds")
    time.sleep(delay)

def human_like_delay(base_delay: float = 1.0, variance: float = 0.5) -> None:
    """
    Create a human-like delay with natural variation.
    
    Args:
        base_delay: Base delay time in seconds
        variance: Variance factor (0.0 to 1.0)
    """
    # Add random variance
    delay = base_delay * (1 + random.uniform(-variance, variance))
    # Ensure positive delay
    delay = max(0.1, delay)
    
    logger.debug(f"Human-like delay: {delay:.2f} seconds")
    time.sleep(delay)

def get_random_user_agent(user_agents: List[str]) -> str:
    """
    Get a random user agent from the list.
    
    Args:
        user_agents: List of user agent strings
        
    Returns:
        Random user agent string
    """
    return random.choice(user_agents)

def extract_tweet_id(tweet_url: str) -> Optional[str]:
    """
    Extract tweet ID from Twitter URL.
    
    Args:
        tweet_url: Twitter URL
        
    Returns:
        Tweet ID if found, None otherwise
    """
    # Pattern to match Twitter URLs and extract ID
    patterns = [
        r'twitter\.com/\w+/status/(\d+)',
        r'x\.com/\w+/status/(\d+)',
        r'/status/(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, tweet_url)
        if match:
            return match.group(1)
    
    return None

def clean_tweet_text(text: str) -> str:
    """
    Clean and normalize tweet text.
    
    Args:
        text: Raw tweet text
        
    Returns:
        Cleaned tweet text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove or replace problematic characters
    text = text.replace('\n', ' ')
    text = text.replace('\r', ' ')
    text = text.replace('\t', ' ')
    
    return text

def parse_engagement_numbers(text: str) -> int:
    """
    Parse engagement numbers from text (e.g., "1.2K", "5M").
    
    Args:
        text: Text containing numbers
        
    Returns:
        Parsed number
    """
    if not text or not isinstance(text, str):
        return 0
    
    # Remove commas and spaces
    text = text.replace(',', '').replace(' ', '').strip()
    
    # Handle K, M, B suffixes
    multipliers = {
        'K': 1000,
        'M': 1000000,
        'B': 1000000000,
    }
    
    for suffix, multiplier in multipliers.items():
        if text.upper().endswith(suffix):
            try:
                number = float(text[:-1])
                return int(number * multiplier)
            except ValueError:
                pass
    
    # Try to parse as regular number
    try:
        return int(float(text))
    except ValueError:
        return 0

def is_weekend() -> bool:
    """
    Check if current day is weekend.
    
    Returns:
        True if weekend, False otherwise
    """
    return datetime.now().weekday() >= 5  # Saturday=5, Sunday=6

def get_time_until_next_hour() -> int:
    """
    Get seconds until next hour.
    
    Returns:
        Seconds until next hour
    """
    now = datetime.now()
    next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return int((next_hour - now).total_seconds())

def get_time_until_next_day() -> int:
    """
    Get seconds until next day.
    
    Returns:
        Seconds until next day
    """
    now = datetime.now()
    next_day = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return int((next_day - now).total_seconds())

def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h"

def validate_url(url: str) -> bool:
    """
    Validate if URL is properly formatted.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def safe_get_attribute(element, attribute: str, default: Any = None) -> Any:
    """
    Safely get attribute from web element.
    
    Args:
        element: Web element
        attribute: Attribute name
        default: Default value if attribute not found
        
    Returns:
        Attribute value or default
    """
    try:
        return element.get_attribute(attribute)
    except Exception:
        return default

def safe_get_text(element, default: str = "") -> str:
    """
    Safely get text from web element.
    
    Args:
        element: Web element
        default: Default value if text not found
        
    Returns:
        Element text or default
    """
    try:
        return element.text or default
    except Exception:
        return default

def contains_blocked_keywords(text: str, blocked_keywords: List[str]) -> bool:
    """
    Check if text contains any blocked keywords.
    
    Args:
        text: Text to check
        blocked_keywords: List of blocked keywords
        
    Returns:
        True if blocked keywords found, False otherwise
    """
    if not text or not blocked_keywords:
        return False
    
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in blocked_keywords)

def calculate_weighted_choice(items: List[Tuple[Any, float]]) -> Any:
    """
    Make a weighted random choice from a list of items.
    
    Args:
        items: List of (item, weight) tuples
        
    Returns:
        Randomly selected item based on weights
    """
    if not items:
        return None
    
    items_list, weights = zip(*items)
    return random.choices(items_list, weights=weights)[0]

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename.strip()

def get_tweet_age_hours(tweet_time: str) -> Optional[int]:
    """
    Calculate tweet age in hours from timestamp.
    
    Args:
        tweet_time: Tweet timestamp string
        
    Returns:
        Age in hours or None if parsing fails
    """
    try:
        # Common Twitter timestamp formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%a %b %d %H:%M:%S %z %Y",
        ]
        
        for fmt in formats:
            try:
                tweet_dt = datetime.strptime(tweet_time, fmt)
                age = datetime.now() - tweet_dt
                return int(age.total_seconds() / 3600)
            except ValueError:
                continue
        
        # If no format matches, return None
        return None
    except Exception:
        return None

def create_backup_file(file_path: str) -> bool:
    """
    Create a backup of a file.
    
    Args:
        file_path: Path to file to backup
        
    Returns:
        True if backup created successfully, False otherwise
    """
    try:
        import shutil
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup_{timestamp}"
        shutil.copy2(file_path, backup_path)
        logger.info(f"Backup created: {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create backup of {file_path}: {e}")
        return False

def retry_with_backoff(func, max_retries: int = 3, 
                      base_delay: float = 1.0, 
                      backoff_multiplier: float = 2.0,
                      exceptions: Tuple = (Exception,)) -> Any:
    """
    Retry function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        base_delay: Base delay between retries
        backoff_multiplier: Multiplier for exponential backoff
        exceptions: Tuple of exceptions to catch
        
    Returns:
        Function result or raises last exception
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            if attempt < max_retries:
                delay = base_delay * (backoff_multiplier ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")
                time.sleep(delay)
            else:
                logger.error(f"All {max_retries + 1} attempts failed")
    
    raise last_exception

def get_current_timestamp() -> str:
    """
    Get current timestamp as string.
    
    Returns:
        Current timestamp string
    """
    return datetime.now().isoformat()

def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    Parse timestamp string to datetime object.
    
    Args:
        timestamp_str: Timestamp string
        
    Returns:
        Datetime object or None if parsing fails
    """
    try:
        return datetime.fromisoformat(timestamp_str)
    except Exception:
        return None

class RateLimitTracker:
    """Simple rate limit tracker for actions."""
    
    def __init__(self):
        self.actions = []
    
    def add_action(self, action_type: str, timestamp: Optional[datetime] = None):
        """Add an action to the tracker."""
        if timestamp is None:
            timestamp = datetime.now()
        self.actions.append({
            'type': action_type,
            'timestamp': timestamp
        })
    
    def get_actions_in_period(self, hours: int, action_type: Optional[str] = None) -> int:
        """Get number of actions in the last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        filtered_actions = [
            action for action in self.actions 
            if action['timestamp'] > cutoff
        ]
        
        if action_type:
            filtered_actions = [
                action for action in filtered_actions 
                if action['type'] == action_type
            ]
        
        return len(filtered_actions)
    
    def cleanup_old_actions(self, days: int = 7):
        """Remove actions older than N days."""
        cutoff = datetime.now() - timedelta(days=days)
        self.actions = [
            action for action in self.actions 
            if action['timestamp'] > cutoff
        ]

# Global rate limit tracker instance
rate_tracker = RateLimitTracker()

def log_performance_metric(metric_name: str, value: float, unit: str = ""):
    """
    Log a performance metric.
    
    Args:
        metric_name: Name of the metric
        value: Metric value
        unit: Unit of measurement
    """
    logger.info(f"METRIC: {metric_name} = {value} {unit}".strip())

def get_system_info() -> Dict[str, Any]:
    """
    Get system information for debugging.
    
    Returns:
        Dictionary with system information
    """
    import platform
    import psutil
    
    try:
        info = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
            'disk_usage': psutil.disk_usage('/').percent,
            'timestamp': get_current_timestamp(),
        }
        return info
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        return {'error': str(e)}

# Export commonly used functions
__all__ = [
    'setup_logging',
    'load_json_file',
    'save_json_file',
    'random_delay',
    'human_like_delay',
    'get_random_user_agent',
    'extract_tweet_id',
    'clean_tweet_text',
    'parse_engagement_numbers',
    'is_weekend',
    'get_time_until_next_hour',
    'get_time_until_next_day',
    'format_duration',
    'validate_url',
    'safe_get_attribute',
    'safe_get_text',
    'contains_blocked_keywords',
    'calculate_weighted_choice',
    'sanitize_filename',
    'get_tweet_age_hours',
    'create_backup_file',
    'retry_with_backoff',
    'get_current_timestamp',
    'parse_timestamp',
    'RateLimitTracker',
    'rate_tracker',
    'log_performance_metric',
    'get_system_info',
]