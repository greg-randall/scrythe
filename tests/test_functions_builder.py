import pytest
from bs4 import BeautifulSoup
from unittest.mock import patch, Mock, MagicMock
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
    write_config_to_csv,  # Add this if it was moved
    pretty_round,
    filter_xpath_patterns,
    sift_next_page_link,
    create_job_page_schema,
    process_gpt_response
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


def test_pretty_round():
    """Test pretty_round number formatting."""
    # Test basic rounding
    assert pretty_round(1.2345) == 1.23
    assert pretty_round(1.2) == 1.2
    assert pretty_round(1.0) == 1.0
    
    # Test with trailing zeros
    assert pretty_round(1.20000) == 1.2
    assert pretty_round(1.00100) == 1.001
    
    # Test with very small numbers
    assert pretty_round(0.00123) == 0.001
    assert pretty_round(0.000123) == 0.0001

def test_filter_xpath_patterns():
    """Test filtering and grouping of XPath patterns."""
    # Test with similar patterns
    similar_xpaths = [
        "/html/body/div[1]/a",
        "/html/body/div[2]/a",
        "/html/body/div[3]/a",
        "/html/body/div[1]/span"  # Different pattern
    ]
    filtered = filter_xpath_patterns(similar_xpaths)
    assert len(filtered) == 3  # Should exclude the span pattern
    assert all("div" in xpath for xpath in filtered)
    
    # Test with no clear pattern
    diverse_xpaths = [
        "/html/body/div[1]/a",
        "/html/body/span/p",
        "/html/section/article",
        "/div/p/span"
    ]
    filtered = filter_xpath_patterns(diverse_xpaths)
    assert len(filtered) == 4  # Should return original list if no clear pattern
    
    # Test with empty input
    assert filter_xpath_patterns([]) == []
    
    # Test with single item
    single_xpath = ["/html/body/div[1]/a"]
    assert filter_xpath_patterns(single_xpath) == single_xpath

def test_sift_next_page_link():
    """Test pagination pattern analysis."""
    # Test standard pagination
    html_standard = '''
    <div class="pagination">
        <a href="/jobs/search?page=1">1</a>
        <a href="/jobs/search?page=2">2</a>
        <a href="/jobs/search?page=3">3</a>
    </div>
    '''
    url, increment, cost = sift_next_page_link(html_standard)
    assert url == "/jobs/search?page="
    assert increment == 1
    assert isinstance(cost, float)
    
    # Test non-standard increment
    html_nonstandard = '''
    <div class="pagination">
        <a href="/jobs?from=10">Page 1</a>
        <a href="/jobs?from=20">Page 2</a>
        <a href="/jobs?from=30">Page 3</a>
    </div>
    '''
    url, increment, cost = sift_next_page_link(html_nonstandard)
    assert url == "/jobs?from="
    assert increment == 10
    assert isinstance(cost, float)
    
    # Test no pagination
    html_no_pagination = '<div>No pagination here</div>'
    url, increment, cost = sift_next_page_link(html_no_pagination)
    assert url is False
    assert increment is False
    assert cost is False

def test_create_job_page_schema():
    """Test job page schema creation."""
    schema = create_job_page_schema()
    
    # Verify schema structure
    assert isinstance(schema, list)
    assert len(schema) == 1
    assert 'name' in schema[0]
    assert 'description' in schema[0]
    assert 'parameters' in schema[0]
    
    # Verify parameters
    params = schema[0]['parameters']
    assert params['type'] == 'object'
    assert 'job_elements' in params['properties']
    assert 'next_page' in params['properties']
    assert params['required'] == ['next_page', 'job_elements']

def test_process_gpt_response():
    """Test GPT response processing."""
    # Test successful response
    mock_response = Mock()
    mock_response.choices = [
        Mock(
            message=Mock(
                function_call=Mock(
                    arguments='{"job_elements": ["job1", "job2"], "next_page": "<a>Next</a>"}'
                )
            )
        )
    ]
    mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50)
    mock_response.model = "gpt-4o-mini"
    
    result, cost = process_gpt_response(mock_response)
    assert isinstance(result, dict)
    assert 'job_elements' in result
    assert 'next_page' in result
    assert isinstance(cost, float)
    assert result['job_elements'] == ['job1', 'job2']
    assert result['next_page'] == '<a>Next</a>'
    
    # Test invalid JSON response
    mock_response.choices[0].message.function_call.arguments = 'invalid json'
    result, cost = process_gpt_response(mock_response)
    assert result is False
    assert cost is False
    
    # Test with missing function call
    mock_response.choices[0].message = Mock(content="Some content")
    mock_response.choices[0].message.function_call = None
    result, cost = process_gpt_response(mock_response)
    assert result is False
    assert cost is False