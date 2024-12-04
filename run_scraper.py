"""
Module for running web scrapers using configured settings from CSV file.
This module focuses on orchestrating the scraping process, while delegating
the implementation details to functions in functions_scraper.py.
"""
from typing import Dict, List, Optional
import sys
import secrets
from selenium.webdriver.remote.webdriver import WebDriver

from functions.functions_selenium import init_selenium
from functions.functions_scraper import (
    load_scraper_configs,
    randomize_configs,
    scrape_single_site
)

def run_scrapers(configs: List[Dict], driver: WebDriver) -> None:
    """
    Execute scraping process for all configured sites.
    
    This is the main orchestration function that:
    1. Takes a list of scraper configurations
    2. Iterates through each config
    3. Executes the scraping process for each site
    
    Args:
        configs: List of dictionaries containing scraper configurations
        driver: Initialized Selenium WebDriver instance
    """
    for config in configs:
        scrape_single_site(config, driver)

def main() -> None:
    """
    Main entry point for the scraping process.
    
    Process flow:
    1. Load scraper configurations from CSV
    2. Randomize the order of sites to scrape
    3. Initialize the browser
    4. Execute the scraping process
    5. Clean up browser resources
    
    Handles errors gracefully and ensures browser cleanup.
    """
    driver = None
    try:
        driver = init_selenium()
        
        # Load and randomize configurations
        configs = load_scraper_configs('sites_to_scrape.csv')
        randomized_configs = randomize_configs(configs)
        
        # Run scrapers
        run_scrapers(randomized_configs, driver)
        
    except Exception as e:
        print(f"Error during scraping process: {str(e)}", file=sys.stderr)
        sys.exit(1)
        
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()