"""
Analytics PAL Workflow.
This module defines the main workflow for analytics processing.
"""

import asyncio
import traceback
import json
import os
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List, Union
from pkg.log.logger import Logger
from pkg.llm_provider.llm_client import LLMClient, LLMModel
from datetime import datetime
from uuid import UUID
from app.pal.analytics.agents.code_generator import CodeGenerator
from app.pal.analytics.agents.insight_generator import InsightGenerator
from app.pal.analytics.agents.query_analyzer import QueryAnalyzer
from app.pal.analytics.agents.data_summarizer import DataSummarizer
from app.pal.analytics.executors.python_executor import PythonExecutor
from app.pal.analytics.executors.csv_executor import CSVExecutor
from app.pal.analytics.adapters.analytics_repository_adapter import AnalyticsRepositoryAdapter
from app.analytics.repository.analytics_repository import AnalyticsRepository
from app.pal.analytics.utils.models import (
    QueryAnalysisResult,
    GeneratedCode,
    InsightResult,
    SchemaInfo,
    DatabaseInfo,
    CodeGenerationResult,
    InsightGenerationResult,
    TableData
)
from app.pal.analytics.utils.code_execution import execute_python_code, execute_sql
from app.pal.analytics.utils.dev_logger import DevLogger
from pkg.redis.client import RedisClient
from pkg.s3.s3_client import S3Client
from app.pal.analytics.agents import QueryCoachAgent
from app.chat.repository.chat_repository import ChatRepository
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, SystemPromptPart, UserPromptPart, TextPart
from app.tokens.service.service import TokensService
from app.analytics.service.analytics_service import AnalyticsService
from app.code_execution.client.http_client import CodeExecutionClient
from app.tokens.exceptions import TokenLimitError, TOKEN_LIMIT_ERROR_MESSAGE

class AnalyticsPAL:
    """
    Analytics PAL - Processing, Analysis, and Learning workflow.
    This class orchestrates the analytics workflow using specialized agents.
    """

    def __init__(
            self,
            llm_client: LLMClient,
            chat_repository: ChatRepository,
            analytics_repository: AnalyticsRepositoryAdapter,
            analytics_service: AnalyticsService,    
            s3_client: S3Client,
            redis_client: RedisClient,
            tokens_service: TokensService,
            logger: Logger,
            model: Optional[LLMModel] = None,
            enable_cache: bool = True,
            code_execution_timeout: int = 30,
            enable_dev_logging: bool = False,
            dev_mode: bool = False,
            dev_log_dir: str = "./logs/analytics",
            code_execution_client: CodeExecutionClient = None
    ):
        """
        Initialize the AnalyticsPAL.
        
        Args:
            llm_client: LLM client for agent communication
            analytics_repository: Analytics repository instance
            s3_client: S3 client for file operations
            redis_client: Redis client for caching
            logger: Optional logger instance
            model: Model to use for LLM calls
            enable_cache: Whether to enable caching
            code_execution_timeout: Timeout for code execution in seconds
            enable_dev_logging: Whether to enable development mode logging
            dev_mode: Alternative name for enable_dev_logging (for compatibility)
            dev_log_dir: Directory for development logs
        """
        self.llm_client = llm_client
        self.chat_repository = chat_repository
        self.analytics_repository = analytics_repository
        self.analytics_service = analytics_service
        self.s3_client = s3_client
        self.redis_client = redis_client
        self.logger = logger
        self.tokens_service = tokens_service
        self.code_execution_client = code_execution_client

        # Validate the model
        self.llm_model = model if model is not None else LLMModel.GEMINI_2_0_FLASH  # type: ignore

        self.enable_cache = enable_cache
        self.code_execution_timeout = code_execution_timeout

        # Handle compatibility with both parameter names
        self.enable_dev_logging = enable_dev_logging or dev_mode

        # Initialize logger
        self.dev_logger = DevLogger(
            enabled=self.enable_dev_logging,
            log_dir=dev_log_dir,
            logger=self.logger
        )

        # Initialize agents
        self.query_analyzer = QueryAnalyzer(
            llm_client=self.llm_client,
            tokens_service=self.tokens_service,
            llm_model=self.llm_model,  # type: ignore
            logger=self.logger,
            dev_mode=dev_mode
        )

        self.code_generator = CodeGenerator(
            llm_client=self.llm_client,
            tokens_service=self.tokens_service,
            llm_model=self.llm_model,  # type: ignore
            logger=self.logger,
            dev_mode=dev_mode
        )

        self.insight_generator = InsightGenerator(
            llm_client=self.llm_client,
            tokens_service=self.tokens_service,
            llm_model=self.llm_model,  # type: ignore
            logger=self.logger,
            dev_mode=dev_mode
        )

        self.data_summarizer = DataSummarizer(
            llm_client=self.llm_client,
            tokens_service=self.tokens_service,
            llm_model=self.llm_model,  # type: ignore
            logger=self.logger,
            dev_mode=dev_mode
        )

        # Initialize the Query Coach agent
        self.query_coach = QueryCoachAgent(
            llm_client=self.llm_client,
            tokens_service=self.tokens_service,
            llm_model=self.llm_model,  # type: ignore
            logger=self.logger,
            dev_mode=dev_mode
        )

        # Initialize code executor
        self.code_executor = PythonExecutor(timeout=self.code_execution_timeout)

        # Initialize cache for analysis results
        self.cache = {}

        # Track meta_content ids for sequence
        self._meta_id_counter = 0

        # Initialize timing metrics dictionary
        self.timing_metrics = {
            "schema_fetch": [],
            "query_analysis": [],
            "code_generation": [],
            "code_execution": [],
            "insight_generation": [],
            "total_processing": []
        }

        self.logger.info("AnalyticsPAL initialized")

    def _extract_clean_text(self, obj: Any, field_name: str = None) -> str:
        """
        Helper function to extract clean text from various objects or strings.
        
        Args:
            obj: The object to extract text from
            field_name: Optional field name to extract from the object
            
        Returns:
            Clean text as a string
        """
        # Handle direct string case
        if isinstance(obj, str):
            # Check if this is a string representation of an object
            if "AgentRunResult" in obj:
                # Try to extract the specific field
                if field_name and f"{field_name}='" in obj:
                    start_index = obj.find(f"{field_name}='") + len(f"{field_name}='")
                    end_index = obj.find("'", start_index)
                    if end_index > start_index:
                        return obj[start_index:end_index]
                elif field_name and f"{field_name}=\"" in obj:
                    start_index = obj.find(f"{field_name}=\"") + len(f"{field_name}=\"")
                    end_index = obj.find("\"", start_index)
                    if end_index > start_index:
                        return obj[start_index:end_index]

                # Generic extraction looking for first quoted string
                import re
                matches = re.findall(r"['\"]([^'\"]+)['\"]", obj)
                if matches:
                    return matches[0]

            # Return the original string if no extraction was done
            return obj

        # Handle objects with the specific field
        if field_name and hasattr(obj, field_name):
            field_value = getattr(obj, field_name)
            if field_value is not None:
                return self._extract_clean_text(field_value)

        # Handle dictionary-like objects
        if field_name and hasattr(obj, '__getitem__') and field_name in obj:
            return self._extract_clean_text(obj[field_name])

        # Handle objects with data attribute (AgentRunResult pattern)
        if hasattr(obj, 'data') and obj.data is not None:
            if field_name:
                return self._extract_clean_text(obj.data, field_name)
            else:
                return self._extract_clean_text(obj.data)

        # If we can't extract anything meaningful, convert to string
        return str(obj)

    async def handle_message(self, user_id: str, prompt: str, conversation_id: UUID, attachments: List[Dict] = None,
            thread_id: UUID = None, suggestions: List[Dict] = None, database_uid: str = None, table_uid: str = None):
        """
        Handle an analytics query message.
        
        Args:
            message: The user's natural language query
            attachments: Optional attachments
            thread_id: Optional thread ID for conversation context
            suggestions: Optional suggestions for the query
            database_uid: Optional database UID
            table_uid: Optional table UID
            
        Yields:
            Progress updates and final response with analysis, code, results, and insights
        """
        self.logger.info(f"AnalyticsPAL.handle_message - Processing query: {prompt}")

        try:
            # Track start time for performance monitoring
            start_time = datetime.now()
            operation_start = start_time

            # Check if database connection is missing
            if not database_uid:
                self.logger.info(
                    "No database connected for Analytics_pal. Sending connection_required message to frontend.")
                # Yield a special response to indicate the need for database connection
                yield {
                    "content": "To use the Analytics PAL, please connect to a database or datasource first."
                }
                # Early return to stop further processing
                return

            # Enhanced initial meta_content with more details
            starting_analysis_description = [
                {
                    "title": "Analyzing your query",
                    "type": "text",
                    "status": "inprogress"
                }
            ]
            yield self._create_meta_content("Starting analysis", "inprogress", "text", starting_analysis_description)

            # Get schema for the specified database (if provided)
            schema_start = datetime.now()
            schema = None
            db_type = "unknown"
            schema_str = None

            # fetch previous conversation if available
            conversation = await self.chat_repository.get_conversation(user_id,conversation_id, include_messages=True)
            
            # Extract messages from conversation to pass as history
            
            # Max 14 messages
            if(len(conversation.messages) > 14):
                conversation.messages = conversation.messages[-14:]
            
            message_history = []
            for message in conversation.messages:
                if(message.role.value == "user"):
                    message_history.append(ModelRequest(parts=[UserPromptPart(content=message.content)]))
                elif(message.role.value == "assistant"):
                    if message.role == "assistant":
                        for art in message.artifacts:
                            if art.artifact_type == "code":
                                message_history.append(ModelResponse(parts=[TextPart(content=art.content)]))
                                
            if database_uid and self.analytics_repository:
                self.logger.info(f"AnalyticsPAL.handle_message - Fetching schema for {database_uid}")
                # Get database type and other info
                db_info = await self.analytics_repository.get_database_info(database_uid)
                if db_info:
                    db_type = db_info.type
                    self.logger.info(f"AnalyticsPAL.handle_message - Database type: {db_type}")

                # Get schema               
                schema = await self.analytics_service.get_database_schema(database_uid, table_uid)
                self.logger.info(f"AnalyticsPAL.handle_message - Schema: {schema}")
                
                if schema:
                    self.logger.info(f"AnalyticsPAL.handle_message - Schema retrieved")
                else:
                    self.logger.warning(f"AnalyticsPAL.handle_message - No schema available for {database_uid}")

            # Record schema fetch time
            schema_time = (datetime.now() - schema_start).total_seconds()
            self.timing_metrics["schema_fetch"].append(schema_time)
            self.logger.info(f"AnalyticsPAL.handle_message - Schema fetched in {schema_time:.2f}s")

            # Step 1: Analyze the query
            analysis_start = datetime.now()


            try:
                query_analysis_result = await self._analyze_query(user_id, prompt, schema, message_history)
            except TokenLimitError as e:
                self.logger.error(f"AnalyticsPAL.handle_message - Credits limit exceeded: {str(e)}")
                yield {
                    "content": TOKEN_LIMIT_ERROR_MESSAGE
                }
                return
            except Exception as e:
                self.logger.error(f"AnalyticsPAL.handle_message - Error analyzing query final: {str(e)}")
                return
            
            # Record analysis time
            analysis_time = (datetime.now() - analysis_start).total_seconds()
            self.timing_metrics["query_analysis"].append(analysis_time)
            self.logger.info(f"AnalyticsPAL.handle_message - Query analysis completed in {analysis_time:.2f}s")

            # NEW: Check if the query is too ambiguous before proceeding
            if query_analysis_result and (
                    getattr(query_analysis_result, 'is_ambiguous', False) or
                    getattr(query_analysis_result, 'ambiguity_score', 0.0) > 0.6
            ):
                self.logger.info(
                    f"AnalyticsPAL.handle_message - Query is ambiguous with score: {getattr(query_analysis_result, 'ambiguity_score', 0.0)}")

                # Get ambiguity reason
                ambiguity_reason = getattr(query_analysis_result, 'ambiguity_reason',
                                           "Your query needs more details for me to provide a meaningful answer.")

                # Use QueryCoach to get clarification suggestions
                self.logger.info(f"AnalyticsPAL.handle_message - Generating query suggestions for ambiguous query")

                try:
                    # Generate empty code placeholder for QueryCoach
                    placeholder_code = ""
                    if hasattr(query_analysis_result, 'intent') and query_analysis_result.intent:
                        if query_analysis_result.intent.lower() in ['aggregation', 'filtering', 'summarization']:
                            placeholder_code = "SELECT * FROM table WHERE condition"
                        elif query_analysis_result.intent.lower() in ['trend_analysis', 'time_series']:
                            placeholder_code = "SELECT date, metric FROM table ORDER BY date"

                    suggestions = await self.analytics_service.get_recommendations(
                        database_uid=database_uid,
                        table_uid=table_uid,
                        count=5,
                        user_question=prompt
                    )

                    # Format suggestions for response
                    formatted_suggestions = []
                    for suggestion in suggestions.recommendations:
                        formatted_suggestions.append({
                            "type": "QUERY",
                            "suggestion_content": {
                                "text": suggestion.question,
                                "title": suggestion.title,
                                "description": suggestion.explanation
                            }
                        })

                    # Create response explaining the ambiguity
                    response_message = f"I need more information to answer your query. {ambiguity_reason}\n\nHere are some suggestions:"

                    # Initialize results with default values to prevent reference errors later
                    results = {
                        "columns": [],
                        "records": [],
                        "total_rows": 0,
                        "returned_rows": 0
                    }

                    # Initialize results_df as empty DataFrame for consistency
                    results_df = pd.DataFrame()
                    self._df = results_df  # Also set _df for statistics generation

                    # Return response with clarification needed
                    yield {
                        "type": "content",
                        "content": response_message
                    }

                    # Add suggestions as separate objects
                    yield {
                        "type": "suggestions",
                        "suggestions": formatted_suggestions
                    }

                    # Create minimal artifacts for ambiguous queries
                    artifacts = []

                    # Add ambiguity explanation as an artifact
                    artifacts.append({
                        "artifact_type": "explanation",
                        "content": f"Query is ambiguous: {ambiguity_reason}"
                    })

                    # Add empty data artifacts
                    artifacts.append({
                        "artifact_type": "data",
                        "content": "[]"
                    })

                    artifacts.append({
                        "artifact_type": "columns",
                        "content": json.dumps(results.get("columns", []))
                    })

                    # Add metadata with ambiguity information
                    metadata = {
                        "is_ambiguous": True,
                        "ambiguity_reason": ambiguity_reason,
                        "ambiguity_score": getattr(query_analysis_result, 'ambiguity_score', 0.7),
                        "total_rows": 0,
                        "returned_rows": 0
                    }

                    artifacts.append({
                        "artifact_type": "metadata",
                        "content": json.dumps(metadata)
                    })

                    # Yield artifacts
                    if artifacts:
                        yield {
                            "type": "artifacts",
                            "artifacts": artifacts
                        }

                    # Early return as we can't proceed without clarification
                    return

                except Exception as e:
                    self.logger.error(
                        f"AnalyticsPAL.handle_message - Error generating suggestions for ambiguous query: {str(e)}")
                    # Fall through to normal processing if suggestions fail

            # ADDITIONAL CHECK: For hallucinated entities in vague queries like "TOP 5 most preferred"
            if query_analysis_result and hasattr(query_analysis_result,
                                                 'target_entities') and query_analysis_result.target_entities:
                # Check if target entities were explicitly mentioned in the query
                has_hallucinated_entities = False
                hallucinated_entities = []

                for entity in query_analysis_result.target_entities:
                    # Convert both to lowercase for comparison
                    entity_lower = entity.lower()
                    message_lower = prompt.lower()

                    # Check if the entity or a related term is mentioned in the message
                    # Allow for plural/singular variations by checking for the entity name without 's'
                    if (entity_lower not in message_lower and
                            (entity_lower.endswith('s') and entity_lower[:-1] not in message_lower) and
                            (not entity_lower.endswith('s') and entity_lower + 's' not in message_lower)):
                        has_hallucinated_entities = True
                        hallucinated_entities.append(entity)

                # If we detected hallucinated entities, treat as ambiguous and get suggestions
                if has_hallucinated_entities:
                    self.logger.info(
                        f"AnalyticsPAL.handle_message - Detected potentially hallucinated entities: {hallucinated_entities}")

                    # Create ambiguity reason based on hallucinated entities
                    if len(hallucinated_entities) == 1:
                        ambiguity_reason = f"You mentioned '{hallucinated_entities[0]}' but I don't see this explicitly in your query."
                    else:
                        entity_list = ", ".join([f"'{e}'" for e in hallucinated_entities])
                        ambiguity_reason = f"You mentioned {entity_list} but I don't see these explicitly in your query."

                    try:
                        # Get suggestions from QueryCoach
                        placeholder_code = "SELECT * FROM table"

                        suggestions = await self.analytics_service.get_recommendations(
                            database_uid=database_uid,
                            table_uid=table_uid,
                            count=5,
                            user_question=prompt
                        )

                        # Format suggestions for response
                        formatted_suggestions = []
                        for suggestion in suggestions.recommendations:
                            formatted_suggestions.append({
                                "type": "QUERY",
                                "suggestion_content": {
                                    "text": suggestion.question,
                                    "title": suggestion.title,
                                    "description": suggestion.explanation
                                }
                            })

                        # Create response explaining the issue
                        response_message = (
                            f"I need more information to answer your query. {ambiguity_reason}\n\n"
                            f"Could you please specify what exactly you're looking for information about?\n\n"
                            f"Here are some suggestions:"
                        )

                        # Initialize results with default values to prevent reference errors later
                        results = {
                            "columns": [],
                            "records": [],
                            "total_rows": 0,
                            "returned_rows": 0
                        }

                        # Initialize results_df as empty DataFrame for consistency
                        results_df = pd.DataFrame()
                        self._df = results_df  # Also set _df for statistics generation

                        # Return response with clarification needed
                        yield {
                            "type": "content",
                            "content": response_message
                        }

                        # Add suggestions as separate objects
                        yield {
                            "type": "suggestions",
                            "suggestions": formatted_suggestions
                        }

                        # Create minimal artifacts for hallucinated entities
                        artifacts = []

                        # Add explanation as an artifact
                        artifacts.append({
                            "artifact_type": "explanation",
                            "content": f"Query has potential hallucinated entities: {ambiguity_reason}"
                        })

                        # Add empty data artifacts
                        artifacts.append({
                            "artifact_type": "data",
                            "content": "[]"
                        })

                        artifacts.append({
                            "artifact_type": "columns",
                            "content": json.dumps(results.get("columns", []))
                        })

                        # Add metadata with ambiguity information
                        metadata = {
                            "is_ambiguous": True,
                            "hallucinated_entities": hallucinated_entities,
                            "ambiguity_reason": ambiguity_reason,
                            "total_rows": 0,
                            "returned_rows": 0
                        }

                        artifacts.append({
                            "artifact_type": "metadata",
                            "content": json.dumps(metadata)
                        })

                        # Yield artifacts
                        if artifacts:
                            yield {
                                "type": "artifacts",
                                "artifacts": artifacts
                            }

                        # Early return as we can't proceed without clarification
                        return

                    except Exception as e:
                        self.logger.error(
                            f"AnalyticsPAL.handle_message - Error generating suggestions for query with hallucinated entities: {str(e)}")
                        # Fall through to normal processing if suggestions fail

            # Progress update - Generating code
            yield self._create_meta_content("Generating code", "inprogress", "text")

            # Step 2: Generate code
            results_df = None
            final_error = None
            code_result = None
            code_time = 0
            execution_time = 0
            
            async for item in self.generate_and_execute_code(user_id, prompt, query_analysis_result, schema, db_type, database_uid, table_uid):
                if(item["type"] == "final_result"):
                    results_df = item["result"]
                elif(item["type"] == "final_error"):
                    final_error = item["error"]
                elif(item["type"] == "code_result"):
                    code_result = item["result"]
                elif(item["type"] == "code_time"):
                    code_time = item["time"]
                elif(item["type"] == "execution_time"):
                    execution_time = item["time"]
                else:
                    yield item

            if final_error:
                    # Update meta content with error status
                    print(f"AnalyticsPAL.handle_message - Error generating and executing code: {final_error}")
                    return
                
            # Check if the query returned empty results
            if results_df is not None and (results_df.empty or len(results_df) == 0):
                self.logger.info("AnalyticsPAL.handle_message - Query returned empty results, generating suggestions")

                # Create content that explains the empty results
                empty_results_explanation = (
                    "Your query was executed successfully, but no results were found. "
                    "This could be because:\n\n"
                    "- The filter conditions may be too restrictive\n"
                    "- The data you're looking for might not exist in the database\n"
                    "- There might be a mismatch between the query terms and the actual data"
                )

                # Format the results but with empty data
                results = self._format_results(results_df)

                # Process artifacts as usual but with empty data
                artifacts = []
                if code_result:
                    # Add code artifacts
                    code_content = self._extract_clean_text(code_result, "code")
                    artifacts.append({
                        "artifact_type": "code",
                        "content": code_content
                    })

                    code_type_content = self._extract_clean_text(code_result, "code_type")
                    artifacts.append({
                        "artifact_type": "code_type",
                        "content": code_type_content
                    })

                    explanation_content = self._extract_clean_text(code_result, "explanation")
                    artifacts.append({
                        "artifact_type": "explanation",
                        "content": explanation_content
                    })

                # Add empty data artifact
                artifacts.append({
                    "artifact_type": "data",
                    "content": "[]"
                })

                # Add empty columns artifact
                artifacts.append({
                    "artifact_type": "columns",
                    "content": json.dumps(results.get("columns", []))
                })

                # Generate query suggestions asynchronously
                suggestions = await self._generate_query_suggestions(
                    original_query=prompt,
                    code_result=code_result,
                    schema=schema,
                    error_message=None,  # No error, just empty results
                    database_uid=database_uid,
                    table_uid=table_uid
                )

                # Yield artifacts
                if artifacts:
                    yield {
                        "type": "artifacts",
                        "artifacts": artifacts
                    }

                # Yield the content explaining the empty results
                yield {
                    "type": "content",
                    "content": empty_results_explanation
                }

                # Yield suggestions if any were generated
                if suggestions:
                    self.logger.info(f"AnalyticsPAL.handle_message - Yielding {len(suggestions)} query suggestions")
                    yield {
                        "type": "suggestions",
                        "suggestions": suggestions
                    }

                return

            # For non-empty results, format them here - before insights generation
            # This ensures 'results' is defined for all code paths
            self.logger.info(f"AnalyticsPAL.handle_message - Query returned {len(results_df)} rows, formatting results")
            results = self._format_results(results_df)
            # Store DataFrame reference for statistics generation
            self._df = results_df

            # Progress update - Generating insights
            # yield self._create_meta_content("Generating insights", "inprogress", "text")

            # Step 4: Generate insights (if we have results)
            insights_start = datetime.now()
            insights_result = None
            if results_df is not None and not results_df.empty:
                insights_result = await self._generate_insights(
                    user_id,
                    results_df,
                    query_analysis_result,
                    code_result,
                    prompt
                )

                # Record insight generation time
                insights_time = (datetime.now() - insights_start).total_seconds()
                self.timing_metrics["insight_generation"].append(insights_time)
                self.logger.info(f"AnalyticsPAL.handle_message - Insights generated in {insights_time:.2f}s")

                if insights_result:
                    insights = {
                        "summary": insights_result.summary,
                        "insights": insights_result.insights,
                    }
                    self.logger.info(
                        f"AnalyticsPAL.handle_message - Generated {len(insights_result.insights)} insights")

                    # Update meta_content with insight generation completion
                    yield self._create_meta_content(
                        f"Generated {len(insights_result.insights)} insights",
                        "completed",
                        "text",
                        description=[{"title": insight.description} for insight in insights_result.insights[:3]]
                    )
            else:
                # No insights could be generated
                yield self._create_meta_content("No data available for insights", "completed", "text")

            # Calculate and record total time
            total_time = (datetime.now() - start_time).total_seconds()
            self.timing_metrics["total_processing"].append(total_time)
            self.logger.info(f"AnalyticsPAL.handle_message - Total processing time: {total_time:.2f}s")

            # Add timing information to metadata
            timing_metadata = {
                "timing_metrics": {
                    "schema_fetch_time": schema_time,
                    "analysis_time": analysis_time,
                    "code_generation_time": code_time,
                    "execution_time": execution_time,
                    "insight_generation_time": insights_time if 'insights_time' in locals() else 0,
                    "total_time": total_time
                }
            }

            # Yield content
            if insights_result and insights_result.summary:
                markdown_content = f"# Analysis Results\n\n{insights_result.summary}\n\n"

                if insights_result.insights:
                    markdown_content += "## Key Insights\n\n"
                    markdown_content += "\n".join(f"- {insight.description}" for insight in insights_result.insights)

                self.logger.info(
                    f"AnalyticsPAL.handle_message - Yielding content with {len(markdown_content)} characters")
                print("\n\n=== YIELDING CONTENT ===")
                print(markdown_content)
                print("=== END CONTENT ===\n\n")
                yield {
                    "content": markdown_content
                }
            else:
                # Fallback content if no insights
                fallback_content = f"# Analysis Results\n\nAnalysis of query: {prompt}\n\nQuery was processed successfully in {total_time:.2f}s."
                self.logger.info(f"AnalyticsPAL.handle_message - Yielding fallback content")
                print("\n\n=== YIELDING FALLBACK CONTENT ===")
                print(fallback_content)
                print("=== END FALLBACK CONTENT ===\n\n")
                yield {
                    "content": fallback_content
                }

            # Build the artifacts response
            artifacts = []

            # Add code artifacts - separated into individual artifacts
            if code_result:
                # Extract code properly from AgentRunResult if necessary
                code_content = self._extract_clean_text(code_result, "code")

                # Clean the code content - remove any explanation text
                if code_content and isinstance(code_content, str):
                    # For SQL, remove any comments at the beginning that explain the query
                    if code_result.code_type.lower() == "sql":
                        # Remove any explanation lines at the beginning (like "-- This query finds...")
                        code_lines = code_content.split("\n")
                        cleaned_lines = []
                        for line in code_lines:
                            # Keep SQL comments that are part of the code, but not explanatory ones at the beginning
                            if line.strip().startswith("--") and not cleaned_lines and "query" in line.lower():
                                continue
                            cleaned_lines.append(line)
                        code_content = "\n".join(cleaned_lines)
                    elif code_result.code_type.lower() == "python":
                        # Remove any explanation lines at the beginning (like "# This script performs...")
                        code_lines = code_content.split("\n")
                        cleaned_lines = []
                        for line in code_lines:
                            # Keep Python comments that are part of the code, but not explanatory ones at the beginning
                            if line.strip().startswith("#") and not cleaned_lines and "script" in line.lower():
                                continue
                            cleaned_lines.append(line)
                        code_content = "\n".join(cleaned_lines)

                print(f"\n=== CODE ARTIFACT ===")
                print(f"Type: {type(code_content)}")
                print(f"Content: {code_content[:100]}...")
                print("=== END CODE ARTIFACT ===\n")

                # Add the code artifact with proper extraction
                artifacts.append({
                    "artifact_type": "code",
                    "content": code_content
                })

                # Handle code_type similarly
                code_type_content = self._extract_clean_text(code_result, "code_type")

                print(f"\n=== CODE TYPE ARTIFACT ===")
                print(f"Type: {type(code_type_content)}")
                print(f"Content: {code_type_content}")
                print("=== END CODE TYPE ARTIFACT ===\n")

                # Add the code_type artifact
                artifacts.append({
                    "artifact_type": "code_type",
                    "content": code_type_content
                })

                # Handle explanation similarly
                explanation_content = self._extract_clean_text(code_result, "explanation")

                # Ensure explanation is only explanation, no code
                if explanation_content and isinstance(explanation_content, str):
                    # Remove any code snippets from the explanation
                    if code_result.code_type.lower() == "sql":
                        # Remove any SQL code from the explanation
                        explanation_lines = explanation_content.split("\n")
                        cleaned_explanation = []
                        for line in explanation_lines:
                            # Skip lines that look like SQL code
                            if (line.strip().startswith("SELECT") or
                                    line.strip().startswith("FROM") or
                                    line.strip().startswith("WHERE") or
                                    line.strip().startswith("GROUP BY") or
                                    line.strip().startswith("ORDER BY") or
                                    line.strip().startswith("HAVING") or
                                    line.strip().startswith("JOIN")):
                                continue
                            cleaned_explanation.append(line)
                        explanation_content = "\n".join(cleaned_explanation)
                    elif code_result.code_type.lower() == "python":
                        # Remove any Python code from the explanation
                        explanation_lines = explanation_content.split("\n")
                        cleaned_explanation = []
                        in_code_block = False
                        for line in explanation_lines:
                            # Skip lines that look like Python code
                            if line.strip().startswith("import ") or line.strip().startswith("from "):
                                continue
                            if line.strip().startswith("```python"):
                                in_code_block = True
                                continue
                            if line.strip() == "```" and in_code_block:
                                in_code_block = False
                                continue
                            if in_code_block:
                                continue
                            cleaned_explanation.append(line)
                        explanation_content = "\n".join(cleaned_explanation)

                print(f"\n=== EXPLANATION ARTIFACT ===")
                print(f"Type: {type(explanation_content)}")
                print(f"Content: {explanation_content[:100]}...")
                print("=== END EXPLANATION ARTIFACT ===\n")

                # Add the explanation artifact
                artifacts.append({
                    "artifact_type": "explanation",
                    "content": explanation_content
                })

            # Add data artifacts
            # Ensure results is defined to avoid reference errors
            if not 'results' in locals() or results is None:
                self.logger.warning(
                    "AnalyticsPAL.handle_message - Results variable not defined, creating empty results structure")
                results = {
                    "columns": [],
                    "records": [],
                    "total_rows": 0,
                    "returned_rows": 0
                }

            # Now safely use results
            try:
                # Create data artifact with records
                records_content = results.get("records", [])
                # Ensure records are serializable
                if isinstance(records_content, str):
                    # Already a string
                    data_content = records_content
                else:
                    # Convert to JSON string
                    data_content = json.dumps(records_content)

                artifacts.append({
                    "artifact_type": "data",
                    "content": data_content
                })

                # Create metadata artifact with database info
                db_type = "unknown"
                if database_uid:
                    try:
                        # Get database info to determine actual type
                        db_info = await self.analytics_repository.get_database_info(database_uid)
                        if db_info and hasattr(db_info, 'type'):
                            db_type = db_info.type.lower()
                    except Exception as e:
                        self.logger.warning(f"Could not determine database type: {str(e)}")

                # Ensure metadata is serializable
                if 'results' in locals() and results is not None:
                    metadata = {
                        "total_rows": results.get("total_rows", len(records_content)),
                        "returned_rows": len(records_content),
                        "data_source": {
                            "type": db_type,
                            "id": database_uid or "unknown"
                        }
                    }
                else:
                    # Default metadata when results is not available
                    metadata = {
                        "total_rows": len(records_content) if isinstance(records_content, list) else 0,
                        "returned_rows": len(records_content) if isinstance(records_content, list) else 0,
                        "data_source": {
                            "type": db_type,
                            "id": database_uid or "unknown"
                        }
                    }

                artifacts.append({
                    "artifact_type": "metadata",
                    "content": json.dumps(metadata)
                })

                # Add statistics if we have numeric columns
                if hasattr(self, "_df") and self._df is not None and not self._df.empty:
                    try:
                        numeric_cols = self._df.select_dtypes(include=['number']).columns.tolist()
                        if numeric_cols:
                            statistics = {"numeric": {}}
                            for col in numeric_cols:
                                statistics["numeric"][col] = {
                                    "min": float(self._df[col].min()),
                                    "max": float(self._df[col].max()),
                                    "mean": float(self._df[col].mean()),
                                    "median": float(self._df[col].median())
                                }
                            artifacts.append({
                                "artifact_type": "statistics",
                                "content": json.dumps(statistics)
                            })
                    except Exception as e:
                        self.logger.warning(f"Could not generate statistics: {str(e)}")

                # Add column information
                columns = []

                # Ensure results is defined
                if 'results' in locals() and results is not None:
                    for col in results.get("columns", []):
                        try:
                            col_type = col.get("type", "").upper()
                            # Determine icon based on column type
                            icon = "🔣"  # Default icon for unknown types

                            # Numeric types
                            if any(num_type in col_type for num_type in
                                   ["INT", "FLOAT", "DECIMAL", "DOUBLE", "NUMBER", "NUMERIC"]):
                                icon = "🔢"
                            # Date/time types
                            elif any(date_type in col_type for date_type in ["DATE", "TIME", "TIMESTAMP", "DATETIME"]):
                                icon = "📅"
                            # Boolean types
                            elif "BOOL" in col_type:
                                icon = "✓"
                            # Text/string types
                            elif any(text_type in col_type for text_type in ["CHAR", "TEXT", "VARCHAR", "STRING"]):
                                icon = "🔠"

                            column_info = {
                                "name": col.get("name", ""),
                                "display_name": col.get("name", "").replace("_", " ").title(),
                                "type": col_type,
                                "icon": icon,  # Use the determined icon
                                "sortable": True,
                                "filterable": True
                            }

                            # Add sample values if available
                            if results.get("records") and len(results.get("records")) > 0:
                                sample_values = list(
                                    set([str(r.get(col.get("name"), "")) for r in results.get("records")[:5]]))
                                if sample_values:
                                    column_info["sample_values"] = sample_values

                            columns.append(column_info)
                        except Exception as e:
                            self.logger.warning(f"Error processing column {col.get('name', 'unknown')}: {str(e)}")
                else:
                    self.logger.warning(
                        "AnalyticsPAL.handle_message - Results variable not defined for columns artifact")

                artifacts.append({
                    "artifact_type": "columns",
                    "content": json.dumps(columns)
                })
            except Exception as e:
                self.logger.warning(f"Error creating data artifacts: {str(e)}")

            # Add timing metadata to artifacts
            artifacts.append({
                "artifact_type": "timing_metrics",
                "content": json.dumps(timing_metadata)
            })

            # Yield the artifacts
            if artifacts:
                self.logger.info(f"AnalyticsPAL.handle_message - Yielding {len(artifacts)} artifacts")

                # Log details about each artifact for debugging
                for i, artifact in enumerate(artifacts):
                    try:
                        artifact_type = artifact.get("artifact_type", "unknown")
                        content = artifact.get("content", "")

                        # Ensure content is a string
                        if not isinstance(content, str):
                            self.logger.warning(f"Artifact {i + 1} content is not a string, converting to string")
                            content = str(content)
                            artifact["content"] = content

                        content_preview = content[:50] + "..." if len(content) > 50 else content
                        self.logger.info(
                            f"AnalyticsPAL.handle_message - Artifact {i + 1}: type={artifact_type}, content_preview={content_preview}")
                    except Exception as e:
                        self.logger.warning(f"Error logging artifact {i + 1}: {str(e)}")

                print("\n\n=== YIELDING ARTIFACTS ===")
                print(f"Number of artifacts: {len(artifacts)}")
                for i, artifact in enumerate(artifacts):
                    print(f"\nArtifact {i + 1}:")
                    print(f"  Type: {artifact.get('artifact_type', 'unknown')}")
                    content = artifact.get("content", "")
                    print(f"  Content Type: {type(content)}")
                    print(f"  Content Preview: {content[:50]}..." if len(content) > 50 else content)
                print("=== END ARTIFACTS ===\n\n")

                try:
                    yield {
                        "type": "artifacts",
                        "artifacts": artifacts
                    }

                    # Final status update
                    yield self._create_meta_content("Analysis complete", "completed", "text")
                except Exception as e:
                    self.logger.error(f"Error yielding artifacts: {str(e)}")
                    print(f"ERROR YIELDING ARTIFACTS: {str(e)}")

                    # Error status update
                    yield self._create_meta_content(f"Error sending artifacts: {str(e)}", "error", "text")
            else:
                self.logger.warning("AnalyticsPAL.handle_message - No artifacts to yield")

            # Generate query suggestions asynchronously as the final step
            suggestions = await self._generate_query_suggestions(
                original_query=prompt,
                code_result=code_result,
                schema=schema,
                error_message=None,
                database_uid=database_uid,
                table_uid=table_uid
            )

            # Yield suggestions if any were generated
            if suggestions:
                self.logger.info(f"AnalyticsPAL.handle_message - Yielding {len(suggestions)} query suggestions")
                yield {
                    "type": "suggestions",
                    "suggestions": suggestions
                }

        except TokenLimitError as e:
            self.logger.error(f"AnalyticsPAL.handle_message - Credits limit exceeded: {str(e)}")
            yield {
                "content": TOKEN_LIMIT_ERROR_MESSAGE
            }
            return

        except Exception as e:
            self.logger.error(f"AnalyticsPAL.handle_message - Error processing message: {str(e)}")
            yield {
                "type": "content",
                "content": f"Error processing your query: {str(e)}"
            }

    async def _analyze_query(
            self,
            user_id: str,
            message: str,
            schema: Optional[Union[SchemaInfo, str]] = None,
            message_history: Optional[List[Dict]] = None
    ) -> QueryAnalysisResult:
        """
        Analyze a natural language query using the QueryAnalyzer agent.
        
        Args:
            message: The natural language query
            schema: The database schema information
            message_history: The history of messages
        Returns:
            QueryAnalysisResult: Analysis of the query
        """
        self.logger.info("AnalyticsPAL._analyze_query - Starting query analysis")
        start_time = datetime.now()

        try:
            # Extract database name from schema for reference
            db_name = None
            db_type = "unknown"

            if schema:
                if isinstance(schema, SchemaInfo):
                    db_name = schema.database_name
                    db_type = schema.database_type
                elif isinstance(schema, str) and "Database:" in schema:
                    # Try to extract from string format
                    for line in schema.split('\n'):
                        if line.startswith("Database:"):
                            parts = line.split(":", 1)
                            if len(parts) > 1:
                                db_info = parts[1].strip()
                                if "(" in db_info and ")" in db_info:
                                    db_name_part = db_info.split("(")[0].strip()
                                    db_type_part = db_info.split("(")[1].split(")")[0].strip()
                                    db_name = db_name_part
                                    db_type = db_type_part

            self.logger.info(f"AnalyticsPAL._analyze_query - Using database: {db_name} ({db_type})")

            # Run the query analyzer with the schema
            try:
                result = await self.query_analyzer.run(
                    user_id=user_id,
                    query=message,
                    schema=schema,
                    message_history=message_history
                )
            except TokenLimitError as e:
                self.logger.error(f"AnalyticsPAL._analyze_query - Credits limit exceeded: {str(e)}")
                raise  # Re-raise the TokenLimitError to be caught by handle_message
            except Exception as e:
                self.logger.error(f"AnalyticsPAL._analyze_query - Error running query analyzer: {str(e)}")
                raise e

            print("AnalyticsPAL._analyze_query - Query analysis completed:", result)

            # Log the process in development mode
            end_time = datetime.now()
            timings = {"total_seconds": (end_time - start_time).total_seconds()}
            self.dev_logger.log_query_analysis(
                query=message,
                schema=schema,
                result=result,
                timings=timings
            )

            self.logger.info("AnalyticsPAL._analyze_query - Query analysis complete")
            return result

        except TokenLimitError as e:
            # This catch block is specifically for TokenLimitError that might occur outside the try block
            self.logger.error(f"AnalyticsPAL._analyze_query - Credits limit exceeded: {str(e)}")
            raise  # Re-raise to be caught by handle_message
        except Exception as e:
            end_time = datetime.now()
            timings = {"total_seconds": (end_time - start_time).total_seconds()}

            # Create fallback result
            fallback_result = QueryAnalysisResult(
                tables=[],
                columns=[],
                conditions=[],
                aggregations=[],
                groupings=[],
                orderings=[],
                analysis="Error analyzing query: " + str(e),
                suggested_approach="Unable to analyze query due to an error."
            )

            # Log the error in development mode
            self.dev_logger.log_query_analysis(
                query=message,
                schema=schema,
                result=fallback_result,
                timings={**timings, "error": str(e)}
            )

            self.logger.error(f"AnalyticsPAL._analyze_query - Error analyzing query: {str(e)}")
            return fallback_result

    async def _generate_code(
            self,
            user_id: str,
            query: str,
            query_analysis: QueryAnalysisResult,
            schema: Optional[Union[SchemaInfo, str]] = None,
            db_type: str = "unknown",
            additional_context: Optional[str] = None
    ) -> CodeGenerationResult:
        """
        Generate code based on query analysis using the CodeGenerator agent.
        
        Args:
            query: The natural language query
            query_analysis: The analysis of the query
            schema: The database schema information
            db_type: The database type
            
        Returns:
            CodeGenerationResult: Generated code with metadata
        """
        self.logger.info("AnalyticsPAL._generate_code - Starting code generation")
        start_time = datetime.now()

        # Determine the code type based on the database type
        code_type = "sql" if db_type.lower() == "postgres" else "python"
        self.logger.info(f"AnalyticsPAL._generate_code - Using code type: {code_type}")

        try:
            # Pass the structured schema directly to the agent
            result = await self.code_generator.run(
                user_id=user_id,
                query=query,
                query_analysis=query_analysis,
                schema=schema,
                db_type=db_type,
                code_type=code_type,
                additional_context=additional_context
            )

            # Log the process in development mode
            end_time = datetime.now()
            timings = {"total_seconds": (end_time - start_time).total_seconds()}
            self.dev_logger.log_code_generation(
                query=query,
                query_analysis=query_analysis,
                schema=schema,
                db_type=db_type,
                code_type=code_type,
                result=result,
                timings=timings
            )

            self.logger.info("AnalyticsPAL._generate_code - Code generation complete")
            return result

        except TokenLimitError as e:
            self.logger.error(f"AnalyticsPAL._generate_code - Credits limit exceeded: {str(e)}")
            raise  # Re-raise to be caught by handle_message
        except Exception as e:
            end_time = datetime.now()
            timings = {"total_seconds": (end_time - start_time).total_seconds()}

            # Create fallback result
            fallback_result = CodeGenerationResult(
                code="# Error generating code\n# " + str(e),
                code_type=code_type,
                explanation="An error occurred during code generation: " + str(e),
                estimated_accuracy=0.0,
                warnings=["Code generation failed due to an error"],
                expected_output_format=None
            )

            # Log the error in development mode
            self.dev_logger.log_code_generation(
                query=query,
                query_analysis=query_analysis,
                schema=schema,
                db_type=db_type,
                code_type=code_type,
                result=fallback_result,
                timings={**timings, "error": str(e)}
            )

            self.logger.error(f"AnalyticsPAL._generate_code - Error generating code: {str(e)}")
            return fallback_result

    async def _execute_code(
            self,
            user_id: str,
            code_result: CodeGenerationResult,
            query_analysis_result: QueryAnalysisResult,
            database_uid: Optional[str] = None,
            table_uid: Optional[str] = None
    ) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        Execute generated code using the appropriate executor.
        
        Args:
            code_result: The generated code result
            query_analysis: The query analysis result
            database_uid: Optional database UID
            table_uid: Optional table UID
            
        Returns:
            Tuple with DataFrame result and optional error message
        """
        self.logger.info("AnalyticsPAL._execute_code - Starting code execution")
        start_time = datetime.now()

        try:
            code = code_result.code
            code_type = code_result.code_type

            self.logger.info(f"AnalyticsPAL._execute_code - Code type: {code_type}")

            # Determine database type if database_uid is provided
            db_type = "unknown"
            if database_uid and self.analytics_repository:
                try:
                    db_info = await self.analytics_repository.get_database_info(database_uid)
                    if db_info and hasattr(db_info, 'type'):
                        db_type = db_info.type.lower()
                        self.logger.info(f"AnalyticsPAL._execute_code - Database type: {db_type}")
                except Exception as e:
                    self.logger.warning(f"AnalyticsPAL._execute_code - Error getting database type: {str(e)}")

            result = None
            error = None

            # Handle SQL code
            if code_type.lower() == "sql":
                self.logger.info("AnalyticsPAL._execute_code - Executing SQL code")
                result, error = await execute_sql(
                    query=code,
                    repository_adapter=self.analytics_repository,
                    database_uid=database_uid,
                    logger=self.logger
                )
                self.logger.info(f"AnalyticsPAL._execute_code - SQL execution complete")

            # Handle Python code
            elif code_type.lower() == "python":
                self.logger.info("AnalyticsPAL._execute_code - Executing Python code")
                # For CSV or Excel data
                context_data = {}

                # Try to load CSV data if possible
                if self.analytics_repository and database_uid and db_type == "csv":
                    try:
                        self.logger.info(f"AnalyticsPAL._execute_code - Fetching CSV data for {database_uid}")
                        # Check if we have a specific table_uid
                        if table_uid:
                            # Use the CSV executor to load the data
                            if not hasattr(self, 'csv_executor'):
                                from app.pal.analytics.executors.csv_executor import CSVExecutor
                                self.csv_executor = CSVExecutor(
                                    s3_client=self.analytics_repository.s3_client,
                                    analytics_repository=self.analytics_repository,
                                    logger=self.logger
                                )

                            # Get a preview of the data - will use the full dataset in production
                            df, csv_error = await self.csv_executor.preview_csv(
                                database_uid=database_uid,
                                table_uid=table_uid,
                                limit=10000  # Get a meaningful amount of data
                            )

                            if csv_error:
                                self.logger.warning(f"AnalyticsPAL._execute_code - CSV loading warning: {csv_error}")

                            if df is not None:
                                context_data['df'] = df
                        else:
                            # Get database tables if no specific table_uid
                            tables = await self.analytics_repository.get_tables(database_uid)
                            if tables and len(tables) > 0:
                                # Use the first table as default
                                table = tables[0]
                                table_id = table.uid if hasattr(table, 'uid') else table.id if hasattr(table,
                                                                                                       'id') else None

                                if table_id:
                                    # Initialize CSV executor if needed
                                    if not hasattr(self, 'csv_executor'):
                                        from app.pal.analytics.executors.csv_executor import CSVExecutor
                                        self.csv_executor = CSVExecutor(
                                            s3_client=self.analytics_repository.s3_client,
                                            analytics_repository=self.analytics_repository,
                                            logger=self.logger
                                        )

                                    # Get a preview of the data
                                    df, csv_error = await self.csv_executor.preview_csv(
                                        database_uid=database_uid,
                                        table_uid=table_id,
                                        limit=10000
                                    )

                                    if csv_error:
                                        self.logger.warning(
                                            f"AnalyticsPAL._execute_code - CSV loading warning: {csv_error}")

                                    if df is not None:
                                        context_data['df'] = df
                    except Exception as e:
                        self.logger.error(f"AnalyticsPAL._execute_code - Error loading CSV data: {str(e)}")
                        self.logger.error(traceback.format_exc())
                
                # Try to load Excel data if possible
                elif self.analytics_repository and database_uid and db_type == "excel":
                    try:
                        self.logger.info(f"AnalyticsPAL._execute_code - Fetching Excel data for {database_uid}")
                        # Check if we have a specific table_uid (sheet in Excel)
                        if table_uid:
                            # Use the Excel executor to load the data
                            if not hasattr(self, 'excel_executor'):
                                from app.pal.analytics.executors.excel_executor import ExcelExecutor
                                self.excel_executor = ExcelExecutor(
                                    s3_client=self.analytics_repository.s3_client,
                                    analytics_repository=self.analytics_repository,
                                    logger=self.logger
                                )

                            # Get a preview of the data - will use the full dataset in production
                            df, excel_error = await self.excel_executor.preview_excel(
                                database_uid=database_uid,
                                table_uid=table_uid,  # In Excel, this could represent a sheet name or index
                                limit=10000  # Get a meaningful amount of data
                            )

                            if excel_error:
                                self.logger.warning(f"AnalyticsPAL._execute_code - Excel loading warning: {excel_error}")

                            if df is not None:
                                context_data['df'] = df
                        else:
                            # Get all sheets if no specific table_uid (sheet) is provided
                            sheets = await self.analytics_repository.get_tables(database_uid)
                            if sheets and len(sheets) > 0:
                                # Use the first sheet as default
                                sheet = sheets[0]
                                sheet_id = sheet.uid if hasattr(sheet, 'uid') else sheet.id if hasattr(sheet, 'id') else None

                                if sheet_id:
                                    # Initialize Excel executor if needed
                                    if not hasattr(self, 'excel_executor'):
                                        from app.pal.analytics.executors.excel_executor import ExcelExecutor
                                        self.excel_executor = ExcelExecutor(
                                            s3_client=self.analytics_repository.s3_client,
                                            analytics_repository=self.analytics_repository,
                                            logger=self.logger
                                        )

                                    # Get a preview of the data
                                    df, excel_error = await self.excel_executor.preview_excel(
                                        database_uid=database_uid,
                                        table_uid=sheet_id,
                                        limit=10000
                                    )

                                    if excel_error:
                                        self.logger.warning(
                                            f"AnalyticsPAL._execute_code - Excel loading warning: {excel_error}")

                                    if df is not None:
                                        context_data['df'] = df
                    except Exception as e:
                        self.logger.error(f"AnalyticsPAL._execute_code - Error loading Excel data: {str(e)}")
                        self.logger.error(traceback.format_exc())

                # Convert DataFrame to JSON-serializable format
                try:
                    if 'df' in context_data and context_data['df'] is not None:
                        context_data['df'] = context_data["df"].to_dict(orient="records")
                    else:
                        return None, "No DataFrame found in context_data to serialize."
                except Exception as e:
                    return None, f"Error serializing DataFrame: {str(e)}"
                
                try:
                    result_from_code_execution_client = self.code_execution_client.execute_code_sync(
                        user_id=user_id,
                        code=code,
                        input_data=context_data,
                        timeout_seconds=self.code_execution_timeout
                    )

                    self.logger.info(f"Result from code execution client: {result_from_code_execution_client}")
                    
                    # Convert the result back to DataFrame if needed
                    if result_from_code_execution_client and hasattr(result_from_code_execution_client, 'dataframe') and result_from_code_execution_client.dataframe is not None:
                        if isinstance(result_from_code_execution_client.dataframe, dict):
                            try:
                                df = pd.DataFrame(result_from_code_execution_client.dataframe)
                                return df, None
                            except Exception as e:
                                self.logger.error(f"Error converting dict to DataFrame: {str(e)}")
                                return None, f"Error converting result to DataFrame: {str(e)}"
                        elif isinstance(result_from_code_execution_client.dataframe, pd.DataFrame):
                            return result_from_code_execution_client.dataframe, None
                        else:
                            return None, f"Unexpected result type: {type(result_from_code_execution_client.dataframe)}"
                    
                    # # If no DataFrame was created, proceed with normal execution
                    # result, error = await execute_python_code(
                    #     code,
                    #     context_data,
                    #     self.logger,
                    #     timeout=self.code_execution_timeout
                    # )
                    self.logger.info(f"AnalyticsPAL._execute_code - Python execution complete")
                except Exception as e:
                    self.logger.error(f"AnalyticsPAL._execute_code - Error executing code: {str(e)}")
                    self.logger.error(traceback.format_exc())
                    return None, f"Error executing code: {str(e)}"

            else:
                self.logger.error(f"AnalyticsPAL._execute_code - Unsupported code type: {code_type}")
                return None, f"Unsupported code type: {code_type}"

                # After code execution, ensure the result is a DataFrame

            if result is not None and not isinstance(result, pd.DataFrame):
                self.logger.warning(f"AnalyticsPAL._execute_code - Result is not a DataFrame: {type(result)}")

                if isinstance(result, (int, float)):
                    self.logger.info("AnalyticsPAL._execute_code - Converting scalar result to DataFrame")
                    result = pd.DataFrame({"Total value": [result]})

                elif isinstance(result, (list, dict)):
                    try:
                        result = pd.DataFrame(result)
                    except Exception as df_error:
                        self.logger.error(
                            f"AnalyticsPAL._execute_code - Failed to convert result to DataFrame: {df_error}")
                        return None, f"Error: Cannot convert result to DataFrame."
            if isinstance(result, pd.DataFrame) and list(result.columns) == [0]:
                result.columns = ["Total value"]

                # Log the process in development mode
            end_time = datetime.now()
            timings = {"total_seconds": (end_time - start_time).total_seconds()}
            self.dev_logger.log_execution(
                code_result=code_result,
                database_uid=database_uid or "unknown",
                table_uid=table_uid or "unknown",
                result=result,
                error=error,
                timings=timings
            )

            return result, error

        except Exception as e:
            error_msg = f"Error executing code: {str(e)}"

            # Log the error in development mode
            end_time = datetime.now()
            timings = {"total_seconds": (end_time - start_time).total_seconds()}
            self.dev_logger.log_execution(
                code_result=code_result,
                database_uid=database_uid or "unknown",
                table_uid=table_uid or "unknown",
                result=None,
                error=error_msg,
                timings={**timings, "error": str(e)}
            )

            self.logger.error(f"AnalyticsPAL._execute_code - {error_msg}")
            return None, error_msg
    
    async def _generate_insights(
            self,
            user_id: str,
            data: pd.DataFrame,
            query_analysis: QueryAnalysisResult,
            code_result: CodeGenerationResult,
            query: str
    ) -> InsightGenerationResult:
        """
        Generate insights from data using the InsightGenerator agent.
        
        Args:
            data: The query result data
            query_analysis: The query analysis result
            code_result: The code generation result
            query: The original natural language query
            
        Returns:
            InsightGenerationResult: Generated insights
        """
        self.logger.info("AnalyticsPAL._generate_insights - Starting insight generation")
        start_time = datetime.now()

        try:
            # Convert dataframe to JSON string for passing to agent
            data = data.rename(columns=lambda x: str(x))
            result_data_json = data.to_json(orient="records")

            # Get schema information from the dataframe
            schema = self._get_schema_from_dataframe(data)

            # Run the insight generator with the data and context
            result = await self.insight_generator.run(
                user_id=user_id,
                query=query,
                query_analysis=query_analysis,
                code_result=code_result,
                result_data=result_data_json,
                schema=schema,
                row_count=len(data),
                column_count=len(data.columns)
            )

            # Log the process in development mode
            end_time = datetime.now()
            timings = {"total_seconds": (end_time - start_time).total_seconds()}
            self.dev_logger.log_insight_generation(
                query=query,
                query_analysis=query_analysis,
                code_result=code_result,
                data=data,
                result=result,
                timings=timings
            )

            self.logger.info(f"AnalyticsPAL._generate_insights - Generated {len(result.insights)} insights")
            return result

        except Exception as e:
            end_time = datetime.now()
            timings = {"total_seconds": (end_time - start_time).total_seconds()}

            # Create fallback result
            fallback_result = InsightGenerationResult(
                insights=[],
                summary=f"Error generating insights: {str(e)}",
                visualization_suggestions=[]
            )

            # Log the error in development mode
            self.dev_logger.log_insight_generation(
                query=query,
                query_analysis=query_analysis,
                code_result=code_result,
                data=data,
                result=fallback_result,
                timings={**timings, "error": str(e)}
            )

            self.logger.error(f"AnalyticsPAL._generate_insights - Error generating insights: {str(e)}")
            return fallback_result

    def _format_results(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Format DataFrame results to a JSON serializable format.
        
        Args:
            df: DataFrame with results
            
        Returns:
            Dictionary with formatted results
        """
        if df is None:
            return None

        try:
            # Get column names and types
            columns = []
            for col in df.columns:
                col_type = str(df[col].dtype)
                columns.append({
                    "name": col,
                    "type": col_type
                })

            # Convert DataFrame to list of records
            records = []
            for _, row in df.head(100).iterrows():  # Limit to 100 rows for performance
                record = {}
                for col in df.columns:
                    val = row[col]

                    # Convert non-serializable values to strings
                    if pd.isna(val):
                        record[col] = None
                    elif isinstance(val, pd.Timestamp):
                        record[col] = val.isoformat()
                    else:
                        try:
                            # Test if value is JSON serializable
                            json.dumps(val)
                            record[col] = val
                        except:
                            record[col] = str(val)

                records.append(record)

            # Return formatted results
            return {
                "columns": columns,
                "records": records,
                "total_rows": len(df),
                "returned_rows": min(len(df), 100)
            }

        except Exception as e:
            self.logger.error(f"Error formatting results: {str(e)}")
            return {
                "error": f"Error formatting results: {str(e)}",
                "data": df.to_dict(orient="records")[:10]  # Fallback: return first 10 rows as dict
            }

    def _get_schema_from_dataframe(self, df: pd.DataFrame) -> str:
        """
        Extract schema information from a DataFrame.
        
        Args:
            df: The DataFrame to extract schema from
            
        Returns:
            str: Schema information as a formatted string
        """
        try:
            # Create a simple schema representation
            columns = []
            for col_name in df.columns:
                col_str = str(col_name)
                # Determine data type
                dtype = df[col_name].dtype
                if pd.api.types.is_numeric_dtype(dtype):
                    if pd.api.types.is_integer_dtype(dtype):
                        data_type = "integer"
                    else:
                        data_type = "float"
                elif pd.api.types.is_datetime64_dtype(dtype):
                    data_type = "datetime"
                else:
                    data_type = "string"

                # Add column info
                columns.append({
                    "name": col_str,
                    "data_type": data_type,
                    "nullable": bool(df[col_name].isna().any())
                })

            # Create schema object
            schema_info = {
                "table_name": "query_result",
                "columns": columns,
                "row_count": len(df)
            }

            # Convert to formatted string
            return json.dumps(schema_info, indent=2)

        except Exception as e:
            self.logger.warning(f"Error extracting schema from DataFrame: {str(e)}")
            return "{}"

    async def analyze_query(self, user_id: str, message: str, message_history: Optional[List[Dict]] = None) -> QueryAnalysisResult:
        """
        Analyze a natural language query.
        
        Args:
            message: User's natural language query
            
        Returns:
            QueryAnalysisResult: Structured analysis of the query
        """
        self.logger.info(f"AnalyticsPAL.analyze_query - Analyzing query: {message}")

        # Check cache first if enabled
        if self.enable_cache and message in self.cache.get("query_analysis", {}):
            self.logger.info("AnalyticsPAL.analyze_query - Using cached result")
            return self.cache["query_analysis"][message]

        # Run query analysis
        try:
            # Get schema for all connected databases
            schema = await self._prepare_schema()

            # Use the query analyzer agent
            analysis_result = await self.query_analyzer.run(
                user_id=user_id,
                query=message,
                schema=schema
            )

            # Log the result
            self.logger.info(f"AnalyticsPAL.analyze_query - Analysis result: {analysis_result.intent}")

            # Cache the result if caching is enabled
            if self.enable_cache:
                if "query_analysis" not in self.cache:
                    self.cache["query_analysis"] = {}
                self.cache["query_analysis"][message] = analysis_result

            return analysis_result

        except Exception as e:
            self.logger.error(f"AnalyticsPAL.analyze_query - Error analyzing query: {str(e)}")
            # Return a fallback analysis result
            return QueryAnalysisResult(
                intent="unknown",
                target_entities=[],
                conditions=[],
                complexity="unknown",
                requires_join=False,
                feasible=False,
                reason=f"Error during analysis: {str(e)}",
                metrics=[],
                is_ambiguous=False,
                ambiguity_score=0.0,
                ambiguity_reason="",
                intent_category="unknown",
                grouping=[],
                time_range=None
            )

    async def generate_code(
            self,
            user_id: str,
            message: str,
            query_analysis: Optional[QueryAnalysisResult] = None,
            code_type: str = "sql"
    ) -> CodeGenerationResult:
        """
        Generate code for a natural language query.
        
        Args:
            message: User's natural language query
            query_analysis: Optional pre-computed query analysis
            code_type: Type of code to generate (python or sql)
            
        Returns:
            CodeGenerationResult: The generated code with metadata
        """
        self.logger.info(f"AnalyticsPAL.generate_code - Generating {code_type} code for: {message}")

        # Check cache first if enabled
        cache_key = f"{message}_{code_type}"
        if self.enable_cache and cache_key in self.cache.get("code_generation", {}):
            self.logger.info("AnalyticsPAL.generate_code - Using cached result")
            return self.cache["code_generation"][cache_key]

        # Run code generation
        try:
            # Analyze the query first if not provided
            if query_analysis is None:
                query_analysis = await self.analyze_query(user_id, message)

            # Get schema for all connected databases
            schema = await self._prepare_schema()

            # Detect database type from query analysis
            db_type = "unknown"
            if query_analysis.target_entities and len(query_analysis.target_entities) > 0:
                # Try to infer from target entities and schema
                if schema:
                    db_type = getattr(schema, "database_type", "unknown")

            # Use the code generator agent
            code_result = await self.code_generator.run(
                user_id=user_id,
                query=message,
                query_analysis=query_analysis,
                schema=schema,
                db_type=db_type,
                code_type=code_type
            )

            # Log the result
            self.logger.info(f"AnalyticsPAL.generate_code - Generated {code_type} code")

            # Cache the result if caching is enabled
            if self.enable_cache:
                if "code_generation" not in self.cache:
                    self.cache["code_generation"] = {}
                self.cache["code_generation"][cache_key] = code_result

            return code_result

        except Exception as e:
            self.logger.error(f"AnalyticsPAL.generate_code - Error generating code: {str(e)}")

            # Return a fallback code generation result
            return CodeGenerationResult(
                code=f"-- Error generating {code_type} code: {str(e)}",
                code_type=code_type,
                explanation=f"Failed to generate code: {str(e)}",
                estimated_accuracy=0.0,
                warnings=[f"Error: {str(e)}"],
                expected_output_format=None
            )

    async def _generate_query_suggestions(
            self,
            original_query: str,
            code_result,
            schema: Optional[Union[SchemaInfo, str]] = None,
            error_message: Optional[str] = None,
            database_uid: Optional[str] = None,
            table_uid: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Generate alternative query suggestions when the original query returns no results.
        
        Args:
            original_query: The original natural language query
            code_result: The generated code result
            schema: Optional schema information
            error_message: Optional error message from execution
            database_uid: Optional database UID for recommendations
            table_uid: Optional table UID for recommendations
            
        Returns:
            List of query suggestions formatted for the UI
        """
        self.logger.info(
            f"AnalyticsPAL._generate_query_suggestions - Generating suggestions for query: {original_query}")

        try:
            # Get recommendations from analytics service
            suggestions = await self.analytics_service.get_recommendations(
                database_uid=database_uid,
                table_uid=table_uid,
                count=5,
                user_question=original_query
            )

            # Format suggestions for the UI
            formatted_suggestions = []
            for suggestion in suggestions.recommendations:
                formatted_suggestions.append({
                    "type": "QUERY",
                    "suggestion_content": {
                        "text": suggestion.question,
                        "title": suggestion.title,
                        "description": suggestion.explanation
                    }
                })

            self.logger.info(
                f"AnalyticsPAL._generate_query_suggestions - Generated {len(formatted_suggestions)} suggestions")
            return formatted_suggestions

        except Exception as e:
            self.logger.error(f"AnalyticsPAL._generate_query_suggestions - Error: {str(e)}")
            return []

    def _create_meta_content(self, title, status="inprogress", content_type="text", description=None):
        """
        Create a meta_content event with consistent formatting.
        
        Args:
            title: The title/main message of the meta_content
            status: Status (inprogress, completed, error)
            content_type: Type of content (text, code, data)
            description: Optional list of descriptive items or dict with additional metadata
            
        Returns:
            Dict containing the meta_content event
        """
        self._meta_id_counter += 1  # NOTE: Very important to mark previous meta_content as completed on the client side.

        # Validate status - ensure it's one of the expected values
        valid_statuses = ["inprogress", "completed", "error", "warning"]
        if status not in valid_statuses:
            status = "inprogress"  # Default to inprogress if invalid

        # Prepare description list
        desc_list = []
        if description:
            if isinstance(description, list):
                desc_list = description
            elif isinstance(description, dict):
                desc_list = [description]
            else:
                # Convert to string and add as single item
                desc_list = [{"title": str(description), "type": "text"}]

        # Create meta_content with timestamp for tracking
        return {
            "type": "meta_content",
            "meta_content": {
                "id": str(self._meta_id_counter),
                "title": title,
                "status": status,
                "type": content_type,
                "description": desc_list,
                "timestamp": datetime.now().isoformat()
            }
        }

    def get_average_timings(self) -> Dict[str, float]:
        """
        Get average timing metrics for each operation.
        
        Returns:
            Dict with average times in seconds for each operation
        """
        averages = {}
        for operation, times in self.timing_metrics.items():
            if times:
                avg_time = sum(times) / len(times)
                averages[operation] = round(avg_time, 3)
            else:
                averages[operation] = 0
        return averages

    def get_timing_statistics(self) -> Dict[str, Dict[str, float]]:
        """
        Get detailed timing statistics for each operation.
        
        Returns:
            Dict with min, max, avg times in seconds for each operation
        """
        stats = {}
        for operation, times in self.timing_metrics.items():
            if times:
                stats[operation] = {
                    "min": round(min(times), 3),
                    "max": round(max(times), 3),
                    "avg": round(sum(times) / len(times), 3),
                    "total_calls": len(times)
                }
            else:
                stats[operation] = {
                    "min": 0,
                    "max": 0,
                    "avg": 0,
                    "total_calls": 0
                }
        return stats

    def _get_error_description(self, error_message):
        """
        Extract error description from various error object types.
        
        Args:
            error_message: The error object which could be a string, dict, or Exception
            
        Returns:
            str: A string representation of the error
        """
        if error_message is None:
            return "Unknown error"

        # If it's a string, return directly
        if isinstance(error_message, str):
            return error_message[:100] if len(error_message) > 100 else error_message

        # If it's a dictionary with a 'message' key
        if isinstance(error_message, dict) and 'message' in error_message:
            message = error_message['message']
            return message[:100] if len(message) > 100 else message

        # If it's an Exception object
        if isinstance(error_message, Exception):
            # Try to extract 'message' from the exception
            try:
                # Check if exception has a message attribute
                if hasattr(error_message, 'message'):
                    return str(error_message.message)[:100]

                # Check if exception has args that might contain a message dict
                if hasattr(error_message, 'args') and error_message.args:
                    for arg in error_message.args:
                        if isinstance(arg, dict) and 'message' in arg:
                            return str(arg['message'])[:100]
            except:
                pass  # Silently continue to standard string conversion

            # Fall back to standard string conversion
            return str(error_message)[:100]

        # As a fallback, convert to string
        return str(error_message)[:100]

    async def _format_messages(self, context_messages, extras: str) -> List[dict]:
        """Format messages with proper context and handling of attachments"""
        messages_list = []

        # Add extras as initial context if provided
        if extras.strip():
            messages_list.append({
                "role": "system",
                "content": f" You are a MIPAL AI model (LLM) that helps in answering user queries. Consider this additional "
                           f"context when relevant: {extras}"
            })
        else:
            messages_list.append({
                "role": "system",
                "content": "You are a MIPAL AI model (LLM) that helps in answering user queries."
            })

        # Process each message in the context
        for msg in context_messages:
            formatted_message = await self._format_single_message(msg)
            if formatted_message:
                messages_list.append(formatted_message)

        return messages_list
    
    async def generate_and_execute_code(self, user_id: str, message, query_analysis_result, schema, db_type, database_uid, table_uid):
        """
        Generate and execute code for a natural language query.
        
        Args:
            message: User's natural language query
        """
        
        attempt = 1
        max_retries = 2
        execution_error = None
        additional_context = ""

        while attempt <= max_retries:
            if attempt > 1 and execution_error:
                additional_context = f"The code execution failed with the following error: {execution_error}. Please fix the error and try again."
    
            # Step 2: Generate code
            code_start = datetime.now()

            try:
                code_result = await self._generate_code(user_id, message, query_analysis_result, schema, db_type, additional_context)
            except TokenLimitError as e:
                self.logger.error(f"AnalyticsPAL._generate_code - Credits limit exceeded: {str(e)}")
                raise  # Re-raise to be caught by handle_message
            
            yield {"type": "code_result", "result": code_result}

            # Record code generation time
            code_time = (datetime.now() - code_start).total_seconds()
            self.timing_metrics["code_generation"].append(code_time)
            self.logger.info(f"AnalyticsPAL.handle_message - Code generation completed in {code_time:.2f}s")

            yield {"type": "code_time", "time": code_time}

            # Progress update - Executing code
            execution_start = datetime.now()

            yield self._create_meta_content(f"Executing code ({attempt}/{max_retries})", "inprogress", "text", [
                {"title": "Executing code...", "type": code_result.code_type, "execution": code_result.code,
                "status": "inprogress"}])
                
            results_df, error_message = await self._execute_code(
                user_id=user_id,
                code_result=code_result,
                query_analysis_result=query_analysis_result,
                database_uid=database_uid,
                table_uid=table_uid
            )


            # Record execution time
            execution_time = (datetime.now() - execution_start).total_seconds()
            self.timing_metrics["code_execution"].append(execution_time)
            self.logger.info(f"AnalyticsPAL.handle_message - Code execution completed in {execution_time:.2f}s")

            yield {"type": "execution_time", "time": execution_time}

            # Check if there was an error executing the code
            if error_message:
                self.logger.warning(f"AnalyticsPAL.handle_message - Error executing code: {error_message}")

                # Update meta content with error status
                yield self._create_meta_content(f"Executing code ({attempt}/{max_retries})", "inprogress", "text", [
                    {"title": "Executing code...", "type": code_result.code_type, "execution": code_result.code,
                     "status": "inprogress"},
                    {
                        "title": "Code execution failed",
                        "type": "text",
                        "status": "error",
                        "description": self._get_error_description(error_message)
                    }])

                
                if attempt == max_retries:
                    # Return error message as content if it's the last attempt
                    yield {
                        "type": "content",
                        "content": f"Error executing query: {self._get_error_description(error_message)}"
                    }
                
                attempt += 1
                execution_error = error_message

                yield self._create_meta_content("Retrying", "inprogress", "text")
                
                continue
            else:
                # Code execution was successful - update meta_content
                yield self._create_meta_content("Code executed successfully", "completed", "text")
                
                yield {"type": "final_result", "result": results_df}
                return
            
        yield {"type": "final_error", "error": "Failed to execute code after multiple attempts"}