"""
Functions for running scrapers and managing the scraping process.
Includes pagination handling, content downloading, caching, and configuration management.
"""
from typing import List, Set, Optional, Dict, Any
import hashlib
import os
import secrets
import time
import csv
from pathlib import Path
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta
from selenium.webdriver.remote.webdriver import WebDriver

# Local module imports
from .functions_selenium import navigate_and_wait, get_page_html, extract_links_by_xpath

# Constants
CACHE_DIR = Path('cache')
DEFAULT_CACHE_MAX_AGE = timedelta(days=28)  # 28 days in seconds
DEFAULT_MIN_FILE_LENGTH = 100
DEFAULT_SLEEP_TIME = 5

def ensure_cache_dir_exists() -> None:
    """Create cache directory if it doesn't exist."""
    CACHE_DIR.mkdir(exist_ok=True)

def generate_url_hash(url: str) -> str:
    """Generate SHA256 hash of URL."""
    return hashlib.sha256(url.encode()).hexdigest()

def create_cache_filename(name: str, url: str) -> str:
    """Generate a cache filename from site name and URL hash."""
    sanitized_name = name.strip()
    url_hash = generate_url_hash(url)
    return f"{sanitized_name}_{url_hash}.html"

def get_file_length(file_path: Path) -> int:
    """Get the length of text content in a file with error handling."""
    try:
        return len(file_path.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return 0

def should_update_cache(
    cache_file: Path,
    max_age: timedelta = DEFAULT_CACHE_MAX_AGE,
    min_length: int = DEFAULT_MIN_FILE_LENGTH
) -> bool:
    """
    Determine if cache file should be updated based on age and length.
    Returns True if file should be updated, False otherwise.
    """
    if not cache_file.exists():
        return True
        
    file_age = datetime.now().timestamp() - cache_file.stat().st_mtime
    if file_age >= max_age.total_seconds():
        return True
        
    if get_file_length(cache_file) < min_length:
        cache_file.unlink()
        return True
        
    return False

def manage_cache_file(
    filename: str,
    max_age: timedelta = DEFAULT_CACHE_MAX_AGE,
    min_length: int = DEFAULT_MIN_FILE_LENGTH
) -> bool:
    """
    Manage cache file: check existence, age, and length.
    Returns True if cache is valid, False if needs update.
    """
    ensure_cache_dir_exists()
    cache_file = CACHE_DIR / filename
    return not should_update_cache(cache_file, max_age, min_length)

def save_to_cache(name: str, url: str, content: str) -> None:
    """Save content to cache with URL as comment."""
    ensure_cache_dir_exists()
    filename = create_cache_filename(name, url)
    cache_path = CACHE_DIR / filename
    
    cache_content = f"<!-- {url} -->\n{content}"
    cache_path.write_text(cache_content, encoding='utf-8')

def normalize_url(base_url: str, link: str) -> str:
    """Convert relative URLs to absolute URLs."""
    return urljoin(base_url, link) if not link.startswith('http') else link

def is_new_job(job: str, existing_jobs: Set[str]) -> bool:
    """Check if job URL is new and not already processed."""
    return job not in existing_jobs

def should_stop_scraping(consecutive_single_pages: int, max_consecutive: int = 5) -> bool:
    """Determine if scraping should stop based on consecutive single-page results."""
    return consecutive_single_pages >= max_consecutive

def process_jobs_page(
    driver: WebDriver,
    xpath: str,
    base_url: str,
    existing_jobs: Set[str]
) -> List[str]:
    """Process a single page of job listings and extract new job URLs."""
    jobs = extract_links_by_xpath(driver, xpath)
    if not jobs:
        return []
        
    normalized_jobs = [normalize_url(base_url, job) for job in jobs]
    return [job for job in normalized_jobs if is_new_job(job, existing_jobs)]

def generic_paged_scraper_by_xpath(
    url: str,
    driver: WebDriver,
    xpath: str,
    debug: bool = False,
    page: int = 1,
    increment: int = 1
) -> List[str]:
    """Scrape pages using XPath pattern with pagination."""
    found_links: Set[str] = set()
    consecutive_single_job_pages = 0
    
    while True:
        if debug:
            print(f"Scraping page {page}")
            
        current_url = f"{url}{page}"
        navigate_and_wait(driver, current_url)
        time.sleep(DEFAULT_SLEEP_TIME)
        
        new_jobs = process_jobs_page(driver, xpath, url, found_links)
        
        if not new_jobs:
            break
            
        found_links.update(new_jobs)
        
        if len(new_jobs) == 1:
            consecutive_single_job_pages += 1
        else:
            consecutive_single_job_pages = 0
            
        if should_stop_scraping(consecutive_single_job_pages):
            if debug:
                print("\tFound only one job for five consecutive pages. Ending scraping.")
            break
            
        page += increment
    
    return list(found_links)

def download_all_links(
    links: List[str],
    driver: WebDriver,
    name: str,
    sleep_time: float = 0
) -> None:
    """Download content from all provided links with randomization."""
    sanitized_name = name.strip()
    randomized_links = list(links)
    secrets.SystemRandom().shuffle(randomized_links)
    
    for index, link in enumerate(randomized_links, start=1):
        normalized_link = normalize_url(driver.current_url, link)
        filename = create_cache_filename(sanitized_name, normalized_link)
        
        print(f"{index}/{len(links)} - Getting {normalized_link} - {filename}")
        
        if manage_cache_file(filename):
            print("\t\tAlready downloaded")
            continue
        
        navigate_and_wait(driver, normalized_link)
        content = get_page_html(driver)
        save_to_cache(sanitized_name, normalized_link, content)
        
        if sleep_time > 0:
            time.sleep(sleep_time)

def parse_scraper_config(row: List[str]) -> Dict[str, Any]:
    """
    Parse a CSV row into a scraper configuration dictionary.
    
    Args:
        row: List containing [xpath, url, increment] values
        
    Returns:
        Dictionary containing scraper configuration
    """
    return {
        'xpath': row[2].strip(),  # Generic Job XPath
        'url': row[3].strip(),    # Paged Link URL
        'increment': int(row[4].strip())  # Page Increment Value
    }

def load_scraper_configs(csv_path: str) -> List[Dict[str, Any]]:
    """
    Load scraper configurations from CSV file.
    
    Args:
        csv_path: Path to CSV configuration file
        
    Returns:
        List of configuration dictionaries
    """
    configs = []
    with open(csv_path, mode='r', newline='') as file:
        reader = csv.reader(file)
        next(reader)  # Skip header row
        for row in reader:
            configs.append(parse_scraper_config(row))
    return configs

def randomize_configs(configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Randomly shuffle scraper configurations.
    
    Args:
        configs: List of configuration dictionaries
        
    Returns:
        Shuffled list of configuration dictionaries
    """
    shuffled = configs.copy()
    secrets.SystemRandom().shuffle(shuffled)
    return shuffled

def get_site_name(url: str) -> str:
    """
    Extract site name from URL.
    
    Args:
        url: Full URL string
        
    Returns:
        Domain name from URL
    """
    return urlparse(url).netloc

def determine_start_page(increment: int) -> int:
    """
    Determine starting page number based on increment.
    
    Args:
        increment: Page increment value
        
    Returns:
        Starting page number (0 or 1)
    """
    return 1 if increment == 1 else 0

def scrape_single_site(
    config: Dict[str, Any],
    driver: WebDriver,
    sleep_time: int = 2
) -> None:
    """
    Scrape job listings from a single site.
    
    Args:
        config: Dictionary containing scraping configuration
        driver: Selenium WebDriver instance
        sleep_time: Time to wait between requests in seconds
    """
    try:
        site_name = get_site_name(config['url'])
        print(f"Scraping {config['url']}")
        
        start_page = determine_start_page(config['increment'])
        links = generic_paged_scraper_by_xpath(
            config['url'],
            driver,
            config['xpath'],
            True,
            start_page,
            config['increment']
        )
        
        download_all_links(links, driver, site_name, sleep_time)
        print(f"Finished scraping {config['url']}\n\n")
        
    except Exception as e:
        print(f"Error scraping {config['url']}: {e}")
        print(f"Maybe check the xpath \n\t{config['xpath']}\n\n")