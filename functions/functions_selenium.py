"""
Utility functions for Selenium browser automation and web interaction.
Module provides browser setup, navigation, and page interaction functions.
"""
from typing import Tuple, List, Optional
import random
import time
from dataclasses import dataclass
from contextlib import contextmanager

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium_stealth import stealth
from fake_useragent import UserAgent
from webdriver_manager.chrome import ChromeDriverManager

# Type aliases
Driver = webdriver.Chrome
LogEntry = dict
ChromeCapabilities = dict

# Constants
SCREEN_SIZES: List[str] = [
    "1024x768",
    "1280x800", 
    "1366x768",
    "1440x900",
    "1920x1080",
    "3840x2160"
]
DEFAULT_TIMEOUT: float = 10.0
DEFAULT_SLEEP: float = 0.25

@dataclass
class BrowserConfig:
    """Configuration settings for browser initialization."""
    user_agent: str
    screen_size: str
    debug: bool = False

def create_browser_config(debug: bool = False) -> BrowserConfig:
    """Create browser configuration with random user agent and screen size."""
    ua = UserAgent()
    return BrowserConfig(
        user_agent=ua.random,
        screen_size=random.choice(SCREEN_SIZES),
        debug=debug
    )

def setup_chrome_options(config: BrowserConfig) -> Options:
    """Configure Chrome options with specified settings."""
    options = Options()
    options.add_argument(f"user-agent={config.user_agent}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--window-size={config.screen_size}")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.page_load_strategy = 'none'
    
    if not config.debug:
        options.add_argument("--headless")
    
    return options

def setup_chrome_capabilities() -> ChromeCapabilities:
    """Configure Chrome capabilities for performance logging."""
    capabilities = DesiredCapabilities.CHROME.copy()
    capabilities['goog:loggingPrefs'] = {'performance': 'ALL'}
    return capabilities

def configure_stealth_settings(driver: Driver) -> None:
    """Apply anti-detection stealth settings to driver."""
    stealth(
        driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True
    )

def init_selenium(debug: bool = False) -> Driver:
    """Initialize and configure Selenium WebDriver with stealth settings."""
    config = create_browser_config(debug)
    options = setup_chrome_options(config)
    capabilities = setup_chrome_capabilities()
    
    options.set_capability('goog:loggingPrefs', capabilities['goog:loggingPrefs'])
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    
    configure_stealth_settings(driver)
    return driver

def analyze_network_activity(
    driver: Driver,
    previous_log_length: Optional[int]
) -> Tuple[bool, int]:
    """Analyze network activity to determine if page loading is complete."""
    logs = driver.get_log('performance')
    current_log_length = len(logs)
    
    if previous_log_length is None:
        return False, current_log_length
        
    activity_threshold = previous_log_length * 1.1
    is_loaded = not current_log_length > activity_threshold
    
    return is_loaded, current_log_length

@contextmanager
def wait_for_page_load(driver: Driver, timeout: float = DEFAULT_TIMEOUT, sleep: float = DEFAULT_SLEEP):
    """Context manager to wait for page load completion."""
    previous_log_length = None
    end_time = time.time() + timeout
    
    yield
    
    while time.time() < end_time:
        is_loaded, log_length = analyze_network_activity(driver, previous_log_length)
        if is_loaded:
            break
        previous_log_length = log_length
        time.sleep(sleep)
    
    # Additional buffer time for final rendering
    time.sleep(sleep * 1.5)

def navigate_and_wait(
    driver: Driver,
    url: str,
    timeout: float = DEFAULT_TIMEOUT,
    sleep: float = DEFAULT_SLEEP
) -> Driver:
    """Navigate to URL and wait for page load completion."""
    with wait_for_page_load(driver, timeout, sleep):
        driver.get(url)
    return driver

def get_page_html(driver: Driver) -> str:
    """Retrieve HTML content of current page with error handling."""
    try:
        time.sleep(DEFAULT_SLEEP)
        return driver.page_source or ""
    except Exception as e:
        print(f"Error retrieving page HTML: {str(e)}")
        return ""

def extract_links_by_xpath(driver: Driver, xpath: str) -> List[str]:
    """Extract href attributes from elements matching XPath pattern."""
    elements = driver.find_elements(By.XPATH, xpath)
    return [
        element.get_attribute('href')
        for element in elements
        if element.get_attribute('href')
    ]