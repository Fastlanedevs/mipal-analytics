"""
Chart model for Neo4j database schema representation.
"""
from typing import Dict, Any, Optional
from datetime import datetime
from neomodel import (
    StructuredNode, StringProperty, RelationshipTo, RelationshipFrom,
    ZeroOrMore, One, JSONProperty, BooleanProperty, IntegerProperty, UniqueIdProperty
)
from pkg.log.logger import get_logger

# Initialize logger
logger = get_logger("chart_model")


class Chart(StructuredNode):
    """Node representing a chart"""
    uid = UniqueIdProperty()  # Unique identifier for the chart
    title = StringProperty(required=True, index=True)
    description = StringProperty(default="")
    chart_type = StringProperty(required=True)  # Type of chart (e.g., 'bar', 'line', 'pie')
    config = JSONProperty(default={})  # Chart configuration as JSON
    chart_data = JSONProperty(default={})  # Chart data as JSON
    
    # Relationships
    dashboards = RelationshipFrom('app.analytics.repository.schema.models.dashboard.Dashboard', 'CONTAINS_CHART', cardinality=ZeroOrMore)
    
    # Metadata
    created_by = StringProperty(required=True, index=True)  # Owner of the chart
    org_id = StringProperty(index=True)  # Organization this chart belongs to
    message_id = StringProperty(index=True)  # Message this chart belongs to
    is_deleted = BooleanProperty(default=False)
    created_at = StringProperty(required=True)  # ISO format datetime
    updated_at = StringProperty(required=True)  # ISO format datetime
    
    def __init__(self, *args, **kwargs):
        """Initialize chart node with automatic timestamps"""
        if 'created_at' not in kwargs:
            kwargs['created_at'] = datetime.utcnow().isoformat()
        if 'updated_at' not in kwargs:
            kwargs['updated_at'] = datetime.utcnow().isoformat()
            
        super().__init__(*args, **kwargs)
    
    @staticmethod
    def create_chart(
        title: str,
        user_id: str,
        chart_type: str,
        org_id: Optional[str] = None,
        description: str = "",
        config: Dict = None,
        data: Dict = None
    ) -> 'Chart':
        """Create a new chart"""
        now = datetime.utcnow().isoformat()
        
        return Chart(
            title=title,
            description=description,
            chart_type=chart_type,
            config=config or {},
            data=data or {},
            user_id=user_id,
            org_id=org_id,
            created_at=now,
            updated_at=now,
            is_deleted=False
        ).save()
    
    def update(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        chart_type: Optional[str] = None,
        config: Optional[Dict] = None,
        chart_data: Optional[Dict] = None
    ) -> 'Chart':
        """Update chart properties"""
        if title is not None:
            self.title = title
        
        if description is not None:
            self.description = description
            
        if chart_type is not None:
            self.chart_type = chart_type
            
        if config is not None:
            self.config = config
            
        if chart_data is not None:
            self.chart_data = chart_data
            
        self.updated_at = datetime.utcnow().isoformat()
        self.save()
        return self
    
    def soft_delete(self):
        """Soft delete this chart"""
        self.is_deleted = True
        self.updated_at = datetime.utcnow().isoformat()
        self.save()
        return self
    
    def restore(self):
        """Restore a soft-deleted chart"""
        self.is_deleted = False
        self.updated_at = datetime.utcnow().isoformat()
        self.save()
        return self 