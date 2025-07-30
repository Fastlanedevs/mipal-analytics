import json
import os
import sys
import time
import base64
import traceback
import importlib
import subprocess
from typing import Dict, Any, Optional, List, Tuple

# Set up AWS Lambda specific configurations
IS_COLD_START = True  # Track cold starts
START_TIME = time.time()  # For tracking total execution time




def execute_code(code_str: str, input_data: Dict[str, Any] = None, timeout_seconds: int = 30) -> Dict[str, Any]:
    """
    Execute Python code in a controlled environment.
    
    Args:
        code_str: The Python code to execute
        input_data: Optional dictionary of data to provide to the code
        timeout_seconds: Maximum execution time in seconds
        
    Returns:
        Dictionary containing execution results
    """
    execution_start = time.time()
    
    # Setup execution environment
    temp_dir = "/tmp/execution"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Write code to file
    code_file = f"{temp_dir}/code_to_execute.py"
    with open(code_file, 'w') as f:
        f.write(code_str)
    
    
    # Set up command with timeout
    command = [
        sys.executable,  # Current Python interpreter
        "-c",
        f"""
import sys
import json
import io
from contextlib import redirect_stdout, redirect_stderr

# Setup for execution
input_data = {json.dumps(input_data) if input_data else "None"}
output_files = {{}}

# Capture outputs
stdout_capture = io.StringIO()
stderr_capture = io.StringIO()

try:
    # Execute the code with redirected output
    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        # Execute the code
        with open("{code_file}", "r") as f:
            code = f.read()
            exec(code, {{"input_data": input_data, "output_files": output_files}})
    
    # Create result object
    result = {{
        "stdout": stdout_capture.getvalue(),
        "stderr": stderr_capture.getvalue(),
        "exit_code": 0,
        "output_files": output_files
    }}
    
    # Print JSON result
    print(json.dumps(result))
    
except Exception as e:
    # Handle exceptions
    import traceback
    stderr_capture.write(f"Exception: {{str(e)}}\\n")
    stderr_capture.write(traceback.format_exc())
    
    # Create error result
    result = {{
        "stdout": stdout_capture.getvalue(),
        "stderr": stderr_capture.getvalue(),
        "exit_code": 1,
        "output_files": output_files
    }}
    
    # Print JSON result
    print(json.dumps(result))
"""
    ]
    
    try:
        # Execute the command with timeout
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
            exit_code = process.returncode
        except subprocess.TimeoutExpired:
            # Kill the process if it times out
            process.kill()
            stdout, stderr = process.communicate()
            stderr = f"Execution timed out after {timeout_seconds} seconds"
            exit_code = 124  # Standard timeout exit code
        
        # Parse result from stdout
        try:
            result = json.loads(stdout)
            result["execution_time_ms"] = int((time.time() - execution_start) * 1000)
            result["memory_usage_kb"] = 0  # Lambda doesn't provide easy memory tracking
            return result
        except json.JSONDecodeError:
            # If parsing fails, return raw output
            return {
                "stdout": stdout,
                "stderr": stderr or "Failed to parse execution result",
                "exit_code": exit_code,
                "execution_time_ms": int((time.time() - execution_start) * 1000),
                "memory_usage_kb": 0,
                "output_files": {}
            }
            
    except Exception as e:
        return {
            "stdout": "",
            "stderr": f"Execution error: {str(e)}\n{traceback.format_exc()}",
            "exit_code": 1,
            "execution_time_ms": int((time.time() - execution_start) * 1000),
            "memory_usage_kb": 0,
            "output_files": {}
        }


def lambda_handler(event, context):
    """
    AWS Lambda handler function
    
    Args:
        event: Dictionary containing Lambda event data
        context: Lambda context object
        
    Returns:
        Dictionary containing execution results
    """
    global IS_COLD_START
    
    # Prepare response object with default values
    response = {
        "stdout": "",
        "stderr": "Execution failed: Invalid request",
        "exit_code": 1,
        "execution_time_ms": 0,
        "memory_usage_kb": 0,
        "output_files": {},
        "cold_start": IS_COLD_START
    }
    
    # Process valid requests only
    try:
        # Extract code and input data from event
        code = event.get("code")
        input_data = event.get("input_data", {})
        timeout_seconds = int(event.get("timeout_seconds", 30))
        
        # Validate input
        if not code:
            response["stderr"] = "Error: No code provided"
            return response
            
        # Execute the code
        result = execute_code(
            code_str=code,
            input_data=input_data,
            timeout_seconds=timeout_seconds
        )
        
        # Add cold start flag
        result["cold_start"] = IS_COLD_START
        
        # Reset cold start flag
        IS_COLD_START = False
        
        return result
        
    except Exception as e:
        response["stderr"] = f"Lambda error: {str(e)}\n{traceback.format_exc()}"
        return response