import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
import uuid

from app.analytics.repository.chart_repository import ChartRepository
from app.analytics.service.code_executor_service import CodeExecutorService
from app.analytics.service.chart_generation_service import ChartGenerationService
from app.analytics.entity.chart import Chart, ChartHistory, ChartVisibility, ChartType
from app.analytics.errors import (
    ChartNotFoundError, 
    ChartAccessDeniedError, 
    MessageNotFoundError, 
    ChartCreationError,
    ChartUpdateError,
    ChartRefreshError,
    InvalidChartDataError
)
from app.chat.service.chat_service import ChatService
from pkg.log.logger import Logger
from uuid import UUID

class ChartService:
    """Service for chart-related operations"""

    def __init__(self,  chart_repository: ChartRepository, code_executor_service: CodeExecutorService,
        chart_generation_service: ChartGenerationService, chat_service: ChatService, logger: Logger):
        self.chart_repository = chart_repository
        self.code_executor_service = code_executor_service
        self.chart_generation_service = chart_generation_service
        self.chat_service = chat_service
        self.logger = logger
    
    async def create_chart(self,
        message_id: UUID, user_id: str, org_id: str,
        title: Optional[str] = None, description: Optional[str] = None,
        visibility: str = 'PRIVATE', force_create: bool = False, adjustment_query: Optional[str] = None) -> Chart:

        # Ensure message_id is a UUID object
        if isinstance(message_id, str):
            message_id = UUID(message_id)

        self.logger.info(f"Creating chart for message {message_id} (force_create: {force_create}, adjustment_query: {adjustment_query if adjustment_query else 'None'})")
        
        try:
            # Check for existing charts unless force_create is True or adjustment_query is provided
            if not force_create and adjustment_query is None:
                existing_charts = await self.get_charts_by_message(
                    message_id=message_id,
                    user_id=user_id,
                    org_id=org_id
                )

                if existing_charts:
                    self.logger.info(f"Found {len(existing_charts)} existing charts for message {message_id}, returning latest")
                    # Sort by created_at in descending order and return the latest
                    latest_chart = sorted(existing_charts, key=lambda x: x.created_at.replace(tzinfo=None) if x.created_at.tzinfo else x.created_at, reverse=True)[0]
                    return latest_chart

            # If force_create is True, adjustment_query is provided, or no existing charts, proceed with chart creation
            if adjustment_query:
                self.logger.info(f"Creating new chart for message {message_id} due to adjustment query: {adjustment_query}")
            
            # Validate the request
            try:
                visibility_enum = ChartVisibility(visibility)
            except ValueError:
                raise Exception(f"Invalid visibility value: {visibility}")
            
            # Get the message using chat_service
            try:
                message = await self.chat_service.get_message(user_id=user_id, message_id=message_id)
                if not message:
                    self.logger.error(f"Message {message_id} not found or access denied")
                    raise Exception(f"Message not found: {message_id}")
            except Exception as e:
                self.logger.error(f"Unexpected error getting message: {str(e)}")
                raise Exception(f"Failed to get message: {str(e)}")
                
            # Extract data from message
            data = []
            sample_data = []
            columns = []
            query = ""
            code = ""
            previous_chart_data = None

            if adjustment_query is not None:
                # Get the latest chart data for this message
                latest_chart = await self.get_latest_chart_by_message(
                    message_id=message_id,
                    user_id=user_id,
                    org_id=org_id
                )
                if latest_chart:
                    previous_chart_data = str(latest_chart.chart_schema)

            # Handle different message content types
            if hasattr(message, 'content') and message.content:
                if isinstance(message.content, dict):
                    # Extract values based on content type
                    if message.content.get('type') == 'table':
                        # Extract data from table
                        data = message.content.get('data', [])
                        sample_data = data[:100] if data else []  # Limit sample size
                        columns = message.content.get('columns', [])
                        query = message.content.get('query', '')
                        sql = message.content.get('sql', '')
                    elif message.content.get('type') == 'query_result':
                        # Extract from query result
                        data = message.content.get('data', [])
                        sample_data = data[:100] if data else []
                        columns = message.content.get('columns', [])
                        query = message.content.get('query', '')
                        sql = message.content.get('sql', '')
                elif isinstance(message.content, str):
                    # Use content as query
                    query = message.content
                
                # If no data found in content, try to extract from artifacts
                if not data and hasattr(message, 'artifacts') and message.artifacts:
                    # Extract artifacts
                    artifacts = message.artifacts
                    parsed_artifacts = self.code_executor_service.parse_message_artifacts(artifacts)
                    
                    # Get data and columns from artifacts
                    if 'data' in parsed_artifacts and parsed_artifacts['data']:
                        data = parsed_artifacts['data']
                        sample_data = data[:500] if data else []
                    
                    if 'columns' in parsed_artifacts and parsed_artifacts['columns']:
                        columns = parsed_artifacts['columns']
                    
                    if 'code' in parsed_artifacts:
                        code = parsed_artifacts['code']
            
            if not data:
                raise ChartCreationError("No data found in message")
            
            if not columns:
                # Infer columns from data if not provided
                if data and isinstance(data[0], dict):
                    columns = [{"name": key, "data_type": self._infer_data_type(val)} 
                              for key, val in data[0].items()]
            
            # Generate chart schema
            self.logger.info(f"Generating chart for data with {len(data)} rows and {len(columns)} columns")
            chart_result = await self.chart_generation_service.generate_chart_schema(
                user_id=user_id,
                data=sample_data,
                columns=columns,
                query=query,
                code=code,
                adjustment_query=adjustment_query,
                previous_chart_data=previous_chart_data
            )
            
            # Don't default to 'bar' - let the chart generation service recommend the most appropriate type
            chart_type = chart_result.get('chart_type')
            # If chart_type is None or empty after chart generation, only then default to 'bar'
            if not chart_type:
                chart_type = 'bar'
                self.logger.warning("No chart type provided by generation service, defaulting to 'bar'")
            else:
                self.logger.info(f"Using chart type recommended by generation service: {chart_type}")
            
            chart_schema = chart_result.get('chart_schema', {})
            reasoning = chart_result.get('reasoning', '')
            
            # Log chart generation decision
            self.logger.info(f"Chart generation decision - Type: {chart_type}, Reasoning: {reasoning[:100]}..." if len(reasoning) > 100 else f"Chart generation decision - Type: {chart_type}, Reasoning: {reasoning}")
            
            # Extract alternative visualization queries if available
            alternative_visualization_queries = chart_result.get('alternative_visualization_queries', [])
            self.logger.info(f"Found {len(alternative_visualization_queries)} alternative visualization queries")
            
            # Check for special mark types and handle them correctly
            if 'mark' in chart_schema:
                mark = chart_schema['mark']
                if isinstance(mark, str) and mark.lower() == 'arc':
                    self.logger.info(f"Chart schema has 'arc' mark type. Setting chart_type to 'pie'.")
                    chart_type = 'pie'
                elif isinstance(mark, dict) and mark.get('type', '').lower() == 'arc':
                    self.logger.info(f"Chart schema has 'arc' mark type. Setting chart_type to 'pie'.")
                    chart_type = 'pie'
            
            # Properly handle grouped_bar and other chart types that need special encoding properties
            if chart_type == 'grouped_bar' and 'encoding' in chart_schema:
                # Make sure we have xOffset in the encoding for grouped bar charts
                if 'xOffset' not in chart_schema['encoding'] and 'color' in chart_schema['encoding']:
                    self.logger.info("Adding xOffset to grouped bar chart encoding")
                    color_field = chart_schema['encoding']['color'].get('field')
                    if color_field:
                        # Use the color field for xOffset as well
                        chart_schema['encoding']['xOffset'] = {
                            'field': color_field,
                            'type': 'nominal'
                        }
                        self.logger.info(f"Added xOffset using color field: {color_field}")
            # Conversely, if we have xOffset in the encoding, make sure the chart type is grouped_bar
            elif 'encoding' in chart_schema and 'xOffset' in chart_schema['encoding'] and chart_type != 'grouped_bar':
                self.logger.info(f"Chart schema has xOffset encoding but chart_type is {chart_type}. Setting to grouped_bar.")
                chart_type = 'grouped_bar'
            
            # Set chart title if not provided
            chart_title = title
            if not chart_title:
                chart_title = f"{chart_type.title()} Chart"
                if query:
                    chart_title = f"Chart for: {query[:50]}..." if len(query) > 50 else f"Chart for: {query}"
            
            # Create chart in repository
            chart_id = await self.chart_repository.create_chart(
                message_id=message_id.hex,
                chart_data=data,
                chart_schema=chart_schema,
                chart_type_from_llm=chart_type,
                user_id=user_id,
                org_id=org_id,
                title=chart_title,
                description=description or reasoning or f"Generated {chart_type} chart",
                visibility=visibility,
                alternative_visualization_queries=alternative_visualization_queries
            )
            
            # Get the created chart
            chart = await self.chart_repository.get_chart(
                chart_id=chart_id,
                user_id=user_id,
                org_id=org_id
            )
            
            if not chart:
                raise ChartCreationError("Failed to retrieve created chart")
                
            return chart

        except Exception as e:
            self.logger.error(f"Error creating chart: {str(e)}")
            raise e

    def _infer_data_type(self, value):
        """Infer the data type of a value."""
        if isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, str):
            # Try to parse as date
            try:
                datetime.fromisoformat(value.replace('Z', '+00:00'))
                return "date"
            except (ValueError, TypeError):
                pass
            
            # Check if it might be a numeric string
            try:
                float(value)
                return "numeric"
            except (ValueError, TypeError):
                pass
            
            return "string"
        elif value is None:
            return "null"
        else:
            return "object"
    
    async def get_chart(self, chart_id: str, user_id: str, org_id: str) -> Chart:

        try:
            self.logger.info(f"Getting chart {chart_id}")
            
            chart = await self.chart_repository.get_chart(
                chart_id=chart_id,
                user_id=user_id,
                org_id=org_id
            )
            
            if not chart:
                raise ChartNotFoundError(f"Chart with ID {chart_id} not found or access denied")
                
            return chart
            
        except ChartNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Error getting chart {chart_id}: {str(e)}")
            raise
    
    async def get_charts_by_message(self, message_id: UUID, user_id: str, org_id: str) -> List[Chart]:

        # Ensure message_id is a UUID object
        if isinstance(message_id, str):
            message_id = UUID(message_id)

        try:
            self.logger.info(f"Getting charts for message {message_id}")
            
            charts = await self.chart_repository.get_charts_by_message(
                message_id=message_id.hex,
                user_id=user_id,
                org_id=org_id
            )

            # Sort charts by created_at in descending order
            charts.sort(key=lambda x: x.created_at.replace(tzinfo=None) if x.created_at.tzinfo else x.created_at, reverse=True)            
            
            return charts
            
        except Exception as e:
            self.logger.error(f"Error getting charts for message {message_id}: {str(e)}")
            raise
    
    async def list_charts(
        self, user_id: str, org_id: str, limit: int = 20, offset: int = 0 ) -> Tuple[List[Chart], int]:

        try:
            self.logger.info(f"Listing charts for user {user_id}")
            
            charts, total = await self.chart_repository.list_charts(
                user_id=user_id,
                org_id=org_id,
                limit=limit,
                offset=offset
            )
            
            return charts, total
            
        except Exception as e:
            self.logger.error(f"Error listing charts: {str(e)}")
            raise
    
    async def update_chart(self, chart_id: str, user_id: str,org_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        visibility: Optional[ChartVisibility] = None
    ) -> Chart:

        try:
            self.logger.info(f"Updating chart {chart_id}")
            
            # Build update data
            update_data = {}
            if title is not None:
                update_data['title'] = title
            if description is not None:
                update_data['description'] = description
            if visibility is not None:
                update_data['visibility'] = visibility.value
                
            if not update_data:
                # Nothing to update
                return await self.get_chart(chart_id, user_id, org_id)
            
            # Update chart
            updated_chart = await self.chart_repository.update_chart(
                chart_id=chart_id,
                user_id=user_id,
                update_data=update_data
            )
            
            if not updated_chart:
                raise ChartNotFoundError(f"Chart with ID {chart_id} not found or access denied")
                
            return updated_chart
            
        except ChartNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Error updating chart {chart_id}: {str(e)}")
            raise ChartUpdateError(f"Failed to update chart: {str(e)}")
    
    async def adjust_chart(self, chart_id: str, user_id: str, org_id: str, adjustment_options: Dict[str, Any]) -> Chart:

        self.logger.info(f"Adjusting chart {chart_id} with options: {adjustment_options}")
        
        try:
            # Get the original chart
            original_chart = await self.get_chart(
                chart_id=chart_id,
                user_id=user_id,
                org_id=org_id
            )
            
            if not original_chart:
                raise ChartNotFoundError(f"Chart not found: {chart_id}")
                
            # Get the message associated with the chart to access the data
            message_id = original_chart.message_id
            if not message_id:
                raise InvalidAdjustmentError("No message associated with this chart")
                
            # Extract current chart schema
            current_schema = original_chart.chart_schema
            if not current_schema:
                raise InvalidAdjustmentError("No chart schema available to adjust")
                
            # Log current chart details for debugging
            self.logger.info(f"Current chart type: {original_chart.chart_type}")
            
            # Log alternative visualizations if available
            if hasattr(original_chart, 'alternative_visualizations') and original_chart.alternative_visualizations:
                self.logger.info(f"Original chart has {len(original_chart.alternative_visualizations)} alternative visualizations")
                alt_types = []
                for alt in original_chart.alternative_visualizations:
                    if isinstance(alt, dict) and 'chart_type' in alt:
                        alt_types.append(alt['chart_type'])
                if alt_types:
                    self.logger.info(f"Alternative visualization types: {alt_types}")
            
            # Create a history entry before adjustment
            history_id = await self.chart_repository.create_chart_history(
                chart_id=chart_id,
                chart_data=original_chart.chart_data,
                chart_schema=original_chart.chart_schema,
                modified_by=user_id
            )
            self.logger.info(f"Created chart history entry {history_id} before adjustment")
            
            # Extract current available adjustments
            available_adjustments = {}
            current_settings = {}
            
            if hasattr(original_chart, 'available_adjustments') and original_chart.available_adjustments:
                # Make a deep copy of the original adjustments to preserve them
                import copy
                available_adjustments = copy.deepcopy(original_chart.available_adjustments)
                
                # Store original current_settings for potential restoration later
                if 'current_settings' in available_adjustments:
                    current_settings = copy.deepcopy(available_adjustments['current_settings'])
                
            # Get chart data
            chart_data = original_chart.chart_data
            
            # Prepare for adjustment
            data_len = len(chart_data) if chart_data else 0
            columns_count = len(chart_data[0].keys()) if data_len > 0 else 0
            self.logger.info(f"Adjusting chart with {data_len} data points and {columns_count} columns")
            
            # Get columns information
            columns = []
            if data_len > 0:
                sample_row = chart_data[0]
                for col_name, value in sample_row.items():
                    data_type = self._infer_data_type(value)
                    columns.append({
                        "name": col_name,
                        "data_type": data_type
                    })
            
            # Get new chart type from adjustment options - FIXED to handle ChartAdjustmentOption object
            new_chart_type = adjustment_options.chart_type if hasattr(adjustment_options, 'chart_type') else None
            
            # Adjust chart through chart generation service
            adjustment_result = await self.chart_generation_service.adjust_chart(
                original_schema=current_schema,
                data=chart_data, 
                columns=columns,
                adjustment_options=adjustment_options
            )
            
            # Check if adjustment was successful
            adjustment_successful = True
            
            # If chart schema is empty, adjustment failed
            if not adjustment_result.get("chart_schema"):
                self.logger.warning("Chart adjustment was rejected - empty chart schema returned")
                self.logger.info("DEBUG FIX: Adjustment FAILED - detected empty chart schema")
                print("***** CHART ADJUSTMENT FIX: Detected empty chart schema, preserving original settings *****")
                adjustment_successful = False
            
            # If chart_type is empty, adjustment failed  
            if not adjustment_result.get("chart_type"):
                self.logger.info(f"New chart type from adjustment: {adjustment_result.get('chart_type', '')}")
                self.logger.info("DEBUG FIX: Adjustment FAILED - empty chart type")
                print("***** CHART ADJUSTMENT FIX: Detected empty chart type, preserving original settings *****")
                adjustment_successful = False
            
            # ==========================================
            # KEY FIX: Handle failed adjustments properly
            # ==========================================
            if not adjustment_successful:
                # Restore the original current_settings if adjustment failed
                if 'current_settings' in available_adjustments:
                    self.logger.info(f"Adjustment was rejected, keeping original settings")
                    self.logger.info(f"DEBUG FIX: Restoring original settings: {current_settings}")
                    print(f"***** CHART ADJUSTMENT FIX: Adjustment FAILED - restoring original settings {current_settings} *****")
                    available_adjustments['current_settings'] = current_settings
            else:
                # Adjustment successful - update current settings
                if 'current_settings' not in available_adjustments:
                    available_adjustments['current_settings'] = {}
                
                # Update settings with new values from adjustment options - FIXED to handle ChartAdjustmentOption
                fields_to_check = ["chart_type", "x_axis", "y_axis", "color", "x_offset", "column", "theta"]
                for field in fields_to_check:
                    if hasattr(adjustment_options, field):
                        value = getattr(adjustment_options, field)
                        if value is not None:
                            available_adjustments['current_settings'][field] = value
            
            # ==========================================
            
            # Process adjustment result
            chart_type = adjustment_result.get('chart_type', original_chart.chart_type)
            chart_schema = adjustment_result.get('chart_schema', {})
            
            # Extract alternative visualizations if available
            alt_visualizations = []
            if "alternative_visualizations" in adjustment_result and adjustment_result["alternative_visualizations"]:
                try:
                    alt_vis_raw = adjustment_result["alternative_visualizations"]
                    self.logger.info(f"Found {len(alt_vis_raw)} alternative visualizations in adjustment result")
                    
                    # Process alternative visualizations
                    for alt_viz in alt_vis_raw:
                        viz_dict = {}
                        # Extract chart_type
                        if hasattr(alt_viz, 'chart_type'):
                            viz_dict['chart_type'] = alt_viz.chart_type
                        elif isinstance(alt_viz, dict) and 'chart_type' in alt_viz:
                            viz_dict['chart_type'] = alt_viz['chart_type']
                        
                        # Extract description
                        if hasattr(alt_viz, 'description'):
                            viz_dict['description'] = alt_viz.description
                        elif isinstance(alt_viz, dict) and 'description' in alt_viz:
                            viz_dict['description'] = alt_viz['description']
                        
                        # Extract and convert field_mappings to dictionary
                        fm_dict = {}
                        if hasattr(alt_viz, 'field_mappings'):
                            fm = alt_viz.field_mappings
                            # Extract all field mapping properties
                            for field in ['x_axis', 'y_axis', 'color', 'theta', 'column', 'tooltip']:
                                if hasattr(fm, field) and getattr(fm, field) is not None:
                                    fm_dict[field] = getattr(fm, field)
                        elif isinstance(alt_viz, dict) and 'field_mappings' in alt_viz:
                            fm = alt_viz['field_mappings']
                            if isinstance(fm, dict):
                                fm_dict = fm
                            else:
                                # Extract all field mapping properties
                                for field in ['x_axis', 'y_axis', 'color', 'theta', 'column', 'tooltip']:
                                    if hasattr(fm, field) and getattr(fm, field) is not None:
                                        fm_dict[field] = getattr(fm, field)
                        
                        viz_dict['field_mappings'] = fm_dict
                        alt_visualizations.append(viz_dict)
                        self.logger.info(f"Converted alternative visualization to serializable dict: {viz_dict.keys()}")
                except Exception as e:
                    self.logger.error(f"Error processing alternative visualizations: {str(e)}", exc_info=True)
                
                # Log for debugging
                alt_vis_types = [av.get('chart_type', 'unknown') for av in alt_visualizations if isinstance(av, dict)]
                self.logger.info(f"Alternative visualization types: {alt_vis_types}")
            else:
                self.logger.info("No alternative visualizations found in adjustment result")
                
            # Incorporate alternative visualizations into available_adjustments
            if alt_visualizations:
                available_adjustments["alternative_visualizations"] = alt_visualizations
                self.logger.info(f"Added {len(alt_visualizations)} alternative visualizations to available_adjustments")
            else:
                # Preserve original alternative visualizations if available
                if hasattr(original_chart, 'alternative_visualizations') and original_chart.alternative_visualizations:
                    available_adjustments["alternative_visualizations"] = original_chart.alternative_visualizations
                    self.logger.info(f"Preserved {len(original_chart.alternative_visualizations)} existing alternative visualizations")
            
            # Update the chart with new data
            if chart_schema:
                # Handle arc mark type (pie charts)
                if 'mark' in chart_schema:
                    mark = chart_schema['mark']
                    if isinstance(mark, str) and mark.lower() == 'arc':
                        self.logger.info("Detected 'arc' mark type in adjustment result, mapping to 'pie' chart type")
                        chart_type = 'pie'
                    elif isinstance(mark, dict) and mark.get('type', '').lower() == 'arc':
                        self.logger.info("Detected 'arc' mark type in adjustment result, mapping to 'pie' chart type")
                        chart_type = 'pie'
            
            # Update chart in repository
            updated_chart = await self.chart_repository.update_chart_data(
                chart_id=chart_id,
                user_id=user_id,
                chart_data=chart_data,
                chart_schema=chart_schema,
                available_adjustments=available_adjustments,
                chart_type=chart_type,
                alternative_visualizations=alt_visualizations if alt_visualizations else None
            )
            
            if not updated_chart:
                raise ChartUpdateError(f"Failed to update chart {chart_id}")
            
            return updated_chart
        
        except Exception as e:
            self.logger.error(f"Error adjusting chart {chart_id}: {str(e)}", exc_info=True)
            raise ChartUpdateError(f"Error adjusting chart: {str(e)}")
    
    async def refresh_chart(self, chart_id: str, user_id: str, org_id: str) -> Chart:

        try:
            self.logger.info(f"Refreshing chart {chart_id}")
            
            # Get chart
            chart = await self.get_chart(chart_id, user_id, org_id)
            if not chart:
                raise ChartNotFoundError(f"Chart with ID {chart_id} not found or access denied")
            
            # Get message to get the original code
            message_id = chart.message_id
            message = await self.chat_service.get_message(user_id=user_id, message_id=message_id)
            if not message:
                raise MessageNotFoundError(f"Message with ID {message_id} not found")
            
            # Extract artifacts from message
            artifacts = message.artifacts
            parsed_artifacts = self.code_executor_service.parse_message_artifacts(artifacts)
            
            # Check if we have code to re-execute
            if not parsed_artifacts['code'] or not parsed_artifacts['code_type']:
                raise ChartRefreshError("No code available to refresh chart data")
            
            # Create history entry for previous version
            await self.chart_repository.create_chart_history(
                chart_id=chart_id,
                chart_data=chart.chart_data,
                chart_schema=chart.chart_schema,
                modified_by=user_id
            )
            
            # Re-execute code based on type
            code_type = parsed_artifacts['code_type'].lower()
            new_data = []
            error_message = None
            
            if code_type == 'sql':
                # Get database ID if available
                database_id = None
                if parsed_artifacts['metadata'] and 'data_source' in parsed_artifacts['metadata']:
                    database_id = parsed_artifacts['metadata']['data_source'].get('id')
                
                # Execute SQL
                new_data, error_message = await self.code_executor_service.execute_sql(
                    sql=parsed_artifacts['code'],
                    database_id=database_id
                )
                
            elif code_type in ['python', 'py']:
                # Execute Python
                new_data, error_message = await self.code_executor_service.execute_python(
                    code=parsed_artifacts['code']
                )
                
            else:
                raise ChartRefreshError(f"Unsupported code type: {code_type}")
                
            if error_message:
                raise ChartRefreshError(f"Error executing code: {error_message}")
                
            if not new_data:
                raise ChartRefreshError("Code execution returned no data")
            
            # Update chart with new data
            updated_chart = await self.chart_repository.update_chart_data(
                chart_id=chart_id,
                user_id=user_id,
                chart_data=new_data
            )
            
            if not updated_chart:
                raise ChartRefreshError(f"Failed to update chart with ID {chart_id}")
                
            return updated_chart
            
        except (ChartNotFoundError, MessageNotFoundError, ChartRefreshError):
            raise
        except Exception as e:
            self.logger.error(f"Error refreshing chart {chart_id}: {str(e)}")
            raise ChartRefreshError(f"Failed to refresh chart: {str(e)}")
    
    async def get_chart_history(
        self,
        chart_id: str,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[ChartHistory], int]:

        try:
            self.logger.info(f"Getting history for chart {chart_id}")
            
            history, total = await self.chart_repository.get_chart_history(
                chart_id=chart_id,
                user_id=user_id,
                limit=limit,
                offset=offset
            )
            
            return history, total
            
        except ChartAccessDeniedError:
            raise
        except Exception as e:
            self.logger.error(f"Error getting history for chart {chart_id}: {str(e)}")
            raise e
    
    async def delete_chart(self, chart_id: str, user_id: str) -> bool:

        try:
            self.logger.info(f"Deleting chart {chart_id}")
            
            success = await self.chart_repository.delete_chart(
                chart_id=chart_id,
                user_id=user_id
            )
            
            if not success:
                raise ChartNotFoundError(f"Chart with ID {chart_id} not found or access denied")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting chart {chart_id}: {str(e)}")
            raise

    def _calculate_available_field_mappings(self, data: List[Dict[str, Any]], columns: List[Dict[str, Any]], current_schema: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Calculate available field mappings for chart adjustments based on data types.
        
        Returns a dictionary with available chart types and field mappings for different encoding channels.
        Also includes recommended combinations and current settings.
        """
        if not data or not columns:
            self.logger.warning("Cannot calculate field mappings: empty data or columns")
            return {}
        
        # Initialize the structure with empty chart_types to be populated based on data structure
        available_adjustments = {
            "chart_types": [],
            "field_mappings": {
                "x_axis": [],
                "y_axis": [],
                "color": [],
                "theta": [],
                "x_offset": []
            },
            "recommended_combinations": [],
            "current_settings": {}
        }
        
        # Extract current settings if available
        if current_schema:
            try:
                current_settings = {
                    "chart_type": current_schema.get("mark", "")
                }
                
                # Extract current encodings
                if "encoding" in current_schema:
                    encodings = current_schema["encoding"]
                    if "x" in encodings and "field" in encodings["x"]:
                        current_settings["x_axis"] = encodings["x"]["field"]
                    if "y" in encodings and "field" in encodings["y"]:
                        current_settings["y_axis"] = encodings["y"]["field"]
                    if "color" in encodings and "field" in encodings["color"]:
                        current_settings["color"] = encodings["color"]["field"]
                    if "theta" in encodings and "field" in encodings["theta"]:
                        current_settings["theta"] = encodings["theta"]["field"]
                    if "column" in encodings and "field" in encodings["column"]:
                        current_settings["x_offset"] = encodings["column"]["field"]
                
                available_adjustments["current_settings"] = current_settings
            except Exception as e:
                self.logger.warning(f"Failed to extract current settings: {e}")
        
        # Categorize columns by data type
        numeric_fields = []
        categorical_fields = []
        temporal_fields = []
        
        for col in columns:
            col_name = col.get("name")
            data_type = col.get("data_type", "").lower()
            
            # Also check for type field which might be used instead of data_type
            if not data_type and "type" in col:
                data_type = col.get("type", "").lower()
            
            self.logger.info(f"Field {col_name} has data_type: {data_type}")
            
            if not col_name:
                continue
                
            # Categorize fields - expanded to include more numeric type variations
            if (data_type in ["integer", "float", "number", "numeric", "decimal", "double", "real"] or 
                "float" in data_type or "int" in data_type or "num" in data_type):
                numeric_fields.append(col_name)
                available_adjustments["field_mappings"]["y_axis"].append(col_name)
                available_adjustments["field_mappings"]["theta"].append(col_name)
                self.logger.info(f"Added {col_name} as numeric field for y_axis and theta")
            elif data_type in ["date", "datetime", "timestamp", "time"]:
                temporal_fields.append(col_name)
                available_adjustments["field_mappings"]["x_axis"].append(col_name)
            else:  # Treat as categorical
                categorical_fields.append(col_name)
                available_adjustments["field_mappings"]["x_axis"].append(col_name)
                available_adjustments["field_mappings"]["color"].append(col_name)
                available_adjustments["field_mappings"]["x_offset"].append(col_name)
        
        # All fields can potentially be used for color
        available_adjustments["field_mappings"]["color"].extend(numeric_fields)
        available_adjustments["field_mappings"]["color"].extend(temporal_fields)
        
        # Generate recommended combinations
        self._generate_recommended_combinations(
            available_adjustments,
            numeric_fields,
            categorical_fields,
            temporal_fields
        )
        
        # Populate chart_types based on data characteristics
        # Basic chart types that work with most data structures
        available_adjustments["chart_types"].append("bar")
        available_adjustments["chart_types"].append("line")
        
        # Pie charts require one numeric and one categorical field
        if len(numeric_fields) > 0 and len(categorical_fields) > 0:
            available_adjustments["chart_types"].append("pie")
        
        # Stacked/grouped bar charts require at least 2 categorical fields and 1 numeric field
        if len(categorical_fields) >= 2 and len(numeric_fields) > 0:
            available_adjustments["chart_types"].append("grouped_bar")
            available_adjustments["chart_types"].append("stacked_bar")
        
        # Multi-line and area charts typically need temporal or categorical data with multiple series
        if (len(temporal_fields) > 0 or len(categorical_fields) > 0) and len(numeric_fields) > 0:
            available_adjustments["chart_types"].append("area")
            
            # Multi-line charts typically need multiple series to be useful
            if len(categorical_fields) >= 2 or len(numeric_fields) >= 2:
                available_adjustments["chart_types"].append("multi_line")
        
        # Ensure the current chart type is included in available types
        if current_schema and "mark" in current_schema:
            current_type = current_schema.get("mark", "")
            if current_type and current_type not in available_adjustments["chart_types"]:
                available_adjustments["chart_types"].append(current_type)
                self.logger.info(f"Added current chart type {current_type} to available types")
        
        return available_adjustments

    def _generate_recommended_combinations(self, available_adjustments: Dict[str, Any], numeric_fields: List[str],
                                           categorical_fields: List[str], temporal_fields: List[str]) -> None:
        """Generate recommended combinations of chart types and field mappings."""
        recommendations = []
        
        if numeric_fields and categorical_fields:
            # Bar chart: Categorical on x, numeric on y
            if len(categorical_fields) > 0 and len(numeric_fields) > 0:
                recommendations.append({
                    "chart_type": "bar",
                    "x_axis": categorical_fields[0],
                    "y_axis": numeric_fields[0],
                    "description": f"Bar chart showing {numeric_fields[0]} by {categorical_fields[0]}"
                })
            
            # Pie chart: Numeric for theta, categorical for color
            if len(categorical_fields) > 0 and len(numeric_fields) > 0:
                recommendations.append({
                    "chart_type": "pie",
                    "theta": numeric_fields[0],
                    "color": categorical_fields[0],
                    "description": f"Pie chart showing distribution of {numeric_fields[0]} across {categorical_fields[0]}"
                })
        
        if temporal_fields and numeric_fields:
            # Line chart: Temporal on x, numeric on y
            recommendations.append({
                "chart_type": "line",
                "x_axis": temporal_fields[0],
                "y_axis": numeric_fields[0],
                "description": f"Line chart showing {numeric_fields[0]} over time"
            })
        
        if len(numeric_fields) >= 2 and categorical_fields:
            # Scatter plot could be another option
            recommendations.append({
                "chart_type": "point",
                "x_axis": numeric_fields[0],
                "y_axis": numeric_fields[1],
                "color": categorical_fields[0] if categorical_fields else None,
                "description": f"Scatter plot comparing {numeric_fields[0]} vs {numeric_fields[1]}"
            })
        
        if categorical_fields and len(categorical_fields) >= 2 and numeric_fields:
            # Grouped bar chart: Primary categorical on x, secondary for color
            recommendations.append({
                "chart_type": "grouped_bar",
                "x_axis": categorical_fields[0],
                "y_axis": numeric_fields[0],
                "x_offset": categorical_fields[1],
                "description": f"Grouped bar chart showing {numeric_fields[0]} by {categorical_fields[0]} and {categorical_fields[1]}"
            })
        
        available_adjustments["recommended_combinations"] = recommendations 

    # NOTE: This is not used right now, might be useful if we want to use previous chart data for adjustments
    async def get_latest_chart_by_message(self, message_id: UUID, user_id:str, org_id:str ) -> Optional[Chart]:

        # Ensure message_id is a UUID object
        if isinstance(message_id, str):
            message_id = UUID(message_id)

        try:
            self.logger.info(f"Getting latest chart for message {message_id}")
            
            charts = await self.get_charts_by_message(
                message_id=message_id,
                user_id=user_id,
                org_id=org_id
            )
            
            # Return the first chart (latest) or None if no charts exist
            return charts[0] if charts else None
            
        except Exception as e:
            self.logger.error(f"Error getting latest chart for message {message_id}: {str(e)}")
            raise e