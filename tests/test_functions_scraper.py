import pytest
import csv
from pathlib import Path
from datetime import timedelta
import hashlib
from unittest.mock import patch, mock_open, Mock
from functions.functions_scraper import (
    ensure_cache_dir_exists,
    generate_url_hash,
    create_cache_filename,
    get_file_length,
    should_update_cache,
    manage_cache_file,
    normalize_url,
    is_new_job,
    should_stop_scraping,
    process_jobs_page,
    parse_scraper_config,
    load_scraper_configs,
    randomize_configs,
    get_site_name,
    determine_start_page,
    scrape_single_site
)

@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory for testing."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir

@pytest.fixture
def mock_driver():
    """Create a mock Selenium WebDriver."""
    driver = Mock()
    driver.page_source = "<html><body>Test content</body></html>"
    driver.current_url = "https://example.com"
    return driver

def test_ensure_cache_dir_exists(tmp_path, monkeypatch):
    """Test cache directory creation."""
    cache_dir = tmp_path / "cache"
    monkeypatch.setattr("functions.functions_scraper.CACHE_DIR", cache_dir)
    
    ensure_cache_dir_exists()
    assert cache_dir.exists()
    assert cache_dir.is_dir()

def test_generate_url_hash():
    """Test URL hash generation."""
    url = "https://example.com/jobs"
    hash_value = generate_url_hash(url)
    
    # Verify it matches direct SHA256 calculation
    expected_hash = hashlib.sha256(url.encode()).hexdigest()
    assert hash_value == expected_hash
    assert len(hash_value) == 64  # SHA256 produces 64 character hex string

def test_create_cache_filename():
    """Test cache filename generation."""
    name = "test_site"
    url = "https://example.com/jobs"
    filename = create_cache_filename(name, url)
    
    assert filename.startswith("test_site_")
    assert filename.endswith(".html")
    assert generate_url_hash(url) in filename

def test_get_file_length(tmp_path):
    """Test file length calculation."""
    test_file = tmp_path / "test.txt"
    test_content = "Test content\nwith multiple lines"
    test_file.write_text(test_content)
    
    assert get_file_length(test_file) == len(test_content)
    
    # Test with non-existent file
    non_existent = tmp_path / "nonexistent.txt"
    assert get_file_length(non_existent) == 0

def test_should_update_cache(tmp_path):
    """Test cache update checking."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")
    
    # Test with fresh file
    assert not should_update_cache(
        test_file,
        max_age=timedelta(days=1),
        min_length=5
    )
    
    # Test with short content
    short_file = tmp_path / "short.txt"
    short_file.write_text("Hi")
    assert should_update_cache(
        short_file,
        max_age=timedelta(days=1),
        min_length=5
    )

def test_manage_cache_file(tmp_path, monkeypatch):
    """Test cache file management."""
    cache_dir = tmp_path / "cache"
    monkeypatch.setattr("functions.functions_scraper.CACHE_DIR", cache_dir)
    
    filename = "test.html"
    
    # Test with non-existent cache
    assert not manage_cache_file(filename)
    assert cache_dir.exists()
    
    # Test with existing valid cache
    cache_file = cache_dir / filename
    cache_file.write_text("Test content")
    assert manage_cache_file(
        filename,
        max_age=timedelta(days=1),
        min_length=5
    )

def test_normalize_url():
    """Test URL normalization."""
    base_url = "https://example.com"
    
    # Test absolute URL
    assert normalize_url(base_url, "https://other.com/jobs") == "https://other.com/jobs"
    
    # Test relative URL
    assert normalize_url(base_url, "/jobs") == "https://example.com/jobs"
    
    # Test relative URL without leading slash
    assert normalize_url(base_url, "careers") == "https://example.com/careers"

def test_is_new_job():
    """Test job uniqueness checking."""
    existing_jobs = {"job1", "job2", "job3"}
    
    assert is_new_job("job4", existing_jobs)
    assert not is_new_job("job2", existing_jobs)
    assert is_new_job("", existing_jobs)

def test_should_stop_scraping():
    """Test scraping stop condition."""
    # Test below threshold
    assert not should_stop_scraping(3, max_consecutive=5)
    
    # Test at threshold
    assert should_stop_scraping(5, max_consecutive=5)
    
    # Test above threshold
    assert should_stop_scraping(6, max_consecutive=5)
    
    # Test with custom threshold
    assert should_stop_scraping(3, max_consecutive=3)

def test_process_jobs_page(mock_driver):
    """Test job page processing."""
    xpath = "//div[@class='job']"
    base_url = "https://example.com"
    existing_jobs = set()
    
    # Mock driver to return some job links
    mock_driver.find_elements.return_value = [
        type('Element', (), {'get_attribute': lambda x: '/job1'}),
        type('Element', (), {'get_attribute': lambda x: '/job2'})
    ]
    
    jobs = process_jobs_page(mock_driver, xpath, base_url, existing_jobs)
    
    assert len(jobs) == 2
    assert all(job.startswith('https://example.com/') for job in jobs)

def test_parse_scraper_config():
    """Test parsing of CSV row into config dict."""
    row = ['timestamp', 'unix_time', '//div[@class="job"]', 'https://example.com/jobs?page=', '1']
    config = parse_scraper_config(row)
    
    assert config['xpath'] == '//div[@class="job"]'
    assert config['url'] == 'https://example.com/jobs?page='
    assert config['increment'] == 1

def test_load_scraper_configs(tmp_path):
    """Test loading configurations from CSV file."""
    csv_content = '''timestamp,unix_time,xpath,url,increment
2024-01-01,1704067200,//div[@class="job"],https://example.com/jobs?page=,1
2024-01-01,1704067200,//a[@class="position"],https://test.com/careers/,10'''
    
    csv_path = tmp_path / "test_config.csv"
    csv_path.write_text(csv_content)
    
    configs = load_scraper_configs(str(csv_path))
    assert len(configs) == 2
    assert configs[0]['increment'] == 1
    assert configs[1]['increment'] == 10

def test_randomize_configs():
    """Test configuration randomization."""
    configs = [
        {'url': 'url1', 'xpath': 'xpath1', 'increment': 1},
        {'url': 'url2', 'xpath': 'xpath2', 'increment': 2},
        {'url': 'url3', 'xpath': 'xpath3', 'increment': 3}
    ]
    
    randomized = randomize_configs(configs)
    
    # Check that all configs are present
    assert len(randomized) == len(configs)
    assert all(config in randomized for config in configs)
    
    # Check that original configs weren't modified
    assert configs[0]['url'] == 'url1'

def test_get_site_name():
    """Test site name extraction from URL."""
    assert get_site_name("https://example.com/jobs") == "example.com"
    assert get_site_name("http://test.org/careers/") == "test.org"
    assert get_site_name("https://sub.domain.net/path") == "sub.domain.net"

def test_determine_start_page():
    """Test start page determination."""
    assert determine_start_page(1) == 1
    assert determine_start_page(10) == 0
    assert determine_start_page(20) == 0

def test_scrape_single_site(mock_driver):
    """Test scraping process for a single site."""
    config = {
        'xpath': '//div[@class="job"]',
        'url': 'https://example.com/jobs?page=',
        'increment': 1
    }
    
    # Mock the necessary functions
    with patch('functions.functions_scraper.generic_paged_scraper_by_xpath', return_value=['job1', 'job2']), \
         patch('functions.functions_scraper.download_all_links') as mock_download:
        
        scrape_single_site(config, mock_driver)
        
        # Verify download was called with correct arguments
        mock_download.assert_called_once()