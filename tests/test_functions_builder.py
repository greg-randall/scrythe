import pytest
from bs4 import BeautifulSoup
from functions.functions_builder import (
    clean_page,
    clean_html_attributes,
    clean_html_content,
    is_fully_qualified_domain,
    validate_xpath,
    generate_single_xpath,
    generate_xpaths_for_all_elements,
    process_jobs_page_with_gpt,
    extract_job_urls,  # Add this to test the moved function
    process_and_extract_jobs,  # Add this if it was moved
    analyze_pagination,  # Add this if it was moved
    write_config_to_csv  # Add this if it was moved
)

# Add new test for extract_job_urls function
def test_extract_job_urls():
    """Test extraction of job URLs from various formats."""
    job_elements = [
        "https://example.com/job1",  # Direct URL
        "<a href='https://example.com/job2'>Job 2</a>",  # HTML with absolute URL
        "<a href='/job3'>Job 3</a>",  # HTML with relative URL
        "invalid<>html"  # Invalid HTML
    ]
    
    urls = extract_job_urls(job_elements)
    assert len(urls) == 3
    assert "https://example.com/job1" in urls
    assert "https://example.com/job2" in urls
    assert "/job3" in urls


def test_clean_html_attributes():
    """Test cleaning of HTML attributes."""
    soup = BeautifulSoup('<div data-test="test" class="keep">Content</div>', 'html.parser')
    tag = soup.div
    
    # Test normal cleaning
    clean_html_attributes(tag, extra_cleaning=False)
    assert 'data-test' in tag.attrs
    assert 'class' in tag.attrs
    
    # Test extra cleaning
    clean_html_attributes(tag, extra_cleaning=True)
    assert 'data-test' not in tag.attrs
    assert 'class' not in tag.attrs

def test_clean_html_content():
    """Test cleaning of HTML content."""
    html = '''
    <html>
        <head><script>test</script></head>
        <body>
            <div>Content</div>
            <footer>Footer</footer>
            <img src="data:image/jpeg;base64,test"/>
        </body>
    </html>
    '''
    soup = BeautifulSoup(html, 'html.parser')
    
    # Test normal cleaning
    cleaned = clean_html_content(soup, extra_cleaning=False)
    assert cleaned.find('script') is None
    assert cleaned.find('footer') is None
    assert cleaned.find('div') is not None
    
    # Test extra cleaning
    cleaned = clean_html_content(soup, extra_cleaning=True)
    assert cleaned.find('script') is None
    assert cleaned.find('footer') is None
    assert cleaned.find('img') is None

def test_clean_page():
    """Test HTML cleaning functionality."""
    html = """
    <html>
        <head><script>test</script></head>
        <body>
            <div>Content</div>
            <footer>Footer</footer>
        </body>
    </html>
    """
    cleaned = clean_page(html)
    assert "<script>" not in cleaned
    assert "<footer>" not in cleaned
    assert "Content" in cleaned

def test_is_fully_qualified_domain():
    """Test URL qualification checking."""
    assert is_fully_qualified_domain("https://example.com/jobs")
    assert is_fully_qualified_domain("http://example.com")
    assert not is_fully_qualified_domain("/jobs")
    assert not is_fully_qualified_domain("example.com")
    assert not is_fully_qualified_domain("")

def test_validate_xpath():
    """Test XPath validation."""
    assert validate_xpath("//div[@class='job']")
    assert validate_xpath("//a[contains(@href, 'jobs')]")
    assert not validate_xpath("//div[")
    assert not validate_xpath("invalid xpath")

def test_generate_single_xpath():
    """Test generation of XPath for a single element."""
    html = '<div><p class="test">Text</p></div>'
    soup = BeautifulSoup(html, 'html.parser')
    p_tag = soup.find('p')
    xpath = generate_single_xpath(p_tag)
    assert xpath.startswith('/')
    assert 'p' in xpath
    assert isinstance(xpath, str)

def test_generate_xpaths_for_all_elements():
    """Test XPath generation for all elements."""
    html = '<div><p>Test1</p><p>Test2</p></div>'
    xpaths = generate_xpaths_for_all_elements(html)
    
    assert isinstance(xpaths, dict)
    assert len(xpaths) >= 3  # div + 2 p tags
    assert any('p[1]' in xpath for xpath in xpaths.keys())
    assert any('p[2]' in xpath for xpath in xpaths.keys())

def test_generate_xpaths():
    """Test XPath generation for HTML elements."""
    html = "<div><p>Test</p><p>Test2</p></div>"
    xpaths = generate_xpaths_for_all_elements(html)
    assert isinstance(xpaths, dict)
    assert len(xpaths) > 0
    assert any("p[1]" in xpath for xpath in xpaths.keys())

def test_process_jobs_page_with_gpt(mock_openai):
    """Test job page processing with mocked OpenAI."""
    html = "<div><a href='/job1'>Job 1</a><a href='/job2'>Job 2</a></div>"
    result, cost = process_jobs_page_with_gpt(html)