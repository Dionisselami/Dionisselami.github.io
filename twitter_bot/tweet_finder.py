"""
Tweet discovery and selection system for the Twitter bot.
Finds and selects tweets based on engagement metrics and criteria.
"""

import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from .utils import (
    human_like_delay, parse_engagement_numbers, clean_tweet_text,
    extract_tweet_id, safe_get_text, safe_get_attribute,
    calculate_weighted_choice, contains_blocked_keywords,
    get_tweet_age_hours, log_performance_metric
)
from .config import get_weighted_search_query, should_engage_with_tweet, get_engagement_score

logger = logging.getLogger(__name__)

class TweetFinder:
    """
    Discovers and selects tweets for engagement based on various criteria.
    """
    
    def __init__(self, config: Dict[str, Any], cookie_manager):
        """
        Initialize tweet finder.
        
        Args:
            config: Configuration dictionary
            cookie_manager: Cookie manager instance
        """
        self.config = config
        self.cookie_manager = cookie_manager
        self.search_config = config.get('search', {})
        self.safety_config = config.get('safety', {})
        self.behavior_config = config.get('behavior', {})
        
        # Search settings
        self.queries = self.search_config.get('queries', [])
        self.min_likes = self.search_config.get('min_likes', 5)
        self.max_likes = self.search_config.get('max_likes', 10000)
        self.min_replies = self.search_config.get('min_replies', 0)
        self.max_replies = self.search_config.get('max_replies', 100)
        self.age_limit_hours = self.search_config.get('age_limit_hours', 24)
        
        # Safety settings
        self.avoid_own_content = self.safety_config.get('avoid_own_content', True)
        self.avoid_sensitive = self.safety_config.get('avoid_sensitive', True)
        self.blocked_keywords = self.safety_config.get('blocked_keywords', [])
        
        # Tracking
        self.seen_tweets = set()
        self.rejected_tweets = set()
        self.engagement_history = []
        
        # URLs
        self.search_url = "https://twitter.com/search"
        self.explore_url = "https://twitter.com/explore"
        self.trending_url = "https://twitter.com/explore/tabs/trending"
        
        logger.info("Tweet finder initialized")
    
    def _get_driver(self) -> Optional[webdriver.Chrome]:
        """Get WebDriver instance from cookie manager."""
        return self.cookie_manager.get_driver()
    
    def _perform_search(self, query: str, result_type: str = "latest") -> bool:
        """
        Perform a search on Twitter.
        
        Args:
            query: Search query
            result_type: Type of results ('latest', 'top', 'people', 'photos', 'videos')
            
        Returns:
            True if search was successful, False otherwise
        """
        try:
            driver = self._get_driver()
            if not driver:
                logger.error("No driver available for search")
                return False
            
            logger.info(f"Searching for: {query}")
            
            # Navigate to search page
            search_url = f"{self.search_url}?q={query.replace(' ', '%20')}&src=typed_query"
            if result_type != "latest":
                search_url += f"&f={result_type}"
            
            driver.get(search_url)
            human_like_delay(3, 0.5)
            
            # Wait for search results to load
            wait = WebDriverWait(driver, 15)
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='tweet']")))
                logger.info("Search results loaded successfully")
                return True
            except TimeoutException:
                logger.warning("Search results took too long to load")
                return False
            
        except Exception as e:
            logger.error(f"Error performing search: {e}")
            return False
    
    def _scroll_to_load_tweets(self, scroll_count: int = 3) -> None:
        """
        Scroll down to load more tweets.
        
        Args:
            scroll_count: Number of scroll actions to perform
        """
        try:
            driver = self._get_driver()
            if not driver:
                return
            
            logger.debug(f"Scrolling to load more tweets ({scroll_count} scrolls)")
            
            for i in range(scroll_count):
                # Scroll down
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                human_like_delay(2, 0.5)
                
                # Random human-like scroll behavior
                if random.random() < 0.3:  # 30% chance
                    # Scroll up a bit (like humans do)
                    driver.execute_script("window.scrollBy(0, -200);")
                    human_like_delay(1, 0.2)
                    
                    # Then scroll back down
                    driver.execute_script("window.scrollBy(0, 300);")
                    human_like_delay(1, 0.2)
            
        except Exception as e:
            logger.error(f"Error scrolling: {e}")
    
    def _extract_tweet_data(self, tweet_element) -> Optional[Dict[str, Any]]:
        """
        Extract data from a tweet element.
        
        Args:
            tweet_element: WebElement representing a tweet
            
        Returns:
            Dictionary with tweet data or None if extraction failed
        """
        try:
            # Extract tweet text
            text_selectors = [
                "div[data-testid='tweetText']",
                "div[lang]",
                "span[data-testid='tweetText']",
            ]
            
            tweet_text = ""
            for selector in text_selectors:
                try:
                    text_element = tweet_element.find_element(By.CSS_SELECTOR, selector)
                    tweet_text = safe_get_text(text_element)
                    if tweet_text:
                        break
                except NoSuchElementException:
                    continue
            
            if not tweet_text:
                logger.debug("Could not extract tweet text")
                return None
            
            # Extract tweet URL/ID
            link_selectors = [
                "a[href*='/status/']",
                "time[datetime] a",
                "a[role='link']",
            ]
            
            tweet_url = ""
            for selector in link_selectors:
                try:
                    link_element = tweet_element.find_element(By.CSS_SELECTOR, selector)
                    tweet_url = safe_get_attribute(link_element, 'href')
                    if tweet_url and '/status/' in tweet_url:
                        break
                except NoSuchElementException:
                    continue
            
            tweet_id = extract_tweet_id(tweet_url) if tweet_url else None
            
            # Extract engagement metrics
            engagement_selectors = [
                "div[data-testid='reply']",
                "div[data-testid='retweet']",
                "div[data-testid='like']",
                "div[data-testid='unretweet']",
                "div[data-testid='unlike']",
            ]
            
            likes = 0
            replies = 0
            retweets = 0
            
            for selector in engagement_selectors:
                try:
                    elements = tweet_element.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        aria_label = safe_get_attribute(element, 'aria-label', '')
                        
                        if 'like' in aria_label.lower():
                            likes = parse_engagement_numbers(aria_label)
                        elif 'repl' in aria_label.lower():
                            replies = parse_engagement_numbers(aria_label)
                        elif 'retweet' in aria_label.lower():
                            retweets = parse_engagement_numbers(aria_label)
                except:
                    continue
            
            # Extract author information
            author_selectors = [
                "div[data-testid='User-Name'] a",
                "div[data-testid='User-Names'] a",
                "a[role='link'][href*='/']",
            ]
            
            author_username = ""
            author_name = ""
            
            for selector in author_selectors:
                try:
                    author_element = tweet_element.find_element(By.CSS_SELECTOR, selector)
                    href = safe_get_attribute(author_element, 'href', '')
                    if href and href.count('/') >= 3:
                        author_username = href.split('/')[-1]
                        author_name = safe_get_text(author_element)
                        break
                except NoSuchElementException:
                    continue
            
            # Extract timestamp
            time_selectors = [
                "time[datetime]",
                "a[href*='/status/'] time",
            ]
            
            timestamp = None
            for selector in time_selectors:
                try:
                    time_element = tweet_element.find_element(By.CSS_SELECTOR, selector)
                    datetime_attr = safe_get_attribute(time_element, 'datetime')
                    if datetime_attr:
                        timestamp = datetime_attr
                        break
                except NoSuchElementException:
                    continue
            
            # Calculate tweet age
            tweet_age_hours = get_tweet_age_hours(timestamp) if timestamp else None
            
            # Compile tweet data
            tweet_data = {
                'id': tweet_id,
                'text': clean_tweet_text(tweet_text),
                'url': tweet_url,
                'likes': likes,
                'replies': replies,
                'retweets': retweets,
                'author_username': author_username,
                'author_name': author_name,
                'timestamp': timestamp,
                'age_hours': tweet_age_hours,
                'engagement_score': 0.0,
                'extracted_at': datetime.now().isoformat(),
            }
            
            # Calculate engagement score
            tweet_data['engagement_score'] = get_engagement_score(tweet_data)
            
            return tweet_data
            
        except StaleElementReferenceException:
            logger.debug("Tweet element became stale during extraction")
            return None
        except Exception as e:
            logger.error(f"Error extracting tweet data: {e}")
            return None
    
    def _is_tweet_suitable(self, tweet_data: Dict[str, Any]) -> bool:
        """
        Check if a tweet meets the criteria for engagement.
        
        Args:
            tweet_data: Tweet data dictionary
            
        Returns:
            True if tweet is suitable, False otherwise
        """
        try:
            # Check if we've seen this tweet before
            if tweet_data['id'] in self.seen_tweets:
                logger.debug(f"Tweet {tweet_data['id']} already seen")
                return False
            
            # Check if we've rejected this tweet before
            if tweet_data['id'] in self.rejected_tweets:
                logger.debug(f"Tweet {tweet_data['id']} was previously rejected")
                return False
            
            # Check if it's our own content
            if self.avoid_own_content and tweet_data['author_username']:
                # Would need to check against bot's username
                # For now, skip tweets with no username
                pass
            
            # Check engagement thresholds
            if not should_engage_with_tweet(tweet_data):
                logger.debug(f"Tweet {tweet_data['id']} doesn't meet engagement criteria")
                self.rejected_tweets.add(tweet_data['id'])
                return False
            
            # Check for blocked keywords
            if contains_blocked_keywords(tweet_data['text'], self.blocked_keywords):
                logger.debug(f"Tweet {tweet_data['id']} contains blocked keywords")
                self.rejected_tweets.add(tweet_data['id'])
                return False
            
            # Check tweet age
            if tweet_data['age_hours'] is not None and tweet_data['age_hours'] > self.age_limit_hours:
                logger.debug(f"Tweet {tweet_data['id']} is too old ({tweet_data['age_hours']} hours)")
                self.rejected_tweets.add(tweet_data['id'])
                return False
            
            # Check for sensitive content indicators
            if self.avoid_sensitive:
                sensitive_indicators = [
                    'sensitive content',
                    'potentially sensitive',
                    'content warning',
                    'trigger warning',
                ]
                
                text_lower = tweet_data['text'].lower()
                for indicator in sensitive_indicators:
                    if indicator in text_lower:
                        logger.debug(f"Tweet {tweet_data['id']} contains sensitive content")
                        self.rejected_tweets.add(tweet_data['id'])
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking tweet suitability: {e}")
            return False
    
    def find_tweets(self, query: Optional[str] = None, count: int = 10) -> List[Dict[str, Any]]:
        """
        Find tweets based on search criteria.
        
        Args:
            query: Search query (if None, uses weighted random selection)
            count: Number of tweets to find
            
        Returns:
            List of tweet data dictionaries
        """
        try:
            # Select query if not provided
            if not query:
                query = get_weighted_search_query()
            
            logger.info(f"Finding tweets for query: {query}")
            
            # Perform search
            if not self._perform_search(query):
                logger.error("Failed to perform search")
                return []
            
            # Scroll to load more tweets
            self._scroll_to_load_tweets(3)
            
            # Extract tweets
            driver = self._get_driver()
            if not driver:
                return []
            
            # Find tweet elements
            tweet_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='tweet']")
            logger.info(f"Found {len(tweet_elements)} tweet elements")
            
            suitable_tweets = []
            
            for i, tweet_element in enumerate(tweet_elements):
                if len(suitable_tweets) >= count:
                    break
                
                try:
                    # Extract tweet data
                    tweet_data = self._extract_tweet_data(tweet_element)
                    if not tweet_data:
                        continue
                    
                    # Check if tweet is suitable
                    if self._is_tweet_suitable(tweet_data):
                        suitable_tweets.append(tweet_data)
                        self.seen_tweets.add(tweet_data['id'])
                        logger.debug(f"Added suitable tweet: {tweet_data['id']}")
                    
                    # Add small delay between extractions
                    if i % 5 == 0:
                        human_like_delay(1, 0.2)
                        
                except Exception as e:
                    logger.error(f"Error processing tweet element {i}: {e}")
                    continue
            
            logger.info(f"Found {len(suitable_tweets)} suitable tweets out of {len(tweet_elements)} total")
            
            # Log performance metrics
            log_performance_metric("tweets_found", len(suitable_tweets))
            log_performance_metric("tweets_processed", len(tweet_elements))
            
            return suitable_tweets
            
        except Exception as e:
            logger.error(f"Error finding tweets: {e}")
            return []
    
    def select_best_tweet(self, tweets: List[Dict[str, Any]], 
                         selection_method: str = "weighted_random") -> Optional[Dict[str, Any]]:
        """
        Select the best tweet from a list based on engagement score.
        
        Args:
            tweets: List of tweet data dictionaries
            selection_method: Method for selection ('weighted_random', 'highest_score', 'random')
            
        Returns:
            Selected tweet data or None if no suitable tweet found
        """
        try:
            if not tweets:
                return None
            
            logger.info(f"Selecting best tweet from {len(tweets)} candidates using {selection_method}")
            
            if selection_method == "random":
                selected = random.choice(tweets)
                
            elif selection_method == "highest_score":
                selected = max(tweets, key=lambda t: t['engagement_score'])
                
            elif selection_method == "weighted_random":
                # Create weighted list based on engagement scores
                weighted_tweets = [(tweet, max(0.1, tweet['engagement_score'])) for tweet in tweets]
                selected = calculate_weighted_choice(weighted_tweets)
                
            else:
                logger.warning(f"Unknown selection method: {selection_method}, using random")
                selected = random.choice(tweets)
            
            if selected:
                logger.info(f"Selected tweet {selected['id']} with engagement score {selected['engagement_score']:.2f}")
                
                # Add to engagement history
                self.engagement_history.append({
                    'tweet_id': selected['id'],
                    'engagement_score': selected['engagement_score'],
                    'selected_at': datetime.now().isoformat(),
                    'selection_method': selection_method,
                })
                
                # Keep only last 1000 entries
                if len(self.engagement_history) > 1000:
                    self.engagement_history = self.engagement_history[-1000:]
            
            return selected
            
        except Exception as e:
            logger.error(f"Error selecting best tweet: {e}")
            return None
    
    def find_trending_tweets(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Find tweets from trending topics.
        
        Args:
            count: Number of tweets to find
            
        Returns:
            List of tweet data dictionaries
        """
        try:
            logger.info("Finding trending tweets")
            
            driver = self._get_driver()
            if not driver:
                return []
            
            # Navigate to trending page
            driver.get(self.trending_url)
            human_like_delay(3, 0.5)
            
            # Find trending topics
            trending_selectors = [
                "div[data-testid='trend']",
                "div[data-testid='trendingTopic']",
                "span[data-testid='trendingTopic']",
            ]
            
            trending_topics = []
            for selector in trending_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        topic_text = safe_get_text(element)
                        if topic_text and topic_text not in trending_topics:
                            trending_topics.append(topic_text)
                except:
                    continue
            
            logger.info(f"Found {len(trending_topics)} trending topics")
            
            # Select random trending topics and search for tweets
            all_tweets = []
            selected_topics = random.sample(trending_topics, min(3, len(trending_topics)))
            
            for topic in selected_topics:
                topic_tweets = self.find_tweets(topic, count // len(selected_topics))
                all_tweets.extend(topic_tweets)
                
                if len(all_tweets) >= count:
                    break
            
            return all_tweets[:count]
            
        except Exception as e:
            logger.error(f"Error finding trending tweets: {e}")
            return []
    
    def find_random_tweets(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Find random tweets using various search strategies.
        
        Args:
            count: Number of tweets to find
            
        Returns:
            List of tweet data dictionaries
        """
        try:
            logger.info("Finding random tweets")
            
            all_tweets = []
            
            # Strategy 1: Use configured search queries
            if self.queries:
                query = get_weighted_search_query()
                tweets = self.find_tweets(query, count // 2)
                all_tweets.extend(tweets)
            
            # Strategy 2: Find trending tweets
            if len(all_tweets) < count:
                trending_tweets = self.find_trending_tweets(count - len(all_tweets))
                all_tweets.extend(trending_tweets)
            
            # Strategy 3: Use random popular hashtags
            if len(all_tweets) < count:
                popular_hashtags = [
                    "#technology", "#programming", "#AI", "#MachineLearning",
                    "#WebDevelopment", "#JavaScript", "#Python", "#React",
                    "#TechNews", "#Innovation", "#Startup", "#OpenSource"
                ]
                
                hashtag = random.choice(popular_hashtags)
                hashtag_tweets = self.find_tweets(hashtag, count - len(all_tweets))
                all_tweets.extend(hashtag_tweets)
            
            # Remove duplicates
            seen_ids = set()
            unique_tweets = []
            for tweet in all_tweets:
                if tweet['id'] not in seen_ids:
                    unique_tweets.append(tweet)
                    seen_ids.add(tweet['id'])
            
            logger.info(f"Found {len(unique_tweets)} unique random tweets")
            return unique_tweets[:count]
            
        except Exception as e:
            logger.error(f"Error finding random tweets: {e}")
            return []
    
    def get_tweet_context(self, tweet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get additional context for a tweet (replies, author info, etc.).
        
        Args:
            tweet_data: Tweet data dictionary
            
        Returns:
            Dictionary with additional context
        """
        try:
            if not tweet_data['url']:
                return {}
            
            driver = self._get_driver()
            if not driver:
                return {}
            
            logger.debug(f"Getting context for tweet {tweet_data['id']}")
            
            # Navigate to tweet page
            driver.get(tweet_data['url'])
            human_like_delay(3, 0.5)
            
            context = {}
            
            # Get author follower count
            try:
                author_link = driver.find_element(By.CSS_SELECTOR, "div[data-testid='User-Names'] a")
                author_link.click()
                human_like_delay(2, 0.3)
                
                follower_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='/followers']")
                for element in follower_elements:
                    follower_text = safe_get_text(element)
                    if follower_text:
                        context['author_followers'] = parse_engagement_numbers(follower_text)
                        break
                
                # Go back to tweet
                driver.back()
                human_like_delay(2, 0.3)
                
            except Exception as e:
                logger.debug(f"Could not get author followers: {e}")
            
            # Get reply count and samples
            try:
                reply_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='tweet']")
                if len(reply_elements) > 1:  # First is the main tweet
                    context['reply_count'] = len(reply_elements) - 1
                    context['has_replies'] = True
                else:
                    context['reply_count'] = 0
                    context['has_replies'] = False
                
            except Exception as e:
                logger.debug(f"Could not get reply context: {e}")
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting tweet context: {e}")
            return {}
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about tweet finding activity.
        
        Returns:
            Dictionary with statistics
        """
        try:
            stats = {
                'tweets_seen': len(self.seen_tweets),
                'tweets_rejected': len(self.rejected_tweets),
                'engagement_history_count': len(self.engagement_history),
                'average_engagement_score': 0.0,
                'rejection_rate': 0.0,
            }
            
            # Calculate average engagement score
            if self.engagement_history:
                total_score = sum(entry['engagement_score'] for entry in self.engagement_history)
                stats['average_engagement_score'] = total_score / len(self.engagement_history)
            
            # Calculate rejection rate
            total_processed = len(self.seen_tweets) + len(self.rejected_tweets)
            if total_processed > 0:
                stats['rejection_rate'] = (len(self.rejected_tweets) / total_processed) * 100
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
    
    def clear_history(self) -> None:
        """Clear seen and rejected tweet history."""
        self.seen_tweets.clear()
        self.rejected_tweets.clear()
        self.engagement_history.clear()
        logger.info("Tweet finder history cleared")

def create_tweet_finder(config: Dict[str, Any], cookie_manager) -> TweetFinder:
    """
    Create and initialize a tweet finder.
    
    Args:
        config: Configuration dictionary
        cookie_manager: Cookie manager instance
        
    Returns:
        Initialized TweetFinder instance
    """
    return TweetFinder(config, cookie_manager)