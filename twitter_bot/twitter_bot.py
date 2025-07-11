"""
Main Twitter bot orchestration script.
Coordinates all bot activities including authentication, tweet finding, and engagement.
"""

import logging
import signal
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import threading
import queue

from .config import CONFIG
from .utils import setup_logging, get_current_timestamp, format_duration, get_system_info
from .cookie_manager import create_cookie_manager
from .rate_limiter import create_rate_limiter
from .tweet_finder import create_tweet_finder
from .engagement_engine import create_engagement_engine

logger = logging.getLogger(__name__)

class TwitterBot:
    """
    Main Twitter bot class that orchestrates all activities.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize Twitter bot.
        
        Args:
            config: Configuration dictionary (uses CONFIG if None)
        """
        self.config = config or CONFIG
        self.running = False
        self.paused = False
        self.start_time = None
        self.stats = {
            'tweets_found': 0,
            'engagements_attempted': 0,
            'engagements_successful': 0,
            'errors': 0,
            'cycles_completed': 0,
            'session_duration': 0,
        }
        
        # Initialize logging
        log_config = self.config.get('logging', {})
        setup_logging(
            log_file=log_config.get('file', 'twitter_bot.log'),
            log_level=log_config.get('level', 'INFO'),
            log_format=log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            max_size=log_config.get('max_size', 10 * 1024 * 1024),
            backup_count=log_config.get('backup_count', 5)
        )
        
        # Initialize components
        self.cookie_manager = None
        self.rate_limiter = None
        self.tweet_finder = None
        self.engagement_engine = None
        
        # Control settings
        self.runtime_config = self.config.get('runtime', {})
        self.continuous_mode = self.runtime_config.get('continuous', True)
        self.run_duration_hours = self.runtime_config.get('duration_hours', 24)
        self.pause_between_cycles = self.runtime_config.get('pause_between_cycles', 1800)  # 30 minutes
        
        # Monitoring
        self.monitoring_config = self.config.get('monitoring', {})
        self.monitoring_enabled = self.monitoring_config.get('enabled', True)
        self.health_check_interval = self.monitoring_config.get('health_check_interval', 3600)  # 1 hour
        
        # Error handling
        self.safety_config = self.config.get('safety', {})
        self.max_consecutive_errors = self.safety_config.get('max_consecutive_errors', 5)
        self.error_cooldown_minutes = self.safety_config.get('error_cooldown_minutes', 30)
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        logger.info("Twitter bot initialized")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _initialize_components(self) -> bool:
        """
        Initialize all bot components.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing bot components...")
            
            # Initialize cookie manager
            self.cookie_manager = create_cookie_manager(self.config)
            if not self.cookie_manager.initialize_session():
                logger.error("Failed to initialize cookie manager")
                return False
            
            # Initialize rate limiter
            self.rate_limiter = create_rate_limiter(self.config)
            
            # Initialize tweet finder
            self.tweet_finder = create_tweet_finder(self.config, self.cookie_manager)
            
            # Initialize engagement engine
            self.engagement_engine = create_engagement_engine(self.config, self.cookie_manager)
            
            logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            return False
    
    def _cleanup_components(self):
        """Clean up all bot components."""
        try:
            logger.info("Cleaning up bot components...")
            
            if self.cookie_manager:
                self.cookie_manager.close_session()
                
            logger.info("Components cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def _perform_health_check(self) -> bool:
        """
        Perform health check on bot components.
        
        Returns:
            True if all components are healthy, False otherwise
        """
        try:
            logger.debug("Performing health check...")
            
            # Check cookie manager session
            if not self.cookie_manager or not self.cookie_manager.is_session_valid():
                logger.warning("Cookie manager session is invalid")
                
                # Try to refresh session
                if self.cookie_manager:
                    if not self.cookie_manager.refresh_session():
                        logger.error("Failed to refresh session")
                        return False
                else:
                    logger.error("Cookie manager not initialized")
                    return False
            
            # Check rate limiter status
            if self.rate_limiter:
                status = self.rate_limiter.get_rate_limit_status()
                if status.get('consecutive_errors', 0) >= self.max_consecutive_errors:
                    logger.warning("Too many consecutive errors detected")
                    return False
            
            logger.debug("Health check passed")
            return True
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def _find_tweets_to_engage(self) -> List[Dict[str, Any]]:
        """
        Find tweets to engage with.
        
        Returns:
            List of tweet data dictionaries
        """
        try:
            logger.info("Finding tweets to engage with...")
            
            # Use different strategies based on configuration
            search_strategies = [
                'random_queries',
                'trending_topics',
                'mixed_approach',
            ]
            
            strategy = 'mixed_approach'  # Default strategy
            
            if strategy == 'random_queries':
                tweets = self.tweet_finder.find_random_tweets(count=10)
            elif strategy == 'trending_topics':
                tweets = self.tweet_finder.find_trending_tweets(count=10)
            else:  # mixed_approach
                # Combine different sources
                tweets = []
                
                # Get some from random queries
                random_tweets = self.tweet_finder.find_random_tweets(count=5)
                tweets.extend(random_tweets)
                
                # Get some from trending topics
                trending_tweets = self.tweet_finder.find_trending_tweets(count=5)
                tweets.extend(trending_tweets)
                
                # Remove duplicates
                seen_ids = set()
                unique_tweets = []
                for tweet in tweets:
                    if tweet['id'] not in seen_ids:
                        unique_tweets.append(tweet)
                        seen_ids.add(tweet['id'])
                
                tweets = unique_tweets
            
            logger.info(f"Found {len(tweets)} tweets to potentially engage with")
            self.stats['tweets_found'] += len(tweets)
            
            return tweets
            
        except Exception as e:
            logger.error(f"Error finding tweets: {e}")
            self.stats['errors'] += 1
            return []
    
    def _select_tweets_for_engagement(self, tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Select best tweets for engagement based on rate limits and criteria.
        
        Args:
            tweets: List of tweet data dictionaries
            
        Returns:
            List of selected tweets
        """
        try:
            if not tweets:
                return []
            
            # Filter tweets based on rate limits
            available_actions = {
                'like': self.rate_limiter.can_perform_action('like'),
                'reply': self.rate_limiter.can_perform_action('reply'),
                'retweet': self.rate_limiter.can_perform_action('retweet'),
            }
            
            # If no actions are available, return empty list
            if not any(available_actions.values()):
                logger.warning("No actions available due to rate limits")
                return []
            
            # Select tweets based on engagement scores
            selected_tweets = []
            
            # Sort by engagement score (descending)
            sorted_tweets = sorted(tweets, key=lambda t: t.get('engagement_score', 0), reverse=True)
            
            # Select top tweets based on available actions
            max_selections = 3  # Conservative limit
            
            for tweet in sorted_tweets[:max_selections]:
                # Check if we can perform at least one action
                if any(available_actions.values()):
                    selected_tweets.append(tweet)
            
            logger.info(f"Selected {len(selected_tweets)} tweets for engagement")
            return selected_tweets
            
        except Exception as e:
            logger.error(f"Error selecting tweets for engagement: {e}")
            return []
    
    def _engage_with_selected_tweets(self, tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Engage with selected tweets.
        
        Args:
            tweets: List of tweet data dictionaries
            
        Returns:
            Dictionary with engagement results
        """
        try:
            logger.info(f"Engaging with {len(tweets)} selected tweets")
            
            results = {
                'total_tweets': len(tweets),
                'successful_engagements': 0,
                'failed_engagements': 0,
                'actions_performed': {
                    'likes': 0,
                    'replies': 0,
                    'retweets': 0,
                },
                'errors': 0,
            }
            
            for tweet in tweets:
                try:
                    # Check rate limits before each engagement
                    if not any([
                        self.rate_limiter.can_perform_action('like'),
                        self.rate_limiter.can_perform_action('reply'),
                        self.rate_limiter.can_perform_action('retweet'),
                    ]):
                        logger.warning("Rate limits reached, stopping engagement")
                        break
                    
                    # Wait before action
                    self.rate_limiter.wait_before_action('engagement')
                    
                    # Engage with tweet
                    engagement_result = self.engagement_engine.engage_with_tweet(tweet)
                    
                    # Record actions in rate limiter
                    if engagement_result.get('like'):
                        self.rate_limiter.record_action('like', True)
                        results['actions_performed']['likes'] += 1
                    
                    if engagement_result.get('reply'):
                        self.rate_limiter.record_action('reply', True)
                        results['actions_performed']['replies'] += 1
                    
                    if engagement_result.get('retweet'):
                        self.rate_limiter.record_action('retweet', True)
                        results['actions_performed']['retweets'] += 1
                    
                    # Check if any action was successful
                    if any(engagement_result.values()):
                        results['successful_engagements'] += 1
                        logger.info(f"Successfully engaged with tweet: {tweet['id']}")
                    else:
                        results['failed_engagements'] += 1
                        logger.warning(f"Failed to engage with tweet: {tweet['id']}")
                        
                        # Record failed engagement
                        self.rate_limiter.record_action('engagement', False)
                    
                except Exception as e:
                    logger.error(f"Error engaging with tweet {tweet.get('id', 'unknown')}: {e}")
                    results['errors'] += 1
                    self.rate_limiter.record_action('engagement', False)
            
            self.stats['engagements_attempted'] += results['total_tweets']
            self.stats['engagements_successful'] += results['successful_engagements']
            self.stats['errors'] += results['errors']
            
            logger.info(f"Engagement completed. Successful: {results['successful_engagements']}, Failed: {results['failed_engagements']}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in tweet engagement: {e}")
            self.stats['errors'] += 1
            return {'errors': 1}
    
    def _perform_bot_cycle(self) -> bool:
        """
        Perform one complete bot cycle.
        
        Returns:
            True if cycle completed successfully, False otherwise
        """
        try:
            logger.info("Starting bot cycle...")
            
            # Health check
            if not self._perform_health_check():
                logger.error("Health check failed, skipping cycle")
                return False
            
            # Find tweets
            tweets = self._find_tweets_to_engage()
            if not tweets:
                logger.warning("No tweets found for engagement")
                return False
            
            # Select tweets for engagement
            selected_tweets = self._select_tweets_for_engagement(tweets)
            if not selected_tweets:
                logger.warning("No tweets selected for engagement")
                return False
            
            # Engage with selected tweets
            engagement_results = self._engage_with_selected_tweets(selected_tweets)
            
            # Check if engagement was successful
            if engagement_results.get('successful_engagements', 0) > 0:
                logger.info("Bot cycle completed successfully")
                self.stats['cycles_completed'] += 1
                return True
            else:
                logger.warning("Bot cycle completed with no successful engagements")
                return False
            
        except Exception as e:
            logger.error(f"Error in bot cycle: {e}")
            self.stats['errors'] += 1
            return False
    
    def _log_statistics(self):
        """Log current bot statistics."""
        try:
            if self.start_time:
                self.stats['session_duration'] = (datetime.now() - self.start_time).total_seconds()
            
            # Get component statistics
            rate_limit_stats = self.rate_limiter.get_rate_limit_status() if self.rate_limiter else {}
            engagement_stats = self.engagement_engine.get_engagement_statistics() if self.engagement_engine else {}
            tweet_finder_stats = self.tweet_finder.get_statistics() if self.tweet_finder else {}
            
            logger.info("=== BOT STATISTICS ===")
            logger.info(f"Session Duration: {format_duration(int(self.stats['session_duration']))}")
            logger.info(f"Cycles Completed: {self.stats['cycles_completed']}")
            logger.info(f"Tweets Found: {self.stats['tweets_found']}")
            logger.info(f"Engagements Attempted: {self.stats['engagements_attempted']}")
            logger.info(f"Engagements Successful: {self.stats['engagements_successful']}")
            logger.info(f"Errors: {self.stats['errors']}")
            
            if rate_limit_stats:
                logger.info(f"Rate Limits - Hourly: {rate_limit_stats.get('hourly_actions', {}).get('used', 0)}/{rate_limit_stats.get('hourly_actions', {}).get('limit', 0)}")
                logger.info(f"Rate Limits - Daily: {rate_limit_stats.get('daily_actions', {}).get('used', 0)}/{rate_limit_stats.get('daily_actions', {}).get('limit', 0)}")
            
            if engagement_stats:
                logger.info(f"Engagement Stats - Likes: {engagement_stats.get('likes', 0)}, Replies: {engagement_stats.get('replies', 0)}, Retweets: {engagement_stats.get('retweets', 0)}")
            
            logger.info("=== END STATISTICS ===")
            
        except Exception as e:
            logger.error(f"Error logging statistics: {e}")
    
    def run(self) -> bool:
        """
        Run the Twitter bot.
        
        Returns:
            True if bot ran successfully, False otherwise
        """
        try:
            logger.info("Starting Twitter bot...")
            
            # Initialize components
            if not self._initialize_components():
                logger.error("Failed to initialize bot components")
                return False
            
            self.running = True
            self.start_time = datetime.now()
            
            # Log system information
            system_info = get_system_info()
            logger.info(f"System Info: {system_info}")
            
            # Calculate end time if not continuous
            end_time = None
            if not self.continuous_mode:
                end_time = self.start_time + timedelta(hours=self.run_duration_hours)
                logger.info(f"Bot will run until: {end_time}")
            
            # Main bot loop
            while self.running:
                try:
                    # Check if we should stop (time limit)
                    if end_time and datetime.now() >= end_time:
                        logger.info("Time limit reached, stopping bot")
                        break
                    
                    # Check if paused
                    if self.paused:
                        logger.info("Bot is paused, waiting...")
                        time.sleep(60)  # Check every minute
                        continue
                    
                    # Perform bot cycle
                    cycle_success = self._perform_bot_cycle()
                    
                    # Log statistics periodically
                    if self.stats['cycles_completed'] % 5 == 0:  # Every 5 cycles
                        self._log_statistics()
                    
                    # Handle consecutive errors
                    if not cycle_success:
                        # Wait longer after errors
                        self.rate_limiter.wait_after_error()
                    
                    # Pause between cycles
                    if self.running and self.pause_between_cycles > 0:
                        logger.info(f"Pausing for {format_duration(self.pause_between_cycles)} between cycles")
                        time.sleep(self.pause_between_cycles)
                    
                except KeyboardInterrupt:
                    logger.info("Received keyboard interrupt, stopping bot")
                    break
                except Exception as e:
                    logger.error(f"Error in main bot loop: {e}")
                    self.stats['errors'] += 1
                    time.sleep(300)  # Wait 5 minutes before retrying
            
            # Final statistics
            self._log_statistics()
            
            logger.info("Twitter bot stopped")
            return True
            
        except Exception as e:
            logger.error(f"Critical error in bot execution: {e}")
            return False
        
        finally:
            self.running = False
            self._cleanup_components()
    
    def stop(self):
        """Stop the Twitter bot."""
        logger.info("Stopping Twitter bot...")
        self.running = False
    
    def pause(self):
        """Pause the Twitter bot."""
        logger.info("Pausing Twitter bot...")
        self.paused = True
    
    def resume(self):
        """Resume the Twitter bot."""
        logger.info("Resuming Twitter bot...")
        self.paused = False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current bot status.
        
        Returns:
            Dictionary with bot status information
        """
        try:
            if self.start_time:
                session_duration = (datetime.now() - self.start_time).total_seconds()
            else:
                session_duration = 0
            
            status = {
                'running': self.running,
                'paused': self.paused,
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'session_duration': format_duration(int(session_duration)),
                'statistics': self.stats.copy(),
            }
            
            # Add component status
            if self.cookie_manager:
                status['cookie_manager'] = self.cookie_manager.get_session_info()
            
            if self.rate_limiter:
                status['rate_limiter'] = self.rate_limiter.get_rate_limit_status()
            
            if self.engagement_engine:
                status['engagement_engine'] = self.engagement_engine.get_engagement_statistics()
            
            if self.tweet_finder:
                status['tweet_finder'] = self.tweet_finder.get_statistics()
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting bot status: {e}")
            return {'error': str(e)}

def main():
    """Main function to run the Twitter bot."""
    try:
        # Create and run bot
        bot = TwitterBot()
        success = bot.run()
        
        if success:
            logger.info("Bot execution completed successfully")
            sys.exit(0)
        else:
            logger.error("Bot execution failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()