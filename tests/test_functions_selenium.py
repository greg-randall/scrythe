import pytest
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from functions.functions_selenium import (
    create_browser_config,
    setup_chrome_options,
    setup_chrome_capabilities,
    analyze_network_activity,
    wait_for_page_load,
    navigate_and_wait,
    get_page_html,
    extract_links_by_xpath
)


def test_create_browser_config():
    """Test browser configuration creation."""
    config = create_browser_config(debug=False)
    
    assert hasattr(config, 'user_agent')
    assert hasattr(config, 'screen_size')
    assert hasattr(config, 'debug')
    assert isinstance(config.user_agent, str)
    assert isinstance(config.screen_size, str)
    assert config.debug is False

def test_setup_chrome_options():
    """Test Chrome options setup."""
    config = create_browser_config(debug=False)
    options = setup_chrome_options(config)
    
    assert isinstance(options, Options)
    assert "--disable-blink-features=AutomationControlled" in options.arguments
    assert any(arg.startswith("user-agent=") for arg in options.arguments)
    assert any(arg.startswith("--window-size=") for arg in options.arguments)
    assert "--headless" in options.arguments
    
    # Test debug mode
    debug_config = create_browser_config(debug=True)
    debug_options = setup_chrome_options(debug_config)
    assert "--headless" not in debug_options.arguments

def test_setup_chrome_capabilities():
    """Test Chrome capabilities setup."""
    capabilities = setup_chrome_capabilities()
    
    assert isinstance(capabilities, dict)
    assert 'goog:loggingPrefs' in capabilities
    assert 'performance' in capabilities['goog:loggingPrefs']
    assert capabilities['goog:loggingPrefs']['performance'] == 'ALL'

def test_analyze_network_activity(mock_driver):
    """Test network activity analysis."""
    # Test initial call
    is_loaded, length = analyze_network_activity(mock_driver, None)
    assert not is_loaded
    assert isinstance(length, int)
    
    # Test subsequent call with no new activity
    mock_driver.get_log.return_value = []
    is_loaded, length = analyze_network_activity(mock_driver, 10)
    assert is_loaded
    assert length == 0
    
    # Test with new activity
    mock_driver.get_log.return_value = ['event1', 'event2']
    is_loaded, length = analyze_network_activity(mock_driver, 1)
    assert not is_loaded
    assert length == 2

def test_wait_for_page_load(mock_driver):
    """Test page load waiting."""
    mock_driver.get_log.return_value = []
    
    with wait_for_page_load(mock_driver, timeout=1, sleep=0.1):
        pass
    
    assert mock_driver.get_log.called

def test_navigate_and_wait(mock_driver):
    """Test navigation with waiting."""
    url = "https://example.com"
    result = navigate_and_wait(mock_driver, url, timeout=1, sleep=0.1)
    
    assert result == mock_driver
    mock_driver.get.assert_called_once_with(url)

def test_get_page_html(mock_driver):
    """Test HTML content retrieval."""
    mock_driver.page_source = "<html><body>Test content</body></html>"
    html = get_page_html(mock_driver)
    
    assert isinstance(html, str)
    assert "Test content" in html
    
    # Test error handling
    mock_driver.page_source = None
    html = get_page_html(mock_driver)
    assert html == ""

def test_extract_links_by_xpath(mock_driver):
    """Test link extraction by XPath."""
    # Mock elements with href attributes
    mock_elements = [
        type('Element', (), {'get_attribute': lambda x: 'https://example.com/job1'}),
        type('Element', (), {'get_attribute': lambda x: 'https://example.com/job2'}),
        type('Element', (), {'get_attribute': lambda x: None})  # Test element without href
    ]
    mock_driver.find_elements.return_value = mock_elements
    
    links = extract_links_by_xpath(mock_driver, "//a[@class='job']")
    
    assert len(links) == 2
    assert all(link.startswith('https://example.com/') for link in links)
    mock_driver.find_elements.assert_called_once()