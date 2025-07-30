# AnalyticsPAL Code Execution Client

## Overview

The AnalyticsPAL (Processing, Analysis, and Learning) system uses a code execution client to safely execute Python code generated from natural language queries. This document explains how the code execution client is integrated and used within the AnalyticsPAL workflow.

## Code Execution Client Integration

The code execution client is initialized in the `AnalyticsPAL` class and is used to execute Python code in a controlled environment. Here's how it works:

### Initialization

The code execution client is passed to the `AnalyticsPAL` constructor:

```python
def __init__(
    self,
    # ... other parameters ...
    code_execution_client: CodeExecutionClient = None
):
    self.code_execution_client = code_execution_client
```

### Code Execution Flow

1. **Data Preparation**:

   - Before execution, the input data (DataFrame) is converted to a JSON-serializable format
   - Datetime columns are converted to Timestamp format
   - The DataFrame is converted to a list of records

2. **Code Execution**:

   ```python
   result_from_code_execution_client = self.code_execution_client.execute_code_sync(
       user_id=user_id,
       code=code,
       input_data=context_data,
       timeout_seconds=self.code_execution_timeout
   )
   ```

3. **Result Processing**:
   - The client returns a result object that may contain a DataFrame
   - The system handles different result types:
     - Dictionary results are converted to DataFrames
     - Direct DataFrame results are returned as-is
     - Other types trigger appropriate error handling

### Key Features

- **Timeout Control**: Code execution is limited by `code_execution_timeout` (default: 30 seconds)
- **Data Serialization**: Handles complex data types like datetime objects
- **Error Handling**: Comprehensive error handling and logging
- **Result Conversion**: Automatic conversion of results to DataFrame format

### Usage Example

```python
# Execute code with context data
result_df, error = await self._execute_code(
    user_id=user_id,
    code_result=code_result,
    query_analysis_result=query_analysis_result,
    database_uid=database_uid,
    table_uid=table_uid
)
```

## Best Practices

1. **Data Preparation**:

   - Always ensure input data is properly serialized
   - Handle datetime columns appropriately
   - Convert DataFrames to records format

2. **Error Handling**:

   - Check for execution errors
   - Handle different result types appropriately
   - Log errors for debugging

3. **Performance**:
   - Set appropriate timeout values
   - Monitor execution times
   - Handle large datasets efficiently

## Security Considerations

- Code execution is sandboxed
- User-specific execution context
- Timeout limits prevent infinite loops
- Input validation and sanitization

## Troubleshooting

Common issues and solutions:

1. **Serialization Errors**:

   - Check for non-serializable data types
   - Ensure datetime columns are properly formatted

2. **Timeout Issues**:

   - Review code complexity
   - Adjust timeout settings if needed
   - Optimize data processing

3. **Result Conversion Errors**:
   - Verify result format
   - Check DataFrame structure
   - Handle edge cases appropriately
