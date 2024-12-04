# Scrythe

## Overview

This tool helps automate the process of scraping job listings from various job boards by intelligently detecting pagination and job listing patterns using OpenAI's GPT models.

The name "Scrythe" is a bit of a combination between scrying, scythe, and scrape.

## Prerequisites

- Python 3.8+
- OpenAI API Key
- Selenium WebDriver
- Required Python packages (install via `pip install -r requirements.txt`)

## Setup

1. Set your OpenAI API key as a system environment variable:

```bash
export OPENAI_API_KEY='your_api_key_here'
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Step 1: Build Scraper Configuration

Run `build_scraper.py` with the URL of a job board:

```bash
python build_scraper.py https://example.com/jobs [-v]
```

Options:
- `-v, --verbose`: Enable verbose output showing detailed progress and timing information

This script will:
- Navigate to the job board
- Detect job listing and pagination patterns using GPT-4o-mini
- Analyze HTML structure and generate XPath patterns
- Verify pagination functionality
- Write configuration to `sites_to_scrape.csv`

The build process typically costs around $0.05 per site in OpenAI API usage.

### Step 2: Scrape Job Listings

Run `run_scraper.py` to scrape all configured job boards:

```bash
python run_scraper.py
```

This script will:
- Read configurations from `sites_to_scrape.csv`
- Randomize the order of sites to scrape
- Scrape job listings from each configured job board
- Download job descriptions with caching
- Handle pagination automatically

## Output

- Scraped job descriptions are saved in a `cache` directory
- Each cached file includes:
  - Original job listing URL as a comment in the first line
  - Full HTML content of the job description
- Cache is maintained for 28 days by default
- Files are named using a combination of site name and URL hash

## Technical Details

The scraper supports:
- Numbered pagination (page 1, page 2, page 3)
- Offset pagination (start with item 0, item 10, item 20)
- Various URL patterns and increments
- Handles both relative and absolute URLs
- Intelligent detection of pagination patterns using GPT models
- Built-in rate limiting and randomized delays
- Smart caching with configurable expiration
- Anti-detection measures via Selenium stealth

## Notes

- Ensure you have the appropriate Selenium WebDriver installed
- Some job boards may have anti-scraping measures that could interrupt the process, but Selenium stealth helps mitigate this
- The scraper automatically cleans and processes HTML content to optimize token usage
- Built-in error handling and retry mechanisms for robustness