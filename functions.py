# Standard library imports
import hashlib
import json
import os
import random
import re
import secrets
import time
from pprint import pprint
from urllib.parse import urlparse, urljoin

# Web parsing imports
from bs4 import BeautifulSoup, Comment

# Sorting imports
from natsort import natsorted

# Selenium and browser automation imports
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager

# AI/API imports
from openai import OpenAI

def init_selenium(debug=False):
    # Create a UserAgent object
    ua = UserAgent()

    # List of possible screen sizes
    screen_sizes = ["1024x768", "1280x800", "1366x768", "1440x900", "1920x1080", "3840x2160"]
    # Choose a random screen size from the list
    screen_size = random.choice(screen_sizes)

    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument(f"user-agent={ua.random}")  # Set the user agent to a random one
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Disable automation detection
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])  # Disable automation detection
    chrome_options.add_argument(f"--window-size={screen_size}")

    # Set page load strategy to 'none' to make navigation faster
    chrome_options.page_load_strategy = 'none'

    # Set up Chrome capabilities
    capabilities = DesiredCapabilities.CHROME
    capabilities['goog:loggingPrefs'] = {'performance': 'ALL'}
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    if not debug:
        chrome_options.add_argument("--headless")  # Run in headless mode if not in debug mode

    # Create a WebDriver object with the specified capabilities
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    # Apply stealth settings to the WebDriver
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True)

    return driver


def navigate_and_wait(driver, url, timeout=10, sleep=0.25):
    driver.get(url)
    is_page_loaded(driver, timeout, sleep)
    return driver

def is_page_loaded(driver, timeout=10, sleep=0.25):
    # Check for network activity
    end_time = time.time() + timeout
    first_request = True
    while time.time() < end_time:
        logs = driver.get_log('performance')
        log_length = len(logs)
        if first_request:
            first_request = False
            previous_log_length = log_length
            time.sleep(sleep)
            continue
        if not log_length > previous_log_length * 1.1:
            break
        time.sleep(sleep)
    time.sleep(sleep*1.5)

def get_page_html(driver):
    return driver.page_source

def clean_page(html, extra_cleaning=False):
    soup = BeautifulSoup(html, 'html.parser')

    # Remove all inlined images
    for img in soup.find_all('img'):
        if img.get('src', '').startswith('data:'):
            img.decompose()

    # Remove specified tags
    tags_to_remove = ['script', 'head', 'style', 'footer']
    if extra_cleaning:
        tags_to_remove.extend(['symbol', 'svg', 'noscript', 'iframe'])
    soup = remove_tags(soup, tags_to_remove)

    # Remove all attributes except src and href if extra_cleaning is enabled
    if extra_cleaning:
        for tag in soup.find_all(True):
            attrs = {key: value for key, value in tag.attrs.items() if key in ['src', 'href']}
            tag.attrs = attrs

    # Remove all comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    return str(soup)

def remove_tags(soup, tags):
    for tag in tags:
        for element in soup.find_all(tag):
            element.decompose()
    return soup

def process_jobs_page(html):
    gpt_output = [
        {
            "name": "get_gpt_output",
            "description": "Extract job listing urls and pagination from the given HTML",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_elements": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Get the URL/relative path of the job listings on this page. If you can't find URLs/relative paths, please return an empty array."
                    },

                    "next_page": {
                        "type": "string",
                        "description": "Extract the html for the page numbers, previous, next links, 'view all', 'show more' or similar buttons/links from the following HTML. !!Get more rather than less including the html around the list items, divs, etc!! Please do not explain, please just output the html!"
                    }
                },
                "required": ["next_page", "job_elements"]
            }
        }
    ]
    client = OpenAI(
        api_key=os.environ.get('OPENAI_API_KEY')
    )
    response = client.chat.completions.create(
        model = 'gpt-4o-mini',
        messages = [{'role': 'user', 'content': html }],
        functions = gpt_output,
        function_call = 'auto'
    )
    try:
        json_response = json.loads(response.choices[0].message.function_call.arguments)
        cost = open_ai_cost(response)
        return json_response, cost
    except:
        pprint(response)
        print("\nprocess_jobs_page -- Error processing\n\n\n")
        return False, False

from open_ai_cost import OPEN_AI_COST

def calculate_cost(prompt_tokens, completion_tokens, input_cost, output_cost):
    return (prompt_tokens * input_cost) + (completion_tokens * output_cost)

def open_ai_cost(response):
    model = response.model if not response.model.startswith('gpt-4o') else 'gpt-4o'
    model = model if model in OPEN_AI_COST else 'o1-preview'

    if model == 'o1-preview':
        print("Model not found, using the most expensive model")

    input_cost = OPEN_AI_COST[model]['input']
    output_cost = OPEN_AI_COST[model]['output']

    cost = calculate_cost(response.usage.prompt_tokens, response.usage.completion_tokens, input_cost, output_cost)

    return cost

def generate_xpaths_for_all_elements(html_content):
    soup = BeautifulSoup(html_content, 'lxml')
    all_elements = soup.find_all()
    xpaths = {}

    for element in all_elements:
        xpath = generate_xpath(element)
        xpaths[xpath] = element

    # Sort the dictionary by the number of slashes in the XPath
    xpaths = {k: v for k, v in sorted(xpaths.items(), key=lambda item: item[0].count('/'), reverse=True)}

    xpaths = {k: str(v) for k, v in xpaths.items()}

    return xpaths

def generate_xpath(element):
    components = []
    child = element if element.name else element.parent
    for parent in child.parents:
        siblings = parent.find_all(child.name, recursive=False)
        components.append(
            child.name if siblings == [child] else
            f"{child.name}[{siblings.index(child) + 1}]"
        )
        child = parent
    components.reverse()
    return '/' + '/'.join(components)

def find_xpath_for_string(xpaths_dict, html_fragments):
    result = {}
    for fragment in html_fragments:
        for xpath, html in xpaths_dict.items():
            if fragment in html:
                result[fragment] = xpath
                break
    return result

def generalize_xpath(xpaths_dict):
    xpaths = '\n'.join(natsorted(str(v) for v in xpaths_dict.values()))
    
    prompt = f"Please review the below XPATHS (one per line) and see if they have commonalities, if they do please return a generic XPATH selector that will select the majority of the elements, if it looks like a range use the asterisk to select all, typically there will be one asterisk in the generic XPATH. Do NOT add any formatting or explanation, just return the raw XPATH string. If you can't figure out a generic XPATH, reply with 'False':\n\n{xpaths}"

    #print(f"\n\n{prompt}\n")

    gpt_output, cost = gpt_me(prompt, 'gpt-4o-mini', None, True)
    
    # Clean the output by removing backticks, xpath prefix, and whitespace
    cleaned_xpath = gpt_output.replace('```xpath', '').replace('```', '').strip()
    
    return cleaned_xpath, cost

def gpt_me(prompt, model, key=None, return_cost=False):
    if key is None:
        key = os.getenv('OPENAI_API_KEY')
        if key is None:
            raise ValueError("gpt_me -- API key must be provided either as an argument or set in the environment variable 'GPT_API_KEY'")
    client = OpenAI(
        api_key=key
    )
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model=model,
    )
    if return_cost:
        return chat_completion.choices[0].message.content, open_ai_cost(chat_completion)
    else:
        return chat_completion.choices[0].message.content

def sift_next_page_link(html):
    prompt = f"Please review the below HTML and find links to pages, try to discern a page number/increment pattern ie \"jobs/search?page=1&query=example\", \"jobs/search?page=2&query=example\" or \"https://example.com/jobs?from=10&s=1&rk=l-faculty-jobs\", \"https://example.com/jobs?from=20&s=1&rk=l-faculty-jobs\", \"https://example.com/jobs?from=30&s=1&rk=l-faculty-jobs\". DO NOT EXPLAIN, just reply with the pattern with no number at the end ie \"jobs/search?query=example&page=\". If the pattern seems to increment by a number other than 1 reply with the pattern with no number at the end then a tilde (~) and the increment number ie \"https://example.com/jobs?s=1&rk=l-faculty-jobs&from=~10\". If you can't find a pattern, reply with the string \"False\":\n\n{html}"

    print(f"\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n{prompt}\n")

    gpt_output, cost = gpt_me(prompt, 'gpt-4o-mini', None, True)

    print(f"\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n{gpt_output}\n")

    gpt_output = gpt_output.replace('```html\n', '').replace('\n```', '')

    if len(gpt_output.strip())<=5:
        return False, False, False

    if '~' in gpt_output:
        gpt_output = gpt_output.split('~')
        return gpt_output[0], int(gpt_output[1]), cost
    else:
        gpt_output = re.sub(r'(^.+=).+', '$1', gpt_output)
        gpt_output = gpt_output.replace('$1', '')
        return gpt_output, 1, cost

def extract_links_by_xpath(driver, xpath):
    elements = driver.find_elements(By.XPATH, xpath)
    hrefs = [element.get_attribute('href') for element in elements]
    return hrefs

def is_fully_qualified_domain(url):
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except:
        print(f"Error parsing URL: {url}")
        return False

def pretty_round(number):
    str_num = str(number)
    if '.' in str_num:
        integer_part, fractional_part = str_num.split('.')
        non_zero_count = 0
        for i, digit in enumerate(fractional_part):
            if digit != '0':
                non_zero_count += 1
            if non_zero_count == 2:
                return round(number, i + 1)
    return round(number, 2)  # Default rounding if no fractional part


def generic_paged_scraper_by_xpath(url, driver, xpath, debug=False, page=1, increment=1):
    links = []
    consecutive_single_job_pages = 0

    while True:
        if debug:
            print(f"Scraping page {page}")
        navigate_and_wait(driver, f"{url}{page}")
        time.sleep(5)
        jobs = extract_links_by_xpath(driver, xpath)
        if debug:
            print(f"\tFound {len(jobs)} jobs")
        if len(jobs) == 0:
            break

        # Convert relative links to absolute links
        jobs = [urljoin(url, job) for job in jobs]

        # Check if all jobs are already in the list
        if all(job in links for job in jobs):
            if debug:
                print("\tAll jobs are already in the list. Ending scraping.")
            break

        links.extend(jobs)

        # Check for consecutive pages with only one job
        if len(jobs) == 1:
            consecutive_single_job_pages += 1
        else:
            consecutive_single_job_pages = 0

        if consecutive_single_job_pages >= 5:
            if debug:
                print("\tFound only one job for five consecutive pages. Ending scraping.")
            break

        page += increment

        if debug:
            print(f"\tsample job link from page {jobs[:1]}")

    return list(set(links))


def download_all_links(links, driver, name, sleep_time=0):
    name = name.strip()
    
    secrets.SystemRandom().shuffle(links)

    total_links = len(links)
    for index, link in enumerate(links, start=1):
        if not link.startswith('http'):
            link = urljoin(get_current_page_url(driver), link)
        filename = f'{name}_{url_hash(link)}.html'
        print(f"{index}/{total_links} - Getting {link} - {filename}")
        
        # Log the cache check
        cached = is_cached(filename)
        #print(f"\t\tCache check for {filename}: {cached}")

        if cached:
            print("\t\tAlready downloaded")
        else:
            navigate_and_wait(driver, link, timeout=10, sleep=0.25)
            job_content = get_page_html(driver)
            save_to_cache(name, link, job_content)
            if sleep_time != 0:
                time.sleep(sleep_time)

def get_current_page_url(driver):
    return driver.current_url
    
def is_cached(filename, max_age=2419200, debug=False):
    try:
        cache_files = os.listdir('cache')
        #print(f"Cache directory contains: {cache_files}")
        
        if filename in cache_files:
            file_path = os.path.join('cache', filename)
            file_age = time.time() - os.path.getmtime(file_path)
            file_length = file_text_length(file_path)
            
            if debug:
                print(f"Checking cache for {filename}:")
                print(f"\tFile path: {file_path}")
                print(f"\tFile age: {file_age} seconds")
                print(f"\tFile length: {file_length} characters")
            
            if file_age < max_age:
                if file_length >= 100:
                    return True
                else:
                    if debug:
                        print(f"\tFile {filename} is too short, removing.")
                    os.remove(file_path)
                    return False
            else:
                if debug:
                    print(f"\tFile {filename} is too old, removing.")
                os.remove(file_path)
                return False
        else:
            if debug:
                print(f"\tFile {filename} not found in cache.")
    except Exception as e:
        print(f"is_cached -- Error checking cache for {filename}: {e}")
    
    return False

def file_text_length(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            return len(content)
    except Exception as e:
        print(f"file_text_length -- Error reading file {file_path}: {e}")
        return 0

def url_hash(url):
    # Create a SHA256 hash of the URL
    url_hash = hashlib.sha256(url.encode()).hexdigest()
    return url_hash

def save_to_cache(name, link, job):
    filename = f'cache/{name}_{url_hash(link)}.html'
    with open(filename, 'w') as f:
        f.write(f"<!-- {link} -->\n{job}")