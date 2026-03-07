"""
Base Agent class using PydanticAI.
Abstract foundation for all specialized agents in the system.
"""

from abc import ABC
from typing import Any, Dict, Optional
from pydantic import BaseModel
from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.models.anthropic import AnthropicModel

from config import settings
from utils.logger import logger


class AgentConfig(BaseModel):
    """Configuration for agent instances."""
    model_name: str = settings.default_llm_model
    temperature: float = settings.temperature
    max_tokens: int = settings.max_tokens
    system_prompt: str = ""
    provider: str = settings.default_provider  # openai, google, anthropic


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents.
    Implements common functionality and enforces interface.
    Follows Open/Closed Principle - open for extension, closed for modification.

    Supports multiple LLM providers: OpenAI, Google Gemini, Anthropic.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        """
        Initialize base agent.

        Args:
            config: Agent configuration
        """
        self.config = config or AgentConfig()
        self.model = self._create_model()
        self._agent: Optional[PydanticAgent] = None
        logger.info(
            f"Initialized {self.__class__.__name__} with "
            f"{self.config.provider} model {self.config.model_name}"
        )

    def _create_model(self):
        """
        Create LLM model based on provider with fallback logic.

        Returns:
            Model instance (OpenAI, Gemini, or Anthropic)
        """
        providers_to_try = [self.config.provider.lower()]

        # Add fallbacks if the primary choice fails
        all_providers = ["google", "openai", "anthropic"]
        for p in all_providers:
            if p not in providers_to_try:
                providers_to_try.append(p)

        errors = []
        for provider in providers_to_try:
            try:
                if provider == "openai":
                    if not settings.openai_api_key:
                        raise ValueError("OPENAI_API_KEY not configured")
                    return OpenAIModel(
                        model_name=self.config.model_name if provider == self.config.provider.lower() else "gpt-4o-mini",
                        api_key=settings.openai_api_key,
                    )

                elif provider == "google" or provider == "gemini":
                    if not settings.gemini_api_key:
                        raise ValueError("GEMINI_API_KEY not configured")

                    import os
                    os.environ['GEMINI_API_KEY'] = settings.gemini_api_key
                    return GeminiModel(
                        model_name=self.config.model_name if provider == self.config.provider.lower() else "gemini-2.5-pro",
                    )

                elif provider == "anthropic":
                    if not settings.anthropic_api_key:
                        raise ValueError("ANTHROPIC_API_KEY not configured")
                    return AnthropicModel(
                        model_name=self.config.model_name if provider == self.config.provider.lower() else "claude-3-haiku-20240307",
                        api_key=settings.anthropic_api_key,
                    )
            except Exception as e:
                errors.append(f"{provider}: {str(e)}")
                continue

        raise ValueError(f"Could not initialize any AI model. Errors: {'; '.join(errors)}")

    def _create_agent(self, system_prompt: str, **kwargs) -> PydanticAgent:
        """
        Create PydanticAI agent instance.

        Args:
            system_prompt: System prompt for the agent
            **kwargs: Additional agent configuration

        Returns:
            Configured PydanticAgent instance
        """
        return PydanticAgent(
            model=self.model,
            system_prompt=system_prompt,
            **kwargs,
        )

    def get_agent_name(self) -> str:
        """Get agent class name."""
        return self.__class__.__name__

    async def run(self, *args, **kwargs) -> Any:
        """
        Main entry point for agent execution.
        Must be implemented by subclasses.
        """
        raise NotImplementedError(f"{self.get_agent_name()} must implement run() method")
