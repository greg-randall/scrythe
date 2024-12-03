# Standard library imports
import argparse
import csv
import os
import sys
import time
from pprint import pprint
from urllib.parse import urlparse, urlunparse, urljoin

# Third-party library imports
from bs4 import BeautifulSoup
import tiktoken
import validators

# Local module imports
from functions import (
    init_selenium,
    navigate_and_wait,
    get_page_html,
    clean_page,
    process_jobs_page,
    generate_xpaths_for_all_elements,
    find_xpath_for_string,
    generalize_xpath,
    sift_next_page_link,
    is_fully_qualified_domain,
    pretty_round,
    extract_links_by_xpath
)


parser = argparse.ArgumentParser(description="Scrape job listings from a given URL.")
parser.add_argument('url', type=str, help='The URL to scrape job listings from')
args = parser.parse_args()

if not validators.url(args.url):
    print("Invalid URL provided.")
    sys.exit(1)

overall_cost = 0

print("Initializing Selenium")
driver = init_selenium()
print("Initialized Selenium\n\n")

print("Navigating to URL")
driver = navigate_and_wait(driver, args.url)
time.sleep(5)
print("Navigated to URL\n\n")

print("Getting & Cleaning Page HTML")
html = get_page_html(driver)
html = clean_page(html)
print("Got & Cleaned Page HTML\n\n")


print("Initializing tokenizer & tokenizing HTML to make sure it's not too long")
# Initialize the tokenizer
tokenizer = tiktoken.get_encoding("cl100k_base")
# Tokenize the html string
tokens = tokenizer.encode(html)
if len(tokens) > 128000:
    print("\tHTML too long. Doing further cleaning, output might be degraded.")
    html = clean_page(html, True) # Clean the page with more aggressive settings
    tokens = tokenizer.encode(html)
    if len(tokens) > 128000:
        print("\tHTML still too long. Exiting.")
        exit()
    else:
        print("\tHTML length is fine after further cleaning.")
else:
    print("\tHTML length is fine")
print("Initialized tokenizer & tokenized HTML\n\n")
    


print("Finding job listings & next page")
gpt_output, cost = process_jobs_page(html)

print("\tJob elements sample:")    
job_elements = gpt_output['job_elements']
job_urls = []

for element in job_elements:
    if is_fully_qualified_domain(element) or not "<" in element:
        job_urls.append(element)
    else:
        soup = BeautifulSoup(element, 'html.parser')
        link = soup.find('a', href=True)
        if link:
            job_urls.append(link['href'])

#print('job elements')
#pprint(job_elements)
#print("job urls")
pprint(job_urls[:5])
print("")
print("\tNext page sample:")
next_page = gpt_output['next_page']
print(f"\t{next_page}")

print(f"\tCost ${pretty_round(cost)}")
overall_cost += cost
print("Found job listings & next page\n\n")

print("Generating XPaths")
xpaths = generate_xpaths_for_all_elements(html)
print("Generated XPaths\n\n")


print("Finding XPaths for Job Elements")
xpaths_for_job_elements = find_xpath_for_string(xpaths, job_urls)
xpaths_for_job_elements_sorted = {k: v for k, v in sorted(xpaths_for_job_elements.items(), key=lambda item: str(item[1]))}
pprint(list(xpaths_for_job_elements_sorted.items())[:5])
print("Found XPaths for Job Elements\n\n")



print("Generalizing job XPaths")
generalized_xpath, cost = generalize_xpath(xpaths_for_job_elements_sorted)
if not generalized_xpath:
    print("\tNo generalized XPath found")
    exit()
print(f"\t{generalized_xpath}")
print(f"\tCost ${pretty_round(cost)}")
overall_cost += cost
print("Generalized job XPath\n\n")



# Generate the data
print("Reviewing next page html for url based pagination")
sifted_next_page_url, page_increment, cost = sift_next_page_link(next_page)

if not sifted_next_page_url:
    print("\tNo easy url based pagination found")
    url_based_pagination = False
    exit()

if is_fully_qualified_domain(sifted_next_page_url):
    full_url = sifted_next_page_url
else:
    parsed_url = urlparse(args.url)
    base_url = urlunparse((parsed_url.scheme, parsed_url.netloc, '', '', '', ''))
    full_url = urljoin(base_url + '/', sifted_next_page_url)

if not sifted_next_page_url:
    print("\tNo easy url based pagination found")
    exit()

print(f"\tEasy url based pagination found: {full_url} with page increment {page_increment}")
print(f"\tCost ${pretty_round(cost)}")
overall_cost += cost
print("Reviewed next page html for actual button/link\n\n")

print("Navigating to next page:")
if page_increment == 1:
    page_number = 2
else:
    page_number = page_increment
print(f"\t{full_url}{page_number}")
navigate_and_wait(driver, f"{full_url}{page_number}")
time.sleep(2)
print("Navigated to next page\n\n")

print("Testing XPath link collection")
links = extract_links_by_xpath(driver, generalized_xpath)
pprint(links)
print("Tested XPath link collection\n\n")


print("Writing data to CSV")

# Get current time
human_readable_timestamp = time.strftime('%Y-%m-%d %I:%M:%S %p', time.localtime())
unix_timestamp = int(time.time())

# Data to write
data = [
    human_readable_timestamp,
    unix_timestamp,
    generalized_xpath,
    full_url,
    page_increment
]

file_exists = os.path.isfile('sites_to_scrape.csv')

# Write to CSV
with open('sites_to_scrape.csv', mode='a', newline='') as file:
    writer = csv.writer(file)
    if not file_exists:
        writer.writerow(['Human Readable Timestamp', 'Unix Timestamp', 'Generic Job XPath', 'Paged Link URL', 'Page Increment Value'])
    writer.writerow(data)

print("Data written to sites_to_scrape.csv")

print(f"\nOverall cost: ${pretty_round(overall_cost)}")

