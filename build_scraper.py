"""
Build scraper configuration from a job board URL.
Analyzes page structure and writes scraping configuration to CSV.
"""

from typing import Tuple
import argparse
import os
import sys
import time
import validators
from pprint import pprint
from functions.functions_selenium import init_selenium, navigate_and_wait, get_page_html
from functions.functions_builder import (
    clean_page,
    process_and_extract_jobs,
    initialize_tokenizer,
    analyze_pagination,
    generate_xpaths_for_all_elements,
    find_xpath_for_string,
    generalize_xpath,
    write_config_to_csv
)

def parse_arguments() -> Tuple[str, bool]:
    """
    Parse command line arguments.
    
    Returns:
        Tuple of (url, verbose_flag)
        
    Raises:
        SystemExit: If URL is invalid
    """
    parser = argparse.ArgumentParser(description="Scrape job listings from a given URL.")
    parser.add_argument('url', type=str, help='The URL to scrape job listings from')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    args = parser.parse_args()
    
    if not validators.url(args.url):
        print("Invalid URL provided.")
        sys.exit(1)
        
    return args.url, args.verbose

def verify_pagination(driver, full_url: str, page_increment: int) -> bool:
    """
    Verify pagination pattern by attempting to navigate to the next page.
    
    Args:
        driver: Selenium WebDriver instance
        full_url: Base URL for pagination
        page_increment: Page number increment
        
    Returns:
        bool: True if pagination works, False otherwise
    """
    try:
        page_number = 2 if page_increment == 1 else page_increment
        next_url = f"{full_url}{page_number}"
        navigate_and_wait(driver, next_url)
        return True
    except Exception as e:
        print(f"Error verifying pagination: {str(e)}")
        return False

def main() -> None:
    """
    Main execution function for building scraper configuration.
    
    Process flow:
    1. Validate environment and arguments
    2. Initialize browser and navigate to URL
    3. Process page content and extract job listings
    4. Generate and verify XPath patterns
    5. Analyze pagination
    6. Save configuration to CSV
    """
    if 'OPENAI_API_KEY' not in os.environ:
        print("OPENAI_API_KEY environment variable not set")
        sys.exit(1)
        
    url, verbose = parse_arguments()
    overall_cost = 0
    start_time = time.time()
    
    try:
        print(f"Building scraper configuration for {url}...")
        
        # Initialize browser and navigate to URL
        if verbose:
            print("Initializing Selenium...")
        driver = init_selenium()
        
        if verbose:
            print(f"Selenium initialized in {time.time() - start_time:.2f} seconds")
            print(f"Navigating to {url}...")
            
        navigate_and_wait(driver, url)
        time.sleep(2)
        
        # Process page content
        if verbose:
            print("Processing page content...")
        html = get_page_html(driver)
        html = clean_page(html)
        html, _ = initialize_tokenizer(html)
        
        # Extract job listings
        if verbose:
            print("Analyzing page for job listings...")
        job_urls, next_page, cost = process_and_extract_jobs(html)
        overall_cost += cost
        
        if not job_urls:
            print("No job listings found")
            sys.exit(1)
            
        if verbose:
            print(f"Found {len(job_urls)} job listings")
            
        # Generate and verify XPath patterns
        if verbose:
            print("Generating XPath patterns...")
        xpaths = generate_xpaths_for_all_elements(html)
 
        xpaths_for_job_elements = find_xpath_for_string(xpaths, job_urls)
                
        generalized_xpath, cost = generalize_xpath(xpaths_for_job_elements)
        overall_cost += cost
        
        if not generalized_xpath:
            print("No generalized XPath found")
            sys.exit(1)
            
        if verbose:
            print(f"Generated XPath pattern: {generalized_xpath}")
            
        # Analyze and verify pagination
        if verbose:
            print("Analyzing pagination pattern...")
        full_url, page_increment = analyze_pagination(next_page, url)
        
        if not full_url or not page_increment:
            print("Could not determine pagination pattern")
            sys.exit(1)
            
        if not verify_pagination(driver, full_url, page_increment):
            print("Could not verify pagination")
            sys.exit(1)
            
        if verbose:
            print(f"Found pagination pattern: {full_url} (increment: {page_increment})")
        
        if generalized_xpath == False:
            print("No generalized XPath found\nNo configuration saved")
        else:       
            # Save configuration
            timestamp_human = time.strftime('%Y-%m-%d %I:%M:%S %p', time.localtime())
            timestamp_unix = int(time.time())
            
            write_config_to_csv(
                timestamp_human,
                timestamp_unix,
                generalized_xpath,
                full_url,
                page_increment
            )
        
        # Print summary
        total_time = time.time() - start_time
        print(f"\nScraper configuration complete:")
        print(f"- Pagniated link: {full_url}")
        print(f"- Page increment: {page_increment}")
        print(f"- Generic job XPath: {generalized_xpath}")
        print(f"- OpenAI API cost: ${overall_cost:.4f}")
        print(f"- Total time: {total_time:.2f} seconds")
        if generalized_xpath == False:
            print("No configuration saved")
        else:
            print("Configuration saved to sites_to_scrape.csv")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    finally:
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    main()