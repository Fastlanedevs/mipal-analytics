"""
Code Generator Agent for Analytics PAL.
This agent generates executable code for data analysis based on query analysis.
"""

import json
import time
from typing import Dict, Any, List, Optional, Union

from pydantic import BaseModel, Field
from app.agents.base_agent import BaseAgent
from pkg.llm_provider.llm_client import LLMClient, LLMModel
from pkg.log.logger import Logger
from app.tokens.exceptions import TokenLimitError

from app.pal.analytics.utils.models import (
    CodeGenerationResult,
    QueryAnalysisResult,
    SchemaInfo
)
from app.pal.analytics.utils.prompts import (
    CODE_GENERATOR_SYSTEM_PROMPT,
    CODE_GENERATOR_USER_PROMPT
)
from app.pal.analytics.utils.agent_logger import AgentLogger
from app.tokens.service.service import TokensService


class CodeGeneratorInput(BaseModel):
    """Input for the Code Generator"""
    query: str = Field(..., description="The original user query")
    query_analysis: Dict[str, Any] = Field(..., description="Analysis of the query")
    schema: Optional[Union[Dict[str, Any], str]] = Field(None, description="Database schema information")
    db_type: str = Field("unknown", description="The type of database")
    code_type: str = Field("python", description="The type of code to generate (python or sql)")


class CodeGenerator:
    """Agent for generating executable code based on query analysis"""

    def __init__(self, llm_client: LLMClient, tokens_service: TokensService, llm_model: LLMModel,
                 logger: Logger, dev_mode: bool = False):
        """
        Initialize the CodeGenerator agent.
        
        Args:
            llm_client: LLM client for agent communication
            model: Model name to use
            logger: Optional logger instance
            dev_mode: Whether to enable development mode logging
        """
        self.llm_client = llm_client
        self.llm_model = llm_model
        self.logger = logger
        self.tokens_service = tokens_service

        self.logger.info(f"CodeGenerator.__init__ - Initializing with model: {self.llm_model}")

        # Initialize dev mode logger
        self.dev_logger = AgentLogger(
            enabled=dev_mode,
            agent_name="code_generator"
        )

        # Simplified system prompt for basic SQL generation
        enhanced_system_prompt = CODE_GENERATOR_SYSTEM_PROMPT + """

IMPORTANT: For PostgreSQL databases, follow these simple guidelines:

1. Use the most basic table references possible: `products`, `order_items`, etc.
2. Do NOT use schema prefixes (like public.table_name)
3. Do NOT use quotes around table or column names
4. Keep SQL simple and standards-compliant

Example of correct SQL:
```sql
SELECT 
    p.product_id, 
    p.product_name, 
    COUNT(oi.order_item_id) as total_sold
FROM 
    products AS p
JOIN 
    order_items AS oi ON p.product_id = oi.product_id
GROUP BY 
    p.product_id, p.product_name
ORDER BY 
    total_sold DESC
LIMIT 5;
```
"""

        # Create the agent with explicit output_type and enhanced prompt
        self._agent = BaseAgent(
            llm_model=self.llm_model,
            logger=self.logger,
            system_prompt=enhanced_system_prompt,
            output_type=CodeGenerationResult,
            tokens_service=self.tokens_service,
        )

    async def run(
            self,
            user_id: str,
            query: str,
            query_analysis: QueryAnalysisResult,
            schema: Optional[Union[SchemaInfo, str]] = None,
            db_type: str = "unknown",
            code_type: str = "sql",
            additional_context: Optional[str] = None,
            temperature: float = 0.1
    ) -> CodeGenerationResult:
        """
        Generate code based on query analysis and schema.
        
        Args:
            query: The user's natural language query
            query_analysis: Structured analysis of the query
            schema: Optional schema information
            db_type: Database type (postgres, mysql, etc.)
            code_type: Type of code to generate (python or sql)
            temperature: Temperature parameter for LLM
            
        Returns:
            CodeGenerationResult: The generated code with metadata
        """
        self.logger.info(f"CodeGenerator.run - Generating {code_type} code for: {query}")

        try:
            # Format schema for code generation
            formatted_schema = self._format_schema(schema)

            # Convert query_analysis to dict if needed
            query_analysis_dict = None
            if isinstance(query_analysis, QueryAnalysisResult):
                try:
                    query_analysis_dict = query_analysis.dict()
                except AttributeError:
                    try:
                        query_analysis_dict = query_analysis.model_dump()
                    except AttributeError:
                        query_analysis_dict = json.loads(query_analysis.json())
            else:
                query_analysis_dict = query_analysis

            # Track timing for development logging
            start_time = None
            if self.dev_logger.enabled:
                start_time = time.time()

            # Create a user message with JSON formatted input
            user_message = json.dumps({
                "query": query,
                "query_analysis": query_analysis_dict,
                "schema": formatted_schema,
                "db_type": db_type,
                "code_type": code_type,
                "additional_context": additional_context
            })

            # Run the agent and get structured result directly
            try:
                # Note: temperature is handled at the model level in Pydantic AI 0.0.25
                result = await self._agent.run(
                    user_id=user_id,
                    prompt=user_message,
                )

                # Extract the typed CodeGenerationResult directly from result data
                code_result = result.data

                # Log for development mode
                if self.dev_logger.enabled and start_time:
                    duration_ms = (time.time() - start_time) * 1000
                    self.dev_logger.log_agent_run(
                        input_data={
                            "query": query,
                            "query_analysis": query_analysis_dict,
                            "schema": formatted_schema,
                            "db_type": db_type,
                            "code_type": code_type
                        },
                        output=code_result,
                        llm_client=self.llm_client,
                        temperature=temperature,
                        duration_ms=duration_ms
                    )

                self.logger.info(f"CodeGenerator.run - Code generation complete. Type: {code_result.code_type}")
                return code_result
            
            except TokenLimitError as e:
                self.logger.error(f"CodeGenerator.run - Credits limit exceeded: {str(e)}")
                raise e
            except Exception as e:
                self.logger.error(f"CodeGenerator.run - Error in agent execution: {str(e)}")
                return self._fallback_result(code_type, error=str(e))

        except TokenLimitError as e:
            self.logger.error(f"CodeGenerator.run - Credits limit exceeded: {str(e)}")
            raise e
        except Exception as e:
            self.logger.error(f"CodeGenerator.run - Unexpected error: {str(e)}")
            return self._fallback_result(code_type, error=str(e))

    def _format_schema(self, schema: Optional[Union[SchemaInfo, str]]) -> Optional[Union[Dict[str, Any], str]]:
        """
        Format schema for code generation.
        
        Args:
            schema: Schema information
            
        Returns:
            Formatted schema
        """
        if schema is None:
            return None

        if isinstance(schema, str):
            return schema

        if isinstance(schema, SchemaInfo):
            # Convert to dict
            try:
                return schema.dict()
            except AttributeError:
                # Fallback to model_dump for newer Pydantic versions
                try:
                    return schema.model_dump()
                except AttributeError:
                    # Last resort: JSON serialization
                    return json.loads(schema.json())

        # Passed a dict or other JSON-serializable type
        return schema

    def _fallback_result(self, code_type: str, error: Optional[str] = None) -> CodeGenerationResult:
        """
        Create a fallback result when code generation fails.
        
        Args:
            code_type: The type of code that was requested
            error: Optional error message
            
        Returns:
            A basic CodeGenerationResult
        """
        reason = f"Error during code generation: {error}" if error else "Code could not be generated"

        self.logger.warning(f"CodeGenerator - Using fallback result: {reason}")

        return CodeGenerationResult(
            code="-- Code generation failed",
            code_type=code_type,
            explanation=reason,
            estimated_accuracy=0.0,
            warnings=[reason]
        )

    def format_schema_for_code_generation(self, schema: SchemaInfo, code_type: str) -> str:
        """
        Format a schema object specifically for code generation.
        This emphasizes SQL structure and types for better code generation.
        
        Args:
            schema: The schema information object
            code_type: The type of code to generate (sql, python)
            
        Returns:
            Formatted schema string for code generation
        """
        if not schema:
            return ""

        schema_lines = [
            f"Database: {schema.database_name} ({schema.database_type})",
            ""
        ]

        # For SQL code generation, include CREATE TABLE statements
        if code_type.lower() == "sql":
            schema_lines.append("SQL Schema:")

            for table in schema.tables:
                create_table = [f"CREATE TABLE {table.name} ("]
                column_defs = []

                for column in table.columns:
                    # Build column definition with constraints
                    col_def = f"    {column.name} {column.data_type}"

                    # Add constraints
                    constraints = []
                    if column.primary_key:
                        constraints.append("PRIMARY KEY")
                    if not column.nullable:
                        constraints.append("NOT NULL")
                    if column.unique:
                        constraints.append("UNIQUE")

                    if constraints:
                        col_def += " " + " ".join(constraints)

                    column_defs.append(col_def)

                # Add foreign key constraints
                for rel in table.relationships:
                    if hasattr(rel, 'relationship_type') and rel.relationship_type == 'foreign_key':
                        fk_constraint = f"    FOREIGN KEY ({rel.from_column}) REFERENCES {rel.to_table} ({rel.to_column})"
                        column_defs.append(fk_constraint)

                create_table.append(",\n".join(column_defs))
                create_table.append(");")

                schema_lines.append("\n".join(create_table))
                schema_lines.append("")

        # For Python, include sample pandas operations
        if code_type.lower() == "python":
            schema_lines.append("Python Schema:")

            for table in schema.tables:
                schema_lines.append(f"# Table: {table.name}")
                schema_lines.append("# DataFrame structure:")
                schema_lines.append(f"df_{table.name.lower()} = pd.DataFrame({{")

                for column in table.columns:
                    schema_lines.append(f"    '{column.name}': [<{column.data_type}>],  # {column.description}")

                schema_lines.append("})")
                schema_lines.append("")

        # Add tables and their columns in a more standard format
        schema_lines.append("Tables:")
        for table in schema.tables:
            schema_lines.append(f"Table: {table.name}")
            if table.description:
                schema_lines.append(f"Description: {table.description}")

            schema_lines.append("Columns:")
            for column in table.columns:
                column_info = [
                    f"  - {column.name} ({column.data_type})"
                ]

                # Add constraints
                constraints = []
                if column.primary_key:
                    constraints.append("PRIMARY KEY")
                if not column.nullable:
                    constraints.append("NOT NULL")
                if column.unique:
                    constraints.append("UNIQUE")

                if constraints:
                    column_info.append(" " + ", ".join(constraints))

                # Add description
                if column.description:
                    column_info.append(f" - {column.description}")

                schema_lines.append("".join(column_info))

            # Add a blank line between tables
            schema_lines.append("")

        # Add relationships section
        has_relationships = False
        for table in schema.tables:
            if table.relationships:
                if not has_relationships:
                    schema_lines.append("Relationships:")
                    has_relationships = True

                for rel in table.relationships:
                    schema_lines.append(f"  - {table.name}.{rel.from_column} → {rel.to_table}.{rel.to_column}")

        return "\n".join(schema_lines)
