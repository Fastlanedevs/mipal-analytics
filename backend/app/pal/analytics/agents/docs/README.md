# Analytics PAL Executors

This directory contains executor classes for running analytical code against different data sources in MiPAL.

## Overview

The executors are responsible for safely running code against various data sources:

- `SQLExecutor`: Executes SQL queries against PostgreSQL databases
- `CSVExecutor`: Executes Python/pandas code against CSV data sources
- `PythonExecutor`: Executes general Python code with data analysis libraries

## Current Implementation

### Python and CSV Executors

Both Python and CSV executors support:

1. **Timeout Management**:
   - Configurable timeout (default: 30 seconds)
   - Prevents long-running code from blocking the system

2. **Error Handling**:
   - Comprehensive error handling with detailed tracebacks
   - All errors are caught and converted to meaningful return values

3. **Result Type Handling**:
   - Ensures results are pandas DataFrames
   - Attempts to convert non-DataFrame results when possible
   - Provides clear error messages when conversion fails

4. **CSV Source Flexibility**:
   - Supports multiple sources: S3, HTTP/HTTPS URLs, and local files
   - Handles different storage location formats

### SQL Executor

The SQL Executor:

- Executes SQL queries against PostgreSQL databases
- Handles connection management
- Converts query results to pandas DataFrames for consistency

## Integration with CodeExecutorService

The `CodeExecutorService` now fully integrates with the `PythonExecutor` for executing Python code:

1. **Dependency Injection**:
   - The Python executor is injected into the `CodeExecutorService` through the `set_python_executor` method
   - The container automatically wires the executor during application startup

2. **Execute Python Method**:
   ```python
   async def execute_python(self, code: str, data: Optional[List[Dict[str, Any]]] = None,
                            context: Optional[Dict[str, Any]] = None, timeout: int = 30) 
                            -> tuple[List[Dict[str, Any]], Optional[str]]:
   ```
   - Receives Python code and optional data/context
   - Uses the Python executor to safely run the code
   - Returns results as a list of dictionaries and an optional error message

3. **Transform Data Method**:
   ```python
   async def transform_data(self, data: List[Dict[str, Any]], transformation_code: str, 
                            timeout: int = 30) -> List[Dict[str, Any]]:
   ```
   - Takes input data and transformation code
   - Wraps the code to ensure a 'result' variable is set
   - Returns the transformed data

4. **Graceful Fallback**:
   - If the Python executor is not available, provides meaningful warnings
   - Returns sensible default values to prevent application crashes

## Security Considerations

The current implementation has some limitations:

1. **Limited Sandboxing**:
   - Current implementation uses Python's `exec()` which runs code with application privileges
   - No restricted execution environment

2. **No Code Sanitization**:
   - No filtering or validation of code before execution

3. **Lack of Resource Controls**:
   - Only timeout controls are implemented
   - No memory or CPU usage limits

## Future Improvements

The following improvements are planned for future implementation:

1. **Proper Sandboxing**:
   - Implement libraries like `RestrictedPython` to restrict operations
   - Consider using Docker containers for true sandboxing

2. **Code Sanitization**:
   - Implement code analysis to detect and block dangerous operations
   - Filter out risky module imports and system operations
   - Complete the `_sanitize_code` method in `CodeExecutorService`

3. **Resource Limitations**:
   - Add memory and CPU usage limits
   - Restrict file system and network access

4. **Safer Execution Models**:
   - Replace `exec()` with more controlled evaluation methods
   - Consider a restricted subset of Python or a DSL

## Usage Guidelines

When using these executors:

1. Always pass a timeout value appropriate to the expected execution time
2. Validate and sanitize code before passing it to executors when possible
3. Be aware that executed code runs with the privileges of the application
4. Check the returned error messages before using results

## Example Usage

### Using the CSV Executor

```python
# Using the CSV Executor
csv_executor = CSVExecutor(s3_client, analytics_repository, logger)
code = "result = df.groupby('category').sum().reset_index()"
result_df, error = await csv_executor.execute(code, database_uid, table_uid)

if error:
    logger.error(f"Error executing code: {error}")
else:
    # Process the result DataFrame
    print(f"Result shape: {result_df.shape}") 
```

### Using the CodeExecutorService with PythonExecutor

```python
# Using the CodeExecutorService with PythonExecutor
python_executor = PythonExecutor(timeout=30, logger=logger)
code_executor = CodeExecutorService(logger=logger)
code_executor.set_python_executor(python_executor)

# Execute Python code
sample_code = """
import pandas as pd
data = pd.DataFrame({
    'col1': [1, 2, 3, 4, 5],
    'col2': ['A', 'B', 'C', 'D', 'E']
})
# Set as result
result = data
"""

results, error = await code_executor.execute_python(code=sample_code)
if error:
    print(f"Error: {error}")
else:
    print(f"Results: {results}")

# Transform data
sample_data = [{"id": 1, "value": 10}, {"id": 2, "value": 20}]
transform_code = """
# Double the value
for item in data:
    item['value'] = item['value'] * 2
result = data
"""

transformed_data = await code_executor.transform_data(
    data=sample_data, 
    transformation_code=transform_code
)
print(f"Transformed data: {transformed_data}")
``` 