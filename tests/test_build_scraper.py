import pytest
from unittest.mock import patch, Mock, mock_open
import sys
import os
from pathlib import Path
import time
from bs4 import BeautifulSoup
import tiktoken

# Update imports to get functions from their new locations
from build_scraper import (
    parse_arguments,
    verify_pagination,
    main
)
from functions.functions_builder import (
    initialize_tokenizer,
    extract_job_urls,
    process_and_extract_jobs,
    analyze_pagination,
    write_config_to_csv
)


@pytest.fixture
def mock_selenium(monkeypatch):
    """Mock Selenium-related functions."""
    mock_driver = Mock()
    mock_driver.page_source = "<html><body>Test content</body></html>"
    
    def mock_init_selenium(*args, **kwargs):
        return mock_driver
    
    def mock_navigate(*args, **kwargs):
        mock_driver.get(args[1])  # This ensures the get method is called with the URL
        return mock_driver
    
    monkeypatch.setattr("build_scraper.init_selenium", mock_init_selenium)
    monkeypatch.setattr("build_scraper.navigate_and_wait", mock_navigate)
    return mock_driver

@pytest.fixture
def mock_gpt_response():
    """Mock GPT response for job processing."""
    return {
        "job_elements": [
            "<a href='/job1'>Job 1</a>",
            "<a href='/job2'>Job 2</a>"
        ],
        "next_page": "<a href='/page/2'>Next</a>"
    }

def test_parse_arguments():
    """Test command line argument parsing."""
    # Test valid URL
    test_args = ['script.py', 'https://example.com']
    with patch.object(sys, 'argv', test_args):
        url, verbose = parse_arguments()
        assert url == 'https://example.com'
        assert verbose == False
    
    # Test invalid URL
    test_args = ['script.py', 'not-a-url']
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit):
            parse_arguments()
            
    # Test with verbose flag
    test_args = ['script.py', 'https://example.com', '-v']
    with patch.object(sys, 'argv', test_args):
        url, verbose = parse_arguments()
        assert url == 'https://example.com'
        assert verbose == True

def test_initialize_tokenizer():
    """Test tokenizer initialization with different HTML lengths."""
    # Test normal HTML
    normal_html = "<html><body>Test content</body></html>"
    result_html, tokenizer = initialize_tokenizer(normal_html)
    assert isinstance(tokenizer, tiktoken.Encoding)
    assert result_html == normal_html
    
    # Test long HTML that requires cleaning
    long_html = "<p>" + "test " * 500000 + "</p>"
    with pytest.raises(SystemExit):
        initialize_tokenizer(long_html)

def test_extract_job_urls():
    """Test extraction of job URLs from different element formats."""
    elements = [
        "https://example.com/job1",  # Direct URL
        "<a href='https://example.com/job2'>Job 2</a>",  # HTML with absolute URL
        "<a href='/job3'>Job 3</a>",  # HTML with relative URL
        "invalid<>html"  # Invalid HTML
    ]
    
    urls = extract_job_urls(elements)
    assert len(urls) == 3
    assert "https://example.com/job1" in urls
    assert "https://example.com/job2" in urls
    assert "/job3" in urls

@patch('functions.functions_builder.process_jobs_page_with_gpt')
def test_process_and_extract_jobs(mock_process, mock_gpt_response):
    """Test processing and extraction of jobs from HTML."""
    mock_process.return_value = (mock_gpt_response, 0.01)
    html = "<html><body>Test content</body></html>"
    
    jobs, next_page, cost = process_and_extract_jobs(html)
    
    assert isinstance(jobs, list)
    assert len(jobs) == 2
    assert all(job.startswith('/job') for job in jobs)
    assert next_page == "<a href='/page/2'>Next</a>"
    assert cost == 0.01

def test_analyze_pagination():
    """Test pagination pattern analysis."""
    next_page = '<a href="/jobs?page=2">Next</a>'
    base_url = "https://example.com"
    
    full_url, page_increment = analyze_pagination(next_page, base_url)
    
    assert full_url.startswith('https://example.com')
    assert page_increment == 1

def test_verify_pagination(mock_selenium):
    """Test pagination verification."""
    full_url = "https://example.com/jobs?page="
    page_increment = 1
    
    verify_pagination(mock_selenium, full_url, page_increment)
    
    # Verify that driver tried to navigate to page 2
    expected_url = f"{full_url}2"
    mock_selenium.get.assert_called_once_with(expected_url)

def test_write_config_to_csv(tmp_path):
    """Test writing configuration to CSV file."""
    # Create a temporary CSV file path
    csv_path = str(tmp_path / "sites_to_scrape.csv")
    
    # Test data
    timestamp_human = "2024-01-01 12:00:00"
    timestamp_unix = int(time.time())
    xpath = "//div[@class='job']"
    url = "https://example.com/jobs?page="
    increment = 1
    
    # Write to new file
    write_config_to_csv(
        timestamp_human,
        timestamp_unix,
        xpath,
        url,
        increment,
        file_path=csv_path  # Explicitly pass the file path
    )
    
    # Verify file exists and contains correct headers
    assert Path(csv_path).exists()
    with open(csv_path, 'r') as f:
        content = f.read()
        assert "Human Readable Timestamp" in content
        assert "Unix Timestamp" in content
        assert "Generic Job XPath" in content
        assert "Paged Link URL" in content
        assert "Page Increment Value" in content

@patch('build_scraper.init_selenium')
@patch('functions.functions_builder.process_jobs_page_with_gpt')
def test_main_function(mock_process, mock_selenium, mock_gpt_response, tmp_path):
    """Test the main function's execution flow."""
    # Mock command line arguments
    test_args = ['script.py', 'https://example.com']
    with patch.object(sys, 'argv', test_args):
        # Mock process_jobs_page response
        mock_process.return_value = (mock_gpt_response, 0.01)
        
        # Mock selenium driver
        mock_driver = Mock()
        mock_driver.page_source = "<html><body>Test content</body></html>"
        mock_selenium.return_value = mock_driver
        
        # Run main function
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        # Verify selenium was initialized
        assert mock_selenium.called
        
        # Verify navigation occurred
        assert mock_driver.get.called

def test_main_error_handling():
    """Test error handling in main function."""
    # Test with invalid URL
    test_args = ['script.py', 'invalid-url']
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit):
            main()
    
    # Test with missing OpenAI key
    test_args = ['script.py', 'https://example.com']
    with patch.object(sys, 'argv', test_args):
        with patch.dict(os.environ, clear=True):
            with pytest.raises(SystemExit):
                main()