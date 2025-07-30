from typing import Optional, Dict, Any
from pkg.log.logger import Logger
import json

class SQLCodeGenerator:
    """Generator for SQL code based on natural language queries"""
    
    def __init__(self, llm_client, model: Optional[str] = None, logger=None):
        """
        Initialize the SQL code generator
        
        Args:
            llm_client: Client for LLM API calls
            model: Optional model to use for LLM calls
            logger: Optional logger instance
        """
        self.llm_client = llm_client
        self.model = model or "gpt-4o"
        self.logger = logger or Logger()
        self.logger.info(f"Initializing SQLCodeGenerator with model: {self.model}")
        
    async def generate(
        self, 
        query: str, 
        analysis_result: Dict[str, Any],
        schema: Optional[str] = None,
        db_type: str = "postgresql"
    ) -> str:
        """
        Generate SQL code based on the natural language query
        
        Args:
            query: The natural language query
            analysis_result: The query analysis result
            schema: Optional database schema information
            db_type: The database type (e.g., "postgresql", "mysql")
            
        Returns:
            The generated SQL code
        """
        self.logger.info(f"SQLCodeGenerator.generate - Generating SQL for query: {query}")
        self.logger.info(f"SQLCodeGenerator.generate - Database type: {db_type}")
        self.logger.debug(f"SQLCodeGenerator.generate - Query analysis: {json.dumps(analysis_result)[:200]}...")
        
        try:
            # Parse the analysis result
            intent = analysis_result.get("intent", "unknown")
            target_entities = analysis_result.get("target_entities", [])
            metrics = analysis_result.get("metrics", [])
            conditions = analysis_result.get("conditions", [])
            
            self.logger.info(f"SQLCodeGenerator.generate - Intent: {intent}, Targets: {target_entities}")
            self.logger.info(f"SQLCodeGenerator.generate - Metrics: {metrics}, Conditions: {len(conditions)}")
            
            # Build the prompt
            prompt = SQL_GENERATOR_PROMPT_TEMPLATE.format(
                query=query,
                intent=intent,
                target_entities=", ".join(target_entities),
                metrics=", ".join([m["name"] for m in metrics]) if metrics else "None",
                conditions=", ".join([c["description"] for c in conditions]) if conditions else "None",
                schema=schema or "No schema provided",
                db_type=db_type
            )
            self.logger.debug("SQLCodeGenerator.generate - Prompt built")
            
            # Get completion from LLM
            self.logger.info(f"SQLCodeGenerator.generate - Sending request to LLM model: {self.model}")
            response = await self.llm_client.get_completion(
                model=self.model,
                prompt=prompt,
                temperature=0.1,
                seed=42
            )
            self.logger.info("SQLCodeGenerator.generate - Received response from LLM")
            
            # Extract SQL code from response
            sql_code = self._extract_sql(response)
            self.logger.info(f"SQLCodeGenerator.generate - SQL generated (length: {len(sql_code)})")
            self.logger.debug(f"SQLCodeGenerator.generate - Generated SQL: {sql_code}")
            
            return sql_code
            
        except Exception as e:
            self.logger.error(f"SQLCodeGenerator.generate - Error generating SQL: {str(e)}")
            # Return a simple SELECT statement on error
            return f"-- Error generating SQL: {str(e)}\nSELECT 'Error: Could not generate valid SQL' as error_message;"
    
    def _extract_sql(self, response: str) -> str:
        """Extract SQL code from LLM response"""
        try:
            # Look for SQL code blocks
            sql_block_start = response.find("```sql")
            if sql_block_start >= 0:
                # Skip the ```sql marker
                sql_start = response.find("\n", sql_block_start) + 1
                sql_end = response.find("```", sql_start)
                if sql_end >= 0:
                    sql_code = response[sql_start:sql_end].strip()
                    self.logger.info("SQLCodeGenerator._extract_sql - Successfully extracted SQL from code block")
                    return sql_code
            
            # Look for just code blocks
            code_block_start = response.find("```")
            if code_block_start >= 0:
                # Skip the ``` marker
                code_start = response.find("\n", code_block_start) + 1
                code_end = response.find("```", code_start)
                if code_end >= 0:
                    code = response[code_start:code_end].strip()
                    self.logger.info("SQLCodeGenerator._extract_sql - Extracted code from generic code block")
                    return code
            
            # If no code blocks, return the whole response
            self.logger.warning("SQLCodeGenerator._extract_sql - No code blocks found, returning full response")
            return response.strip()
            
        except Exception as e:
            self.logger.error(f"SQLCodeGenerator._extract_sql - Error extracting SQL: {str(e)}")
            return f"-- Error extracting SQL: {str(e)}\nSELECT 'Error: Failed to parse SQL' as error_message;" 