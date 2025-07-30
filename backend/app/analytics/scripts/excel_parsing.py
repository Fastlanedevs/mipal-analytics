#!/usr/bin/env python
"""
Script to test Excel file processing functionality in the SchemaService.
This script can:
1. Create a test Excel file with sample data
2. Process an Excel file (test-generated or user-provided) with the schema service

Update the CONFIGURATION section below to customize file paths and processing options.
"""
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime
import io
import uuid
import os
from fastapi import UploadFile
from fastapi.datastructures import UploadFile as FastAPIUploadFile

from app.analytics.service.schema_service import SchemaService
from app.analytics.repository.analytics_repository import AnalyticsRepository
from app.analytics.repository.storage.s3_client import SchemaS3Client
from app.analytics.api.dto import CreateCSVDatabaseRequestDTO
from app.analytics.repository.schema.schema import get_or_create_database
from app.analytics.entity.analytics import DatabaseType
from pkg.log.logger import Logger
from omegaconf import OmegaConf
from cmd_server.server.container import create_container

#-------------- CONFIGURATION (EDIT THESE VALUES) --------------#
# Set to True to create a test Excel file, False to skip file creation
CREATE_TEST_FILE = True

# Path where the test Excel file will be created (if CREATE_TEST_FILE is True)
TEST_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data.xlsx")

# Path to the Excel file to process (can be the test file or your own file)
# If you want to use your own file, set CREATE_TEST_FILE to False and update this path
EXCEL_FILE_TO_PROCESS = TEST_FILE_PATH

# Specific sheet to process (set to None to process all sheets)
SHEET_NAME = None  # Example: "Sales" to only process the Sales sheet
#---------------------------------------------------------------#


class MockUploadFile:
    """
    Simple mock of FastAPI's UploadFile for testing purposes
    This avoids issues with the FastAPI UploadFile constructor
    """
    def __init__(self, filename, content_type, file_obj):
        self.filename = filename
        self._content_type = content_type
        self._file = file_obj
        self.file = file_obj
        self.size = len(file_obj.getvalue())  # Add size attribute
    
    @property
    def content_type(self):
        return self._content_type
        
    async def read(self, size=-1):
        """Read method to make it compatible with FastAPI's UploadFile"""
        self._file.seek(0)
        if size == -1:
            return self._file.read()
        return self._file.read(size)
        
    async def seek(self, offset):
        """Seek method to make it compatible with FastAPI's UploadFile"""
        return self._file.seek(offset)
        
    async def close(self):
        """Close method to make it compatible with FastAPI's UploadFile"""
        pass  # BytesIO objects don't need explicit closing


def create_test_excel_file(output_path):
    """
    Create a test Excel file with multiple sheets and sample data
    
    Args:
        output_path: Path where to save the file
    
    Returns:
        str: Path to the created Excel file
    """
    print(f"Creating test Excel file at: {output_path}")
    
    # Create a pandas ExcelWriter object
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
       # Sheet 1: Sales data
        sales_data = {
            'Date': pd.date_range(start='2023-01-01', periods=50, freq='D'),
            'Product': np.random.choice(['Product A', 'Product B', 'Product C'], size=50),
            'Units': np.random.randint(10, 60, size=50),
            'Revenue': np.round(np.random.uniform(100, 600, size=50), 2),
            'IsPromotion': np.random.choice([True, False], size=50)
        }
        df_sales = pd.DataFrame(sales_data)
        df_sales.to_excel(writer, sheet_name='Sales', index=False)
        
        # Sheet 2: Customer data
        customer_data = {
            'CustomerID': list(range(1001, 1051)),
            'Name': [f'Customer {i}' for i in range(1, 51)],
            'Email': [f'customer{i}@example.com' for i in range(1, 51)],
            'JoinDate': pd.date_range(start='2022-01-01', periods=50, freq='7D'),
            'TotalPurchases': np.random.randint(1, 20, size=50),
            'LifetimeValue': np.round(np.random.uniform(100, 2000, size=50), 2)
        }
        df_customers = pd.DataFrame(customer_data)
        df_customers.to_excel(writer, sheet_name='Customers', index=False)
        
        # Sheet 3: Product inventory
        inventory_data = {
            'ProductID': list(range(101, 151)),
            'ProductName': [f'Product {chr(65 + i % 26)}{i}' for i in range(50)],
            'Category': np.random.choice(['Electronics', 'Clothing', 'Home'], size=50),
            'StockQuantity': np.random.randint(0, 301, size=50),
            'UnitPrice': np.round(np.random.uniform(10, 250, size=50), 2),
            'Discontinued': np.random.choice([True, False], size=50)
        }
        df_inventory = pd.DataFrame(inventory_data)
        df_inventory.to_excel(writer, sheet_name='Inventory', index=False)
    
    print(f"Test Excel file created successfully")
    return output_path


async def file_to_upload(file_path):
    """
    Convert a file path to a MockUploadFile object
    
    Args:
        file_path: Path to the Excel file
        
    Returns:
        MockUploadFile: A mock upload file object
    """
    with open(file_path, 'rb') as f:
        file_content = f.read()
    
    file_obj = io.BytesIO(file_content)
    filename = os.path.basename(file_path)
    
    # Create the mock upload file
    upload_file = MockUploadFile(
        filename=filename,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_obj=file_obj
    )
    
    # Debug info
    print(f"Created MockUploadFile: filename={filename}, content_type={upload_file.content_type}")
    
    return upload_file


async def test_excel_processing(file_path, sheet_name=None):
    """
    Test the Excel file processing functionality
    
    Args:
        file_path: Path to the Excel file to process
        sheet_name: Optional specific sheet to process. If None, processes all sheets.
    """
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"ERROR: Excel file not found: {file_path}")
        return
    
    # Initialize logger
    try:
        logger = Logger()
    except Exception as e:
        print(f"Warning: Couldn't initialize logger with default parameters: {str(e)}")
        # Fallback to a basic logger
        logger = Logger("excel-parsing-test")
    
    logger.info(f"Starting Excel parsing test with file: {file_path}")
    
    # Try to initialize from container, but fall back to direct initialization if that fails
    try:
        config = OmegaConf.load("conf/config.yaml")
        container = create_container(cfg=config)
        analytics_repository = container.analytics_repository()
        s3_client = container.s3_client()
        llm_client = container.llm_client()
        print("Successfully initialized services from container")
    except Exception as e:
        print(f"Warning: Couldn't initialize services from container: {str(e)}")
        print("Falling back to direct initialization")
        analytics_repository = AnalyticsRepository(logger=logger)
        s3_client = SchemaS3Client(logger=logger)
        
    # Initialize the schema service
    schema_service = SchemaService(
        analytics_repository=analytics_repository,
        s3_client=s3_client,
        logger=logger,
        llm_client=llm_client
    )
    
    # Convert file to MockUploadFile
    logger.info(f"Preparing Excel file for processing")
    
    try:
        excel_file = await file_to_upload(file_path)
    except Exception as e:
        print(f"ERROR: Failed to prepare file for upload: {str(e)}")
        return
    
    try:
        # Create a test database
        database_name = f"excel_test_{uuid.uuid4().hex[:8]}"
        logger.info(f"Creating test database: {database_name}")
        print(f"Creating test database: {database_name}")
        
        database = await get_or_create_database(
            name=database_name,
            db_type=DatabaseType.EXCEL.value,  # Use EXCEL type for Excel files
            description="Test database for Excel processing",
            user_id="d63d687ef15d4941b72c2a1866e371a8",
            integration_id=str(uuid.uuid4())
        )
        
        # Process the Excel file
        if sheet_name:
            logger.info(f"Processing Excel file with specific sheet: {sheet_name}")
            print(f"Processing Excel file with specific sheet: {sheet_name}")
            await schema_service._process_excel_file(database, excel_file, sheet_name=sheet_name)
        else:
            logger.info("Processing Excel file with all sheets")
            print("Processing Excel file with all sheets")
            await schema_service._process_excel_file(database, excel_file)
        
        # Check the tables created
        tables = [t.name for t in database.tables.all()]
        logger.info(f"Tables created: {tables}")
        print(f"Tables created: {tables}")
        
        # Log column details for each table
        for table in database.tables.all():
            logger.info(f"Columns in table {table.name}:")
            print(f"\nColumns in table {table.name}:")
            for column in table.columns.all():
                info = f"  - {column.name} ({column.data_type}) - Nullable: {column.is_nullable}"
                logger.info(info)
                print(info)
        
        logger.info("Excel processing test completed successfully")
        print("\nExcel processing test completed successfully")
        
    except Exception as e:
        logger.error(f"Error during Excel processing test: {str(e)}")
        print(f"ERROR: {str(e)}")
        raise
    finally:
        # Clean up (optional - in a real environment you might want to delete test database)
        logger.info("Test completed, clean up resources if needed")


async def main():
    """Main function to run the script"""
    try:
        # Create test Excel file if configured to do so
        if CREATE_TEST_FILE:
            try:
                create_test_excel_file(TEST_FILE_PATH)
            except Exception as e:
                print(f"ERROR creating test Excel file: {str(e)}")
                return
        
        # Check if the file exists
        file_to_process = EXCEL_FILE_TO_PROCESS
        if not os.path.exists(file_to_process):
            print(f"WARNING: File not found: {file_to_process}")
            if CREATE_TEST_FILE:
                print("Creating test file first since it doesn't exist")
                create_test_excel_file(TEST_FILE_PATH)
                file_to_process = TEST_FILE_PATH
            else:
                print("ERROR: Excel file not found and file creation is disabled")
                return
                
        # Process the Excel file
        print(f"Processing Excel file: {file_to_process}")
        if SHEET_NAME:
            print(f"Processing specific sheet: {SHEET_NAME}")
        else:
            print("Processing all sheets")
            
        await test_excel_processing(file_to_process, SHEET_NAME)
    except Exception as e:
        print(f"ERROR in main execution: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the main function
    print("Starting Excel parsing test script")
    asyncio.run(main())
    print("Script completed")

