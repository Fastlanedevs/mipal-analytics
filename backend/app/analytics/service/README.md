# Schema Service Documentation

## Methods

### \_process_excel_file

Processes an Excel file and creates tables for each sheet in the database.

#### Parameters:

- `database` (Any): The database to add the table(s) to
- `file` (UploadFile): The uploaded Excel file
- `sheet_name` (Optional[str]): Optional specific sheet to process. If None, processes all sheets.

#### Technical Implementation:

##### Dependencies:

- `pandas`: For Excel file reading and data manipulation
- `io.BytesIO`: For handling file content in memory
- `SchemaS3Client`: Custom client for S3 storage operations
- `LLMClient`: Custom client for generating embeddings

##### File Validation:

- Validates Excel file format using pandas' `ExcelFile` class
- Supports multiple Excel formats:
  - .xlsx (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)
  - .xls (application/vnd.ms-excel)
  - .xlsm (application/vnd.ms-excel.sheet.macroEnabled.12)

##### Data Processing:

- Uses `pd.read_excel()` to read sheet data into DataFrames
- Implements custom type inference for columns:
  ```python
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
  ```

##### Storage Implementation:

- Uses S3 for file storage with custom path structure
- Implements presigned URL generation for secure access
- Stores metadata in the database including:
  - Table name
  - Schema (default: 'public')
  - Row count
  - Column information
  - Storage location (bucket and path)

#### Process Flow:

1. Reads the Excel file content and validates it
2. Uploads the Excel file to S3 storage
3. Processes each sheet (or specified sheet) in the Excel file:
   - Creates a table for each sheet
   - Generates table embedding for semantic search
   - Processes columns with type inference
   - Stores table metadata and storage information

#### Error Handling:

- Raises `InvalidFileFormatError` if the file cannot be parsed as Excel
- Raises `StorageError` if there are issues uploading to S3
- Raises `SchemaValidationError` for other processing errors
- Continues processing other sheets even if one sheet fails

#### Column Processing:

- Infers data types (integer, numeric, boolean, timestamp, text)
- Tracks nullability of columns
- Creates column metadata in the database

#### Storage:

- Stores the Excel file in S3 with path format: `excel/{database.name}/{file.filename}`
- Maintains storage information (bucket and path) for each table
- Does not store presigned URLs to prevent expiration issues
