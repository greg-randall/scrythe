"""
Functions for building and configuring scrapers.
Includes HTML processing, XPath generation, and pattern analysis.
"""
from typing import Dict, List, Optional, Tuple, Union
import re
from bs4 import BeautifulSoup, Comment, Tag
from natsort import natsorted
import json
from urllib.parse import urlparse
import os
from openai import OpenAI
from lxml import etree
from urllib.parse import urljoin, urlunparse
import csv

from functions.functions_openai import gpt_me, open_ai_cost
import tiktoken
from typing import Tuple

def initialize_tokenizer(html: str) -> Tuple[str, tiktoken.Encoding]:
    """
    Initialize tokenizer and verify HTML length is within processable limits.
    
    Args:
        html: Raw HTML content to be processed
        
    Returns:
        Tuple of (processed_html, tokenizer)
        
    Raises:
        SystemExit: If HTML is too long even after cleaning
    """
    tokenizer = tiktoken.get_encoding("cl100k_base")
    tokens = tokenizer.encode(html)
    
    if len(tokens) > 128000:
        html = clean_page(html, True)
        tokens = tokenizer.encode(html)
        if len(tokens) > 128000:
            raise SystemExit(1)
    
    return html, tokenizer

def extract_job_urls(job_elements: List[str]) -> List[str]:
    """
    Extract job URLs from various formats of job elements.
    
    Args:
        job_elements: List of strings containing job URLs or HTML elements
        
    Returns:
        List of extracted job URLs
    """
    job_urls = []
    for element in job_elements:
        if isinstance(element, str):
            if is_fully_qualified_domain(element) or "<" not in element:
                job_urls.append(element)
            else:
                soup = BeautifulSoup(element, 'html.parser')
                link = soup.find('a', href=True)
                if link and link.get('href'):
                    job_urls.append(link['href'])
    return job_urls

def process_and_extract_jobs(html: str) -> Tuple[List[str], str, float]:
    """
    Process HTML content to extract job listings and pagination information.
    
    Args:
        html: Page HTML content
        
    Returns:
        Tuple of (job_urls, next_page_html, api_cost)
    """
    response, cost = process_jobs_page_with_gpt(html)
    if not response:
        return [], "", 0.0
        
    job_elements = response.get('job_elements', [])
    job_urls = extract_job_urls(job_elements)
    next_page = response.get('next_page', '')
    
    return job_urls, next_page, cost

def write_config_to_csv(
    timestamp_human: str,
    timestamp_unix: int,
    xpath: str,
    url: str,
    increment: int,
    file_path: str = 'sites_to_scrape.csv'
) -> None:
    """
    Write scraper configuration to CSV file.
    
    Args:
        timestamp_human: Human-readable timestamp
        timestamp_unix: Unix timestamp
        xpath: XPath pattern for job elements
        url: Base URL for scraping
        increment: Page increment value
        file_path: Path to output CSV file
    """
    headers = [
        'Human Readable Timestamp',
        'Unix Timestamp',
        'Generic Job XPath',
        'Paged Link URL',
        'Page Increment Value'
    ]
    
    data = [timestamp_human, timestamp_unix, xpath, url, increment]
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)
    
    mode = 'a' if os.path.exists(file_path) else 'w'
    
    with open(file_path, mode=mode, newline='') as file:
        writer = csv.writer(file)
        if mode == 'w':
            writer.writerow(headers)
        writer.writerow(data)
        
def clean_html_attributes(tag: Tag, extra_cleaning: bool = False) -> None:
    """Clean HTML tag attributes based on cleaning level."""
    if extra_cleaning:
        # Keep only essential attributes
        allowed_attrs = {'src', 'href'}
        tag.attrs = {k: v for k, v in tag.attrs.items() if k in allowed_attrs}
    else:
        # Remove data URLs from img tags
        if tag.name == 'img' and tag.get('src', '').startswith('data:'):
            tag.decompose()

def get_tags_to_remove(extra_cleaning: bool = False) -> List[str]:
    """Get list of HTML tags to remove based on cleaning level."""
    tags = ['script', 'head', 'style', 'footer']
    if extra_cleaning:
        tags.extend(['symbol', 'svg', 'noscript', 'iframe'])
    return tags

def clean_html_content(soup: BeautifulSoup, extra_cleaning: bool = False) -> BeautifulSoup:
    """Clean HTML content by removing unnecessary elements."""
    # Remove unwanted tags
    for tag_name in get_tags_to_remove(extra_cleaning):
        for element in soup.find_all(tag_name):
            element.decompose()
    
    # Clean attributes for remaining tags
    for tag in soup.find_all(True):
        clean_html_attributes(tag, extra_cleaning)
    
    # Remove comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    
    return soup

def clean_page(html: str, extra_cleaning: bool = False) -> str:
    """Clean page HTML content."""
    soup = BeautifulSoup(html, 'html.parser')
    cleaned_soup = clean_html_content(soup, extra_cleaning)
    return str(cleaned_soup)

def create_job_page_schema() -> List[Dict]:
    """Create schema for GPT job page processing."""
    return [{
        "name": "get_gpt_output",
        "description": "Extract job listing urls and pagination from the given HTML",
        "parameters": {
            "type": "object",
            "properties": {
                "job_elements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Get the URL/relative path of the job listings on this page. If you can't find URLs/relative paths, please return an empty array."
                },
                "next_page": {
                    "type": "string",
                    "description": "Extract the html for the page numbers, previous, next links, 'view all', 'show more' or similar buttons/links from the following HTML. !!Get more rather than less including the html around the list items, divs, etc!! Please do not explain, please just output the html!"
                }
            },
            "required": ["next_page", "job_elements"]
        }
    }]

def process_gpt_response(response) -> Tuple[Dict, float]:
    """Process GPT API response and calculate cost."""
    try:
        json_response = json.loads(response.choices[0].message.function_call.arguments)
        cost = open_ai_cost(response)
        return json_response, cost
    except Exception as e:
        print(f"\nprocess_jobs_page -- Error processing:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("Error traceback:")
        import traceback
        traceback.print_exc()
        print("\n")
        return False, False

def process_jobs_page_with_gpt(html: str) -> Tuple[Dict, float]:
    """Process job listings page using GPT model."""
    client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[{'role': 'user', 'content': html}],
        functions=create_job_page_schema(),
        function_call='auto'
    )
    return process_gpt_response(response)

def is_fully_qualified_domain(url: str) -> bool:
    """Check if URL is fully qualified with scheme and netloc."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception as e:
        print(f"Error parsing URL: {url}")
        return False

def pretty_round(number: float) -> float:
    """Round number maintaining up to 2 significant decimal places."""
    str_num = str(number)
    if '.' in str_num:
        integer_part, fractional_part = str_num.split('.')
        for i, digit in enumerate(fractional_part):
            if digit != '0':
                if i >= 1:  # We've found 2 non-zero digits
                    return round(number, i + 1)
    return round(number, 2)

def generate_single_xpath(element: Tag) -> str:
    """Generate XPath for a single element."""
    components = []
    child = element if element.name else element.parent
    
    for parent in child.parents:
        siblings = parent.find_all(child.name, recursive=False)
        if siblings == [child]:
            components.append(child.name)
        else:
            components.append(f"{child.name}[{siblings.index(child) + 1}]")
        child = parent
        
    components.reverse()
    return '/' + '/'.join(components)

def generate_xpaths_for_all_elements(html_content: str) -> Dict[str, str]:
    """Generate XPaths for all elements in HTML content."""
    soup = BeautifulSoup(html_content, 'lxml')
    xpaths = {}
    
    for element in soup.find_all():
        xpath = generate_single_xpath(element)
        xpaths[xpath] = str(element)
    
    # Sort by XPath complexity (number of slashes)
    return dict(sorted(xpaths.items(), key=lambda x: x[0].count('/'), reverse=True))

def find_xpath_for_string(xpaths_dict: Dict[str, str], html_fragments: List[str]) -> Dict[str, str]:
    """Find matching XPaths for given HTML fragments."""
    return {
        fragment: next((xpath for xpath, html in xpaths_dict.items() if fragment in html), None)
        for fragment in html_fragments
    }



def validate_xpath(xpath: str) -> bool:
    """
    Validate if an XPath expression is syntactically correct.
    
    Args:
        xpath: String containing the XPath expression
    
    Returns:
        bool: True if valid, False if invalid
    """
    try:
        # Try to compile the XPath expression
        etree.XPath(xpath)
        return True
    except etree.XPathSyntaxError:
        return False
    except Exception:
        return False

def generalize_xpath(xpaths_dict: Dict[str, str]) -> Tuple[Optional[str], float]:
    """Generalize XPaths to find common pattern."""
    xpaths = '\n'.join(natsorted(str(v) for v in xpaths_dict.values()))
    
    prompt = (
        "Please review the below XPATHS (one per line) and see if they have commonalities, "
        "if they do please return a generic XPATH selector that will select the majority "
        "of the elements, if it looks like a range use the asterisk to select all, "
        "typically there will be one asterisk in the generic XPATH. Do NOT add any "
        "formatting or explanation, just return the raw XPATH string. If you can't "
        "figure out a generic XPATH, reply with 'False':\n\n"
        f"{xpaths}"
    )
    
    gpt_output, cost = gpt_me(prompt, 'gpt-4o-mini', None, True)
    cleaned_xpath = gpt_output.replace('```xpath', '').replace('```', '').strip()
    
    # Validate the cleaned XPath
    if cleaned_xpath and cleaned_xpath.lower() != 'false':
        if not validate_xpath(cleaned_xpath):
            print(f"Warning: Generated XPath '{cleaned_xpath}' is invalid")
            return False, cost
            
    return cleaned_xpath, cost

def sift_next_page_link(html: str) -> Tuple[Optional[str], Optional[int], float]:
    """Analyze HTML to find pagination pattern."""
    prompt = (
        "Please review the below HTML and find links to pages, try to discern a page "
        "number/increment pattern ie \"jobs/search?page=1&query=example\", "
        "\"jobs/search?page=2&query=example\" or \"https://example.com/jobs?from=10&s=1&rk=l-faculty-jobs\", "
        "\"https://example.com/jobs?from=20&s=1&rk=l-faculty-jobs\", "
        "\"https://example.com/jobs?from=30&s=1&rk=l-faculty-jobs\". DO NOT EXPLAIN, "
        "just reply with the pattern with no number at the end ie \"jobs/search?query=example&page=\". "
        "If the pattern seems to increment by a number other than 1 reply with the pattern "
        "with no number at the end then a tilde (~) and the increment number ie "
        "\"https://example.com/jobs?s=1&rk=l-faculty-jobs&from=~10\". If you can't find "
        f"a pattern, reply with the string \"False\":\n\n{html}"
    )
    
    gpt_output, cost = gpt_me(prompt, 'gpt-4o-mini', None, True)
    gpt_output = gpt_output.replace('```html\n', '').replace('\n```', '').strip()
    
    if len(gpt_output.strip()) <= 5:
        return False, False, False
    
    if '~' in gpt_output:
        base_url, increment = gpt_output.split('~')
        return base_url, int(increment), cost
    
    base_url = re.sub(r'(^.+=).+', '$1', gpt_output).replace('$1', '')
    return base_url, 1, cost


def analyze_pagination(next_page: str, base_url: str) -> Tuple[Optional[str], Optional[int]]:
    """Analyze pagination pattern and extract URL and increment."""
    if not next_page:
        return None, None
        
    sifted_next_page_url, page_increment, _ = sift_next_page_link(next_page)
    
    if not sifted_next_page_url:
        return None, None
    
    if is_fully_qualified_domain(sifted_next_page_url):
        full_url = sifted_next_page_url
    else:
        parsed_url = urlparse(base_url)
        base_domain = urlunparse((parsed_url.scheme, parsed_url.netloc, '', '', '', ''))
        full_url = urljoin(base_domain + '/', sifted_next_page_url)
    
    return full_url, page_increment