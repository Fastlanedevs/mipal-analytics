"""
Development Mode Logger for Analytics PAL.
This module provides utilities for logging agent results during development.
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional, Union, List
import pandas as pd


class DevLogger:
    """
    Development mode logger for Analytics PAL.
    Provides methods to log agent inputs, outputs, and execution details.
    """

    def __init__(self, enabled=False, log_dir="./logs/analytics", logger=None):
        """
        Initialize the DevLogger.
        
        Args:
            enabled: Whether logging is enabled
            log_dir: Directory to store logs
            logger: Optional logger instance
        """
        self.enabled = enabled
        self.log_dir = log_dir
        self.logger = logger

        if enabled:
            os.makedirs(log_dir, exist_ok=True)

    def log_query_analysis(self, query: str, schema: Any, result: Any, timings: Dict[str, float] = None):
        """
        Log query analysis results.
        
        Args:
            query: The user query
            schema: The schema provided to the agent
            result: The query analysis result
            timings: Optional timing information
        """
        if not self.enabled:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"{self.log_dir}/query_analysis_{timestamp}.json"

        # Prepare log data
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "agent": "QueryAnalyzer",
            "input": {
                "query": query,
                "schema": self._format_for_json(schema)
            },
            "output": self._format_for_json(result),
            "timings": timings or {}
        }

        # Write to file
        try:
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2, default=str)

            if self.logger:
                self.logger.info(f"DevLogger - Query analysis logged to {log_file}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"DevLogger - Error logging query analysis: {str(e)}")

    def log_code_generation(self, query: str, query_analysis: Any, schema: Any,
                            db_type: str, code_type: str, result: Any,
                            timings: Dict[str, float] = None):
        """
        Log code generation results.
        
        Args:
            query: The user query
            query_analysis: The query analysis result
            schema: The schema provided to the agent
            db_type: The database type
            code_type: The code type
            result: The code generation result
            timings: Optional timing information
        """
        if not self.enabled:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"{self.log_dir}/code_generation_{timestamp}.json"

        # Prepare log data
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "agent": "CodeGenerator",
            "input": {
                "query": query,
                "query_analysis": self._format_for_json(query_analysis),
                "schema": self._format_for_json(schema),
                "db_type": db_type,
                "code_type": code_type
            },
            "output": self._format_for_json(result),
            "timings": timings or {}
        }

        # Write to file
        try:
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2, default=str)

            if self.logger:
                self.logger.info(f"DevLogger - Code generation logged to {log_file}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"DevLogger - Error logging code generation: {str(e)}")

    def log_insight_generation(self, query: str, query_analysis: Any, code_result: Any,
                               data: Union[pd.DataFrame, Dict, List], result: Any,
                               timings: Dict[str, float] = None):
        """
        Log insight generation results.
        
        Args:
            query: The user query
            query_analysis: The query analysis result
            code_result: The code generation result
            data: The data used for insight generation
            result: The insight generation result
            timings: Optional timing information
        """
        if not self.enabled:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"{self.log_dir}/insight_generation_{timestamp}.json"

        # Prepare log data
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "agent": "InsightGenerator",
            "input": {
                "query": query,
                "query_analysis": self._format_for_json(query_analysis),
                "code_result": self._format_for_json(code_result),
                "data_shape": self._get_data_shape(data)
            },
            "output": self._format_for_json(result),
            "timings": timings or {}
        }

        # Write to file
        try:
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2, default=str)

            if self.logger:
                self.logger.info(f"DevLogger - Insight generation logged to {log_file}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"DevLogger - Error logging insight generation: {str(e)}")

    def log_execution(self, code_result: Any, database_uid: str, table_uid: str,
                      result: Any, error: Optional[str] = None,
                      timings: Dict[str, float] = None):
        """
        Log code execution results.
        
        Args:
            code_result: The code generation result
            database_uid: The database UID
            table_uid: The table UID
            result: The execution result
            error: Optional error message
            timings: Optional timing information
        """
        if not self.enabled:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"{self.log_dir}/execution_{timestamp}.json"

        # Prepare log data
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "process": "Execution",
            "input": {
                "code_result": self._format_for_json(code_result),
                "database_uid": database_uid,
                "table_uid": table_uid
            },
            "output": {
                "result_shape": self._get_data_shape(result),
                "error": error
            },
            "timings": timings or {}
        }

        # Write to file
        try:
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2, default=str)

            if self.logger:
                self.logger.info(f"DevLogger - Execution logged to {log_file}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"DevLogger - Error logging execution: {str(e)}")

    def _format_for_json(self, obj: Any) -> Any:
        """Format an object for JSON serialization"""
        if obj is None:
            return None

        if hasattr(obj, "dict") and callable(obj.dict):
            return obj.dict()

        if hasattr(obj, "model_dump") and callable(obj.model_dump):
            return obj.model_dump()

        if hasattr(obj, "__dict__"):
            return obj.__dict__

        if isinstance(obj, pd.DataFrame):
            return {"shape": obj.shape, "columns": list(obj.columns), "preview": obj.head(5).to_dict()}

        return str(obj)

    def _get_data_shape(self, data: Any) -> Dict[str, Any]:
        """Get shape information for data objects"""
        if data is None:
            return {"type": "None"}

        if isinstance(data, pd.DataFrame):
            return {
                "type": "DataFrame",
                "rows": len(data),
                "columns": len(data.columns),
                "column_names": list(data.columns)
            }

        if isinstance(data, dict):
            return {"type": "dict", "keys": list(data.keys())}

        if isinstance(data, list):
            return {"type": "list", "length": len(data)}

        return {"type": str(type(data))}
