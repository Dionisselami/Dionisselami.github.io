"""
Rate limiting system for Twitter bot to avoid detection and account suspension.
Implements smart rate limiting with human-like behavior patterns.
"""

import json
import time
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, deque

from .utils import (
    load_json_file, save_json_file, get_current_timestamp, 
    parse_timestamp, is_weekend, format_duration,
    human_like_delay
)

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Advanced rate limiter with human-like behavior patterns.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize rate limiter.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.rate_config = config.get('rate_limits', {})
        self.behavior_config = config.get('behavior', {})
        self.runtime_config = config.get('runtime', {})
        
        # Rate limits
        self.max_actions_per_hour = self.rate_config.get('max_actions_per_hour', 12)
        self.max_actions_per_day = self.rate_config.get('max_actions_per_day', 100)
        self.max_likes_per_hour = self.rate_config.get('max_likes_per_hour', 8)
        self.max_replies_per_hour = self.rate_config.get('max_replies_per_hour', 3)
        self.max_retweets_per_hour = self.rate_config.get('max_retweets_per_hour', 2)
        
        # Action tracking
        self.actions_log_file = self.rate_config.get('actions_log_file', 'actions_log.json')
        self.actions_history = deque(maxlen=10000)  # Keep last 10k actions
        self.daily_counts = defaultdict(int)
        self.hourly_counts = defaultdict(int)
        
        # Behavior settings
        self.delays = self.behavior_config.get('delays', {})
        self.delay_between_actions = self.delays.get('between_actions', (60, 600))
        self.delay_between_searches = self.delays.get('between_searches', (300, 900))
        self.delay_after_error = self.delays.get('after_error', (900, 1800))
        
        # Weekend mode
        self.weekend_mode = self.runtime_config.get('weekend_mode', True)
        self.weekend_reduction = self.runtime_config.get('weekend_reduction', 0.5)
        
        # Adaptive behavior
        self.consecutive_errors = 0
        self.last_error_time = None
        self.session_start_time = datetime.now()
        self.burst_mode = False
        self.quiet_periods = []
        
        # Load existing actions
        self._load_actions_history()
        
        # Initialize behavior patterns
        self._initialize_patterns()
        
        logger.info("Rate limiter initialized")
    
    def _load_actions_history(self) -> None:
        """Load actions history from file."""
        try:
            data = load_json_file(self.actions_log_file, {})
            if not data:
                logger.info("No existing actions history found")
                return
            
            actions = data.get('actions', [])
            for action in actions:
                timestamp_str = action.get('timestamp')
                if timestamp_str:
                    timestamp = parse_timestamp(timestamp_str)
                    if timestamp:
                        action['timestamp'] = timestamp
                        self.actions_history.append(action)
            
            # Clean up old actions (older than 7 days)
            cutoff = datetime.now() - timedelta(days=7)
            self.actions_history = deque([
                action for action in self.actions_history 
                if action['timestamp'] > cutoff
            ], maxlen=10000)
            
            logger.info(f"Loaded {len(self.actions_history)} actions from history")
            
        except Exception as e:
            logger.error(f"Failed to load actions history: {e}")
    
    def _save_actions_history(self) -> None:
        """Save actions history to file."""
        try:
            actions = []
            for action in self.actions_history:
                action_copy = action.copy()
                if isinstance(action_copy['timestamp'], datetime):
                    action_copy['timestamp'] = action_copy['timestamp'].isoformat()
                actions.append(action_copy)
            
            data = {
                'actions': actions,
                'last_updated': get_current_timestamp(),
                'total_actions': len(actions),
            }
            
            success = save_json_file(self.actions_log_file, data)
            if success:
                logger.debug(f"Saved {len(actions)} actions to history")
            
        except Exception as e:
            logger.error(f"Failed to save actions history: {e}")
    
    def _initialize_patterns(self) -> None:
        """Initialize human-like behavior patterns."""
        # Define quiet periods (times when humans are less active)
        current_time = datetime.now()
        
        # Late night quiet period (11 PM - 6 AM)
        self.quiet_periods = [
            (23, 6),  # 11 PM to 6 AM
            (12, 13), # Lunch break
        ]
        
        # Generate daily activity pattern
        self.daily_pattern = self._generate_daily_pattern()
        
        logger.debug("Behavior patterns initialized")
    
    def _generate_daily_pattern(self) -> List[float]:
        """
        Generate daily activity pattern (24 hours).
        
        Returns:
            List of activity multipliers for each hour (0.0 to 2.0)
        """
        pattern = []
        
        for hour in range(24):
            if 6 <= hour <= 9:  # Morning peak
                multiplier = 1.5
            elif 12 <= hour <= 13:  # Lunch break
                multiplier = 0.8
            elif 17 <= hour <= 22:  # Evening peak
                multiplier = 1.8
            elif 23 <= hour <= 5:  # Night (quiet)
                multiplier = 0.3
            else:  # Regular hours
                multiplier = 1.0
            
            # Add some randomness
            multiplier *= (0.8 + random.random() * 0.4)
            pattern.append(multiplier)
        
        return pattern
    
    def _get_current_activity_multiplier(self) -> float:
        """
        Get current activity multiplier based on time patterns.
        
        Returns:
            Activity multiplier (0.0 to 2.0)
        """
        current_hour = datetime.now().hour
        base_multiplier = self.daily_pattern[current_hour]
        
        # Weekend reduction
        if is_weekend() and self.weekend_mode:
            base_multiplier *= self.weekend_reduction
        
        # Burst mode
        if self.burst_mode:
            base_multiplier *= 1.5
        
        return base_multiplier
    
    def _get_actions_in_timeframe(self, hours: int, action_type: Optional[str] = None) -> int:
        """
        Get number of actions in the specified timeframe.
        
        Args:
            hours: Number of hours to look back
            action_type: Filter by action type (optional)
            
        Returns:
            Number of actions in timeframe
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        
        count = 0
        for action in self.actions_history:
            if action['timestamp'] > cutoff:
                if action_type is None or action['type'] == action_type:
                    count += 1
        
        return count
    
    def _calculate_dynamic_delay(self, action_type: str) -> Tuple[float, float]:
        """
        Calculate dynamic delay based on current conditions.
        
        Args:
            action_type: Type of action
            
        Returns:
            Tuple of (min_delay, max_delay) in seconds
        """
        base_min, base_max = self.delay_between_actions
        
        # Get current activity level
        activity_multiplier = self._get_current_activity_multiplier()
        
        # Adjust based on recent activity
        recent_actions = self._get_actions_in_timeframe(1)  # Last hour
        if recent_actions > self.max_actions_per_hour * 0.8:
            # Slow down if approaching limit
            multiplier = 1.5
        elif recent_actions < self.max_actions_per_hour * 0.2:
            # Speed up if very low activity
            multiplier = 0.7
        else:
            multiplier = 1.0
        
        # Apply activity and behavior multipliers
        multiplier *= (2.0 - activity_multiplier)  # Inverse relationship
        
        # Calculate final delays
        min_delay = base_min * multiplier
        max_delay = base_max * multiplier
        
        # Ensure reasonable bounds
        min_delay = max(10, min_delay)  # At least 10 seconds
        max_delay = min(1800, max_delay)  # At most 30 minutes
        
        return min_delay, max_delay
    
    def can_perform_action(self, action_type: str) -> bool:
        """
        Check if an action can be performed based on rate limits.
        
        Args:
            action_type: Type of action ('like', 'reply', 'retweet', 'search')
            
        Returns:
            True if action can be performed, False otherwise
        """
        try:
            # Check if in error cooldown
            if self.consecutive_errors >= 5:
                if self.last_error_time:
                    cooldown_seconds = 30 * 60  # 30 minutes
                    if (datetime.now() - self.last_error_time).total_seconds() < cooldown_seconds:
                        logger.warning(f"In error cooldown, {self.consecutive_errors} consecutive errors")
                        return False
                # Reset error count after cooldown
                self.consecutive_errors = 0
            
            # Check overall daily limit
            daily_actions = self._get_actions_in_timeframe(24)
            if daily_actions >= self.max_actions_per_day:
                logger.warning(f"Daily limit reached: {daily_actions}/{self.max_actions_per_day}")
                return False
            
            # Check hourly limit
            hourly_actions = self._get_actions_in_timeframe(1)
            if hourly_actions >= self.max_actions_per_hour:
                logger.warning(f"Hourly limit reached: {hourly_actions}/{self.max_actions_per_hour}")
                return False
            
            # Check specific action type limits
            if action_type == 'like':
                hourly_likes = self._get_actions_in_timeframe(1, 'like')
                if hourly_likes >= self.max_likes_per_hour:
                    logger.warning(f"Hourly like limit reached: {hourly_likes}/{self.max_likes_per_hour}")
                    return False
            
            elif action_type == 'reply':
                hourly_replies = self._get_actions_in_timeframe(1, 'reply')
                if hourly_replies >= self.max_replies_per_hour:
                    logger.warning(f"Hourly reply limit reached: {hourly_replies}/{self.max_replies_per_hour}")
                    return False
            
            elif action_type == 'retweet':
                hourly_retweets = self._get_actions_in_timeframe(1, 'retweet')
                if hourly_retweets >= self.max_retweets_per_hour:
                    logger.warning(f"Hourly retweet limit reached: {hourly_retweets}/{self.max_retweets_per_hour}")
                    return False
            
            # Check if we're in a quiet period
            current_hour = datetime.now().hour
            for quiet_start, quiet_end in self.quiet_periods:
                if quiet_start > quiet_end:  # Spans midnight
                    if current_hour >= quiet_start or current_hour <= quiet_end:
                        # Reduce activity during quiet periods
                        if random.random() < 0.7:  # 70% chance to skip
                            logger.debug(f"Skipping action during quiet period ({quiet_start}-{quiet_end})")
                            return False
                else:
                    if quiet_start <= current_hour <= quiet_end:
                        if random.random() < 0.7:
                            logger.debug(f"Skipping action during quiet period ({quiet_start}-{quiet_end})")
                            return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking action permission: {e}")
            return False
    
    def record_action(self, action_type: str, success: bool = True, 
                     metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Record an action in the history.
        
        Args:
            action_type: Type of action
            success: Whether the action was successful
            metadata: Additional metadata about the action
        """
        try:
            action = {
                'type': action_type,
                'success': success,
                'timestamp': datetime.now(),
                'metadata': metadata or {},
            }
            
            self.actions_history.append(action)
            
            # Handle errors
            if not success:
                self.consecutive_errors += 1
                self.last_error_time = datetime.now()
                logger.warning(f"Action failed: {action_type} (consecutive errors: {self.consecutive_errors})")
            else:
                self.consecutive_errors = 0
                self.last_error_time = None
            
            # Save to file periodically
            if len(self.actions_history) % 10 == 0:
                self._save_actions_history()
            
            logger.debug(f"Recorded action: {action_type} ({'success' if success else 'failed'})")
            
        except Exception as e:
            logger.error(f"Error recording action: {e}")
    
    def wait_before_action(self, action_type: str) -> None:
        """
        Wait appropriate amount of time before performing an action.
        
        Args:
            action_type: Type of action to be performed
        """
        try:
            # Calculate dynamic delay
            min_delay, max_delay = self._calculate_dynamic_delay(action_type)
            
            # Add some randomness for human-like behavior
            delay = random.uniform(min_delay, max_delay)
            
            logger.info(f"Waiting {delay:.1f}s before {action_type} action")
            
            # Use human-like delay with natural variance
            human_like_delay(delay, 0.2)
            
        except Exception as e:
            logger.error(f"Error in wait_before_action: {e}")
            time.sleep(60)  # Fallback delay
    
    def wait_after_error(self) -> None:
        """Wait appropriate amount of time after an error."""
        try:
            min_delay, max_delay = self.delay_after_error
            
            # Increase delay based on consecutive errors
            multiplier = 1.0 + (self.consecutive_errors * 0.5)
            min_delay *= multiplier
            max_delay *= multiplier
            
            delay = random.uniform(min_delay, max_delay)
            
            logger.warning(f"Waiting {format_duration(int(delay))} after error")
            
            # Use human-like delay
            human_like_delay(delay, 0.1)
            
        except Exception as e:
            logger.error(f"Error in wait_after_error: {e}")
            time.sleep(900)  # Fallback 15 minutes
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get current rate limit status.
        
        Returns:
            Dictionary with rate limit information
        """
        try:
            now = datetime.now()
            
            # Count actions in different timeframes
            hourly_actions = self._get_actions_in_timeframe(1)
            daily_actions = self._get_actions_in_timeframe(24)
            hourly_likes = self._get_actions_in_timeframe(1, 'like')
            hourly_replies = self._get_actions_in_timeframe(1, 'reply')
            hourly_retweets = self._get_actions_in_timeframe(1, 'retweet')
            
            # Calculate remaining limits
            status = {
                'hourly_actions': {
                    'used': hourly_actions,
                    'limit': self.max_actions_per_hour,
                    'remaining': max(0, self.max_actions_per_hour - hourly_actions),
                    'percentage': (hourly_actions / self.max_actions_per_hour) * 100,
                },
                'daily_actions': {
                    'used': daily_actions,
                    'limit': self.max_actions_per_day,
                    'remaining': max(0, self.max_actions_per_day - daily_actions),
                    'percentage': (daily_actions / self.max_actions_per_day) * 100,
                },
                'hourly_likes': {
                    'used': hourly_likes,
                    'limit': self.max_likes_per_hour,
                    'remaining': max(0, self.max_likes_per_hour - hourly_likes),
                    'percentage': (hourly_likes / self.max_likes_per_hour) * 100,
                },
                'hourly_replies': {
                    'used': hourly_replies,
                    'limit': self.max_replies_per_hour,
                    'remaining': max(0, self.max_replies_per_hour - hourly_replies),
                    'percentage': (hourly_replies / self.max_replies_per_hour) * 100,
                },
                'hourly_retweets': {
                    'used': hourly_retweets,
                    'limit': self.max_retweets_per_hour,
                    'remaining': max(0, self.max_retweets_per_hour - hourly_retweets),
                    'percentage': (hourly_retweets / self.max_retweets_per_hour) * 100,
                },
                'consecutive_errors': self.consecutive_errors,
                'last_error_time': self.last_error_time.isoformat() if self.last_error_time else None,
                'activity_multiplier': self._get_current_activity_multiplier(),
                'in_quiet_period': self._is_in_quiet_period(),
                'weekend_mode': is_weekend() and self.weekend_mode,
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting rate limit status: {e}")
            return {}
    
    def _is_in_quiet_period(self) -> bool:
        """Check if currently in a quiet period."""
        current_hour = datetime.now().hour
        
        for quiet_start, quiet_end in self.quiet_periods:
            if quiet_start > quiet_end:  # Spans midnight
                if current_hour >= quiet_start or current_hour <= quiet_end:
                    return True
            else:
                if quiet_start <= current_hour <= quiet_end:
                    return True
        
        return False
    
    def get_next_action_time(self, action_type: str) -> Optional[datetime]:
        """
        Get the earliest time when the next action can be performed.
        
        Args:
            action_type: Type of action
            
        Returns:
            DateTime when action can be performed, or None if available now
        """
        try:
            if self.can_perform_action(action_type):
                return None  # Can perform now
            
            # Check what's blocking the action
            hourly_actions = self._get_actions_in_timeframe(1)
            daily_actions = self._get_actions_in_timeframe(24)
            
            # Find the earliest time we can act
            if daily_actions >= self.max_actions_per_day:
                # Wait until tomorrow
                tomorrow = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
                if tomorrow <= datetime.now():
                    tomorrow += timedelta(days=1)
                return tomorrow
            
            if hourly_actions >= self.max_actions_per_hour:
                # Wait until next hour
                next_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
                next_hour += timedelta(hours=1)
                return next_hour
            
            # Check specific action limits
            if action_type == 'like':
                hourly_likes = self._get_actions_in_timeframe(1, 'like')
                if hourly_likes >= self.max_likes_per_hour:
                    next_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
                    next_hour += timedelta(hours=1)
                    return next_hour
            
            # If we get here, some other condition is blocking
            return datetime.now() + timedelta(minutes=30)
            
        except Exception as e:
            logger.error(f"Error calculating next action time: {e}")
            return datetime.now() + timedelta(hours=1)
    
    def reset_error_count(self) -> None:
        """Reset consecutive error count."""
        self.consecutive_errors = 0
        self.last_error_time = None
        logger.info("Error count reset")
    
    def enable_burst_mode(self, duration_minutes: int = 30) -> None:
        """
        Enable burst mode for increased activity.
        
        Args:
            duration_minutes: Duration of burst mode in minutes
        """
        self.burst_mode = True
        logger.info(f"Burst mode enabled for {duration_minutes} minutes")
        
        # Schedule disabling burst mode
        import threading
        def disable_burst():
            time.sleep(duration_minutes * 60)
            self.burst_mode = False
            logger.info("Burst mode disabled")
        
        threading.Thread(target=disable_burst, daemon=True).start()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about bot activity.
        
        Returns:
            Dictionary with statistics
        """
        try:
            now = datetime.now()
            
            # Count actions by type and timeframe
            stats = {
                'session_duration': format_duration(int((now - self.session_start_time).total_seconds())),
                'total_actions': len(self.actions_history),
                'actions_last_hour': self._get_actions_in_timeframe(1),
                'actions_last_day': self._get_actions_in_timeframe(24),
                'actions_by_type': {},
                'success_rate': 0.0,
                'average_actions_per_hour': 0.0,
                'rate_limit_status': self.get_rate_limit_status(),
            }
            
            # Count by action type
            for action in self.actions_history:
                action_type = action['type']
                if action_type not in stats['actions_by_type']:
                    stats['actions_by_type'][action_type] = {
                        'total': 0,
                        'successful': 0,
                        'failed': 0,
                    }
                
                stats['actions_by_type'][action_type]['total'] += 1
                if action['success']:
                    stats['actions_by_type'][action_type]['successful'] += 1
                else:
                    stats['actions_by_type'][action_type]['failed'] += 1
            
            # Calculate success rate
            if len(self.actions_history) > 0:
                successful_actions = sum(1 for action in self.actions_history if action['success'])
                stats['success_rate'] = (successful_actions / len(self.actions_history)) * 100
            
            # Calculate average actions per hour
            session_hours = (now - self.session_start_time).total_seconds() / 3600
            if session_hours > 0:
                stats['average_actions_per_hour'] = len(self.actions_history) / session_hours
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
    
    def __del__(self):
        """Destructor to save actions history."""
        try:
            self._save_actions_history()
        except:
            pass

def create_rate_limiter(config: Dict[str, Any]) -> RateLimiter:
    """
    Create and initialize a rate limiter.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Initialized RateLimiter instance
    """
    return RateLimiter(config)