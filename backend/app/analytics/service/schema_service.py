from typing import Dict, List, Any, Optional
from fastapi import UploadFile
import pandas as pd
import io
import os
import numpy as np
import warnings
from datetime import datetime
from pandas import Timestamp
import uuid
import requests
from app.analytics.utils.excelCleaner import clean_excel_sheet_to_df

from app.analytics.repository.schema.models.database import Database

# Suppress the pandas datetime warning
warnings.filterwarnings('ignore', category=UserWarning, module='pandas.core.tools.datetimes')

from app.analytics.api.dto import (
    SchemaResponseDTO,
    CreateCSVDatabaseRequestDTO,
    CSVDatabaseDTO
)
from app.analytics.repository.schema.schema import get_or_create_database, Table
from app.analytics.repository.storage.s3_client import SchemaS3Client
from app.analytics.repository.analytics_repository import AnalyticsRepository
from app.analytics.errors import (
    StorageError,
    SchemaValidationError,
    DatabaseNotFoundError,
    InvalidFileFormatError
)
from pkg.log.logger import Logger
from app.analytics.entity.analytics import DatabaseType
from pkg.llm_provider.llm_client import LLMClient
class SchemaService:
    def __init__(
        self,
        analytics_repository: AnalyticsRepository,
        s3_client: SchemaS3Client,
        logger: Logger,
        llm_client: LLMClient
    ):
        self.repository = analytics_repository
        self.s3_client = s3_client
        self.logger = logger
        self.llm_client = llm_client

    async def create_database(
        self,
        request: CreateCSVDatabaseRequestDTO,
        csv_files: List[UploadFile]
    ) -> Database:
        """Create a new CSV database from uploaded files"""
        try:
            # Create database in our system
            if not request.user_id:
                raise ValueError("user_id is required")
                
            database = await get_or_create_database(
                name=request.database_name,
                db_type=DatabaseType.CSV.value,
                description=request.description or "CSV database",
                user_id=request.user_id,
                integration_id=str(uuid.uuid4()) # CSV does not have a corresponding integration so we create a new one
            )

            # Process each CSV file
            for file in csv_files:
                await self._process_csv_file(database, file)

            # Save changes
            await self.repository.save_database(database)
            return database

        except Exception as e:
            self.logger.error(f"Error creating CSV database: {str(e)}")
            raise

    async def create_excel_database(
        self,
        request,
        excel_file: UploadFile,
        sheet_name: Optional[str] = None  # Optional parameter to process specific sheet
    ):
        """Create a new Excel database and process the file"""
        try:
            # Validate file is Excel format
            valid_excel_mime_types = [
                "application/vnd.ms-excel",  # .xls
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
                "application/vnd.ms-excel.sheet.macroEnabled.12"  # .xlsm
            ]
            
            # Check content type
            if excel_file.content_type not in valid_excel_mime_types:
                # Also check filename extension as fallback
                filename = excel_file.filename.lower() if excel_file.filename else ""
                if not (filename.endswith('.xlsx') or filename.endswith('.xls') or filename.endswith('.xlsm')):
                    raise InvalidFileFormatError("Invalid file format. Only Excel files are accepted.")
                    
            # Create database in our system
            database = await get_or_create_database(
                name=request.database_name,
                db_type=DatabaseType.EXCEL.value,
                description=request.description or "Excel database",
                user_id=request.user_id,
                integration_id=str(uuid.uuid4())  # Excel does not have a corresponding integration so we create a new one
            )

            # Process the Excel file
            await self._process_excel_file(database, excel_file, sheet_name)

            # Save changes
            await self.repository.save_database(database)
            return database

        except Exception as e:
            self.logger.error(f"Error creating Excel database: {str(e)}")
            raise

    async def add_files(
        self,
        database: Any,
        csv_files: List[UploadFile]
    ) -> CSVDatabaseDTO:
        """Add more CSV files to an existing database"""
        try:
            # Process each new CSV file
            for file in csv_files:
                await self._process_csv_file(database, file)

            # Save changes
            await self.repository.save_database(database)
            return database

        except Exception as e:
            self.logger.error(f"Error adding CSV files: {str(e)}")
            raise

    async def _process_csv_file(self, database: Any, file: UploadFile) -> None:
        """Process a single CSV file"""
        try:
            # Read file content
            contents = await file.read()
            file_obj = io.BytesIO(contents)
            
            # Read CSV schema with better type inference and encoding handling
            df = self._read_csv_with_encoding_fallback(file_obj)
            row_count = len(df)
            
            # Add table (use filename without extension as table name)
            if not file.filename:
                raise ValueError("File must have a filename")
            table_name = os.path.splitext(file.filename)[0]
            
            # Get table embedding for semantic search
            embedding = await self.llm_client.get_embedding(table_name)
            
            try:
                # Try to find existing table in this database first
                table = next((t for t in database.tables.all() if t.name == table_name), None)
                if table:
                    # Update existing table
                    table.embedding = embedding
                    table.row_count = row_count
                    table.save()
                else:
                    # Try to find table globally
                    try:
                        table = Table.nodes.get(name=table_name)
                        # Connect to this database if not already connected
                        if not any(t.name == table_name for t in database.tables.all()):
                            database.tables.connect(table)
                        # Update properties
                        table.embedding = embedding
                        table.row_count = row_count
                        table.save()
                    except Table.DoesNotExist:  # type: ignore
                        # Create new table if it doesn't exist globally
                        table = database.get_or_create_table(
                            name=table_name,
                            schema='public',  # Use public schema for CSV files
                            embedding=embedding,
                            row_count=row_count
                        )
            except Exception as e:
                self.logger.error(f"Error handling table {table_name}: {str(e)}")
                raise SchemaValidationError(f"Error handling table {table_name}: {str(e)}")
            
            # Upload to S3
            try:
                # Reset file pointer for S3 upload
                file_obj.seek(0)
                
                # Generate S3 path
                object_path = f"csv/{database.name}/{file.filename}"
                
                # Upload to S3
                upload_result = await self.s3_client.upload_file(
                    file_obj=file_obj,
                    object_path=object_path,
                    content_type="text/csv"
                )
                
                # Update table with storage information - MODIFIED HERE
                # Don't store the presigned URL directly, only store the bucket and path
                table.update_storage_info(
                    bucket=upload_result["bucket"],
                    path=upload_result["object_path"],
                    url=None  # Set URL to None to prevent storing the temporary presigned URL
                )
                
                self.logger.info(f"File uploaded to S3: {object_path}")
                
            except Exception as e:
                self.logger.error(f"Failed to upload to S3: {str(e)}")
                raise StorageError(str(e))
            
            # Process columns with enhanced type inference
            for column_name in df.columns:
                # Get column data
                col_data = df[column_name]
                
                # Calculate basic statistics
                stats = {
                    "null_count": int(col_data.isnull().sum()),
                    "unique_count": int(col_data.nunique()),
                    "is_nullable": bool(col_data.isnull().any())
                }
                
                # Infer data type with better accuracy
                if col_data.dtype == 'object':
                    # TEMPORARILY DISABLE DATE DETECTION - treat all string columns as text
                    data_type = 'text'
                    try:
                        # Add text-specific stats
                        stats.update({
                            "max_length": int(col_data.str.len().max() or 0),
                            "avg_length": float(col_data.str.len().mean() or 0)
                        })
                    except (AttributeError, TypeError):
                        # Fallback for weird string data
                        stats.update({
                            "max_length": 0,
                            "avg_length": 0
                        })
                elif np.issubdtype(col_data.dtype, np.number):
                    # Numeric type inference
                    if pd.api.types.is_integer_dtype(col_data):
                        data_type = 'integer'
                    else:
                        # For float types, check if all values are effectively integers
                        if col_data.dropna().apply(lambda x: float(x).is_integer()).all():
                            data_type = 'integer'
                        else:
                            data_type = 'numeric'
                    # Add numeric stats
                    non_null = col_data.dropna()
                    if len(non_null) > 0:
                        stats.update({
                            "min": float(non_null.min()),
                            "max": float(non_null.max()),
                            "mean": float(non_null.mean()),
                            "median": float(non_null.median())
                        })
                elif col_data.dtype == 'bool':
                    data_type = 'boolean'
                    stats.update({
                        "true_count": int(col_data.sum()),
                        "false_count": int(len(col_data) - col_data.sum())
                    })
                else:
                    data_type = 'text'
                
                # Create or update column
                table.get_or_create_column(
                    name=column_name,
                    data_type=data_type,
                    is_nullable=stats["is_nullable"],
                    stats=stats
                )

        except Exception as e:
            self.logger.error(f"Error processing CSV file {file.filename}: {str(e)}")
            if isinstance(e, StorageError):
                raise
            raise SchemaValidationError(str(e))

    def _read_csv_with_encoding_fallback(self, file_obj):
        """
        Read CSV file with encoding fallback to handle different character encodings.
        
        Args:
            file_obj: BytesIO object containing the CSV data
            
        Returns:
            pandas.DataFrame: The loaded CSV data
            
        Raises:
            SchemaValidationError: If all encoding attempts fail
        """
        # List of encodings to try, in order of preference
        encodings = ['utf-8', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                # Reset file pointer to beginning
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
                
                # Try to read with current encoding
                df = pd.read_csv(file_obj, encoding=encoding)
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
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
                
            df = pd.read_csv(file_obj, encoding='utf-8', encoding_errors='replace')
            self.logger.warning("Read CSV with UTF-8 encoding using error replacement")
            return df
        except Exception as e:
            self.logger.error(f"All encoding attempts failed for CSV file: {str(e)}")
            raise SchemaValidationError(f"Could not read CSV file with any encoding: {str(e)}")

    async def _process_excel_file(self, database: Any, file: UploadFile, sheet_name: Optional[str] = None) -> None:
        """Process a single Excel file and create tables for sheets
        
        Args:
            database: The database to add the table to
            file: The uploaded Excel file
            sheet_name: Optional specific sheet to process. If None, processes all sheets.
        """
        try:
            # Read file content
            contents = await file.read()
            file_obj = io.BytesIO(contents)

            # Get the Excel file to examine sheets
            try:
                excel_file = pd.ExcelFile(file_obj)
            except Exception as e:
                self.logger.error(f"Failed to read Excel file: {str(e)}")
                raise InvalidFileFormatError(f"File could not be parsed as Excel: {str(e)}")
            
            # Upload to S3 (only need to do this once for the file)
            try:
                # Generate S3 path
                object_path = f"excel/{database.name}/{file.filename}"
                
                # Create a new BytesIO object for S3 upload
                upload_obj = io.BytesIO(contents)
                
                # Upload to S3
                upload_result = await self.s3_client.upload_file(
                    file_obj=upload_obj,
                    object_path=object_path,
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                s3_bucket = upload_result["bucket"]
                s3_path = upload_result["object_path"]
                
                self.logger.info(f"Excel file uploaded to S3: {object_path}")
                
            except Exception as e:
                self.logger.error(f"Failed to upload Excel file to S3: {str(e)}")
                raise StorageError(str(e))
            

            # Process specific sheet or all sheets
            sheets_to_process = [sheet_name] if sheet_name else excel_file.sheet_names
            
            # Process each sheet
            for current_sheet in sheets_to_process:
                try:
                    self.logger.info(f"Processing sheet: {current_sheet}")
                    
                    # Create a fresh BytesIO object for each sheet from the original contents
                    sheet_file_obj = io.BytesIO(contents)
                    
                    # Read the sheet into a dataframe
                    df = await clean_excel_sheet_to_df(sheet_file_obj, sheet_name=current_sheet)
                    self.logger.info(f"Cleaned df: {df}")
                    row_count = len(df)
                    
                    # Create table name based on the sheet name
                    table_name = current_sheet
                    
                    # Get table embedding for semantic search
                    embedding = await self.llm_client.get_embedding(table_name)
                    
                    # Create a new table
                    table = database.get_or_create_table(
                        name=table_name,
                        schema='public',  # Use public schema for Excel files
                        embedding=embedding,
                        row_count=row_count
                    )
                    
                    # Update table with storage information
                    table.update_storage_info(
                        bucket=s3_bucket,
                        path=s3_path,
                        url=None  # Set URL to None to prevent storing the temporary presigned URL
                    )
                    
                    # Process columns for this sheet
                    for column_name in df.columns:
                        # Get column data
                        col_data = df[column_name]
                        
                        # Simple data type inference
                        if pd.api.types.is_numeric_dtype(col_data):
                            if pd.api.types.is_integer_dtype(col_data):
                                data_type = 'integer'
                            else:
                                data_type = 'numeric'
                        elif pd.api.types.is_bool_dtype(col_data):
                            data_type = 'boolean'
                        elif pd.api.types.is_datetime64_dtype(col_data):
                            data_type = 'timestamp'
                        else:
                            data_type = 'text'
                        
                        # Check if column has any null values
                        is_nullable = col_data.isnull().any()
                        
                        # Create column without detailed stats
                        table.get_or_create_column(
                            name=column_name,
                            data_type=data_type,
                            is_nullable=is_nullable,
                            stats={}  # Empty stats for now
                        )
                    
                    self.logger.info(f"Successfully processed sheet '{current_sheet}' and created table '{table_name}'")
                    
                except Exception as sheet_error:
                    self.logger.error(f"Error processing sheet '{current_sheet}': {str(sheet_error)}")
                    # Continue with other sheets even if one fails

        except Exception as e:
            self.logger.error(f"Error processing Excel file {file.filename}: {str(e)}")
            if isinstance(e, StorageError):
                raise
            raise SchemaValidationError(str(e))

    async def get_preview(
        self,
        database_name: str,
        table_name: str,
        user_id: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get a preview of CSV data"""
        try:
            # Get database
            database = await self.repository.get_database(database_name, user_id)
            if not database or database.type != DatabaseType.CSV.value:
                raise DatabaseNotFoundError(database_name)

            # Get table
            table = database.get_table_by_name(table_name)
            if not table:
                raise ValueError(f"Table {table_name} not found")
                
            self.logger.info(f"Getting preview for table: {table_name}, storage info - bucket: {table.storage_bucket}, path: {table.storage_path}, url: {table.storage_url}")
                
            # Check if we have a storage URL in S3:// format or a presigned URL
            csv_location = None
            
            # Try multiple approaches to access the CSV data
            try:
                # Approach 1: Generate fresh presigned URL from bucket and path
                if hasattr(table, 'storage_bucket') and hasattr(table, 'storage_path') and table.storage_bucket and table.storage_path:
                    try:
                        self.logger.info(f"Generating fresh presigned URL from bucket and path")
                        presigned_url = await self.s3_client.get_fresh_presigned_url(table.storage_bucket, table.storage_path)
                        self.logger.info(f"Generated fresh presigned URL successfully")
                        
                        # Try to download with this URL
                        response = requests.get(presigned_url, timeout=30)
                        if response.status_code == 200:
                            self.logger.info(f"Successfully downloaded CSV with fresh presigned URL")
                            df = self._read_csv_with_encoding_fallback(io.BytesIO(response.content))
                            # Limit rows after reading
                            df = df.head(limit)
                            return {
                                "columns": list(df.columns),
                                "data": df.to_dict(orient='records'),
                                "total_rows": table.row_count,
                                "preview_rows": len(df)
                            }
                        else:
                            self.logger.warning(f"Failed to download with fresh presigned URL: HTTP {response.status_code}")
                            # Continue to other approaches
                    except Exception as e:
                        self.logger.warning(f"Error using fresh presigned URL approach: {str(e)}")
                        # Continue to other approaches
                
                # Approach 2: Parse S3 URI from storage_url
                if hasattr(table, 'storage_url') and table.storage_url and table.storage_url.startswith('s3://'):
                    try:
                        self.logger.info(f"Parsing S3 URI from storage_url: {table.storage_url}")
                        s3_uri = table.storage_url
                        s3_parts = s3_uri[5:].split('/', 1)  # Remove 's3://' and split on first '/'
                        if len(s3_parts) == 2:
                            bucket, object_path = s3_parts
                            self.logger.info(f"Parsed bucket: {bucket}, object_path: {object_path}")
                            
                            # Get object directly from S3
                            try:
                                self.logger.info(f"Attempting to get object directly from S3")
                                file_obj = await self.s3_client.get_file(s3_uri)
                                df = self._read_csv_with_encoding_fallback(file_obj)
                                # Limit rows after reading
                                df = df.head(limit)
                                self.logger.info(f"Successfully loaded CSV directly from S3")
                                return {
                                    "columns": list(df.columns),
                                    "data": df.to_dict(orient='records'),
                                    "total_rows": table.row_count,
                                    "preview_rows": len(df)
                                }
                            except Exception as direct_err:
                                self.logger.warning(f"Error getting object directly from S3: {str(direct_err)}")
                                # Try with presigned URL as fallback
                                try:
                                    presigned_url = await self.s3_client.get_fresh_presigned_url(bucket, object_path)
                                    response = requests.get(presigned_url, timeout=30)
                                    if response.status_code == 200:
                                        df = self._read_csv_with_encoding_fallback(io.BytesIO(response.content))
                                        # Limit rows after reading
                                        df = df.head(limit)
                                        self.logger.info(f"Successfully loaded CSV with presigned URL from S3 URI")
                                        return {
                                            "columns": list(df.columns),
                                            "data": df.to_dict(orient='records'),
                                            "total_rows": table.row_count,
                                            "preview_rows": len(df)
                                        }
                                    else:
                                        self.logger.warning(f"Failed to download with presigned URL from S3 URI: HTTP {response.status_code}")
                                except Exception as url_err:
                                    self.logger.warning(f"Error using presigned URL from S3 URI: {str(url_err)}")
                    except Exception as e:
                        self.logger.warning(f"Error parsing S3 URI: {str(e)}")
                
                # Approach 3: Use the stored URL directly (might be expired)
                if hasattr(table, 'storage_url') and table.storage_url:
                    try:
                        # Use the stored URL (might be presigned and potentially expired)
                        csv_location = table.storage_url
                        self.logger.info(f"Trying stored URL directly: {csv_location}")
                        
                        if csv_location.startswith("http"):
                            response = requests.get(csv_location, timeout=30)
                            if response.status_code == 200:
                                df = self._read_csv_with_encoding_fallback(io.BytesIO(response.content))
                                # Limit rows after reading
                                df = df.head(limit)
                                self.logger.info(f"Successfully loaded CSV with stored URL")
                                return {
                                    "columns": list(df.columns),
                                    "data": df.to_dict(orient='records'),
                                    "total_rows": table.row_count,
                                    "preview_rows": len(df)
                                }
                            else:
                                self.logger.warning(f"Failed to download with stored URL: HTTP {response.status_code}")
                    except Exception as e:
                        self.logger.warning(f"Error using stored URL: {str(e)}")
                
                # If we got here, all approaches failed
                raise ValueError(f"All approaches to access CSV data failed")
                
            except Exception as access_err:
                self.logger.error(f"Error accessing CSV data: {str(access_err)}")
                raise ValueError(f"Failed to access CSV data: {str(access_err)}")

        except Exception as e:
            self.logger.error(f"Error getting CSV preview: {str(e)}")
            raise 