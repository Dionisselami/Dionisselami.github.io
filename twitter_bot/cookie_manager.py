"""
Cookie management system for Twitter bot authentication.
Handles cookie-based authentication without requiring API keys.
"""

import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import TimeoutException, WebDriverException

from .utils import (
    load_json_file, save_json_file, human_like_delay, 
    get_random_user_agent, get_current_timestamp, 
    parse_timestamp, retry_with_backoff
)

logger = logging.getLogger(__name__)

class CookieManager:
    """
    Manages Twitter authentication cookies and session handling.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize cookie manager.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.auth_config = config.get('auth', {})
        self.browser_config = config.get('browser', {})
        self.safety_config = config.get('safety', {})
        
        self.cookie_file = self.auth_config.get('cookie_file', 'twitter_cookies.json')
        self.refresh_interval = self.auth_config.get('refresh_interval', 3600)
        self.username = self.auth_config.get('username', '')
        self.password = self.auth_config.get('password', '')
        
        self.driver = None
        self.cookies = {}
        self.session_data = {}
        self.last_refresh = None
        
        # URLs
        self.login_url = "https://twitter.com/login"
        self.home_url = "https://twitter.com/home"
        self.test_url = "https://twitter.com/explore"
        
    def _create_driver(self) -> webdriver.Chrome:
        """
        Create and configure WebDriver instance.
        
        Returns:
            Configured WebDriver instance
        """
        browser_type = self.browser_config.get('type', 'chrome').lower()
        headless = self.browser_config.get('headless', False)
        timeout = self.browser_config.get('timeout', 30)
        user_agents = self.browser_config.get('user_agents', [])
        
        try:
            if browser_type == 'chrome':
                options = ChromeOptions()
                
                # Basic options
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--disable-web-security')
                options.add_argument('--disable-features=VizDisplayCompositor')
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                
                # Anti-detection measures
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-plugins')
                options.add_argument('--disable-images')
                options.add_argument('--disable-javascript')
                options.add_argument('--disable-default-apps')
                
                # User agent
                if user_agents:
                    user_agent = get_random_user_agent(user_agents)
                    options.add_argument(f'--user-agent={user_agent}')
                
                # Headless mode
                if headless:
                    options.add_argument('--headless')
                
                # Window size
                options.add_argument('--window-size=1920,1080')
                
                driver = webdriver.Chrome(options=options)
                
            elif browser_type == 'firefox':
                options = FirefoxOptions()
                
                # Basic options
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                
                # User agent
                if user_agents:
                    user_agent = get_random_user_agent(user_agents)
                    options.set_preference("general.useragent.override", user_agent)
                
                # Headless mode
                if headless:
                    options.add_argument('--headless')
                
                driver = webdriver.Firefox(options=options)
                
            else:
                raise ValueError(f"Unsupported browser type: {browser_type}")
            
            # Set timeouts
            driver.set_page_load_timeout(timeout)
            driver.implicitly_wait(timeout)
            
            # Anti-detection
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info(f"Created {browser_type} driver successfully")
            return driver
            
        except Exception as e:
            logger.error(f"Failed to create driver: {e}")
            raise
    
    def _load_cookies(self) -> bool:
        """
        Load cookies from file.
        
        Returns:
            True if cookies loaded successfully, False otherwise
        """
        try:
            cookie_data = load_json_file(self.cookie_file)
            if not cookie_data:
                logger.info("No saved cookies found")
                return False
            
            self.cookies = cookie_data.get('cookies', {})
            self.session_data = cookie_data.get('session_data', {})
            
            # Check if cookies are expired
            last_updated = cookie_data.get('last_updated')
            if last_updated:
                last_update_time = parse_timestamp(last_updated)
                if last_update_time:
                    age_hours = (datetime.now() - last_update_time).total_seconds() / 3600
                    if age_hours > 24:  # Cookies older than 24 hours
                        logger.warning(f"Cookies are {age_hours:.1f} hours old, may need refresh")
            
            logger.info(f"Loaded {len(self.cookies)} cookies from file")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            return False
    
    def _save_cookies(self) -> bool:
        """
        Save cookies to file.
        
        Returns:
            True if cookies saved successfully, False otherwise
        """
        try:
            cookie_data = {
                'cookies': self.cookies,
                'session_data': self.session_data,
                'last_updated': get_current_timestamp(),
            }
            
            success = save_json_file(self.cookie_file, cookie_data)
            if success:
                logger.info(f"Saved {len(self.cookies)} cookies to file")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")
            return False
    
    def _extract_cookies_from_driver(self) -> Dict[str, Any]:
        """
        Extract cookies from WebDriver.
        
        Returns:
            Dictionary of cookies
        """
        try:
            if not self.driver:
                return {}
            
            cookies = {}
            for cookie in self.driver.get_cookies():
                cookies[cookie['name']] = cookie['value']
            
            # Extract important session data
            self.session_data = {
                'user_agent': self.driver.execute_script("return navigator.userAgent"),
                'current_url': self.driver.current_url,
                'timestamp': get_current_timestamp(),
            }
            
            logger.info(f"Extracted {len(cookies)} cookies from driver")
            return cookies
            
        except Exception as e:
            logger.error(f"Failed to extract cookies: {e}")
            return {}
    
    def _apply_cookies_to_driver(self) -> bool:
        """
        Apply saved cookies to WebDriver.
        
        Returns:
            True if cookies applied successfully, False otherwise
        """
        try:
            if not self.driver or not self.cookies:
                return False
            
            # Navigate to Twitter first
            self.driver.get("https://twitter.com")
            human_like_delay(2, 0.5)
            
            # Add cookies
            for name, value in self.cookies.items():
                try:
                    self.driver.add_cookie({
                        'name': name,
                        'value': value,
                        'domain': '.twitter.com',
                        'path': '/',
                    })
                except Exception as e:
                    logger.debug(f"Failed to add cookie {name}: {e}")
            
            logger.info(f"Applied {len(self.cookies)} cookies to driver")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply cookies: {e}")
            return False
    
    def _perform_login(self) -> bool:
        """
        Perform manual login to Twitter.
        
        Returns:
            True if login successful, False otherwise
        """
        try:
            if not self.username or not self.password:
                logger.error("Username and password required for login")
                return False
            
            logger.info("Attempting login to Twitter...")
            
            # Navigate to login page
            self.driver.get(self.login_url)
            human_like_delay(3, 0.5)
            
            # Wait for login form
            wait = WebDriverWait(self.driver, 20)
            
            # Find username field
            username_selectors = [
                "input[name='text']",
                "input[autocomplete='username']",
                "input[data-testid='ocfEnterTextTextInput']",
                "input[type='text']",
            ]
            
            username_field = None
            for selector in username_selectors:
                try:
                    username_field = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue
            
            if not username_field:
                logger.error("Could not find username field")
                return False
            
            # Enter username
            username_field.clear()
            for char in self.username:
                username_field.send_keys(char)
                human_like_delay(0.1, 0.1)
            
            human_like_delay(1, 0.2)
            
            # Click next button
            next_button_selectors = [
                "div[data-testid='LoginForm_Login_Button']",
                "button[role='button']",
                "div[role='button']",
            ]
            
            next_button = None
            for selector in next_button_selectors:
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if next_button.is_enabled():
                        break
                except:
                    continue
            
            if next_button:
                next_button.click()
                human_like_delay(2, 0.5)
            
            # Find password field
            password_selectors = [
                "input[name='password']",
                "input[type='password']",
                "input[autocomplete='current-password']",
            ]
            
            password_field = None
            for selector in password_selectors:
                try:
                    password_field = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue
            
            if not password_field:
                logger.error("Could not find password field")
                return False
            
            # Enter password
            password_field.clear()
            for char in self.password:
                password_field.send_keys(char)
                human_like_delay(0.1, 0.1)
            
            human_like_delay(1, 0.2)
            
            # Click login button
            login_button_selectors = [
                "div[data-testid='LoginForm_Login_Button']",
                "button[data-testid='LoginForm_Login_Button']",
                "div[role='button']",
            ]
            
            login_button = None
            for selector in login_button_selectors:
                try:
                    login_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if login_button.is_enabled():
                        break
                except:
                    continue
            
            if login_button:
                login_button.click()
                human_like_delay(5, 1)
            
            # Check if login was successful
            if self._is_logged_in():
                logger.info("Login successful!")
                return True
            else:
                logger.error("Login failed - not redirected to home page")
                return False
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    def _is_logged_in(self) -> bool:
        """
        Check if user is logged in to Twitter.
        
        Returns:
            True if logged in, False otherwise
        """
        try:
            if not self.driver:
                return False
            
            # Check current URL
            current_url = self.driver.current_url
            if 'twitter.com/home' in current_url or 'twitter.com/explore' in current_url:
                return True
            
            # Check for login indicators
            login_indicators = [
                "div[data-testid='SideNav_NewTweet_Button']",
                "div[data-testid='AppTabBar_Home_Link']",
                "div[aria-label='Home timeline']",
                "header[role='banner']",
            ]
            
            for selector in login_indicators:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check login status: {e}")
            return False
    
    def _detect_captcha(self) -> bool:
        """
        Detect if CAPTCHA is present on the page.
        
        Returns:
            True if CAPTCHA detected, False otherwise
        """
        try:
            if not self.driver:
                return False
            
            captcha_indicators = [
                "div[data-testid='ocfEnterTextTextInput']",
                "iframe[title*='captcha']",
                "div[class*='captcha']",
                "div[class*='challenge']",
            ]
            
            for selector in captcha_indicators:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        logger.warning("CAPTCHA detected on page")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to detect CAPTCHA: {e}")
            return False
    
    def initialize_session(self) -> bool:
        """
        Initialize Twitter session with cookies or login.
        
        Returns:
            True if session initialized successfully, False otherwise
        """
        try:
            logger.info("Initializing Twitter session...")
            
            # Create driver
            self.driver = self._create_driver()
            
            # Load saved cookies
            cookies_loaded = self._load_cookies()
            
            if cookies_loaded:
                # Try to use saved cookies
                if self._apply_cookies_to_driver():
                    # Navigate to home page to test cookies
                    self.driver.get(self.home_url)
                    human_like_delay(3, 0.5)
                    
                    if self._is_logged_in():
                        logger.info("Successfully authenticated with saved cookies")
                        self.last_refresh = datetime.now()
                        return True
                    else:
                        logger.warning("Saved cookies are invalid, attempting login")
            
            # If cookies failed or not available, perform login
            if self._perform_login():
                # Extract and save new cookies
                self.cookies = self._extract_cookies_from_driver()
                self._save_cookies()
                self.last_refresh = datetime.now()
                return True
            
            logger.error("Failed to initialize session")
            return False
            
        except Exception as e:
            logger.error(f"Failed to initialize session: {e}")
            return False
    
    def refresh_session(self) -> bool:
        """
        Refresh the current session.
        
        Returns:
            True if session refreshed successfully, False otherwise
        """
        try:
            if not self.driver:
                return self.initialize_session()
            
            logger.info("Refreshing Twitter session...")
            
            # Test current session
            self.driver.get(self.test_url)
            human_like_delay(3, 0.5)
            
            if self._is_logged_in():
                # Update cookies
                self.cookies = self._extract_cookies_from_driver()
                self._save_cookies()
                self.last_refresh = datetime.now()
                logger.info("Session refreshed successfully")
                return True
            else:
                logger.warning("Session is invalid, reinitializing...")
                return self.initialize_session()
            
        except Exception as e:
            logger.error(f"Failed to refresh session: {e}")
            return False
    
    def is_session_valid(self) -> bool:
        """
        Check if current session is valid.
        
        Returns:
            True if session is valid, False otherwise
        """
        try:
            if not self.driver:
                return False
            
            # Check if we need to refresh based on time
            if self.last_refresh:
                age_seconds = (datetime.now() - self.last_refresh).total_seconds()
                if age_seconds > self.refresh_interval:
                    logger.info("Session refresh interval reached")
                    return False
            
            # Test if we're still logged in
            current_url = self.driver.current_url
            if 'login' in current_url or 'logout' in current_url:
                return False
            
            return self._is_logged_in()
            
        except Exception as e:
            logger.error(f"Failed to check session validity: {e}")
            return False
    
    def get_driver(self) -> Optional[webdriver.Chrome]:
        """
        Get the WebDriver instance.
        
        Returns:
            WebDriver instance or None if not initialized
        """
        return self.driver
    
    def close_session(self) -> None:
        """
        Close the current session and clean up resources.
        """
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                logger.info("Session closed successfully")
        except Exception as e:
            logger.error(f"Error closing session: {e}")
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        Get current session information.
        
        Returns:
            Dictionary with session information
        """
        return {
            'cookies_count': len(self.cookies),
            'last_refresh': self.last_refresh.isoformat() if self.last_refresh else None,
            'session_valid': self.is_session_valid(),
            'driver_available': self.driver is not None,
            'session_data': self.session_data,
        }
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_session()

def create_cookie_manager(config: Dict[str, Any]) -> CookieManager:
    """
    Create and initialize a cookie manager.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Initialized CookieManager instance
    """
    return CookieManager(config)