import asyncio
import json
import logging
import traceback
from typing import Any, Dict, List, Optional, Union

from app.analytics.errors import CodeExecutionError
from pkg.log.logger import Logger
from app.pal.analytics.executors.sql_executor import SQLExecutor
from app.pal.analytics.executors.python_executor import PythonExecutor
from app.analytics.repository.analytics_repository import AnalyticsRepository
from app.code_execution.client.http_client import CodeExecutionClient
from uuid import UUID


class CodeExecutorService:
    """Service for executing code snippets in a safe environment"""

    def __init__(self, sql_executor: SQLExecutor, analytics_repository: AnalyticsRepository,
                 python_executor: PythonExecutor, code_executor: CodeExecutionClient, logger: Logger):
        """
        Initialize the code executor service
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        # These will be injected by container or set later if needed
        self.sql_executor = sql_executor
        self.analytics_repository = analytics_repository
        self.python_executor = python_executor
        self.code_executor = code_executor

    async def execute_python(self, code: str, data: Optional[List[Dict[str, Any]]] = None,
                             context: Optional[Dict[str, Any]] = None,
                             timeout: int = 30) -> tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Execute Python code in a safe environment
        
        Args:
            code: Python code to execute
            data: Optional data to make available to the code
            context: Optional additional context variables
            timeout: Maximum execution time in seconds
            
        Returns:
            Tuple of (results, error_message)
        """
        self.logger.info(f"Executing Python code: {code[:100]}{'...' if len(code) > 100 else ''}")

        try:
            # If we have a Python executor available, use it
            if self.python_executor:
                self.logger.info("Using Python executor to execute code")

                # Prepare data source context
                data_source = {}

                # Add data if provided
                if data:
                    data_source['data'] = data

                # Add additional context variables
                if context:
                    data_source.update(context)

                # Execute the code using the Python executor
                df, error = await self.python_executor.execute(
                    code=code,
                    data_source=data_source
                )

                if error:
                    self.logger.error(f"Python execution error: {error}")
                    return [], error

                if df is not None and hasattr(df, 'to_dict'):
                    # Convert DataFrame to list of dictionaries
                    results = df.to_dict(orient='records')
                    self.logger.info(f"Python code execution returned {len(results)} rows")
                    return results, None
                else:
                    self.logger.warning("Python execution returned no DataFrame")
                    return [], "Python execution returned no data"
            else:
                # No Python executor available, return placeholder for now
                self.logger.warning("Python execution not fully implemented - no Python executor available")
                # For backward compatibility, return a simple result
                return [{"message": "Code execution not yet fully implemented"}], None

        except Exception as e:
            error_msg = f"Error executing Python code: {str(e)}"
            self.logger.error(error_msg)
            return [], error_msg

    async def transform_data(self,
                             data: List[Dict[str, Any]],
                             transformation_code: str,
                             timeout: int = 30) -> List[Dict[str, Any]]:
        """
        Transform data using Python code
        
        Args:
            data: Data to transform
            transformation_code: Python code for transformation
            timeout: Maximum execution time in seconds
            
        Returns:
            Transformed data
        """
        try:
            self.logger.info("Transforming data with Python code")

            # Use Python executor if available
            if self.python_executor:
                self.logger.info("Using Python executor for data transformation")

                # Set up initial context with the data
                data_source = {'data': data}

                # Wrap the transformation code to set result
                wrapped_code = f"""
# Original transformation code
{transformation_code}

# Ensure result is set with the transformed data
if 'result' not in locals() and 'result' not in globals():
    result = data  # Default to original data if not explicitly set
"""

                # Execute the wrapped code
                df, error = await self.python_executor.execute(
                    code=wrapped_code,
                    data_source=data_source
                )

                if error:
                    self.logger.error(f"Error in data transformation: {error}")
                    return data  # Return original data on error

                if df is not None and hasattr(df, 'to_dict'):
                    # Convert DataFrame to list of dictionaries
                    transformed_data = df.to_dict(orient='records')
                    self.logger.info(f"Data transformation returned {len(transformed_data)} rows")
                    return transformed_data
                else:
                    self.logger.warning("Data transformation returned no DataFrame")
                    return data  # Return original data
            else:
                # No Python executor available
                self.logger.warning("Data transformation not fully implemented - no Python executor available")
                return data  # Return original data

        except Exception as e:
            self.logger.error(f"Error transforming data: {str(e)}")
            return data  # Return original data on error

    def _sanitize_code(self, code: str) -> str:
        """
        Sanitize code to prevent dangerous operations
        
        Args:
            code: Code to sanitize
            
        Returns:
            Sanitized code
        """
        # TODO: Implement code sanitization
        # This is a placeholder that will be implemented in a future PR
        return code

    def parse_message_artifacts(self, artifacts: List[dict]) -> Dict[str, Any]:
        """
        Parse message artifacts to extract data, columns, code, and metadata
        
        Args:
            artifacts: List of message artifacts
            
        Returns:
            Dictionary containing parsed artifacts:
            - data: Extracted data as JSON or list of dictionaries
            - columns: Column metadata
            - code: Code used to generate the data
            - code_type: Type of code (e.g., 'sql', 'python')
            - metadata: Additional metadata
        """
        try:
            self.logger.info("Parsing message artifacts")

            # Initialize result with default values
            result = {
                'data': None,
                'columns': None,
                'code': None,
                'code_type': None,
                'metadata': None
            }

            # Extract artifacts by type
            for artifact in artifacts:
                # Check the format of the artifact
                artifact_type = None
                content = None

                # If artifact is a dictionary with 'artifact_type' and 'content'
                if isinstance(artifact, dict) and 'artifact_type' in artifact and 'content' in artifact:
                    artifact_type = artifact['artifact_type']
                    content = artifact['content']
                # If artifact is an object with artifact_type and content attributes
                elif hasattr(artifact, 'artifact_type') and hasattr(artifact, 'content'):
                    artifact_type = artifact.artifact_type
                    content = artifact.content
                else:
                    self.logger.warning(f"Skipping artifact with unknown format: {artifact}")
                    continue

                # Extract content based on artifact type
                if artifact_type == 'data':
                    # Data can be a string (JSON) or already parsed
                    if isinstance(content, str):
                        try:
                            # Try to parse as JSON if it's a string
                            result['data'] = json.loads(content)
                        except json.JSONDecodeError:
                            # If not valid JSON, store as is
                            result['data'] = content
                    else:
                        # If already parsed, store as is
                        result['data'] = content

                elif artifact_type == 'columns':
                    # Columns can be a string (JSON) or already parsed
                    if isinstance(content, str):
                        try:
                            result['columns'] = json.loads(content)
                        except json.JSONDecodeError:
                            result['columns'] = content
                    else:
                        result['columns'] = content

                elif artifact_type == 'code':
                    result['code'] = content

                elif artifact_type == 'code_type':
                    result['code_type'] = content

                elif artifact_type == 'metadata':
                    # Metadata can be a string (JSON) or already parsed
                    if isinstance(content, str):
                        try:
                            result['metadata'] = json.loads(content)
                        except json.JSONDecodeError:
                            result['metadata'] = content
                    else:
                        result['metadata'] = content

            return result

        except Exception as e:
            self.logger.error(f"Error parsing message artifacts: {str(e)}")
            # Return empty result on error
            return {
                'data': None,
                'columns': None,
                'code': None,
                'code_type': None,
                'metadata': None
            }

    async def execute_sql(self,
                          sql: str,
                          database_id: Optional[str] = None,
                          timeout: int = 30) -> tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Execute SQL code and return the results
        
        Args:
            sql: SQL code to execute
            database_id: Optional database ID to execute the SQL against
            timeout: Maximum execution time in seconds
            
        Returns:
            Tuple of (results, error_message)
        """
        self.logger.info(f"Executing SQL code: {sql[:100]}{'...' if len(sql) > 100 else ''}")

        try:
            # If we have a SQL executor available, use it
            if self.sql_executor:
                self.logger.info(f"Using SQL executor to execute query on database {database_id}")
                df, error = await self.sql_executor.execute(query=sql, database_uid=database_id)

                if error:
                    self.logger.error(f"SQL execution error: {error}")
                    return [], error

                if df is not None and hasattr(df, 'to_dict'):
                    # Convert DataFrame to list of dictionaries
                    results = df.to_dict(orient='records')
                    self.logger.info(f"SQL query returned {len(results)} rows")
                    return results, None
                else:
                    self.logger.warning("SQL execution returned no DataFrame")
                    return [], "SQL execution returned no data"

            # If we have analytics repository with query method, use it directly
            elif self.analytics_repository and hasattr(self.analytics_repository, 'query'):
                self.logger.info(f"Using analytics repository to execute query on database {database_id}")
                try:
                    df = await self.analytics_repository.query(database_id, sql)

                    if df is not None and hasattr(df, 'to_dict'):
                        # Convert DataFrame to list of dictionaries
                        results = df.to_dict(orient='records')
                        self.logger.info(f"SQL query returned {len(results)} rows")
                        return results, None
                    else:
                        self.logger.warning("SQL execution returned no DataFrame")
                        return [], "SQL execution returned no data"
                except Exception as e:
                    error_msg = f"SQL execution error: {str(e)}"
                    self.logger.error(error_msg)
                    return [], error_msg
            else:
                # No execution service available
                self.logger.warning("SQL execution not fully implemented - no executor or repository available")
                return [], "SQL execution not fully implemented - no executor or repository available"
        except Exception as e:
            error_msg = f"SQL execution error: {str(e)}"
            self.logger.error(error_msg)
            return [], error_msg
