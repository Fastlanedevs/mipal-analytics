"""
Code Execution Utilities for Analytics PAL.
This module provides utilities for executing generated code.
"""

import pandas as pd
import io
import traceback
import asyncio
import sys
import os
from typing import Dict, Any, Optional, List, Union, Tuple
from app.pal.analytics.executors.python_executor import PythonExecutor
import numpy as np
from loguru import logger as loguru_logger
import json
from pandas import DataFrame

from app.pal.analytics.adapters.analytics_repository_adapter import AnalyticsRepositoryAdapter
from app.pal.analytics.utils.models import CodeGenerationResult
from pkg.log.logger import Logger

class RestrictedExecError(Exception):
    """Exception raised for restricted operations in code execution"""
    pass

async def execute_python_code(
    code: str, 
    context_data: Dict[str, Any] = None, 
    logger = None,
    timeout: int = 30
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Execute Python code using the PythonExecutor.
    
    Args:
        code: Python code to execute
        context_data: Dictionary with data to be made available to the code
        logger: Optional logger instance
        timeout: Execution timeout in seconds
        
    Returns:
        Tuple containing:
        - DataFrame with results (or None if error)
        - Error message (or None if successful)
    """
    if logger:
        logger.info("execute_python_code - Starting Python code execution")
        # Enhanced logging: Log the full code
        logger.info(f"execute_python_code - FULL CODE TO EXECUTE:\n{code}")
        logger.debug(f"execute_python_code - Code to execute: {code[:200]}...")
    
    # Default context data if none provided
    if context_data is None:
        context_data = {}
    
    # Add standard libraries to context data
    context_data.update({
        'numpy': __import__('numpy'),
        'np': __import__('numpy'),
        'datetime': __import__('datetime'),
        'math': __import__('math'),
        'stats': __import__('scipy.stats')
    })
    
    if logger:
        logger.info(f"execute_python_code - Context data keys: {list(context_data.keys())}")
    
    try:
        # Create an instance of PythonExecutor with the specified timeout
        executor = PythonExecutor(timeout=timeout, logger=logger)
        
        # Execute the code using the executor
        result, error = await executor.execute(code, context_data)
        
        if error:
            if logger:
                logger.error(f"execute_python_code - Error: {error}")
            return None, error
            
        if logger:
            if isinstance(result, pd.DataFrame):
                logger.info(f"execute_python_code - Execution successful, returned DataFrame with shape {result.shape}")
                # Enhanced logging: Show DataFrame sample
                if not result.empty:
                    logger.info(f"execute_python_code - DataFrame sample:\n{result.head(3)}")
            else:
                logger.info(f"execute_python_code - Execution successful, returned {type(result).__name__}")
                logger.info(f"execute_python_code - Result value: {result}")
                
        return result, None
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        if logger:
            logger.error(f"execute_python_code - Error executing code: {str(e)}")
            logger.error(f"execute_python_code - Traceback: {error_traceback}")
        
        return None, f"Error executing code: {str(e)}\n{error_traceback}"
        
async def execute_sql(
    query: Union[str, CodeGenerationResult],
    repository_adapter: AnalyticsRepositoryAdapter,
    database_uid: Optional[str] = None,
    connection_params: Optional[Dict[str, Any]] = None,
    logger: Optional[Logger] = None
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Execute SQL query and return the result.
    
    Args:
        query: SQL query string or CodeGenerationResult
        repository_adapter: AnalyticsRepositoryAdapter instance
        database_uid: Optional database UID
        connection_params: Optional connection parameters
        logger: Optional logger
    
    Returns:
        Tuple with DataFrame result and optional error message
    """
    if logger:
        logger.info(f"execute_sql - Starting SQL execution on database: {database_uid or 'using connection params'}")
    
    # Extract the SQL code if we're receiving a structured result object
    actual_query = query
    
    if not isinstance(query, str):
        # If it's a direct Pydantic model instance with a code attribute
        if hasattr(query, 'code') and isinstance(query.code, str):
            actual_query = query.code
            if logger:
                logger.info(f"execute_sql - Extracted SQL code from result object attribute: {actual_query[:100]}...")
    else:
        # Handle string representations of result objects
        try:
            # Check if it's a string containing a serialized result object
            if ("CodeGenerationResult" in query or "AgentRunResult" in query):
                if logger:
                    logger.info("execute_sql - Extracting SQL code from string representation of result object")
                
                import re
                # Try to extract the code between code=' and '
                # Handle both single and double quotes
                match = re.search(r"code=['\"](.+?)['\"]", query, re.DOTALL)
                
                if not match:
                    # Try alternative pattern for more complex nested structures
                    match = re.search(r"'code':\s*['\"](.+?)['\"]", query, re.DOTALL)
                
                if match:
                    actual_query = match.group(1)
                    # Clean up escaped quotes and newlines
                    actual_query = actual_query.replace('\\"', '"').replace("\\'", "'").replace('\\n', '\n')
                    if logger:
                        logger.info(f"execute_sql - Extracted SQL using regex: {actual_query[:100]}...")
                else:
                    if logger:
                        logger.warning("execute_sql - Could not extract SQL code from result object string")
                        logger.warning(f"execute_sql - Original query string: {query[:200]}...")
            
            # As a last resort, try to parse as JSON
            elif '{' in query and '}' in query:
                try:
                    import json
                    # Find the JSON part in the string
                    json_start = query.find('{')
                    json_end = query.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = query[json_start:json_end]
                        data = json.loads(json_str)
                        if 'code' in data and isinstance(data['code'], str):
                            actual_query = data['code']
                            if logger:
                                logger.info(f"execute_sql - Extracted SQL from JSON: {actual_query[:100]}...")
                except Exception as json_err:
                    if logger:
                        logger.debug(f"execute_sql - Failed to parse as JSON: {str(json_err)}")
        except Exception as extract_err:
            if logger:
                logger.error(f"execute_sql - Error extracting SQL code: {str(extract_err)}")
    
    # Check if we have a valid query
    if not actual_query or not actual_query.strip():
        error_msg = "Can't execute an empty query"
        if logger:
            logger.error(f"execute_sql - {error_msg}")
        return None, error_msg
    
    if logger:
        logger.info(f"execute_sql - Original query to execute: {actual_query}")
    
    # Define SQL variants to try
    sql_variants = [
        actual_query,  # Original query as-is
    ]
    
    # Add quoted variants only if the original isn't already using quotes
    if '"' not in actual_query:
        # Add a version with quoted identifiers
        quoted_sql = actual_query
        
        # Quote table names in FROM and JOIN
        import re
        for pattern in [r'FROM\s+(\w+)', r'JOIN\s+(\w+)']:
            quoted_sql = re.sub(pattern, lambda m: m.group(0).replace(m.group(1), f'"{m.group(1)}"'), quoted_sql)
            
        # Quote column identifiers
        for pattern in [r'([a-z]+)\.([a-z_]+)', r' ([a-z_]+) ']:
            quoted_sql = re.sub(pattern, lambda m: m.group(0).replace(m.group(1), f'"{m.group(1)}"'), quoted_sql)
        
        sql_variants.append(quoted_sql)
    
    # Try each SQL variant
    last_error = None
    for idx, sql_variant in enumerate(sql_variants):
        if logger:
            logger.info(f"execute_sql - Trying SQL variant {idx+1}/{len(sql_variants)}: {sql_variant}")
        
        try:
            # Set connection parameters if provided
            if connection_params:
                repository_adapter.set_connection_params(connection_params)
                
            # Execute query with this SQL variant
            result = await repository_adapter.execute_query(database_uid, sql_variant)
            
            if logger:
                logger.info(f"execute_sql - Query executed successfully with variant {idx+1}")
                
            return result, None
            
        except Exception as e:   
            last_error = e  # Update last_error with the latest exception
            if logger:
                logger.warning(f"execute_sql - Error with variant {idx+1}: {e}")
            
    
    # If we get here, all variants failed
    if logger:
        logger.error(f"execute_sql - All SQL variants failed. Last error: {last_error}")
    
    return None, last_error 