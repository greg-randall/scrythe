
# Scrythe

## Overview

This tool helps automate the process of scraping job listings from various job boards by intelligently detecting pagination and job listing patterns.

The name "Scrythe" is a bit of a combination between scrying, scythe, and scrape.

## Prerequisites

- Python 3.8+
- OpenAI API Key
- Selenium WebDriver
- Required Python packages (install via `pip install -r requirements.txt`)

## Setup

1. Set your OpenAI API key as a system environment variable:

```

export OPENAI_API_KEY='your_api_key_here'

```

2. Install dependencies:

```

pip install -r requirements.txt

```

## Usage

### Step 1: Build Scraper Configuration

Run `build_scraper.py` with the URL of a job board:

```bash

python  build_scraper.py  https://example.com/jobs

```

This script will:

- Navigate to the job board
- Detect job listing and pagination patterns
- Write configuration to `sites_to_scrape.csv`

### Step 2: Scrape Job Listings

Run `run_scraper.py` to scrape all configured job boards:

```bash

python  run_scraper.py

```

This script will:

- Read configurations from `sites_to_scrape.csv`
- Scrape job listings from each configured job board
- Download job descriptions

## Output

- Scraped job descriptions are saved in a `cache` directory
- Job listing links are saved with timestamps and site-specific configurations
- URL of job listing is saved as a comment on the first line of the cached file

## Notes

- Ensure you have the appropriate Selenium WebDriver installed
- The tool uses OpenAI's API to detect page patterns, so API costs will be incurred
- Some job boards may have anti-scraping measures that could interrupt the process, but Selenium gets around some of that
- The scraper works with job boards that use:
	-   Numbered pagination (page 1, page 2, page 3)
	-   Offset pagination (start with item 0, item 10, item 20)