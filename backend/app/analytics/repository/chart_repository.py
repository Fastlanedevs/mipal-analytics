import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid

from neomodel import db
from app.analytics.entity.chart import Chart, ChartHistory, ChartVisibility, ChartType
from app.analytics.errors import ChartNotFoundError, ChartAccessDeniedError
from app.chat.repository.sql_schema.conversation import ConversationModel, ChartModel, MessageModel
from pkg.db_util.neo4j_conn import Neo4jConnection


def parse_datetime(date_string: str) -> datetime:
    """
    Parse a datetime string into a datetime object.
    Handles different datetime formats commonly used in the app.
    
    Args:
        date_string: String representation of a datetime
        
    Returns:
        datetime object
    """
    try:
        # Try ISO format first (most common)
        return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
    except ValueError:
        # Try more formats if needed
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',  # ISO format with Z
            '%Y-%m-%dT%H:%M:%S.%f',   # ISO format without Z
            '%Y-%m-%dT%H:%M:%S',      # ISO format without fractions
            '%Y-%m-%d %H:%M:%S.%f',   # SQL-like format with fractions
            '%Y-%m-%d %H:%M:%S',      # SQL-like format without fractions
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_string, fmt)
            except ValueError:
                continue
        
        # If all formats fail, default to current datetime
        return datetime.now()


class ChartRepository:
    """Repository for chart-related operations"""

    def __init__(self, db_conn: Neo4jConnection = None, logger=None):
        """Initialize the chart repository"""
        self.db_conn = db_conn
        self.logger = logger or logging.getLogger(__name__)
        # Initialize indexes if they don't exist (will be ignored if already exist)
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Ensure required indexes exist for efficient queries"""
        try:
            # Use Neo4j index syntax with IF NOT EXISTS to prevent errors with existing indexes
            self._execute_query("CREATE INDEX IF NOT EXISTS FOR (c:Chart) ON (c.visibility)")
            self._execute_query("CREATE INDEX IF NOT EXISTS FOR (c:Chart) ON (c.created_by)")
            self._execute_query("CREATE INDEX IF NOT EXISTS FOR (c:Chart) ON (c.org_id)")
            self._execute_query("CREATE INDEX IF NOT EXISTS FOR (c:Chart) ON (c.message_id)")
            
            self.logger.info("Chart indexes verified")
        except Exception as e:
            # Log but don't fail - indexes are for optimization only
            self.logger.warning(f"Could not create indexes: {e}")
    
    def _execute_query(self, query, params=None, transaction=False):
        """Execute a Cypher query using the connection pool"""
        try:
            # Log query for debugging (trimmed for large queries)
            query_log = query[:500] + '...' if len(query) > 500 else query
            self.logger.debug(f"Executing query: {query_log}")
            self.logger.debug(f"Params: {str(params)[:200]}...")
            
            # Use self.db_conn if available, otherwise fallback to direct db usage
            if self.db_conn:
                result = self.db_conn.cypher_query(query, params, transaction)
                self.logger.debug(f"Query execution completed, result type: {type(result)}")
                return result
            else:
                # Fallback to direct db usage if no db_conn is provided
                if transaction:
                    with db.transaction:
                        self.logger.debug("Executing query in transaction")
                        results, meta = db.cypher_query(query, params or {})
                else:
                    self.logger.debug("Executing query without transaction")
                    results, meta = db.cypher_query(query, params or {})
                
                self.logger.debug(f"Query execution completed, result rows: {len(results) if results else 0}")
                db.clear_db_state()  # Clear db state when using direct db
                return results
        except Exception as e:
            # Log detailed error information
            self.logger.error(f"Error executing query: {str(e)}", exc_info=True)
            self.logger.error(f"Query: {query[:200]}...")
            self.logger.error(f"Params: {str(params)[:200]}...")
            raise  # Re-raise to allow caller to handle

    async def create_chart(self, message_id: str, chart_data: List[Dict[str, Any]], chart_type_from_llm: str, chart_schema: Dict[str, Any],
                          user_id: str, org_id: str, title: Optional[str] = None,
                          description: Optional[str] = None, visibility: str = 'PRIVATE',
                          available_adjustments: Optional[Dict[str, Any]] = None,
                          alternative_visualizations: Optional[List[Dict[str, Any]]] = None,
                          alternative_visualization_queries: Optional[List[str]] = None) -> str:
        """
        Create a new chart
        
        Args:
            message_id: ID of the message this chart is based on
            chart_data: Data for the chart
            chart_schema: Schema defining the chart
            chart_type_from_llm: The type of chart generated
            user_id: ID of the user creating the chart
            org_id: ID of the organization
            title: Title of the chart
            description: Description of the chart
            visibility: Chart visibility (PRIVATE, ORGANIZATION, PUBLIC)
            available_adjustments: Available field mappings for chart adjustments
            alternative_visualizations: Alternative visualization options
            alternative_visualization_queries: Alternative visualization queries
            
        Returns:
            ID of the created chart
        """
        self.logger.info(f"Creating chart from message {message_id} for user {user_id}")
        self.logger.info(f"Chart type info recieved from service, {chart_type_from_llm}")
        
        try:
            # Generate chart ID
            chart_id = str(uuid.uuid4())
            chart_type = chart_type_from_llm
            
            # Get chart type from schema only if not provided
            if not chart_type and isinstance(chart_schema, dict):
                if 'chart_type' in chart_schema:
                    chart_type = chart_schema['chart_type']
                else:
                    chart_type = chart_schema.get('type', '')
            
            # Special handling for arc mark type (pie charts)
            if isinstance(chart_schema, dict) and 'mark' in chart_schema:
                mark = chart_schema['mark']
                if isinstance(mark, str) and mark.lower() == 'arc':
                    self.logger.info("Detected 'arc' mark type, mapping to 'pie' chart type")
                    chart_type = 'pie'
                elif isinstance(mark, dict) and mark.get('type', '').lower() == 'arc':
                    self.logger.info("Detected 'arc' mark type, mapping to 'pie' chart type")
                    chart_type = 'pie'
            
            # Ensure the chart_schema has the required $schema field for Vega-Lite
            if isinstance(chart_schema, dict) and '$schema' not in chart_schema:
                chart_schema['$schema'] = "https://vega.github.io/schema/vega-lite/v5.json"
                
            # Validate chart_type is a valid enum value
            valid_chart_types = [chart_type.value for chart_type in ChartType]
            if chart_type not in valid_chart_types:
                if chart_type == 'arc':
                    self.logger.info(f"Converting 'arc' chart_type to 'pie'")
                    chart_type = "pie"
                else:
                    self.logger.warning(f"Invalid chart_type: {chart_type}, defaulting to ''")
                    chart_type = ""
            
            # Make sure all nested objects in chart schema are serialized
            try:
                # Deep copy to avoid mutation issues
                chart_schema_copy = json.loads(json.dumps(chart_schema))
                chart_data_copy = json.loads(json.dumps(chart_data))
                
                # Convert complex objects to JSON strings
                chart_schema_str = json.dumps(chart_schema_copy)
                chart_data_str = json.dumps(chart_data_copy)
                
                # Convert field mappings to JSON string if provided
                field_mappings_str = json.dumps(available_adjustments) if available_adjustments else None
                self.logger.info(f"Field mappings serialized: {field_mappings_str is not None}")
            except (TypeError, json.JSONDecodeError) as e:
                self.logger.error(f"Error serializing chart data: {str(e)}")
                # Fallback to simpler serialization
                chart_schema_str = json.dumps(chart_schema)
                chart_data_str = json.dumps(chart_data)
                field_mappings_str = None
            
            
            # Serialize alternative visualizations if provided
            alt_vis_str = None
            # Serialize alternative visualization queries if available
            alt_queries_str = None
            if alternative_visualization_queries:
                try:
                    # Ensure proper format of alternative_visualization_queries
                    serializable_alt_queries = []
                    
                    for query_item in alternative_visualization_queries:
                        if isinstance(query_item, dict):
                            # If it's already a dict with query and description, use it directly
                            serializable_alt_queries.append(query_item)
                        elif hasattr(query_item, 'dict'):
                            # If it's a Pydantic model, convert to dict
                            serializable_alt_queries.append(query_item.dict())
                        elif hasattr(query_item, '__dict__'):
                            # If it has __dict__, use that
                            serializable_alt_queries.append(query_item.__dict__)
                        else:
                            # Skip unserializable objects
                            self.logger.warning(f"Skipping unserializable alternative visualization query: {type(query_item)}")
                    
                    alt_queries_str = json.dumps(serializable_alt_queries)
                    self.logger.info(f"Serialized {len(alternative_visualization_queries)} alternative visualization queries")
                except Exception as e:
                    self.logger.error(f"Error serializing alternative_visualization_queries: {str(e)}")
                    alt_queries_str = "[]"
            
            now = datetime.utcnow().isoformat()

            # Create the base properties
            properties = [
                "uid: $chart_id",
                "title: $title",
                "description: $description",
                "chart_type: $chart_type",
                "chart_schema: $chart_schema",
                "chart_data: $chart_data",
                "created_by: $user_id",
                "org_id: $org_id",
                "visibility: $visibility",
                "message_id: $message_id",
                "created_at: $now",
                "updated_at: $now",
                "last_refreshed_at: $now"
            ]

            # Add alternative visualization queries if available
            if alternative_visualization_queries:
                properties.append("alternative_visualization_queries: $alternative_visualization_queries")

            # Join properties with commas
            properties_str = ",\n    ".join(properties)

            # Use a single transaction for the entire operation
            query = f"""
            CREATE (c:Chart {{
                {properties_str}
            }})
            RETURN c
            """
            
            params = {
                'message_id': message_id,
                'chart_id': chart_id,
                'title': title or "",
                'description': description or "",
                'chart_type': chart_type,
                'chart_schema': chart_schema_str,
                'chart_data': chart_data_str,
                'user_id': user_id,
                'org_id': org_id,
                'visibility': visibility,
                'now': now
            }
            
            # Add alternative visualization queries to params if available
            if alt_queries_str:
                params['alternative_visualization_queries'] = alt_queries_str
            
            results = self._execute_query(query, params, transaction=True)
                
            if not results:
                raise ValueError(f"Message with ID {message_id} not found")
            
            self.logger.info(f"Successfully created chart {chart_id}")
            
            # Extract node from result and convert to Chart entity
            self.logger.info(f"Create chart result: {type(results)} with length {len(results)}")
            
            # Direct return of chart ID for backward compatibility
            return chart_id
            
        except Exception as e:
            self.logger.error(f"Error creating chart: {str(e)}")
            raise
    
    def _node_to_chart(self, node) -> Chart:
        """
        Convert a Neo4j node to a Chart entity
        
        Args:
            node: Neo4j node
            message_id: Optional message ID if not included in node
            
        Returns:
            Chart entity
        """
        try:
            # Extract all properties from the node
            props = {}
            
            # Handle both types of Neo4j node objects (neo4j-driver and py2neo)
            if hasattr(node, 'items'):
                # For neo4j-driver Node object
                for key, value in dict(node).items():
                    props[key] = value
            else:
                # For py2neo Node object
                for key in dir(node):
                    try:
                        value = getattr(node, key, None)
                        if value is not None:
                            props[key] = value
                    except (AttributeError, TypeError):
                        pass
            
            
            # If we couldn't get any properties, log an error
            if not props:
                self.logger.error(f"Could not extract properties from node: {type(node)}")
                raise ValueError("Could not extract properties from node")
            
            # Parse chart data JSON
            chart_data = []
            if 'chart_data' in props and props['chart_data']:
                try:
                    if isinstance(props['chart_data'], str):
                        chart_data = json.loads(props['chart_data'])
                    elif isinstance(props['chart_data'], list):
                        chart_data = props['chart_data']
                except json.JSONDecodeError:
                    self.logger.error(f"Failed to parse chart data JSON: {props['chart_data']}")
            
            # Parse chart schema JSON
            chart_schema = {}
            if 'chart_schema' in props and props['chart_schema']:
                try:
                    if isinstance(props['chart_schema'], str):
                        chart_schema = json.loads(props['chart_schema'])
                    elif isinstance(props['chart_schema'], dict):
                        chart_schema = props['chart_schema']
                except json.JSONDecodeError:
                    self.logger.error(f"Failed to parse chart schema JSON: {props['chart_schema']}")
            
            # Parse field mappings JSON if available
            field_mappings = None
            
            # Parse alternative visualizations if available
            alternative_visualizations = None
            # Parse alternative visualization queries if available
            alternative_visualization_queries = None
            if 'alternative_visualization_queries' in props and props['alternative_visualization_queries']:
                try:
                    if isinstance(props['alternative_visualization_queries'], str):
                        alternative_visualization_queries = json.loads(props['alternative_visualization_queries'])
                    elif isinstance(props['alternative_visualization_queries'], list):
                        alternative_visualization_queries = props['alternative_visualization_queries']
                except json.JSONDecodeError:
                    self.logger.error(f"Failed to parse alternative_visualization_queries JSON: {props['alternative_visualization_queries']}")
                    alternative_visualization_queries = None
            
            # Get message ID from node properties
            msg_id_from_props = props.get('message_id') 
            if not msg_id_from_props:
                self.logger.error(f"Node {props.get('uid')} is missing message_id property.")
                # This would cause an error in Chart instantiation if message_id is not Optional[UUID]
                # For now, assuming it must exist as per current Chart entity.
                raise ValueError(f"Node {props.get('uid')} is missing essential 'message_id' property.")
            
            # Determine chart type from schema or use fallback
            chart_type = ChartType.BAR  # Default
            
            # First check the explicit chart_type property
            if 'chart_type' in props and props['chart_type']:
                type_str = props['chart_type']
                if isinstance(type_str, str) and type_str in [t.value for t in ChartType]:
                    chart_type = ChartType(type_str)
                    self.logger.info(f"Using chart_type from props: {chart_type}")
            elif 'chart_type' in chart_schema:
                type_str = chart_schema['chart_type']
                if isinstance(type_str, str) and type_str in [t.value for t in ChartType]:
                    chart_type = ChartType(type_str)
                    self.logger.info(f"Using chart_type from chart_schema: {chart_type}")
            
            # But also check the schema for special encodings and mark types
            if chart_schema:
                # Check mark type first as it's most definitive
                if 'mark' in chart_schema:
                    mark = chart_schema['mark']
                    mark_type = None
                    
                    if isinstance(mark, dict) and 'type' in mark:
                        mark_type = mark['type'].lower()
                    elif isinstance(mark, str):
                        mark_type = mark.lower()
                    
                    # Map non-standard mark types to chart types
                    if mark_type == 'arc':
                        chart_type = ChartType.PIE
                        self.logger.info(f"Mapped 'arc' mark type to pie chart type")
                    elif mark_type in [t.value for t in ChartType]:
                        chart_type = ChartType(mark_type)
                        self.logger.info(f"Using chart_type from mark: {chart_type}")
                
                # Then check encoding properties
                if 'encoding' in chart_schema:
                    # For grouped_bar charts: check if xOffset exists in encoding
                    if 'xOffset' in chart_schema['encoding'] and chart_type == ChartType.BAR:
                        chart_type = ChartType.GROUPED_BAR
                        self.logger.info(f"Detected grouped_bar chart based on xOffset encoding")
                    
                    # For stacked_bar charts: check if y contains 'stack' property
                    elif 'y' in chart_schema['encoding'] and 'stack' in chart_schema['encoding']['y'] and chart_type == ChartType.BAR:
                        chart_type = ChartType.STACKED_BAR
                        self.logger.info(f"Detected stacked_bar chart based on y.stack encoding")
                        
                    # For pie charts: check for theta encoding
                    elif 'theta' in chart_schema['encoding'] and chart_type not in [ChartType.PIE]:
                        chart_type = ChartType.PIE
                        self.logger.info(f"Detected pie chart based on theta encoding")
            
            # Parse dates
            created_at = datetime.now()
            updated_at = datetime.now()
            last_refreshed_at = datetime.now()
            
            if 'created_at' in props and props['created_at']:
                try:
                    if isinstance(props['created_at'], str):
                        created_at = parse_datetime(props['created_at'])
                    elif hasattr(props['created_at'], 'year'):  # Neo4j DateTime object
                        created_at = datetime(
                            props['created_at'].year, 
                            props['created_at'].month, 
                            props['created_at'].day,
                            props['created_at'].hour, 
                            props['created_at'].minute, 
                            props['created_at'].second
                        )
                except (ValueError, TypeError):
                    self.logger.error(f"Failed to parse created_at: {props['created_at']}")
            
            if 'updated_at' in props and props['updated_at']:
                try:
                    if isinstance(props['updated_at'], str):
                        updated_at = parse_datetime(props['updated_at'])
                    elif hasattr(props['updated_at'], 'year'):  # Neo4j DateTime object
                        updated_at = datetime(
                            props['updated_at'].year, 
                            props['updated_at'].month, 
                            props['updated_at'].day,
                            props['updated_at'].hour, 
                            props['updated_at'].minute, 
                            props['updated_at'].second
                        )
                except (ValueError, TypeError):
                    self.logger.error(f"Failed to parse updated_at: {props['updated_at']}")
            
            if 'last_refreshed_at' in props and props['last_refreshed_at']:
                try:
                    if isinstance(props['last_refreshed_at'], str):
                        last_refreshed_at = parse_datetime(props['last_refreshed_at'])
                    elif hasattr(props['last_refreshed_at'], 'year'):  # Neo4j DateTime object
                        last_refreshed_at = datetime(
                            props['last_refreshed_at'].year, 
                            props['last_refreshed_at'].month, 
                            props['last_refreshed_at'].day,
                            props['last_refreshed_at'].hour, 
                            props['last_refreshed_at'].minute, 
                            props['last_refreshed_at'].second
                        )
                except (ValueError, TypeError):
                    self.logger.error(f"Failed to parse last_refreshed_at: {props['last_refreshed_at']}")
            
            # Parse visibility
            visibility = ChartVisibility.PRIVATE
            if 'visibility' in props and props['visibility']:
                vis_str = props['visibility']
                if isinstance(vis_str, str) and vis_str in [v.value for v in ChartVisibility]:
                    visibility = ChartVisibility(vis_str)
            
            # Create Chart entity
            chart = Chart(
                uid=props.get('uid', ''),
                title=props.get('title'),
                description=props.get('description'),
                chart_type=chart_type,
                chart_schema=chart_schema,
                chart_data=chart_data,
                message_id=uuid.UUID(hex=msg_id_from_props),
                user_id=props.get('user_id', ''),
                org_id=props.get('org_id'),
                visibility=visibility,
                created_at=created_at,
                updated_at=updated_at,
                last_refreshed_at=last_refreshed_at,
                alternative_visualization_queries=alternative_visualization_queries
            )
            
            # Log created chart details
            self.logger.info(f"Created chart entity with ID: {chart.uid}, Type: {chart.chart_type}")
                
            return chart
            
        except Exception as e:
            self.logger.error(f"Error converting node to Chart: {str(e)}")
            raise
    
    async def get_chart(self, chart_id: str, user_id: str, org_id: Optional[str] = None) -> Optional[Chart]:
        """
        Get a chart by ID with access control
        
        Args:
            chart_id: ID of the chart to retrieve
            user_id: ID of the requesting user
            org_id: ID of the user's organization
            
        Returns:
            Chart entity if found and accessible, None otherwise
        """
        self.logger.info(f"Getting chart {chart_id} for user {user_id}")
        
        try:
            # Query with access control - optimized to get all data in one query
            query = """
            MATCH (c:Chart {uid: $chart_id})
            WHERE (c.created_by = $user_id)
               OR c.visibility = 'PUBLIC'
               OR (c.visibility = 'ORGANIZATION' AND c.org_id = $org_id)
            RETURN c 
            """
            
            params = {
                'chart_id': chart_id,
                'user_id': user_id,
                'org_id': org_id or ''
            }
            
            result = self._execute_query(query, params)
            
            self.logger.info(f"Get chart query result type: {type(result)}")
            
            if not result:
                self.logger.warning(f"No chart found with ID {chart_id} for user {user_id}")
                return None
                
            if len(result) == 0:
                self.logger.warning(f"Empty result for chart {chart_id}")
                return None
                
            self.logger.info(f"Chart query result: {type(result)} with length {len(result)}")
            self.logger.info(f"Result[0] type: {type(result[0])}")
            
            # Try various ways to extract node based on Neo4j result format
            node = None
            
            # Case 1: Result is list of dicts with 'c' key
            if isinstance(result[0], dict):
                self.logger.info(f"Result[0] is a dict with keys: {list(result[0].keys())}")
                if 'c' in result[0]:
                    node = result[0]['c']
                    
            # Case 2: Result is list of lists (most common from Neo4j)
            elif isinstance(result[0], list):
                self.logger.info(f"Result[0] is a list with length: {len(result[0])}")
                if len(result[0]) >= 1:
                    node = result[0][0]  # First item is node
                    
            # Case 3: Direct access (less common)
            else:
                self.logger.info(f"Result[0] is direct access type: {type(result[0])}")
                node = result[0]
            
            # If we extracted a node, convert to Chart
            if node is not None:
                return self._node_to_chart(node)
            else:
                self.logger.error(f"Could not extract node from result: {result}")
                return None
            
        except Exception as e:
            self.logger.error(f"Error retrieving chart {chart_id}: {str(e)}", exc_info=True)
            # Return None instead of raising for better error handling
            return None

    async def get_charts_by_message(self, message_id: str, user_id: str, org_id: Optional[str] = None) -> List[Chart]:
        """
        Get all charts associated with a specific message
        
        Args:
            message_id: ID of the message
            user_id: ID of the requesting user
            org_id: ID of the user's organization
            
        Returns:
            List of charts associated with the message that the user can access
        """
        
        try:
            # Query with access control
            query = """
            MATCH (c:Chart {message_id: $message_id})
            WHERE (c.created_by = $user_id)
               OR c.visibility = 'PUBLIC'
               OR (c.visibility = 'ORGANIZATION' AND c.org_id = $org_id)
            RETURN c
            """
            
            results = self._execute_query(
                query, 
                {
                    'message_id': message_id,
                    'user_id': user_id,
                    'org_id': org_id or ''
                }
            )
            
            charts = []
            for result in results:
                # Handle both list and direct result formats
                chart_node = result[0] if isinstance(result, list) else result
                
                # Convert node to Chart using _node_to_chart
                chart = self._node_to_chart(chart_node)
                charts.append(chart)
                
            return charts
            
        except Exception as e:
            self.logger.error(f"Error retrieving charts for message {message_id}: {str(e)}")
            raise
            
    async def list_charts(self, 
                         user_id: str, 
                         org_id: Optional[str] = None, 
                         limit: int = 20, 
                         offset: int = 0) -> Tuple[List[Chart], int]:
        """
        List charts accessible to a user
        
        Args:
            user_id: ID of the requesting user
            org_id: ID of the user's organization
            limit: Maximum number of charts to return
            offset: Offset for pagination
            
        Returns:
            Tuple of (list of charts, total count)
        """
        self.logger.info(f"Listing charts for user {user_id}")
        
        try:
            # Common WHERE clause for authorization
            auth_where_clause = """
            WHERE (c.created_by = $user_id)
               OR c.visibility = 'PUBLIC'
               OR (c.visibility = 'ORGANIZATION' AND c.org_id = $org_id)
            """

            # Query for paginated charts
            charts_query = f"""
            MATCH (c:Chart)
            {auth_where_clause}
            RETURN c
            ORDER BY c.created_at DESC
            SKIP $offset
            LIMIT $limit
            """
            
            common_params = {
                'user_id': user_id,
                'org_id': org_id or ''
            }

            paginated_params = {
                **common_params,
                'offset': offset,
                'limit': limit
            }
            
            chart_results = self._execute_query(charts_query, paginated_params)
            
            charts = []
            if chart_results:
                for record in chart_results:
                    # Result is expected to be a list of records, where each record is the node itself or a list containing the node
                    chart_node = record[0] if isinstance(record, list) and len(record) > 0 else record
                    chart_entity = self._node_to_chart(chart_node)
                    if chart_entity:
                        charts.append(chart_entity)
            
            # Query for total count
            count_query = f"""
            MATCH (c:Chart)
            {auth_where_clause}
            RETURN count(c) as total
            """
            
            count_results = self._execute_query(count_query, common_params)
            
            total = 0
            if count_results and count_results[0] and isinstance(count_results[0], (list, tuple)) and len(count_results[0]) > 0:
                total = count_results[0][0]
            elif count_results and isinstance(count_results[0], int): # If driver returns count directly e.g. from a transaction result
                 total = count_results[0]
            elif count_results and isinstance(count_results[0], dict) and 'total' in count_results[0]: # if result is dict
                total = count_results[0]['total']

            return charts, total
            
        except Exception as e:
            self.logger.error(f"Error listing charts: {str(e)}")
            raise
    
    async def update_chart(self, 
                          chart_id: str, 
                          user_id: str, 
                          update_data: Dict[str, Any]) -> Optional[Chart]:
        """
        Update chart metadata
        
        Args:
            chart_id: ID of the chart to update
            user_id: ID of the requesting user
            update_data: Dictionary of fields to update
            
        Returns:
            Updated chart if successful, None if chart not found or access denied
        """
        self.logger.info(f"Updating chart {chart_id}")
        
        try:
            # Build SET clause for update dynamically
            set_clauses = []
            params = {
                'chart_id': chart_id,
                'user_id': user_id,
                'updated_at': datetime.utcnow()
            }
            
            # Process allowed fields
            allowed_fields = ['title', 'description', 'visibility']
            for field in allowed_fields:
                if field in update_data:
                    set_clauses.append(f"c.{field} = ${field}")
                    params[field] = update_data[field]
            
            # Add updated_at
            set_clauses.append("c.updated_at = $updated_at")
            
            # If nothing to update, return early
            if len(set_clauses) <= 1:  # Only updated_at
                return await self.get_chart(chart_id, user_id)
            
            # Combine SET clauses
            set_clause = ", ".join(set_clauses)
            
            # Query with authorization
            query = f"""
            MATCH (c:Chart {{uid: $chart_id}})
            WHERE c.created_by = $user_id
            SET {set_clause}
            RETURN c
            """
            
            # Log the final query for debugging
            self.logger.info(f"Update chart query: {query}")
            
            results = self._execute_query(query, params, transaction=True)
            
            if not results or len(results) == 0:
                self.logger.warning(f"Chart {chart_id} update failed - no results returned")
                # Try to get the chart to see if it exists
                return await self.get_chart(chart_id, user_id)
            
            # Process results
            node = results[0][0] if isinstance(results[0], list) else results[0]

            # Convert to Chart object
            return self._node_to_chart(node)
            
        except Exception as e:
            self.logger.error(f"Error updating chart {chart_id}: {str(e)}")
            raise
    
    async def update_chart_data(self, 
                          chart_id: str, 
                          user_id: str, 
                          chart_data: List[Dict[str, Any]],
                          chart_schema: Optional[Dict[str, Any]] = None,
                          available_adjustments: Optional[Dict[str, Any]] = None,
                          chart_type: Optional[str] = None,
                          alternative_visualizations: Optional[List[Dict[str, Any]]] = None) -> Optional[Chart]:
        """
        Update chart data and related fields
        
        Args:
            chart_id: ID of the chart to update
            user_id: ID of the requesting user
            chart_data: New chart data
            chart_schema: Optional new chart schema
            available_adjustments: Optional new available adjustments
            chart_type: Optional new chart type
            alternative_visualizations: Optional new alternative visualizations
            
        Returns:
            Updated chart if successful, None if chart not found or access denied
        """
        try:
            now = datetime.utcnow().isoformat()
            
            # First serialize all complex objects to JSON
            try:
                chart_data_json = json.dumps(chart_data) # This is used for logging/validation, actual param uses original
            except Exception as e:
                self.logger.error(f"Error serializing chart data for logging: {str(e)}")
                # Do not return None here, proceed with original data for query
                
            # Log available adjustments dict details
            if available_adjustments:
                self.logger.info(f"Available adjustments dict keys: {list(available_adjustments.keys())}")
                
                # Try to ensure serializable - key for Neo4j
                try:
                    available_adjustments_json = json.dumps(available_adjustments) 
                    self.logger.info("Successfully serialized available_adjustments to JSON")
                except Exception as e:
                    self.logger.error(f"Error serializing available_adjustments: {str(e)}")
                    
                    # Try to fix by removing problematic fields
                    try:
                        # Create a clean version without alternative_visualizations
                        clean_adjustments = {k: v for k, v in available_adjustments.items() 
                                           if k != 'alternative_visualizations'}
                        json.dumps(clean_adjustments)  # Test if it's serializable
                        self.logger.info("Clean version without alternative_visualizations is serializable")
                        available_adjustments = clean_adjustments
                    except Exception as inner_e:
                        self.logger.error(f"Even clean version failed: {str(inner_e)}")
                        # Just use an empty dict as fallback
                        available_adjustments = {}
            
            # Process parameters to update
            update_params = {'chart_id': chart_id, 'user_id': user_id} # Params for MATCH, WHERE

            set_props_dict = {} # Properties to be set in the SET clause
            
            # Always update chart_data
            set_props_dict['chart_data'] = json.dumps(chart_data)
            
            # Add chart_schema if provided
            if chart_schema:
                set_props_dict['chart_schema'] = json.dumps(chart_schema)
            
            # Add chart_type if provided
            if chart_type:
                set_props_dict['chart_type'] = chart_type
            
            # Process available_adjustments
            field_mappings_str = None
            if available_adjustments:
                # Handle the case where alternative_visualizations is in available_adjustments
                if "alternative_visualizations" in available_adjustments:
                    alt_vis_from_adjustments = available_adjustments["alternative_visualizations"]
                    self.logger.info(f"Found alternative visualizations in available_adjustments: {len(alt_vis_from_adjustments)}")
                    
                    # Don't store alternative_visualizations in available_adjustments if it's provided separately
                    if alternative_visualizations is None: # Prioritize explicitly passed alternative_visualizations
                        alternative_visualizations = alt_vis_from_adjustments # Use from adjustments if not passed separately
                        
                    # Create a clean version without alternative_visualizations for available_field_mappings
                    clean_adjustments = {k: v for k, v in available_adjustments.items() 
                                    if k != 'alternative_visualizations'}
                    
                    self.logger.info("Clean version of available_adjustments without alternative_visualizations is serializable")
                    field_mappings_str = json.dumps(clean_adjustments)
                else:
                    field_mappings_str = json.dumps(available_adjustments)
                
                set_props_dict['available_field_mappings'] = field_mappings_str
            
            # Add alternative_visualizations if provided (either directly or extracted from available_adjustments)
            if alternative_visualizations:
                try:
                    # Make sure all objects in alternative_visualizations are JSON serializable
                    serializable_alt_viz = []
                    
                    for alt_viz in alternative_visualizations:
                        if isinstance(alt_viz, dict):
                            serializable_alt_viz.append(alt_viz)
                        elif hasattr(alt_viz, 'dict'):
                            serializable_alt_viz.append(alt_viz.dict())
                        elif hasattr(alt_viz, '__dict__'):
                            serializable_alt_viz.append(alt_viz.__dict__)
                        else:
                            self.logger.warning(f"Skipping unserializable alternative visualization: {type(alt_viz)}")
                    
                    set_props_dict['alternative_visualizations'] = json.dumps(serializable_alt_viz)
                    self.logger.info(f"Adding alternative_visualizations to set_props_dict: {len(alternative_visualizations)} items")
                except Exception as e:
                    self.logger.error(f"Error serializing alternative visualizations: {str(e)}", exc_info=True)
            
            # Add updated_at
            set_props_dict['updated_at'] = now
            
            # If only updated_at is being set (no other data changes)
            if len(set_props_dict) <= 1 and 'updated_at' in set_props_dict :
                 # org_id is Optional for get_chart; assuming it's okay to pass None if not available here.
                current_chart = await self.get_chart(chart_id, user_id, None) 
                return current_chart
            
            # Combine SET clauses from set_props_dict
            set_clause = ", ".join([f"c.{key} = ${key}" for key in set_props_dict])
            
            # Merge set_props_dict into update_params for query execution
            final_query_params = {**update_params, **set_props_dict}

            query = f"""
            MATCH (c:Chart {{uid: $chart_id}})
            WHERE c.created_by = $user_id
            SET {set_clause}
            RETURN c
            """
            
            # Log the query
            self.logger.info(f"Update query: {query}")
            # self.logger.info(f"Update params: { {k: (type(v), str(v)[:100] + '...' if len(str(v)) > 100 else str(v)) for k,v in final_query_params.items()} }")

            # Execute query
            results = self._execute_query(query, final_query_params, transaction=True)
            
            # Check for results
            if not results or len(results) == 0:
                self.logger.warning(f"Chart {chart_id} update failed - no results returned")
                # Try to get the chart to see if it exists
                return await self.get_chart(chart_id, user_id)
            
            # Process results
            node = results[0][0] if isinstance(results[0], list) else results[0]

            # Convert to Chart object
            return self._node_to_chart(node)
            
        except Exception as e:
            self.logger.error(f"Error updating chart data: {str(e)}", exc_info=True)
            return None
    
    def _ensure_neo4j_safe(self, value):
        """
        Ensure a value is safe to store in Neo4j by converting complex objects to JSON strings
        
        Args:
            value: Value to make Neo4j-safe
            
        Returns:
            Neo4j-safe value (primitives or JSON strings)
        """
        if isinstance(value, (dict, list)):
            try:
                return json.dumps(value)
            except (TypeError, json.JSONDecodeError) as e:
                self.logger.error(f"Error serializing to JSON: {str(e)}")
                # If we can't properly serialize, return empty object/list
                return json.dumps({} if isinstance(value, dict) else [])
        return value
    
    async def create_chart_history(self, 
                                 chart_id: str, 
                                 chart_data: List[Dict[str, Any]], 
                                 chart_schema: Dict[str, Any],
                                 modified_by: str) -> str:
        """
        Create a chart history entry
        
        Args:
            chart_id: ID of the chart
            chart_data: Chart data to save in history
            chart_schema: Chart schema to save in history
            modified_by: ID of the user making the modification
            
        Returns:
            ID of the created history entry
        """
        self.logger.info(f"Creating history entry for chart {chart_id}")
        
        try:
            # Generate history ID
            history_id = str(uuid.uuid4())
            
            # Create history node and relationship in a single query
            query = """
            MATCH (c:Chart {uid: $chart_id})
            WHERE c IS NOT NULL
            CREATE (h:ChartHistory {
                uid: $history_id,
                chart_type: c.chart_type,
                chart_schema: $chart_schema,
                chart_data: $chart_data,
                created_at: datetime(),
                modified_by: $modified_by
            })
            CREATE (c)-[:PREVIOUS_VERSION]->(h)
            RETURN h.uid
            """
            
            # Ensure chart_data and chart_schema are Neo4j-safe
            chart_data_safe = self._ensure_neo4j_safe(chart_data)
            chart_schema_safe = self._ensure_neo4j_safe(chart_schema)
            
            results = self._execute_query(
                query, 
                {
                    'chart_id': chart_id,
                    'history_id': history_id,
                    'chart_schema': chart_schema_safe,
                    'chart_data': chart_data_safe,
                    'modified_by': modified_by
                }
            )
            
            if not results:
                raise ChartNotFoundError(f"Chart with ID {chart_id} not found")
            
            return history_id
            
        except Exception as e:
            self.logger.error(f"Error creating history for chart {chart_id}: {str(e)}")
            raise e
    
    async def get_chart_history(self, 
                              chart_id: str, 
                              user_id: str,
                              limit: int = 20,
                              offset: int = 0) -> Tuple[List[ChartHistory], int]:
        """
        Get history entries for a chart
        
        Args:
            chart_id: ID of the chart
            user_id: ID of the requesting user
            limit: Maximum number of entries to return
            offset: Offset for pagination
            
        Returns:
            Tuple of (list of history entries, total count)
        """
        self.logger.info(f"Getting history for chart {chart_id}")
        
        try:
            # Check access to the chart first
            chart_node = await self.get_chart(chart_id, user_id)
            if not chart_node:
                raise ChartAccessDeniedError(f"Chart with ID {chart_id} not found or access denied")
            
            # First, get the total count
            count_query = """
            MATCH (c:Chart {uid: $chart_id})-[:PREVIOUS_VERSION]->(h:ChartHistory)
            RETURN COUNT(h) as total
            """
            
            count_result = self._execute_query(
                count_query, 
                {
                    'chart_id': chart_id
                }
            )
            
            total = 0
            if count_result and len(count_result) > 0:
                total = count_result[0][0]
            
            # Now get the paginated history entries
            query = """
            MATCH (c:Chart {uid: $chart_id})-[:PREVIOUS_VERSION]->(h:ChartHistory)
            RETURN h
            ORDER BY h.created_at DESC
            SKIP $offset
            LIMIT $limit
            """
            
            results = self._execute_query(
                query, 
                {
                    'chart_id': chart_id,
                    'offset': offset,
                    'limit': limit
                }
            )
            
            history_entries = []
            
            if results:
                for history_record in results:
                    # Extract node from record
                    history_node = history_record[0] if isinstance(history_record, list) else history_record
                    
                    # Extract node properties using the same approach as in _node_to_chart
                    props = {}
                    
                    # Try different approaches to get properties
                    if hasattr(history_node, "properties") and callable(getattr(history_node, "properties", None)):
                        # If it's a neomodel Node with properties() method
                        props = history_node.properties()
                    elif hasattr(history_node, "_properties"):
                        # Direct access to _properties
                        props = history_node._properties
                    elif hasattr(history_node, "get"):
                        # If it supports dictionary-like access
                        for key in ['uid', 'chart_type', 'chart_schema', 'chart_data', 'modified_by', 'created_at']:
                            if history_node.get(key) is not None:
                                props[key] = history_node.get(key)
                    elif isinstance(history_node, dict):
                        # Direct dict
                        props = history_node
                    else:
                        # Last resort: try attribute access
                        for key in ['uid', 'chart_type', 'chart_schema', 'chart_data', 'modified_by', 'created_at']:
                            try:
                                value = getattr(history_node, key, None)
                                if value is not None:
                                    props[key] = value
                            except Exception:
                                pass
                    
                    # Process chart_schema - Parse from JSON string if needed
                    chart_schema = props.get('chart_schema', {})
                    if isinstance(chart_schema, str):
                        try:
                            chart_schema = json.loads(chart_schema)
                        except:
                            chart_schema = {}
                    
                    # Process chart_data - Parse from JSON string if needed
                    chart_data = props.get('chart_data', [])
                    if isinstance(chart_data, str):
                        try:
                            chart_data = json.loads(chart_data)
                        except:
                            chart_data = []
                    
                    # Process created_at - Convert Neo4j DateTime to ISO string
                    created_at = props.get('created_at', datetime.utcnow())
                    if hasattr(created_at, 'iso_format'):
                        # If it has iso_format method, it's probably a datetime object
                        created_at = created_at.isoformat()
                    elif hasattr(created_at, 'to_native'):
                        # Convert Neo4j DateTime to Python datetime
                        created_at = created_at.to_native().isoformat()
                    elif isinstance(created_at, str):
                        # Already a string
                        pass
                    else:
                        # Fallback
                        created_at = datetime.utcnow().isoformat()
                    
                    # Create ChartHistory instance from properties
                    history = ChartHistory(
                        id=props.get('uid', str(uuid.uuid4())),  # Use a random ID if uid not available
                        chart_id=chart_id,
                        chart_type=props.get('chart_type', ChartType.EMPTY),
                        chart_schema=chart_schema,
                        chart_data=chart_data,
                        modified_by=props.get('modified_by', ''),
                        created_at=created_at
                    )
                    history_entries.append(history)
                
            return history_entries, total
            
        except ChartAccessDeniedError:
            raise
        except Exception as e:
            self.logger.error(f"Error getting history for chart {chart_id}: {str(e)}")
            raise
    
    async def delete_chart(self, chart_id: str, user_id: str) -> bool:
        """
        Delete a chart
        
        Args:
            chart_id: ID of the chart to delete
            user_id: ID of the requesting user
            
        Returns:
            True if deleted successfully, False otherwise
        """
        self.logger.info(f"Deleting chart {chart_id}")
        
        try:
            # Delete chart and its history in a single transaction
            query = """
            MATCH (c:Chart {uid: $chart_id})
            WHERE c.created_by = $user_id
            WITH c // Ensure c is bound and authorized before OPTIONAL MATCH and DELETE
            OPTIONAL MATCH (c)-[:PREVIOUS_VERSION]->(h:ChartHistory)
            DETACH DELETE c, h
            RETURN true AS deleted_flag // Return a literal true if deletion part was reached
            """
            
            results = self._execute_query(
                query, 
                {
                    'chart_id': chart_id,
                    'user_id': user_id
                }
            )
            
            # If results are not empty and the first result's first item is true, deletion was successful.
            if results and results[0] and isinstance(results[0], (list, tuple)) and len(results[0]) > 0 and results[0][0] is True:
                return True
            elif results and isinstance(results[0], dict) and results[0].get('deleted_flag') is True: # if result is dict
                return True

            return False # No results, or flag not true means not found, not authorized, or error during deletion
            
        except Exception as e:
            self.logger.error(f"Error deleting chart {chart_id}: {str(e)}")
            raise

