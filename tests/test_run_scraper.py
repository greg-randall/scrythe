# tests/test_run_scraper.py
import pytest
from unittest.mock import patch, Mock, mock_open
import sys
from pathlib import Path

# Import functions to test
from run_scraper import run_scrapers, main

@pytest.fixture
def mock_selenium(monkeypatch):
    """Mock Selenium-related functions."""
    mock_driver = Mock()
    mock_driver.page_source = "<html><body>Test content</body></html>"
    
    def mock_init_selenium(*args, **kwargs):
        return mock_driver
    
    monkeypatch.setattr("run_scraper.init_selenium", mock_init_selenium)
    return mock_driver

@pytest.fixture
def mock_configs():
    """Create sample scraper configurations."""
    return [
        {
            'xpath': "//div[@class='job']",
            'url': "https://example.com/jobs?page=",
            'increment': 1
        },
        {
            'xpath': "//a[@class='position']",
            'url': "https://test.com/careers/",
            'increment': 10
        }
    ]

def test_run_scrapers(mock_selenium, mock_configs):
    """Test the main scraper execution function."""
    with patch('run_scraper.scrape_single_site') as mock_scrape:
        run_scrapers(mock_configs, mock_selenium)
        
        # Verify each config was processed
        assert mock_scrape.call_count == len(mock_configs)
        
        # Verify correct arguments were passed
        for idx, call in enumerate(mock_scrape.call_args_list):
            args, kwargs = call
            assert args[0] == mock_configs[idx]
            assert args[1] == mock_selenium

def test_main_function(mock_selenium):
    """Test the main function execution flow."""
    mock_configs = [{'xpath': '//div', 'url': 'https://test.com', 'increment': 1}]
    
    with patch('run_scraper.load_scraper_configs', return_value=mock_configs) as mock_load, \
         patch('run_scraper.run_scrapers') as mock_run:
             
        main()
        
        # Verify configurations were loaded
        mock_load.assert_called_once_with('sites_to_scrape.csv')
        
        # Verify scrapers were run
        mock_run.assert_called_once()
        
        # Verify driver was properly cleaned up
        mock_selenium.quit.assert_called_once()

def test_main_function_error_handling(mock_selenium):
    """Test error handling in main function."""
    with patch('run_scraper.load_scraper_configs', side_effect=Exception("Test error")), \
         pytest.raises(SystemExit) as exc_info:
        main()
        
        # Verify driver is cleaned up even if an error occurs
        mock_selenium.quit.assert_called_once()
        assert exc_info.value.code == 1  # Verify correct exit code