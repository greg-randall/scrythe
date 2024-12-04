# tests/test_functions_openai.py
import pytest
from unittest.mock import MagicMock
from functions.functions_openai import (
    normalize_model_name,
    get_model_costs,
    calculate_cost,
    open_ai_cost,
    get_api_key,
    create_chat_message
)

def test_normalize_model_name():
    """Test model name normalization."""
    assert normalize_model_name('gpt-4o') == 'gpt-4o'
    assert normalize_model_name('gpt-4o-mini') == 'gpt-4o'
    assert normalize_model_name('unknown-model') == 'o1-preview'

def test_get_model_costs():
    """Test retrieval of model costs."""
    input_cost, output_cost = get_model_costs('gpt-4o-mini')
    assert isinstance(input_cost, float)
    assert isinstance(output_cost, float)
    assert input_cost > 0
    assert output_cost > 0

def test_calculate_cost():
    """Test cost calculation."""
    cost = calculate_cost(
        prompt_tokens=100,
        completion_tokens=50,
        input_cost=0.0015,
        output_cost=0.002
    )
    assert isinstance(cost, float)
    assert cost == (100 * 0.0015) + (50 * 0.002)

def test_open_ai_cost():
    """Test OpenAI API cost calculation."""
    mock_response = MagicMock()
    mock_response.model = 'gpt-4o-mini'
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    
    cost = open_ai_cost(mock_response)
    assert isinstance(cost, float)
    assert cost > 0

def test_get_api_key(monkeypatch):
    """Test API key retrieval."""
    # Test with direct key
    assert get_api_key('test-key') == 'test-key'
    
    # Test with environment variable
    monkeypatch.setenv('OPENAI_API_KEY', 'env-key')
    assert get_api_key() == 'env-key'
    
    # Test with missing key
    monkeypatch.delenv('OPENAI_API_KEY')
    with pytest.raises(ValueError):
        get_api_key()

def test_create_chat_message():
    """Test chat message creation."""
    message = create_chat_message("Test prompt")
    assert isinstance(message, dict)
    assert message['role'] == 'user'
    assert message['content'] == 'Test prompt'