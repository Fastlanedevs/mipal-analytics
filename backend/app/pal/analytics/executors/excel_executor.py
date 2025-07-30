"""
Excel Executor for Analytics PAL.
This executor runs Python/pandas code on Excel files.
"""

import pandas as pd
import io
import traceback
import requests
import re
from typing import Tuple, Dict, Any, Optional, List, Union
from pkg.log.logger import Logger
from app.analytics.utils.excelCleaner import clean_excel_sheet_to_df

class ExcelExecutor:
    """Executes Python/pandas code on Excel files"""
    
    def __init__(self, s3_client, analytics_repository=None, logger=None):
        """
        Initialize the Excel executor.
        
        Args:
            s3_client: S3 client for accessing Excel files
            analytics_repository: Optional repository for getting Excel file info
            logger: Optional logger instance
        """
        self.s3_client = s3_client
        self.repository = analytics_repository
        self.logger = logger or Logger()
        self.max_rows = 10000
        
    async def execute(self, code: str, database_uid: str, table_uid: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        Execute Python/pandas code on an Excel file.
        
        Args:
            code: Python/pandas code to execute
            database_uid: UID of the database (Excel source)
            table_uid: UID of the table (Excel sheet)
            
        Returns:
            Tuple containing:
            - DataFrame with results (or None if error)
            - Error message (or None if successful)
        """
        try:
            self.logger.info(f"FULL CODE TO EXECUTE:\n{code}")

            # Get the Excel file path
            excel_location = await self._get_excel_location(database_uid, table_uid)
            if not excel_location:
                return None, f"Failed to locate Excel file for database {database_uid}, table {table_uid}"
                
            self.logger.info(f"Excel location: {excel_location}")
                
            # Load the Excel data
            try:
                # Extract sheet name from table_uid if available
                sheet_name = None
                if self.repository and database_uid and table_uid:
                    try:
                        table_info = await self.repository.get_table_by_uid(table_uid, database_uid=database_uid)
                        if table_info and hasattr(table_info, 'name'):
                            sheet_name = table_info.name
                    except Exception as e:
                        self.logger.warning(f"Failed to extract sheet name: {str(e)}")
                
                if excel_location.startswith("s3://"):
                    # For s3:// URLs, generate a fresh presigned URL if possible
                    try:
                        # Parse bucket and key
                        bucket, key = self._parse_s3_uri(excel_location)
                        self.logger.info(f"Parsed S3 URI - bucket: {bucket}, key: {key}")
                        
                        # If we have access to the repository's s3_client, use it to generate a fresh URL
                        if hasattr(self.repository, 's3_client') and self.repository.s3_client:
                            # Generate fresh presigned URL
                            presigned_url = await self.repository.s3_client.get_fresh_presigned_url(bucket, key)
                            
                            # Use requests to download with the fresh presigned URL
                            self.logger.info(f"Attempting to download Excel with presigned URL")
                            try:
                                response = requests.get(presigned_url, timeout=30)  # Add timeout
                                self.logger.info(f"Response status: {response.status_code}")
                                
                                if response.status_code != 200:
                                    error_msg = f"Failed to download Excel with presigned URL: HTTP {response.status_code}"
                                    self.logger.error(f"{error_msg}, Response content: {response.content[:200]}")
                                    # Fall back to direct S3 access
                                    self.logger.info("Falling back to direct S3 access")
                                    excel_content = self.s3_client.get_object(bucket, key)
                                    df = await clean_excel_sheet_to_df(io.BytesIO(excel_content), sheet_name=sheet_name, nrows=self.max_rows)
                                else:
                                    df = await clean_excel_sheet_to_df(io.BytesIO(response.content), sheet_name=sheet_name, nrows=self.max_rows)
                                    self.logger.info(f"Successfully loaded Excel {df}")
                                    return df, None
                            except requests.RequestException as req_err:
                                self.logger.error(f"Request error when downloading Excel: {str(req_err)}")
                        else:
                            self.logger.info("No repository S3 client available")         
                    except Exception as e:
                        self.logger.error(f"Error processing S3 URL: {str(e)}")
                
                self.logger.info(f"Loaded Excel with {len(df)} rows and {len(df.columns)} columns")
            except Exception as e:
                self.logger.error(f"Error loading Excel file: {str(e)}")
                return None, f"Error loading Excel file: {str(e)}"
                
            # Set up namespace for code execution
            namespace = {
                'pd': pd,
                'df': df
            }
            # Ensure a result variable exists
            modified_code = self._ensure_result_variable(code)
            self.logger.info(f"MODIFIED CODE TO EXECUTE:\n{modified_code}")
            
            # Execute the code in a sandboxed environment
            try:
                # Use exec to run the code
                exec(modified_code, namespace)
                
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
            self.logger.error(f"Unexpected error in Excel executor: {str(e)}")
            return None, f"Unexpected error: {str(e)}"
            
    async def _get_excel_location(self, database_uid: str, table_uid: str) -> Optional[str]:
        """Get the location of an Excel file"""
        try:
            if self.repository:
                # NOTE: All tables are basically sheets associated with an excel file. Hence, we can extract the storage_url from any table.
                # We do this because we don't save storage_url in the database node.
                if not table_uid:
                    tables = await self.repository.get_tables(database_uid)
                    if tables and len(tables) > 0:
                        table_uid = tables[0].uid
                    
                # Use repository to get table information
                self.logger.info(f"Getting table info for table_uid={table_uid}, database_uid={database_uid}")
                
                table = None
                try:
                    table = await self.repository.get_table_by_uid_internal(table_uid)
                except Exception as e:
                    self.logger.error(f"Error getting table: {str(e)}")
                    return None
                
                if not table:
                    self.logger.error(f"Table with UID {table_uid} in database {database_uid} not found")
                    return None
                
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
            self.logger.error(f"Error getting Excel location: {str(e)}")
            traceback.print_exc()  # Print full traceback for debugging
            return None
            
    def _parse_s3_uri(self, uri: str) -> Tuple[str, str]:
        """
        Parse S3 URI into bucket and key.
        
        Primarily handles the standard s3:// format:
        - s3://bucket/path/to/file.xlsx
        
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
            
    async def preview_excel(self, database_uid: str, table_uid: str, limit: int = 10) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        Get a preview of an Excel file
        
        Args:
            database_uid: UID of the database
            table_uid: UID of the table (sheet)
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