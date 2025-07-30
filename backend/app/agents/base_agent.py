from typing import TypeVar, Generic, Optional, Type, List, Any, Dict, Union
import inspect
import asyncio
from contextlib import asynccontextmanager

from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import Usage
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, UserPromptPart, TextPart
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.exceptions import UnexpectedModelBehavior

from pkg.llm_provider.llm_client import LLMModel, openai_model_map, gemini_model_map
from pkg.log.logger import Logger
from app.tokens.service.service import TokensService
from app.tokens.exceptions import TokenLimitError

DepsT = TypeVar("DepsT")
ResultT = TypeVar("ResultT")


class BaseAgent(Generic[DepsT, ResultT]):
    """
    Base agent class for all specialized agents using Pydantic AI.

    This class provides common functionality like token tracking,
    tool registration, and structured error handling across all agents.

    Generic parameters:
        DepsT: Dependency type expected by the agent
        ResultT: Result type returned by the agent
    """

    def __init__(self,
            llm_model: LLMModel,
            logger: Logger,
            *,
            system_prompt: Optional[str] = (),
            output_type: Optional[Type] = None,
            deps_type: Optional[Type] = None,
            tokens_service: Optional[TokensService] = None,
            retries: int = 2,
            instructions: Optional[str] = None,
            max_tool_calls: int = 10,
            instrument: bool = True,
            **agent_kwargs
    ):
        """
        Initialize the base agent.

        Args:
            llm_model: LLM model to use
            logger: Logger instance
            system_prompt: System prompt for the agent
            output_type: Return type for the agent
            deps_type: Dependencies type for the agent
            tokens_service: Service for token tracking
            retries: Number of retries for model failures
            max_tool_calls: Maximum number of allowed tool calls
            instrument: Whether to instrument with logfire
            **agent_kwargs: Additional kwargs to pass to Pydantic AI Agent
        """
        self.logger = logger
        self.tokens_service = tokens_service
        self.output_type = output_type
        self.llm_model = llm_model

        # Map LLM model to the appropriate provider model
        if llm_model.value in gemini_model_map:
            model_value = GeminiModel(
                model_name=gemini_model_map[llm_model.value],
                provider="google-gla",
            )
        elif llm_model.value in openai_model_map:
            model_value = openai_model_map[llm_model.value]
        else:
            # Fallback to GroqModel if needed
            model_value = GroqModel(model_name=llm_model.value)

        # Collect tool methods using inspection
        tool_funcs = [
            member
            for name, member in inspect.getmembers(self, inspect.ismethod)
            if getattr(member, "_is_tool", False)
        ]

        # Log collected tools
        self.logger.debug(f"Registered {len(tool_funcs)} tools for {self.__class__.__name__}")

        # Initialize the Pydantic AI agent
        self.agent = Agent(
            model=model_value,
            system_prompt=system_prompt,
            instructions=instructions,
            output_type=output_type,
            deps_type=deps_type,
            tools=tool_funcs,
            retries=retries,
            instrument=instrument,
            **agent_kwargs,
        )

        # Register dynamic system prompt functions
        for name, member in inspect.getmembers(self, inspect.ismethod):
            if getattr(member, "_is_system_prompt", False):
                self.logger.debug(f"Registering system prompt function: {name}")
                self.agent.system_prompt(member)

    async def run(self, user_id: str, prompt: str, *, deps: Optional[DepsT] = None,
                  message_history: Optional[List[ModelMessage]] = None, **kwargs):
        """
        Run the agent with token tracking and proper error handling.

        Args:
            user_id: User ID for token tracking
            prompt: User prompt
            deps: Dependencies for the agent
            message_history: Previous messages for context
            **kwargs: Additional arguments to pass to the agent

        Returns:
            Agent run result

        Raises:
            TokenLimitError: If Credits limit is exceeded
            UnexpectedModelBehavior: If model behaves unexpectedly
        """
        # Log the operation
        self.logger.info(f"Running agent with prompt: {prompt}")

        try:
            estimated_tokens = len(prompt) // 4  # Roughly 4 chars per token
            # Add buffer for model overhead
            estimated_tokens = int(estimated_tokens * 1.2)

            if not await self.tokens_service.check_token_limit(user_id, estimated_tokens):
                raise TokenLimitError("Insufficient token balance")
        except Exception as e:
            self.logger.error(f"Error checking Credits limit: {e}")
            raise TokenLimitError(f"Error checking token availability: {str(e)}")

        # Run the agent with proper error handling
        try:
            # Run the agent with message history if provided
            run_params = {"deps": deps,  **kwargs}

            if message_history:
                run_params["message_history"] = message_history

            result = await self.agent.run(prompt, **run_params)

            # Track token usage
            usage = result.usage()
            await self.tokens_service.consume_tokens(user_id, usage.total_tokens)

            return result

        except UnexpectedModelBehavior as e:
            self.logger.error(f"Model error: {e}", exc_info=True)
            raise
        except TokenLimitError:
            # Re-raise token errors without changing
            raise
        except Exception as e:
            self.logger.error(f"Error running agent: {e}", exc_info=True)
            raise RuntimeError(f"Agent execution error: {str(e)}")

    def run_sync(self, user_id: str, prompt: str, *, deps: Optional[DepsT] = None,
                 message_history: Optional[List[ModelMessage]] = None,  **kwargs):
        """
        Synchronous version of run.

        This runs the agent synchronously by wrapping the async run method.
        """
        # Log the operation
        self.logger.info(f"Running agent synchronously with prompt: {prompt}")
        try:
            estimated_tokens = len(prompt) // 4  # Roughly 4 chars per token
            # Add buffer for model overhead
            estimated_tokens = int(estimated_tokens * 1.2)

            if not asyncio.run(self.tokens_service.check_token_limit(user_id, estimated_tokens)):
                raise TokenLimitError("Insufficient token balance")

        except Exception as e:
            self.logger.error(f"Error checking Credits limit: {e}")
            raise TokenLimitError(f"Error checking token availability: {str(e)}")

        # Run the async method in the event loop
        try:
            result = asyncio.run(
                self.run(user_id, prompt, deps=deps, message_history=message_history,**kwargs)
            )
            # Track token usage
            usage = result.usage()
            asyncio.run(self.tokens_service.consume_tokens(user_id, usage.total_tokens))
            return result

        except Exception as e:
            self.logger.error(f"Error in run_sync: {e}")
            raise

    @asynccontextmanager
    async def run_stream(self, user_id: str, prompt: str, *, deps: Optional[DepsT] = None,
                          message_history: Optional[List[ModelMessage]] = None, **kwargs):
        """
        Get an async context manager for streaming the agent's output.
\
        """
        self.logger.info(f"Starting agent stream with prompt: {prompt}")

        try:
            estimated_tokens = len(prompt) // 4  # Roughly 4 chars per token
            # Add buffer for model overhead
            estimated_tokens = int(estimated_tokens * 1.2)

            if not await self.tokens_service.check_token_limit(user_id, estimated_tokens):
                raise TokenLimitError("Insufficient token balance")

        except Exception as e:
            self.logger.error(f"Error checking Credits limit: {e}")
            raise TokenLimitError(f"Error checking token availability: {str(e)}")

        # Build agent run parameters
        agent_run_params = {
            "deps": deps,
            **kwargs
        }

        if message_history:
            agent_run_params["message_history"] = message_history

        # Get the agent iterator context
        try:
            async with self.agent.run_stream(prompt, **agent_run_params) as result:
                yield result

                # After the context exits, record token usage if token service is provided
                if result:
                    usage: Usage | None = result.usage()
                    if usage:
                        await self.tokens_service.consume_tokens(user_id, usage.total_tokens)
        except TokenLimitError:
            # Re-raise token errors without changing
            raise
        except Exception as e:
            self.logger.error(f"Error in agent stream: {e}", exc_info=True)
            raise RuntimeError(f"Agent stream error: {str(e)}")

    @asynccontextmanager
    async def iter(self,user_id: str, prompt: str, *, deps: Optional[DepsT] = None,
            message_history: Optional[List[ModelMessage]] = None, **kwargs):
        """
        Get an async context manager for iterating over the agent's graph execution.

        """
        self.logger.info(f"Starting agent iteration with prompt: {prompt}")

        try:
            estimated_tokens = len(prompt) // 4  # Roughly 4 chars per token
            # Add buffer for model overhead
            estimated_tokens = int(estimated_tokens * 1.2)

            if not asyncio.run(self.tokens_service.check_token_limit(user_id, estimated_tokens)):
                raise TokenLimitError("Insufficient token balance")

        except Exception as e:
            self.logger.error(f"Error checking Credits limit: {e}")
            raise TokenLimitError(f"Error checking token availability: {str(e)}")


        # Build agent run parameters
        agent_run_params = {
            "deps": deps,
            **kwargs
        }

        if message_history:
            agent_run_params["message_history"] = message_history

        # Get the agent iterator context
        try:
            async with self.agent.iter(prompt, **agent_run_params) as agent_run:
                yield agent_run

                # After the context exits, record token usage if token service is provided
                if agent_run.result:
                    usage: Usage | None = agent_run.result.usage()
                    if usage:
                        await self.tokens_service.consume_tokens(user_id, usage.total_tokens)
        except TokenLimitError:
            # Re-raise token errors without changing
            raise
        except Exception as e:
            self.logger.error(f"Error in agent iteration: {e}", exc_info=True)
            raise RuntimeError(f"Agent iteration error: {str(e)}")


# Decorators for marking methods in derived classes
def tool(func):
    """
    Decorator to mark a method as a tool.

    This marks the method to be registered as a tool with the Pydantic AI agent.

    Args:
        func: The function to mark as a tool

    Returns:
        The function with _is_tool attribute set to True
    """
    func._is_tool = True
    return func


def system_prompt(func):
    """
    Decorator to mark a method as a system prompt.

    This marks the method to be registered as a dynamic system prompt with the Pydantic AI agent.

    Args:
        func: The function to mark as a system prompt

    Returns:
        The function with _is_system_prompt attribute set to True
    """
    func._is_system_prompt = True
    return func