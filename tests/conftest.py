import sys
from pathlib import Path
import warnings
from bs4.builder import ParserRejectedMarkup

# Set up paths
root_dir = str(Path(__file__).parent.parent)
sys.path.append(root_dir)

# Filter warnings
warnings.filterwarnings("ignore", message=".*strip_cdata.*", category=DeprecationWarning)

# Import your modules
from functions.functions_builder import clean_page, is_fully_qualified_domain, generate_xpaths_for_all_elements, process_jobs_page_with_gpt

# Import testing libraries
import pytest
from unittest.mock import MagicMock
from selenium import webdriver

def pytest_configure(config):
    """Configure pytest."""
    warnings.filterwarnings("ignore", message=".*strip_cdata.*", category=DeprecationWarning)

# Fixtures
@pytest.fixture
def mock_driver():
    """Mock Selenium WebDriver for testing."""
    driver = MagicMock(spec=webdriver.Chrome)
    driver.page_source = "<html><body>Test content</body></html>"
    driver.get_log.return_value = []
    return driver

@pytest.fixture
def mock_openai():
    """Mock OpenAI client for testing."""
    class MockOpenAI:
        def __init__(self, api_key=None):
            self.chat = MagicMock()
            self.chat.completions.create.return_value = MagicMock(
                choices=[
                    MagicMock(
                        message=MagicMock(
                            content="Test response",
                            function_call=MagicMock(
                                arguments='{"job_elements": ["job1", "job2"], "next_page": "<a>Next</a>"}'
                            )
                        )
                    )
                ],
                usage=MagicMock(prompt_tokens=100, completion_tokens=50),
                model="gpt-4o-mini"
            )
    return MockOpenAI