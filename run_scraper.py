# Standard library imports
import os
import csv
import secrets
from urllib.parse import urlparse

# Import all functions from the functions file
from functions import (
    init_selenium,
    generic_paged_scraper_by_xpath,
    download_all_links
)


# Check if the directory 'cache' exists
if not os.path.isdir('cache'):
    os.makedirs('cache')

# Initialize an empty list to store the extracted data
extracted_data = []

# Read from CSV
with open('sites_to_scrape.csv', mode='r', newline='') as file:
    reader = csv.reader(file)
    # Skip the header
    next(reader)
    # Extract the required columns
    for row in reader:
        extracted_data.append([row[2].strip(), row[3].strip(), int(row[4].strip())])

# Shuffle the data
secrets.SystemRandom().shuffle(extracted_data[-1])

driver = init_selenium(True)

for data in extracted_data:
    url = data[1]
    xpath = data[0]
    increment = data[2]
    if increment == 1:
        start_page = 1
    else:
        start_page = 0
    parsed_url = urlparse(url)
    name = parsed_url.netloc
    print(f"Scraping {url}")
    links = generic_paged_scraper_by_xpath(url, driver, xpath, True, start_page, increment) 
    download_all_links(links, driver, name, 2)

    print(f"Finished scraping {url}\n\n")
driver.quit()
