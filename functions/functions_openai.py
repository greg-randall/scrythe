"""
OpenAI API interaction utilities for cost calculation and API calls.
Includes pricing data and helper functions for API interaction.
"""

from typing import Dict, Union, Optional, Tuple
from decimal import Decimal
import os
from openai import OpenAI
from openai.types.chat import ChatCompletion
from openai.types.chat import ChatCompletionMessage

# Type aliases
Cost = Dict[str, Dict[str, float]]
ModelName = str
ApiKey = str

# Pricing data per million tokens for different OpenAI models
OPENAI_COSTS: Cost = {
    'gpt-4o': {
        'input': 2.50 / 1000000,
        'batch_input': 1.25 / 1000000,
        'cached_input': 1.25 / 1000000,
        'output': 10.00 / 1000000,
        'batch_output': 5.00 / 1000000
    },
    'gpt-4o-mini': {
        'input': 0.150 / 1000000,
        'batch_input': 0.075 / 1000000,
        'cached_input': 0.075 / 1000000,
        'output': 0.600 / 1000000,
        'batch_output': 0.300 / 1000000
    },
    'o1-preview': {
        'input': 15.00 / 1000000,
        'cached_input': 7.50 / 1000000,
        'output': 60.00 / 1000000
    },
    'o1-mini': {
        'input': 3.00 / 1000000,
        'cached_input': 1.50 / 1000000,
        'output': 12.00 / 1000000
    },
    'gpt-4-turbo': {
        'input': 10.00 / 1000000,
        'output': 30.00 / 1000000
    },
    'gpt-4': {
        'input': 30.00 / 1000000,
        'output': 60.00 / 1000000
    },
    'gpt-4-32k': {
        'input': 60.00 / 1000000,
        'output': 120.00 / 1000000
    },
    'gpt-3.5-turbo': {
        'input': 0.50 / 1000000,
        'output': 1.50 / 1000000
    },
    'gpt-3.5-turbo-instruct': {
        'input': 1.50 / 1000000,
        'output': 2.00 / 1000000
    }
}

def normalize_model_name(model: str) -> str:
    """
    Normalize model name to match pricing data keys.
    
    Args:
        model: Raw model name from API response
        
    Returns:
        Normalized model name that matches pricing data
    """
    if model.startswith('gpt-4o'):
        return 'gpt-4o'
    return 'o1-preview' if model not in OPENAI_COSTS else model

def get_model_costs(model: str) -> Tuple[float, float]:
    """
    Get input and output costs for a specific model.
    
    Args:
        model: Normalized model name
        
    Returns:
        Tuple of (input_cost, output_cost)
    """
    model_costs = OPENAI_COSTS.get(model, OPENAI_COSTS['o1-preview'])
    return model_costs['input'], model_costs['output']

def calculate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    input_cost: float,
    output_cost: float
) -> float:
    """
    Calculate total cost based on token counts and rates.
    
    Args:
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens
        input_cost: Cost per input token
        output_cost: Cost per output token
        
    Returns:
        Total cost for the API call
    """
    return (prompt_tokens * input_cost) + (completion_tokens * output_cost)

def open_ai_cost(response: ChatCompletion) -> float:
    """
    Calculate the cost of an OpenAI API response.
    
    Args:
        response: OpenAI API response object
        
    Returns:
        Total cost of the API call
    """
    model = normalize_model_name(response.model)
    
    if model not in OPENAI_COSTS:
        print("Model not found, using the most expensive model")
        
    input_cost, output_cost = get_model_costs(model)
    
    return calculate_cost(
        response.usage.prompt_tokens,
        response.usage.completion_tokens,
        input_cost,
        output_cost
    )

def get_api_key(key: Optional[str] = None) -> str:
    """
    Get OpenAI API key from argument or environment.
    
    Args:
        key: Optional API key provided directly
        
    Returns:
        API key to use
        
    Raises:
        ValueError: If no API key is available
    """
    if key is not None:
        return key
        
    env_key = os.getenv('OPENAI_API_KEY')
    if env_key is not None:
        return env_key
        
    raise ValueError(
        "API key must be provided either as an argument or set in the environment variable 'OPENAI_API_KEY'"
    )

def create_chat_message(prompt: str) -> Dict[str, str]:
    """
    Create a chat message dictionary for the API.
    
    Args:
        prompt: Message content
        
    Returns:
        Formatted chat message dictionary
    """
    return {
        "role": "user",
        "content": prompt
    }

def gpt_me(
    prompt: str,
    model: str,
    key: Optional[str] = None,
    return_cost: bool = False
) -> Union[str, Tuple[str, float]]:
    """
    Send a prompt to OpenAI's API and get the response.
    
    Args:
        prompt: Input text to send to the model
        model: Model name to use
        key: Optional API key
        return_cost: Whether to return cost information
        
    Returns:
        Model response text, or tuple of (response text, cost) if return_cost is True
    """
    api_key = get_api_key(key)
    client = OpenAI(api_key=api_key)
    
    chat_completion = client.chat.completions.create(
        messages=[create_chat_message(prompt)],
        model=model
    )
    
    response_text = chat_completion.choices[0].message.content
    
    if return_cost:
        cost = open_ai_cost(chat_completion)
        return response_text, cost
        
    return response_text