"""
Python Executor for Analytics PAL.
This executor runs Python/pandas code for data analysis.
"""

import pandas as pd
import io
import asyncio
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple, Dict, Any, Optional, List, Union
from pkg.log.logger import Logger
import re

class PythonExecutor:
    """Executes Python code for data analysis"""
    
    def __init__(self, timeout: int = 30, logger=None):
        """
        Initialize the Python executor.
        
        Args:
            timeout: Execution timeout in seconds
            logger: Optional logger instance
        """
        self.executor = ThreadPoolExecutor()
        self.timeout = timeout
        self.logger = logger or Logger()
        
    async def execute(self, code: str, data_source: Optional[Dict[str, Any]] = None) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        Execute Python code for data analysis.
        
        Args:
            code: Python/pandas code to execute
            data_source: Optional dictionary containing data source information
                (could include dataframes, file paths, etc.)
            
        Returns:
            Tuple containing:
            - DataFrame with results (or None if error)
            - Error message (or None if successful)
        """
        try:
            self.logger.info(f"Executing Python code")
            # Enhanced logging: Log the full code being executed
            self.logger.info(f"FULL CODE TO EXECUTE:\n{code}")
            self.logger.debug(f"Code: {code}")
            
            # Modify the code to ensure a result variable exists
            # This will capture the last expression's value and assign it to result

            # Not doing for now, let's see if it works without it
            # modified_code = self._ensure_result_variable(code)
            # self.logger.info(f"MODIFIED CODE TO EXECUTE:\n{modified_code}")
            
            # Set up namespace for code execution
            namespace = {
                'pd': pd,
            }
            
            # Add any data sources to the namespace
            if data_source:
                for key, value in data_source.items():
                    namespace[key] = value
            
            # Enhanced logging: Log namespace keys before execution
            self.logger.info(f"Namespace before execution: {list(namespace.keys())}")
            
            # Execute the code in a sandboxed environment with timeout
            try:
                # Use executor to run the code asynchronously with timeout
                loop = asyncio.get_event_loop()
                await asyncio.wait_for(
                    loop.run_in_executor(
                        self.executor,
                        lambda: exec(code, namespace)
                    ),
                    timeout=self.timeout
                )
                
                # Enhanced logging: Log all variables in namespace after execution
                self.logger.info(f"Namespace after execution: {list(namespace.keys())}")
                
                # Get the result
                if 'result' not in namespace:
                    self.logger.warning("Code execution still did not produce a 'result' variable after modification")
                    # Enhanced logging: Show what variables were defined in the code
                    user_defined_vars = [k for k in namespace.keys() if k not in ['pd', '__builtins__'] + list(data_source.keys() if data_source else [])]
                    self.logger.warning(f"Variables defined in code: {user_defined_vars}")
                    
                    # Try to find a suitable variable to use as result
                    if user_defined_vars:
                        # Use the last defined variable as result
                        fallback_var = user_defined_vars[-1]
                        self.logger.info(f"Using '{fallback_var}' as fallback result variable")
                        namespace['result'] = namespace[fallback_var]
                    else:
                        return None, "Code execution did not produce a 'result' variable. Make sure your code sets a 'result' variable."
                    
                result = namespace['result']
                
                # Check if result is a DataFrame
                if not isinstance(result, pd.DataFrame):
                    self.logger.warning(f"Code execution produced a non-DataFrame result: {type(result)}")
                    
                    # Try to convert to DataFrame
                    try:
                        if isinstance(result, (list, dict)):
                            result = pd.DataFrame(result)
                        else:
                            result = pd.DataFrame([result])
                    except Exception as e:
                        self.logger.error(f"Failed to convert result to DataFrame: {str(e)}")
                        return None, f"Code execution result is not a DataFrame and cannot be converted: {type(result)}"
                
                return result, None
                
            except asyncio.TimeoutError:
                self.logger.error(f"Python code execution timed out after {self.timeout} seconds")
                return None, f"Code execution timed out after {self.timeout} seconds"
                
            except Exception as e:
                self.logger.error(f"Error executing Python code: {str(e)}")
                error_traceback = traceback.format_exc()
                return None, f"Error executing Python code: {str(e)}\n{error_traceback}"
                
        except Exception as e:
            self.logger.error(f"Unexpected error in Python executor: {str(e)}")
            return None, f"Unexpected error: {str(e)}" 

    def _ensure_result_variable(self, code: str) -> str:
        """
        Modifies the code to ensure it sets a 'result' variable.
        
        This function:
        1. Analyzes the code to see if it already sets 'result'
        2. If not, it tries to capture the last expression's value as 'result'
        
        Args:
            code: The original Python code
            
        Returns:
            Modified code that will set a 'result' variable
        """
        # Check if the code already assigns to 'result'
        if re.search(r'\bresult\s*=', code):
            self.logger.info("Code already contains 'result =' assignment")
            return code
        
        # Parse the code to find the last expression
        try:
            # Split the code into lines
            lines = code.strip().split('\n')
            
            # Build modified code
            modified_lines = []
            for i, line in enumerate(lines):
                # Strip comments and whitespace
                stripped = line.split('#')[0].strip()
                
                # Skip empty lines
                if not stripped:
                    modified_lines.append(line)
                    continue
                
                # If this is the last line and it looks like an expression (not assignment)
                if i == len(lines) - 1 and '=' not in stripped and stripped:
                    # This is the last expression, add an assignment to result
                    modified_lines.append(f"result = {stripped}")
                    self.logger.info(f"Added 'result =' to the last expression: {stripped}")
                else:
                    modified_lines.append(line)
                    
                    # Track created variables as potential result candidates
                    if '=' in stripped and not stripped.startswith('if ') and not stripped.startswith('for '):
                        var_name = stripped.split('=')[0].strip()
                        if var_name and var_name != 'result':
                            self.logger.debug(f"Found potential result variable: {var_name}")
            
            # Add a safety line at the end to ensure there's a result if no expressions were found
            modified_lines.append("\n# Ensure result variable exists")
            modified_lines.append("if 'result' not in locals():")
            modified_lines.append("    # Try to find a suitable variable to use as result")
            modified_lines.append("    for var_name in reversed(list(locals().keys())):")
            modified_lines.append("        if var_name not in ['pd', '__builtins__'] and not var_name.startswith('_'):")
            modified_lines.append("            result = locals()[var_name]")
            modified_lines.append("            break")
            
            return '\n'.join(modified_lines)
            
        except Exception as e:
            self.logger.error(f"Error modifying code: {str(e)}")
            # If there was an error, just add a safety line at the end
            return code + "\n\n# Ensure result exists\nif 'result' not in locals(): result = df if 'df' in locals() else None" 