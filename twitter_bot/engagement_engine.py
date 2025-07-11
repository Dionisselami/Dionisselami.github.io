"""
Engagement engine for Twitter bot interactions.
Handles liking, replying, and retweeting with natural behavior patterns.
"""

import logging
import random
import time
from typing import Dict, List, Optional, Any, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

from .utils import (
    human_like_delay, safe_get_text, safe_get_attribute,
    get_current_timestamp, log_performance_metric
)
from .config import get_contextual_reply

logger = logging.getLogger(__name__)

class EngagementEngine:
    """
    Handles all Twitter engagement activities with natural behavior simulation.
    """
    
    def __init__(self, config: Dict[str, Any], cookie_manager):
        """
        Initialize engagement engine.
        
        Args:
            config: Configuration dictionary
            cookie_manager: Cookie manager instance
        """
        self.config = config
        self.cookie_manager = cookie_manager
        self.behavior_config = config.get('behavior', {})
        self.reply_config = config.get('replies', {})
        self.safety_config = config.get('safety', {})
        
        # Action probabilities
        self.action_probabilities = self.behavior_config.get('action_probabilities', {})
        self.like_probability = self.action_probabilities.get('like', 0.7)
        self.reply_probability = self.action_probabilities.get('reply', 0.3)
        self.retweet_probability = self.action_probabilities.get('retweet', 0.2)
        
        # Reply settings
        self.reply_templates = self.reply_config.get('templates', [])
        self.contextual_replies = self.reply_config.get('contextual', {})
        
        # Behavior delays
        self.delays = self.behavior_config.get('delays', {})
        self.typing_delay = self.delays.get('typing', (0.1, 0.3))
        self.click_delay = self.delays.get('click', (0.5, 1.5))
        
        # Safety settings
        self.captcha_detection = self.safety_config.get('captcha_detection', True)
        
        # Engagement tracking
        self.engagement_stats = {
            'likes': 0,
            'replies': 0,
            'retweets': 0,
            'errors': 0,
            'captcha_encounters': 0,
        }
        
        logger.info("Engagement engine initialized")
    
    def _get_driver(self) -> Optional[webdriver.Chrome]:
        """Get WebDriver instance from cookie manager."""
        return self.cookie_manager.get_driver()
    
    def _detect_captcha(self) -> bool:
        """
        Detect if CAPTCHA is present on the page.
        
        Returns:
            True if CAPTCHA detected, False otherwise
        """
        try:
            driver = self._get_driver()
            if not driver:
                return False
            
            captcha_indicators = [
                "div[data-testid='ocfEnterTextTextInput']",
                "iframe[title*='captcha']",
                "div[class*='captcha']",
                "div[class*='challenge']",
                "div[role='dialog']",
            ]
            
            for selector in captcha_indicators:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        logger.warning("CAPTCHA detected during engagement")
                        self.engagement_stats['captcha_encounters'] += 1
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting CAPTCHA: {e}")
            return False
    
    def _navigate_to_tweet(self, tweet_data: Dict[str, Any]) -> bool:
        """
        Navigate to a specific tweet.
        
        Args:
            tweet_data: Tweet data dictionary
            
        Returns:
            True if navigation successful, False otherwise
        """
        try:
            driver = self._get_driver()
            if not driver:
                return False
            
            if not tweet_data.get('url'):
                logger.error("No URL provided for tweet")
                return False
            
            logger.debug(f"Navigating to tweet: {tweet_data['id']}")
            
            driver.get(tweet_data['url'])
            human_like_delay(3, 0.5)
            
            # Wait for tweet to load
            wait = WebDriverWait(driver, 15)
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='tweet']")))
                return True
            except TimeoutException:
                logger.error("Tweet failed to load")
                return False
            
        except Exception as e:
            logger.error(f"Error navigating to tweet: {e}")
            return False
    
    def _find_engagement_buttons(self, tweet_element=None) -> Dict[str, Any]:
        """
        Find engagement buttons (like, reply, retweet) for a tweet.
        
        Args:
            tweet_element: Specific tweet element (optional)
            
        Returns:
            Dictionary with button elements
        """
        try:
            driver = self._get_driver()
            if not driver:
                return {}
            
            # Use specific tweet element or find the main tweet
            if tweet_element is None:
                tweet_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='tweet']")
                if not tweet_elements:
                    return {}
                tweet_element = tweet_elements[0]  # Use first (main) tweet
            
            buttons = {}
            
            # Find like button
            like_selectors = [
                "div[data-testid='like']",
                "div[data-testid='unlike']",
                "button[data-testid='like']",
                "button[data-testid='unlike']",
            ]
            
            for selector in like_selectors:
                try:
                    like_button = tweet_element.find_element(By.CSS_SELECTOR, selector)
                    if like_button:
                        buttons['like'] = like_button
                        break
                except NoSuchElementException:
                    continue
            
            # Find reply button
            reply_selectors = [
                "div[data-testid='reply']",
                "button[data-testid='reply']",
            ]
            
            for selector in reply_selectors:
                try:
                    reply_button = tweet_element.find_element(By.CSS_SELECTOR, selector)
                    if reply_button:
                        buttons['reply'] = reply_button
                        break
                except NoSuchElementException:
                    continue
            
            # Find retweet button
            retweet_selectors = [
                "div[data-testid='retweet']",
                "div[data-testid='unretweet']",
                "button[data-testid='retweet']",
                "button[data-testid='unretweet']",
            ]
            
            for selector in retweet_selectors:
                try:
                    retweet_button = tweet_element.find_element(By.CSS_SELECTOR, selector)
                    if retweet_button:
                        buttons['retweet'] = retweet_button
                        break
                except NoSuchElementException:
                    continue
            
            logger.debug(f"Found {len(buttons)} engagement buttons")
            return buttons
            
        except Exception as e:
            logger.error(f"Error finding engagement buttons: {e}")
            return {}
    
    def _perform_like(self, tweet_data: Dict[str, Any]) -> bool:
        """
        Perform like action on a tweet.
        
        Args:
            tweet_data: Tweet data dictionary
            
        Returns:
            True if like was successful, False otherwise
        """
        try:
            logger.info(f"Attempting to like tweet: {tweet_data['id']}")
            
            # Check for CAPTCHA
            if self.captcha_detection and self._detect_captcha():
                logger.warning("CAPTCHA detected, skipping like action")
                return False
            
            # Find engagement buttons
            buttons = self._find_engagement_buttons()
            if 'like' not in buttons:
                logger.error("Could not find like button")
                return False
            
            like_button = buttons['like']
            
            # Check if already liked
            aria_label = safe_get_attribute(like_button, 'aria-label', '')
            if 'unlike' in aria_label.lower() or 'liked' in aria_label.lower():
                logger.info("Tweet already liked, skipping")
                return True
            
            # Human-like hover before click
            driver = self._get_driver()
            if driver:
                driver.execute_script("arguments[0].scrollIntoView(true);", like_button)
                human_like_delay(0.5, 0.2)
            
            # Click like button
            like_button.click()
            
            # Wait for action to complete
            human_like_delay(random.uniform(*self.click_delay))
            
            # Verify like was successful
            human_like_delay(1, 0.2)
            updated_buttons = self._find_engagement_buttons()
            if 'like' in updated_buttons:
                updated_aria_label = safe_get_attribute(updated_buttons['like'], 'aria-label', '')
                if 'unlike' in updated_aria_label.lower() or 'liked' in updated_aria_label.lower():
                    logger.info(f"Successfully liked tweet: {tweet_data['id']}")
                    self.engagement_stats['likes'] += 1
                    return True
            
            logger.warning("Like action may have failed")
            return False
            
        except ElementClickInterceptedException:
            logger.warning("Like button click was intercepted")
            return False
        except Exception as e:
            logger.error(f"Error liking tweet: {e}")
            self.engagement_stats['errors'] += 1
            return False
    
    def _perform_reply(self, tweet_data: Dict[str, Any], reply_text: Optional[str] = None) -> bool:
        """
        Perform reply action on a tweet.
        
        Args:
            tweet_data: Tweet data dictionary
            reply_text: Reply text (if None, will be generated)
            
        Returns:
            True if reply was successful, False otherwise
        """
        try:
            logger.info(f"Attempting to reply to tweet: {tweet_data['id']}")
            
            # Check for CAPTCHA
            if self.captcha_detection and self._detect_captcha():
                logger.warning("CAPTCHA detected, skipping reply action")
                return False
            
            # Generate reply text if not provided
            if not reply_text:
                reply_text = get_contextual_reply(tweet_data.get('text', ''))
            
            if not reply_text:
                logger.error("No reply text available")
                return False
            
            # Find engagement buttons
            buttons = self._find_engagement_buttons()
            if 'reply' not in buttons:
                logger.error("Could not find reply button")
                return False
            
            reply_button = buttons['reply']
            
            # Click reply button
            reply_button.click()
            human_like_delay(2, 0.5)
            
            # Find reply text box
            reply_selectors = [
                "div[data-testid='tweetTextarea_0']",
                "div[contenteditable='true']",
                "textarea[placeholder*='reply']",
                "div[role='textbox']",
            ]
            
            reply_box = None
            for selector in reply_selectors:
                try:
                    reply_box = WebDriverWait(self._get_driver(), 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue
            
            if not reply_box:
                logger.error("Could not find reply text box")
                return False
            
            # Focus on reply box
            reply_box.click()
            human_like_delay(0.5, 0.2)
            
            # Type reply with human-like typing
            for char in reply_text:
                reply_box.send_keys(char)
                human_like_delay(random.uniform(*self.typing_delay))
                
                # Random pause mid-typing (like humans do)
                if random.random() < 0.05:  # 5% chance
                    human_like_delay(1, 0.5)
            
            # Wait before sending
            human_like_delay(2, 0.5)
            
            # Find and click send button
            send_selectors = [
                "div[data-testid='tweetButtonInline']",
                "button[data-testid='tweetButtonInline']",
                "div[data-testid='tweetButton']",
                "button[data-testid='tweetButton']",
            ]
            
            send_button = None
            for selector in send_selectors:
                try:
                    send_button = self._get_driver().find_element(By.CSS_SELECTOR, selector)
                    if send_button.is_enabled():
                        break
                except NoSuchElementException:
                    continue
            
            if not send_button:
                logger.error("Could not find send button")
                return False
            
            # Click send button
            send_button.click()
            human_like_delay(3, 0.5)
            
            # Check if reply was successful
            # (We could check for success indicators here)
            
            logger.info(f"Successfully replied to tweet: {tweet_data['id']}")
            self.engagement_stats['replies'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Error replying to tweet: {e}")
            self.engagement_stats['errors'] += 1
            return False
    
    def _perform_retweet(self, tweet_data: Dict[str, Any], with_comment: bool = False) -> bool:
        """
        Perform retweet action on a tweet.
        
        Args:
            tweet_data: Tweet data dictionary
            with_comment: Whether to add a comment to the retweet
            
        Returns:
            True if retweet was successful, False otherwise
        """
        try:
            logger.info(f"Attempting to retweet tweet: {tweet_data['id']}")
            
            # Check for CAPTCHA
            if self.captcha_detection and self._detect_captcha():
                logger.warning("CAPTCHA detected, skipping retweet action")
                return False
            
            # Find engagement buttons
            buttons = self._find_engagement_buttons()
            if 'retweet' not in buttons:
                logger.error("Could not find retweet button")
                return False
            
            retweet_button = buttons['retweet']
            
            # Check if already retweeted
            aria_label = safe_get_attribute(retweet_button, 'aria-label', '')
            if 'unretweet' in aria_label.lower() or 'retweeted' in aria_label.lower():
                logger.info("Tweet already retweeted, skipping")
                return True
            
            # Click retweet button
            retweet_button.click()
            human_like_delay(2, 0.5)
            
            # Handle retweet menu
            if with_comment:
                # Look for "Quote Tweet" option
                quote_selectors = [
                    "div[data-testid='Dropdown'] div[role='menuitem']",
                    "div[role='menuitem']",
                ]
                
                for selector in quote_selectors:
                    try:
                        menu_items = self._get_driver().find_elements(By.CSS_SELECTOR, selector)
                        for item in menu_items:
                            item_text = safe_get_text(item)
                            if 'quote' in item_text.lower():
                                item.click()
                                human_like_delay(2, 0.5)
                                
                                # Add comment (similar to reply logic)
                                comment_text = random.choice(self.reply_templates) if self.reply_templates else "Great content!"
                                
                                # Find comment box and type
                                comment_box = self._get_driver().find_element(By.CSS_SELECTOR, "div[data-testid='tweetTextarea_0']")
                                comment_box.click()
                                human_like_delay(0.5, 0.2)
                                
                                for char in comment_text:
                                    comment_box.send_keys(char)
                                    human_like_delay(random.uniform(*self.typing_delay))
                                
                                # Send quote tweet
                                send_button = self._get_driver().find_element(By.CSS_SELECTOR, "div[data-testid='tweetButton']")
                                send_button.click()
                                human_like_delay(3, 0.5)
                                
                                logger.info(f"Successfully quote tweeted: {tweet_data['id']}")
                                self.engagement_stats['retweets'] += 1
                                return True
                    except:
                        continue
            
            else:
                # Look for simple "Retweet" option
                retweet_selectors = [
                    "div[data-testid='Dropdown'] div[role='menuitem']",
                    "div[role='menuitem']",
                ]
                
                for selector in retweet_selectors:
                    try:
                        menu_items = self._get_driver().find_elements(By.CSS_SELECTOR, selector)
                        for item in menu_items:
                            item_text = safe_get_text(item)
                            if 'retweet' in item_text.lower() and 'quote' not in item_text.lower():
                                item.click()
                                human_like_delay(2, 0.5)
                                
                                logger.info(f"Successfully retweeted: {tweet_data['id']}")
                                self.engagement_stats['retweets'] += 1
                                return True
                    except:
                        continue
            
            logger.warning("Retweet action may have failed")
            return False
            
        except Exception as e:
            logger.error(f"Error retweeting tweet: {e}")
            self.engagement_stats['errors'] += 1
            return False
    
    def engage_with_tweet(self, tweet_data: Dict[str, Any], 
                         force_actions: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        Engage with a tweet based on configured probabilities.
        
        Args:
            tweet_data: Tweet data dictionary
            force_actions: List of actions to force (overrides probabilities)
            
        Returns:
            Dictionary with action results
        """
        try:
            logger.info(f"Engaging with tweet: {tweet_data['id']}")
            
            # Navigate to tweet
            if not self._navigate_to_tweet(tweet_data):
                logger.error("Failed to navigate to tweet")
                return {'like': False, 'reply': False, 'retweet': False}
            
            results = {'like': False, 'reply': False, 'retweet': False}
            
            # Determine actions to perform
            if force_actions:
                actions_to_perform = force_actions
            else:
                actions_to_perform = []
                
                # Check probabilities
                if random.random() < self.like_probability:
                    actions_to_perform.append('like')
                
                if random.random() < self.reply_probability:
                    actions_to_perform.append('reply')
                
                if random.random() < self.retweet_probability:
                    actions_to_perform.append('retweet')
            
            logger.info(f"Performing actions: {actions_to_perform}")
            
            # Perform actions in random order (more human-like)
            random.shuffle(actions_to_perform)
            
            for action in actions_to_perform:
                # Check for CAPTCHA before each action
                if self.captcha_detection and self._detect_captcha():
                    logger.warning("CAPTCHA detected, stopping engagement")
                    break
                
                if action == 'like':
                    results['like'] = self._perform_like(tweet_data)
                    
                elif action == 'reply':
                    results['reply'] = self._perform_reply(tweet_data)
                    
                elif action == 'retweet':
                    results['retweet'] = self._perform_retweet(tweet_data)
                
                # Wait between actions
                if len(actions_to_perform) > 1:
                    human_like_delay(random.uniform(2, 5))
            
            # Log engagement results
            successful_actions = [action for action, success in results.items() if success]
            logger.info(f"Engagement completed. Successful actions: {successful_actions}")
            
            # Log performance metrics
            log_performance_metric("engagement_actions", len(successful_actions))
            
            return results
            
        except Exception as e:
            logger.error(f"Error engaging with tweet: {e}")
            self.engagement_stats['errors'] += 1
            return {'like': False, 'reply': False, 'retweet': False}
    
    def bulk_engage(self, tweets: List[Dict[str, Any]], 
                   max_engagements: int = 5) -> List[Dict[str, Any]]:
        """
        Engage with multiple tweets in sequence.
        
        Args:
            tweets: List of tweet data dictionaries
            max_engagements: Maximum number of tweets to engage with
            
        Returns:
            List of engagement results
        """
        try:
            logger.info(f"Starting bulk engagement with {len(tweets)} tweets")
            
            results = []
            engagements_performed = 0
            
            for tweet_data in tweets:
                if engagements_performed >= max_engagements:
                    break
                
                # Engage with tweet
                engagement_result = self.engage_with_tweet(tweet_data)
                
                # Add metadata
                engagement_result['tweet_id'] = tweet_data['id']
                engagement_result['timestamp'] = get_current_timestamp()
                engagement_result['engagement_score'] = tweet_data.get('engagement_score', 0.0)
                
                results.append(engagement_result)
                
                # Check if any action was successful
                if any(engagement_result.values()):
                    engagements_performed += 1
                
                # Human-like delay between tweets
                if engagements_performed < max_engagements:
                    human_like_delay(random.uniform(60, 180))  # 1-3 minutes between tweets
            
            logger.info(f"Bulk engagement completed. Performed {engagements_performed} engagements")
            return results
            
        except Exception as e:
            logger.error(f"Error in bulk engagement: {e}")
            return []
    
    def get_engagement_statistics(self) -> Dict[str, Any]:
        """
        Get engagement statistics.
        
        Returns:
            Dictionary with engagement statistics
        """
        try:
            total_actions = sum(self.engagement_stats.values()) - self.engagement_stats['errors']
            
            stats = {
                'total_actions': total_actions,
                'successful_actions': total_actions - self.engagement_stats['errors'],
                'likes': self.engagement_stats['likes'],
                'replies': self.engagement_stats['replies'],
                'retweets': self.engagement_stats['retweets'],
                'errors': self.engagement_stats['errors'],
                'captcha_encounters': self.engagement_stats['captcha_encounters'],
                'success_rate': 0.0,
                'error_rate': 0.0,
            }
            
            if total_actions > 0:
                stats['success_rate'] = ((total_actions - self.engagement_stats['errors']) / total_actions) * 100
                stats['error_rate'] = (self.engagement_stats['errors'] / total_actions) * 100
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting engagement statistics: {e}")
            return {}
    
    def reset_statistics(self) -> None:
        """Reset engagement statistics."""
        self.engagement_stats = {
            'likes': 0,
            'replies': 0,
            'retweets': 0,
            'errors': 0,
            'captcha_encounters': 0,
        }
        logger.info("Engagement statistics reset")

def create_engagement_engine(config: Dict[str, Any], cookie_manager) -> EngagementEngine:
    """
    Create and initialize an engagement engine.
    
    Args:
        config: Configuration dictionary
        cookie_manager: Cookie manager instance
        
    Returns:
        Initialized EngagementEngine instance
    """
    return EngagementEngine(config, cookie_manager)