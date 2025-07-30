"""
Pydantic models for Analytics PAL.
This module contains the Pydantic models used across the Analytics PAL.
"""

from typing import List, Dict, Any, Optional, Literal, Union
from pydantic import BaseModel, Field
from datetime import datetime

# Query Analyzer Models
class Condition(BaseModel):
    """Represents a condition in a query"""
    field: str
    operator: str
    value: str

class TimeRange(BaseModel):
    """Represents a time range in a query"""
    column: str
    start: Optional[str] = None
    end: Optional[str] = None
    period: Optional[str] = None  # e.g., "last 30 days", "this month"

class MLTask(BaseModel):
    """ML task information"""
    is_ml_task: bool = Field(False, description="Whether this is an ML task")
    task_type: Optional[str] = Field(None, description="Type of ML task (prediction, optimization, classification, anomaly_detection)")
    required_models: List[str] = Field(default_factory=list, description="List of required ML models")
    required_features: List[str] = Field(default_factory=list, description="List of required features")
    target_variable: Optional[str] = Field(None, description="Target variable for ML task")
    evaluation_metrics: List[str] = Field(default_factory=list, description="List of evaluation metrics")

class QueryAnalysisResult(BaseModel):
    """Result of query analysis"""
    intent: str = Field(..., description="The primary intent of the query")
    intent_category: str = Field("analytical", description="Category of the query (analytical, predictive, optimization, classification, command)")
    target_entities: List[str] = Field(..., description="Tables or entities being queried")
    conditions: List[Condition] = Field(default_factory=list, description="Filtering conditions")
    grouping: Optional[List[str]] = Field(None, description="Group by fields")
    metrics: List[str] = Field(default_factory=list, description="Metrics to calculate")
    time_range: Optional[TimeRange] = Field(None, description="Time range for time-series data")
    complexity: str = Field(..., description="Estimated query complexity")
    requires_join: bool = Field(False, description="Whether the query requires joining tables")
    feasible: bool = Field(True, description="Whether the query can be answered with the schema")
    reason: Optional[str] = Field(None, description="Reason why the query is not feasible")
    is_ambiguous: bool = Field(False, description="Whether the query is ambiguous or lacks critical information")
    ambiguity_score: float = Field(0.0, description="Score from 0-1 indicating how ambiguous the query is, with 1 being highly ambiguous")
    ambiguity_reason: Optional[str] = Field(None, description="Explanation of why the query is considered ambiguous")
    ml_task: MLTask = Field(default_factory=MLTask, description="ML task information if applicable")

# Code Generator Models
class GeneratedCode(BaseModel):
    """Generated code for a query"""
    code: str = Field(..., description="The actual SQL or Python code")
    code_type: Literal["sql", "python"] = Field(..., description="Type of code")
    explanation: str = Field(..., description="Natural language explanation")
    expected_columns: List[str] = Field(..., description="Expected columns in result")

class CodeGenerationResult(BaseModel):
    """Result of code generation"""
    code: str = Field(..., description="The generated code")
    code_type: str = Field("sql", description="Type of code generated (sql, python, etc.)")
    explanation: str = Field("", description="Explanation of the generated code")
    estimated_accuracy: float = Field(0.0, description="Estimated accuracy of the generated code")
    required_libraries: List[str] = Field(default_factory=list, description="Required libraries for the code")
    warnings: Optional[List[str]] = Field(None, description="Warnings about the generated code")
    expected_output_format: Optional[Dict[str, Any]] = Field(None, description="Expected format of the output")

class VisualizationSuggestion(BaseModel):
    """Visualization suggestion"""
    chart_type: str = Field(..., description="The type of chart (bar, line, etc.)")
    title: str = Field(..., description="The title of the visualization")
    description: str = Field(..., description="Description of what the visualization shows")
    x_axis: Optional[str] = Field(None, description="Column for the x-axis")
    y_axis: Optional[Union[str, List[str]]] = Field(None, description="Column(s) for the y-axis")
    color_by: Optional[str] = Field(None, description="Column to color by")
    config: Optional[Dict[str, Any]] = Field(None, description="Additional configuration")

class Insight(BaseModel):
    """Individual insight"""
    title: str = Field(..., description="Insight title")
    description: str = Field(..., description="Detailed description of the insight")
    relevance: str = Field(..., description="Why this insight matters")
    confidence: str = Field(..., description="Confidence level (high, medium, low)")

class InsightGenerationResult(BaseModel):
    """Result of insight generation"""
    summary: str = Field(..., description="Summary of the insights")
    insights: List[Insight] = Field(..., description="List of individual insights")

# Enhanced Schema Models
class ForeignKeyRelationship(BaseModel):
    """Foreign key relationship information"""
    table: str = Field(..., description="The referenced table name")
    column: str = Field(..., description="The referenced column name")

class SharedColumnRelationship(BaseModel):
    """Shared column relationship information"""
    table: str = Field(..., description="The related table name")
    column: str = Field(..., description="The related column name")
    source_column: str = Field(..., description="The source column name")

class ColumnStatistics(BaseModel):
    """Statistics for a column"""
    min_value: Optional[Union[float, str]] = Field(None, description="Minimum value in the column")
    max_value: Optional[Union[float, str]] = Field(None, description="Maximum value in the column")
    avg_value: Optional[float] = Field(None, description="Average value in the column")
    median_value: Optional[float] = Field(None, description="Median value in the column")
    null_count: Optional[int] = Field(None, description="Number of null values in the column")
    distinct_count: Optional[int] = Field(None, description="Number of distinct values in the column")
    common_values: Optional[List[Any]] = Field(None, description="List of common values in the column")

class ColumnInfo(BaseModel):
    """Column information"""
    name: str = Field(..., description="The column name")
    data_type: str = Field(..., description="The column data type")
    is_nullable: bool = Field(True, description="Whether the column is nullable")
    is_primary_key: bool = Field(False, description="Whether the column is a primary key")
    is_foreign_key: bool = Field(False, description="Whether the column is a foreign key")
    references_table: Optional[str] = Field(None, description="The table this foreign key references")
    references_column: Optional[str] = Field(None, description="The column this foreign key references")
    unique: bool = Field(False, description="Whether the column has a unique constraint")
    statistics: Optional[ColumnStatistics] = Field(None, description="Statistical information about the column")
    semantic_type: Optional[str] = Field(None, description="Semantic type of the column (e.g., date, money, name)")
    
    # For backward compatibility
    @property
    def nullable(self) -> bool:
        return self.is_nullable
    
    @property
    def primary_key(self) -> bool:
        return self.is_primary_key
    
    @property
    def foreign_key(self) -> Optional[ForeignKeyRelationship]:
        if self.is_foreign_key and self.references_table and self.references_column:
            return ForeignKeyRelationship(table=self.references_table, column=self.references_column)
        return None

class TableRelationship(BaseModel):
    """Relationship between tables"""
    type: str = Field(..., description="Type of relationship (FOREIGN_KEY, etc.)")
    from_table: str = Field(..., description="The source table name")
    to_table: str = Field(..., description="The target table name")
    from_column: str = Field(..., description="Column in the source table for the relationship")
    to_column: str = Field(..., description="Column in the target table for the relationship")
    
    # For backward compatibility
    @property
    def target_table(self) -> str:
        return self.to_table
    
    @property
    def relationship_type(self) -> str:
        return self.type
    
    @property
    def source_column(self) -> str:
        return self.from_column
    
    @property
    def target_column(self) -> str:
        return self.to_column

class TableInfo(BaseModel):
    """Table information"""
    uid: Optional[str] = Field(None, description="Unique ID for the table")
    name: str = Field(..., description="The table name")
    columns: List[ColumnInfo] = Field(default_factory=list, description="The table columns")
    relationships: Optional[List[TableRelationship]] = Field(None, description="Relationships with other tables")
    row_count: Optional[int] = Field(None, description="Approximate number of rows in the table")
    last_updated: Optional[str] = Field(None, description="When the table was last updated")

class SchemaInfo(BaseModel):
    """Database schema information"""
    database_type: str = Field("unknown", description="The type of database (postgres, csv, etc.)")
    database_name: Optional[str] = Field(None, description="The name of the database")
    tables: List[TableInfo] = Field(default_factory=list, description="The database tables")
    relationships: Optional[List[TableRelationship]] = Field(None, description="Relationships between tables")
    
    def get_table(self, table_name: str) -> Optional[TableInfo]:
        """Get a table by name"""
        for table in self.tables:
            if table.name == table_name:
                return table
        return None
    
    def get_column(self, table_name: str, column_name: str) -> Optional[ColumnInfo]:
        """Get a column by table and column name"""
        table = self.get_table(table_name)
        if table:
            for column in table.columns:
                if column.name == column_name:
                    return column
        return None
    
    def find_relationships(self, table_name: str) -> List[TableRelationship]:
        """Find all relationships for a table"""
        if not self.relationships:
            return []
        
        return [rel for rel in self.relationships if rel.from_table == table_name or rel.to_table == table_name]
    
    def find_join_path(self, source_table: str, target_table: str) -> Optional[List[Dict[str, Any]]]:
        """Find a path to join two tables"""
        if source_table == target_table:
            return []
            
        if not self.relationships:
            return None
            
        # Look for direct relationship
        for rel in self.relationships:
            if (rel.from_table == source_table and rel.to_table == target_table) or \
               (rel.from_table == target_table and rel.to_table == source_table):
                return [{
                    "source_table": rel.from_table,
                    "target_table": rel.to_table,
                    "source_column": rel.from_column,
                    "target_column": rel.to_column,
                    "relationship_type": rel.type
                }]
                
        # TODO: Implement more complex join path finding with intermediary tables
        return None

class TableData(BaseModel):
    """Table data with columns and rows"""
    columns: List[str] = Field(..., description="The column names")
    rows: List[Dict[str, Any]] = Field(..., description="The data rows")

class DatabaseInfo(BaseModel):
    """Enhanced database connection information"""
    uid: str
    name: str
    type: Literal["postgres", "csv"]
    description: Optional[str] = None
    connection_info: Dict[str, Any]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user_id: Optional[str] = None
    is_active: bool = True

# Insight Generator Models
class KeyMetric(BaseModel):
    """Key metric with value and context"""
    name: str
    value: Any
    context: str

class InsightResult(BaseModel):
    """Generated insights from data analysis"""
    overview: str = Field(..., description="High-level summary")
    insights: List[str] = Field(..., description="List of specific insights")
    key_metrics: Dict[str, str] = Field(default_factory=dict, description="Key metrics with context")
    recommendations: List[str] = Field(default_factory=list, description="Recommended actions")

# Data Summary Models
class NumericStats(BaseModel):
    """Statistics for numeric columns"""
    min: float
    max: float
    mean: float
    median: float
    std: Optional[float] = None
    null_count: int
    quartiles: Optional[List[float]] = None

class CategoryStats(BaseModel):
    """Statistics for categorical columns"""
    unique_count: int
    null_count: int
    top_values: Dict[str, int]
    sample_values: List[str]

class DataSummary(BaseModel):
    """Summary of data from query results"""
    total_rows: int
    total_columns: int
    numeric_columns: Dict[str, NumericStats] = Field(default_factory=dict)
    categorical_columns: Dict[str, CategoryStats] = Field(default_factory=dict)
    date_columns: Dict[str, Dict[str, str]] = Field(default_factory=dict)

class DatabaseCredential(BaseModel):
    """Database credentials"""
    username: str
    password: str
    host: str
    port: int
    database: str
    

class DatabaseInfo(BaseModel):
    """Database information"""
    uid: str = Field(..., description="Unique ID for the database")
    name: str = Field(..., description="Name of the database")
    description: Optional[str] = Field(None, description="Description of the database")
    type: str = Field(..., description="Type of database (postgres, mysql, etc.)")
    credential: Optional[DatabaseCredential] = Field(None, description="Credentials for the database")
    tables: Optional[List[str]] = Field(None, description="List of tables in the database") 

# Convert raw JSON data to SchemaInfo model
def convert_to_schema_info(data: Dict[str, Any]) -> SchemaInfo:
    """
    Convert raw database schema data to a SchemaInfo object
    
    Args:
        data: Raw schema data from the database
        
    Returns:
        SchemaInfo object representing the database schema
    """
    # Create tables first
    tables = []
    for table_data in data.get("tables", []):
        # Process columns
        columns = []
        for column_data in table_data.get("columns", []):
            column = ColumnInfo(
                name=column_data.get("name", ""),
                data_type=column_data.get("data_type", ""),
                is_nullable=column_data.get("is_nullable", True),
                is_primary_key=column_data.get("is_primary_key", False),
                is_foreign_key=column_data.get("is_foreign_key", False),
                references_table=column_data.get("references_table"),
                references_column=column_data.get("references_column")
            )
            columns.append(column)
        
        # Create table with columns
        table = TableInfo(
            name=table_data.get("table_name", ""),
            columns=columns
        )
        tables.append(table)
    
    # Process relationships
    relationships = []
    for rel_data in data.get("relationships", []):
        relationship = TableRelationship(
            type=rel_data.get("type", "FOREIGN_KEY"),
            from_table=rel_data.get("from_table", ""),
            to_table=rel_data.get("to_table", ""),
            from_column=rel_data.get("from_column", ""),
            to_column=rel_data.get("to_column", "")
        )
        relationships.append(relationship)
    
    # Create the SchemaInfo object
    schema_info = SchemaInfo(
        database_type=data.get("database_type", "unknown"),
        database_name=data.get("database_name", ""),
        tables=tables,
        relationships=relationships
    )
    
    return schema_info 