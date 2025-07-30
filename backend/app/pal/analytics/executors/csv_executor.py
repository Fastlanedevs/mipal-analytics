"""
CSV Executor for Analytics PAL.
This executor runs Python/pandas code on CSV files.
"""

import pandas as pd
import io
import traceback
import requests
import re
from typing import Tuple, Dict, Any, Optional, List, Union
from pkg.log.logger import Logger

class CSVExecutor:
    """Executes Python/pandas code on CSV files"""
    
    def __init__(self, s3_client, analytics_repository=None, logger=None):
        """
        Initialize the CSV executor.
        
        Args:
            s3_client: S3 client for accessing CSV files
            analytics_repository: Optional repository for getting CSV file info
            logger: Optional logger instance
        """
        self.s3_client = s3_client
        self.repository = analytics_repository
        self.logger = logger or Logger()
        
    async def execute(self, code: str, database_uid: str, table_uid: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        Execute Python/pandas code on a CSV file.
        
        Args:
            code: Python/pandas code to execute
            database_uid: UID of the database (CSV source)
            table_uid: UID of the table (CSV file)
            
        Returns:
            Tuple containing:
            - DataFrame with results (or None if error)
            - Error message (or None if successful)
        """
        try:
            self.logger.info(f"Executing Python code on CSV file, database: {database_uid}, table: {table_uid}")
            # Enhanced logging: Log the full code being executed
            self.logger.info(f"FULL CODE TO EXECUTE:\n{code}")
            self.logger.debug(f"Code: {code}")
            
            # Get the CSV file path
            csv_location = await self._get_csv_location(database_uid, table_uid)
            if not csv_location:
                return None, f"Failed to locate CSV file for database {database_uid}, table {table_uid}"
                
            self.logger.info(f"CSV location: {csv_location}")
                
            # Load the CSV data
            try:
                if csv_location.startswith("s3://"):
                    # For s3:// URLs, generate a fresh presigned URL if possible
                    try:
                        # Parse bucket and key
                        bucket, key = self._parse_s3_uri(csv_location)
                        self.logger.info(f"Parsed S3 URI - bucket: {bucket}, key: {key}")
                        
                        # If we have access to the repository's s3_client, use it to generate a fresh URL
                        if hasattr(self.repository, 's3_client') and self.repository.s3_client:  # type: ignore
                            # Generate fresh presigned URL
                            presigned_url = await self.repository.s3_client.get_fresh_presigned_url(bucket, key)  # type: ignore
                            self.logger.info(f"Successfully generated fresh presigned URL for s3://{bucket}/{key}")
                            
                            # Use requests to download with the fresh presigned URL
                            self.logger.info(f"Attempting to download CSV with presigned URL")
                            try:
                                response = requests.get(presigned_url, timeout=30)  # Add timeout
                                self.logger.info(f"Response status: {response.status_code}")
                                
                                if response.status_code != 200:
                                    error_msg = f"Failed to download CSV with presigned URL: HTTP {response.status_code}"
                                    self.logger.error(f"{error_msg}, Response content: {response.content[:200]}")
                                    # Fall back to direct S3 access
                                    self.logger.info("Falling back to direct S3 access")
                                    csv_content = self.s3_client.get_object(bucket, key)
                                    df = self._read_csv_with_encoding_fallback(io.BytesIO(csv_content))
                                else:
                                    df = self._read_csv_with_encoding_fallback(io.BytesIO(response.content))
                                    self.logger.info(f"Successfully loaded CSV with {len(df)} rows")
                            except requests.RequestException as req_err:
                                # Handle request errors
                                self.logger.error(f"Request error when downloading CSV: {str(req_err)}")
                                # Fall back to direct S3 access
                                self.logger.info("Falling back to direct S3 access due to request error")
                                csv_content = self.s3_client.get_object(bucket, key)
                                df = self._read_csv_with_encoding_fallback(io.BytesIO(csv_content))
                        else:
                            # Fallback to using S3 client directly
                            self.logger.info("No repository S3 client available, using direct S3 access")
                            csv_content = self.s3_client.get_object(bucket, key)
                            df = self._read_csv_with_encoding_fallback(io.BytesIO(csv_content))
                    except Exception as e:
                        self.logger.error(f"Error processing S3 URL: {str(e)}")
                        # Fallback to original S3 implementation
                        self.logger.info("Falling back to basic S3 implementation")
                        bucket, key = self._parse_s3_uri(csv_location)
                        csv_content = self.s3_client.get_object(bucket, key)
                        df = self._read_csv_with_encoding_fallback(io.BytesIO(csv_content))
                elif csv_location.startswith("http://") or csv_location.startswith("https://"):
                    # Load from a presigned URL or any HTTP/HTTPS URL
                    self.logger.info(f"Loading CSV from URL: {csv_location}")
                    try:
                        response = requests.get(csv_location, timeout=30)  # Add timeout
                        if response.status_code != 200:
                            error_msg = f"Failed to download CSV from URL: HTTP {response.status_code}"
                            self.logger.error(f"{error_msg}, Response content: {response.content[:200]}")
                            return None, error_msg
                        df = self._read_csv_with_encoding_fallback(io.BytesIO(response.content))
                        self.logger.info(f"Successfully loaded CSV with {len(df)} rows")
                    except requests.RequestException as req_err:
                        error_msg = f"Request error when downloading CSV: {str(req_err)}"
                        self.logger.error(error_msg)
                        return None, error_msg
                else:
                    # Load from local file
                    self.logger.info(f"Loading CSV from local file: {csv_location}")
                    df = self._read_csv_with_encoding_fallback(csv_location)
                    self.logger.info(f"Successfully loaded CSV with {len(df)} rows")
                    
                self.logger.info(f"Loaded CSV with {len(df)} rows and {len(df.columns)} columns")
            except Exception as e:
                self.logger.error(f"Error loading CSV file: {str(e)}")
                return None, f"Error loading CSV file: {str(e)}"
                
            # Set up namespace for code execution
            namespace = {
                'pd': pd,
                'df': df
            }
            
            # Log namespace before execution
            self.logger.info(f"Namespace before execution: {list(namespace.keys())}")
            
            # Modify the code to ensure a result variable exists
            modified_code = self._ensure_result_variable(code)
            self.logger.info(f"MODIFIED CODE TO EXECUTE:\n{modified_code}")
            
            # Execute the code in a sandboxed environment
            try:
                # Use exec to run the code
                exec(modified_code, namespace)
                
                # Enhanced logging: Log all variables in namespace after execution
                self.logger.info(f"Namespace after execution: {list(namespace.keys())}")
                
                # Get the result
                if 'result' not in namespace:
                    self.logger.warning("Code execution still did not produce a 'result' variable after modification")
                    # Enhanced logging: Show what variables were defined in the code
                    user_defined_vars = [k for k in namespace.keys() if k not in ['pd', 'df', '__builtins__']]
                    self.logger.warning(f"Variables defined in code: {user_defined_vars}")
                    
                    # Try to find a suitable variable to use as result
                    if user_defined_vars:
                        # Use the last defined variable as result
                        fallback_var = user_defined_vars[-1]
                        self.logger.info(f"Using '{fallback_var}' as fallback result variable")
                        namespace['result'] = namespace[fallback_var]
                    else:
                        # Last resort: use the original dataframe if nothing else is available
                        self.logger.info("Using original 'df' as fallback result")
                        namespace['result'] = df
                    
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
                
            except Exception as e:
                self.logger.error(f"Error executing Python code: {str(e)}")
                error_traceback = traceback.format_exc()
                return None, f"Error executing Python code: {str(e)}\n{error_traceback}"
                
        except Exception as e:
            self.logger.error(f"Unexpected error in CSV executor: {str(e)}")
            return None, f"Unexpected error: {str(e)}"
            
    async def _get_csv_location(self, database_uid: str, table_uid: str) -> Optional[str]:
        """Get the location of a CSV file"""
        try:
            # Debug info to trace if UIDs are being passed correctly
            self.logger.info(f"_get_csv_location called with database_uid={database_uid}, table_uid={table_uid}")
            
            if self.repository:
                # Skip table lookup if table_uid is empty
                if not table_uid:
                    self.logger.warning("Table UID is empty, cannot determine CSV location")
                    return None
                    
                # Use repository to get table information
                self.logger.info(f"Getting table info for table_uid={table_uid}, database_uid={database_uid}")
                
                # Try to get the raw table object - this works for both direct repository and adapter
                table = None
                try:
                    # First try get_table_by_uid_internal which might be available
                    self.logger.info("Attempting to get table using get_table_by_uid_internal")
                    table = await self.repository.get_table_by_uid_internal(table_uid)
                except AttributeError:
                    # If that fails, repository might not have this method
                    self.logger.info("get_table_by_uid_internal not available, falling back to regular get_table_by_uid")
                    # Fall back to regular get_table_by_uid which returns a TableInfo/DTO
                    table_info = await self.repository.get_table_by_uid(table_uid, database_uid=database_uid)
                    if table_info:
                        # Extract storage_url from TableInfo if it's available
                        if hasattr(table_info, 'storage_url') and table_info.storage_url:
                            self.logger.info(f"Using storage_url from TableInfo: {table_info.storage_url}")
                            return table_info.storage_url
                        # Check metadata for storage_url 
                        if hasattr(table_info, 'metadata') and table_info.metadata:
                            if 'storage_url' in table_info.metadata:
                                self.logger.info(f"Using storage_url from metadata: {table_info.metadata['storage_url']}")
                                return table_info.metadata['storage_url']
                except Exception as e:
                    self.logger.error(f"Error getting table: {str(e)}")
                    return None
                
                if not table:
                    self.logger.error(f"Table with UID {table_uid} in database {database_uid} not found")
                    return None
                
                # Debug table information
                self.logger.info(f"Table retrieved: {type(table)}")
                
                # Direct access to properties in the Neo4j Table object
                if hasattr(table, 'storage_url') and table.storage_url:
                    self.logger.info(f"Using storage_url: {table.storage_url}")
                    return table.storage_url
                    
                # Fallback to constructing S3 URL if bucket and path are available
                if hasattr(table, 'storage_bucket') and hasattr(table, 'storage_path') and table.storage_bucket and table.storage_path:
                    self.logger.info(f"Constructing S3 URL from bucket={table.storage_bucket} and path={table.storage_path}")
                    return f"s3://{table.storage_bucket}/{table.storage_path}"
                
                self.logger.error(f"No storage location found for table {table_uid}")
                return None
            else:
                self.logger.error("No repository available to look up table information")
                return None
            
        except Exception as e:
            self.logger.error(f"Error getting CSV location: {str(e)}")
            traceback.print_exc()  # Print full traceback for debugging
            return None
            
    def _parse_s3_uri(self, uri: str) -> Tuple[str, str]:
        """
        Parse S3 URI into bucket and key.
        
        Primarily handles the standard s3:// format:
        - s3://bucket/path/to/file.csv
        
        Args:
            uri: S3 URI to parse
            
        Returns:
            Tuple (bucket, key)
        """
        self.logger.info(f"Parsing S3 URI: {uri}")
        
        # Standard s3:// format
        if uri.startswith("s3://"):
            path = uri[5:]  # Remove "s3://"
            parts = path.split("/", 1)
            
            if len(parts) < 2:
                raise ValueError(f"Invalid S3 URI format: {uri}")
                
            bucket = parts[0]
            key = parts[1]
            self.logger.info(f"Parsed S3 URI: bucket={bucket}, key={key}")
            return bucket, key
        
        # Unsupported format
        else:
            raise ValueError(f"Unsupported S3 URI format: {uri}, expected s3://bucket/path format")
            
    async def preview_csv(self, database_uid: str, table_uid: str, limit: int = 10) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        Get a preview of a CSV file
        
        Args:
            database_uid: UID of the database
            table_uid: UID of the table
            limit: Maximum number of rows to return
            
        Returns:
            Tuple containing:
            - DataFrame with preview data (or None if error)
            - Error message (or None if successful)
        """
        code = f"result = df.head({limit})"
        return await self.execute(code, database_uid, table_uid) 

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
            
            # Add a safety line at the end to ensure there's a result if no expressions were found
            modified_lines.append("\n# Ensure result variable exists")
            modified_lines.append("if 'result' not in locals():")
            modified_lines.append("    # Try to find a suitable variable to use as result")
            modified_lines.append("    for var_name in reversed(list(locals().keys())):")
            modified_lines.append("        if var_name not in ['pd', 'df', '__builtins__'] and not var_name.startswith('_'):")
            modified_lines.append("            result = locals()[var_name]")
            modified_lines.append("            break")
            modified_lines.append("    else:")
            modified_lines.append("        # Default to the original dataframe if no other variables found")
            modified_lines.append("        result = df")
            
            return '\n'.join(modified_lines)
            
        except Exception as e:
            self.logger.error(f"Error modifying code: {str(e)}")
            # If there was an error, just add a safety line at the end
            return code + "\n\n# Ensure result exists\nif 'result' not in locals(): result = df"

    def _read_csv_with_encoding_fallback(self, file_obj_or_path):
        """
        Read CSV file with encoding fallback to handle different character encodings.
        
        Args:
            file_obj_or_path: BytesIO object or file path containing the CSV data
            
        Returns:
            pandas.DataFrame: The loaded CSV data
            
        Raises:
            Exception: If all encoding attempts fail
        """
        # List of encodings to try, in order of preference
        encodings = ['utf-8', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                # Reset file pointer to beginning
                if hasattr(file_obj_or_path, 'seek'):
                    file_obj_or_path.seek(0)
                
                # Try to read with current encoding
                df = pd.read_csv(file_obj_or_path, encoding=encoding)
                self.logger.info(f"Successfully read CSV with encoding: {encoding}")
                return df
                
            except UnicodeDecodeError as e:
                self.logger.warning(f"Failed to read CSV with encoding {encoding}: {str(e)}")
                continue
            except Exception as e:
                # For other errors (like parsing errors), try the next encoding
                self.logger.warning(f"Error reading CSV with encoding {encoding}: {str(e)}")
                continue
        
        # If all encodings fail, try with error handling
        try:
            # Reset file pointer to beginning
            if hasattr(file_obj_or_path, 'seek'):
                file_obj_or_path.seek(0)
                
            df = pd.read_csv(file_obj_or_path, encoding='utf-8', encoding_errors='replace')
            self.logger.warning("Read CSV with UTF-8 encoding using error replacement")
            return df
        except Exception as e:
            self.logger.error(f"All encoding attempts failed for CSV file: {str(e)}")
            raise Exception(f"Could not read CSV file with any encoding: {str(e)}") 