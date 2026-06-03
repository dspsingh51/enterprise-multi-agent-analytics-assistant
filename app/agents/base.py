import time
from typing import Any, Dict, List, Optional, Union
from pydantic import Field
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from app.config import settings
from app.observability.logger import agent_logger
from app.observability.tracer import tracer


class NoAPIKeyError(Exception):
    """Raised when no valid LLM API key is available."""
    pass


def get_llm(api_key: Optional[str] = None) -> BaseChatModel:
    """
    Factory function returning the configured LLM client.
    Raises NoAPIKeyError if no valid API key is provided.
    No fallback, no mock — real LLM or explicit failure.
    """
    provider = settings.LLM_PROVIDER.lower()

    if provider == "google":
        # Prioritize key passed dynamically from the user UI
        key = api_key or settings.GEMINI_API_KEY
        if key and key.strip() and key.startswith("AIzaSy") and len(key.strip()) >= 30:
            agent_logger.info(f"Initializing Google Gemini Client: {settings.LLM_MODEL}")
            return ChatGoogleGenerativeAI(
                model=settings.LLM_MODEL,
                google_api_key=key,
                temperature=0.2,
                timeout=120.0,
                max_retries=2
            )
        else:
            raise NoAPIKeyError(
                "No valid Google Gemini API key provided. "
                "Please enter your API key in the sidebar (must start with 'AIzaSy')."
            )

    elif provider == "openai":
        key = settings.OPENAI_API_KEY
        if key and key.strip() and key.startswith("sk-") and len(key.strip()) >= 20:
            agent_logger.info(f"Initializing OpenAI Client: {settings.LLM_MODEL}")
            openai_args = {
                "model": settings.LLM_MODEL,
                "api_key": key,
                "temperature": 0.2,
                "timeout": 120.0
            }
            if settings.OPENAI_API_BASE:
                openai_args["base_url"] = settings.OPENAI_API_BASE
            return ChatOpenAI(**openai_args)
        else:
            raise NoAPIKeyError(
                "No valid OpenAI API key provided (must start with 'sk-')."
            )

    else:
        raise NoAPIKeyError(
            f"Unknown LLM provider '{provider}'. Supported providers: 'google', 'openai'."
        )


class BaseAgent:
    """
    Base Agent class that manages execution tracing.
    LLM is created on-demand via get_model(state) using the user's API key from state.
    """
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    def get_model(self, state: Dict[str, Any]) -> BaseChatModel:
        """
        Dynamically gets the model client, using any UI-entered keys in the state.
        """
        return get_llm(state.get("gemini_api_key"))

    def run_with_tracing(self, run_id: str, state_input: Dict[str, Any], execute_fn) -> Dict[str, Any]:
        """
        Executes an agent node wrapped in execution tracing.
        """
        agent_logger.info(f"Starting execution of Agent: {self.name} ({self.role})")
        step_index = tracer.start_step(run_id, self.name, input_data=state_input.get("current_query"))

        try:
            start_time = time.time()
            # Execute agent core logic
            result = execute_fn(state_input)
            duration = round(time.time() - start_time, 3)

            # Log successful step completion
            tracer.complete_step(run_id, self.name, output_data=str(result)[:1000])
            agent_logger.info(f"Agent {self.name} completed successfully in {duration}s")
            return result
        except Exception as e:
            tracer.fail_step(run_id, self.name, error_message=str(e))
            agent_logger.error(f"Agent {self.name} failed during execution: {e}")
            # Add error to state output and return
            errors = state_input.get("errors", [])
            errors.append(f"Error in agent {self.name}: {str(e)}")
            state_input["errors"] = errors
            return state_input
