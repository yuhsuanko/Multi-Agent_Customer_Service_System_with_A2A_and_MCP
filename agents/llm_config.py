# agents/llm_config.py
"""
LLM configuration and initialization utilities.

This module provides LLM instances for agent reasoning.
Supports OpenAI, Anthropic, and other LangChain-compatible LLMs.
"""

import os
from typing import Optional

# Optional imports - will fail gracefully if packages not installed
try:
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    ChatOpenAI = None

try:
    from langchain_anthropic import ChatAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    ChatAnthropic = None

try:
    from langchain_core.language_models import BaseChatModel
except ImportError:
    BaseChatModel = object  # Fallback if not available

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use environment variables only


def get_llm(
    model_name: Optional[str] = None,
    provider: Optional[str] = None,
    temperature: float = 0.0,
) -> BaseChatModel:
    """
    Initialize and return an LLM instance for agent reasoning.
    
    Args:
        model_name: Name of the model (e.g., "gpt-4", "claude-3-sonnet")
        provider: "openai", "anthropic", or None (auto-detect from env)
        temperature: Temperature for LLM responses (0.0 = deterministic)
    
    Returns:
        A LangChain ChatModel instance
    
    Environment Variables:
        - OPENAI_API_KEY: OpenAI API key
        - ANTHROPIC_API_KEY: Anthropic API key
        - LLM_PROVIDER: "openai" or "anthropic" (default: "openai")
        - LLM_MODEL: Model name (default: "gpt-3.5-turbo" or "claude-3-haiku")
    """
    # Determine provider
    if provider is None:
        provider = os.getenv("LLM_PROVIDER", "openai").lower()
    
    # Determine model name
    if model_name is None:
        if provider == "anthropic":
            model_name = os.getenv("LLM_MODEL", "claude-3-haiku-20240307")
        else:
            model_name = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    
    # Initialize LLM based on provider
    if provider == "anthropic":
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "langchain-anthropic is not installed. "
                "Install it with: pip install langchain-anthropic"
            )
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found in environment. "
                "Please set it or use OPENAI_API_KEY with provider='openai'"
            )
        return ChatAnthropic(
            model=model_name,
            temperature=temperature,
            api_key=api_key,
        )
    
    elif provider == "openai":
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "langchain-openai is not installed. "
                "Install it with: pip install langchain-openai"
            )
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment. "
                "Please set it in a .env file or export it."
            )
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key,
        )
    
    else:
        raise ValueError(
            f"Unsupported provider: {provider}. "
            "Supported providers: 'openai', 'anthropic'"
        )


# Default LLM instance for agents
_llm_cache: Optional[BaseChatModel] = None


def get_default_llm() -> Optional[BaseChatModel]:
    """
    Get or create a default LLM instance (cached).
    
    Returns None if no API key is configured, allowing fallback logic to be used.
    """
    global _llm_cache
    if _llm_cache is None:
        try:
            _llm_cache = get_llm()
        except ValueError as e:
            print(f"Warning: {e}")
            print("Agents will use rule-based fallback logic instead of LLM reasoning.")
            return None
    return _llm_cache

