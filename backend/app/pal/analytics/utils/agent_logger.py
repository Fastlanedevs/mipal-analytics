import json
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd
from pkg.log.logger import Logger

class AgentLogger:
    """
    Logger for agent operations in development mode.
    Logs inputs, outputs, and timing information for each agent call.
    """
    
    def __init__(self, enabled=False, log_dir="./logs/analytics", agent_name=""):
        """
        Initialize the agent logger.
        
        Args:
            enabled: Whether logging is enabled
            log_dir: Directory to store logs
            agent_name: Name of the agent for log file naming
        """
        self.enabled = enabled
        self.log_dir = log_dir
        self.agent_name = agent_name
        
        if enabled:
            os.makedirs(log_dir, exist_ok=True)
            
    def log_agent_run(self, 
                      input_data: Any, 
                      output: Any, 
                      llm_client: Any,
                      temperature: float,
                      error: Optional[str] = None,
                      duration_ms: Optional[float] = None):
        """
        Log an agent run with input, output, and timing information.
        
        Args:
            input_data: Input data provided to the agent
            output: Output from the agent
            llm_client: LLM client used for the run
            temperature: Temperature setting used
            error: Optional error message if run failed
            duration_ms: Duration of the run in milliseconds
        """
        if not self.enabled:
            return
            
        # Create timestamp for the log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Format for JSON storage
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "agent": self.agent_name,
            "input": self._format_for_json(input_data),
            "output": self._format_for_json(output),
            "settings": {
                "temperature": temperature,
                "model": getattr(llm_client, "model", "unknown")
            },
            "duration_ms": duration_ms,
            "error": error
        }
        
        # Save to JSON file
        log_path = os.path.join(
            self.log_dir, 
            f"{timestamp}_{self.agent_name}_run.json"
        )
        
        with open(log_path, "w") as f:
            json.dump(log_data, f, indent=2, default=str)

    def log_raw_data(self, title: str, data: Any):
        """Log raw data"""
        if not self.enabled:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        log_data = {
            "timestamp": datetime.now().isoformat(),
            "title": title,
            "data": data
        }
       
        log_path = os.path.join(
            self.log_dir, 
            f"{timestamp}_raw_data.json"
        )

        with open(log_path, "w") as f:
            json.dump(log_data, f, indent=2, default=str)

    def _format_for_json(self, obj: Any) -> Any:
        """Format an object for JSON serialization."""
        if hasattr(obj, "dict") and callable(obj.dict):
            return obj.dict()
        elif hasattr(obj, "model_dump") and callable(obj.model_dump):
            return obj.model_dump()
        elif isinstance(obj, pd.DataFrame):
            return {
                "type": "DataFrame",
                "shape": obj.shape,
                "columns": list(obj.columns),
                "sample": obj.head(5).to_dict(orient="records")
            }
        elif isinstance(obj, Exception):
            return str(obj)
        
        return obj 