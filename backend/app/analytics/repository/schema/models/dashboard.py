"""
Dashboard model for Neo4j database schema representation.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from neomodel import (
    StructuredNode, StringProperty, RelationshipTo, RelationshipFrom,
    ZeroOrMore, One, JSONProperty, BooleanProperty, IntegerProperty, UniqueIdProperty,
    StructuredRel
)
from pkg.log.logger import get_logger

# Initialize logger
logger = get_logger("dashboard_model")


class DashboardAccess(StructuredRel):
    """Relationship representing dashboard access permissions"""
    permission = StringProperty(required=True, choices={'view': 'View Only', 'edit': 'Edit Access'})
    granted_at = StringProperty(default_factory=lambda: datetime.utcnow().isoformat())


class Dashboard(StructuredNode):
    """Node representing a dashboard"""
    dashboard_id = UniqueIdProperty()
    title = StringProperty(required=True, index=True)
    description = StringProperty(default="")
    layout_config = JSONProperty(default={})  # Store layout configuration as JSON
    layouts = JSONProperty(default={})  # Store chart layouts as JSON
    
    # Relationships
    charts = RelationshipTo('app.analytics.repository.schema.models.chart.Chart', 'CONTAINS_CHART', cardinality=ZeroOrMore)
    shared_with = RelationshipTo('app.user.entities.entity.User', 'SHARED_WITH', model=DashboardAccess, cardinality=ZeroOrMore)
    dataframes = RelationshipTo('app.analytics.repository.schema.models.dataframe.Dataframe', 'CONTAINS_DATAFRAME', cardinality=ZeroOrMore)
    
    # Metadata
    user_id = StringProperty(required=True, index=True)  # Owner of the dashboard
    org_id = StringProperty(index=True)  # Organization this dashboard belongs to
    unique_key = StringProperty(unique_index=True)  # Compound key: user_id + title
    is_deleted = BooleanProperty(default=False)
    created_at = StringProperty(required=True)  # ISO format datetime
    updated_at = StringProperty(required=True)  # ISO format datetime
    
    def __init__(self, *args, **kwargs):
        """Initialize dashboard node with automatic timestamps"""
        if 'created_at' not in kwargs:
            kwargs['created_at'] = datetime.utcnow().isoformat()
        if 'updated_at' not in kwargs:
            kwargs['updated_at'] = datetime.utcnow().isoformat()
        if 'user_id' in kwargs and 'title' in kwargs and 'unique_key' not in kwargs:
            kwargs['unique_key'] = f"{kwargs['user_id']}:{kwargs['title']}"
            
        super().__init__(*args, **kwargs)
    
    @staticmethod
    def create_dashboard(title: str, user_id: str, org_id: Optional[str] = None, 
                        description: str = "", layout_config: Dict = None) -> 'Dashboard':
        """Create a new dashboard"""
        now = datetime.utcnow().isoformat()
        
        return Dashboard(
            title=title,
            description=description,
            layout_config=layout_config or {},
            layouts={},
            user_id=user_id,
            org_id=org_id,
            created_at=now,
            updated_at=now,
            is_deleted=False
        ).save()
    
    def update(self, title: Optional[str] = None, description: Optional[str] = None, 
              layout_config: Optional[Dict] = None, layouts: Optional[Dict] = None) -> 'Dashboard':
        """Update dashboard properties"""
        if title is not None:
            self.title = title
            self.unique_key = f"{self.user_id}:{title}"
        
        if description is not None:
            self.description = description
            
        if layout_config is not None:
            self.layout_config = layout_config
            
        if layouts is not None:
            self.layouts = layouts
            
        self.updated_at = datetime.utcnow().isoformat()
        self.save()
        return self
    
    def soft_delete(self):
        """Soft delete this dashboard"""
        self.is_deleted = True
        self.updated_at = datetime.utcnow().isoformat()
        self.save()
        return self
    
    def restore(self):
        """Restore a soft-deleted dashboard"""
        self.is_deleted = False
        self.updated_at = datetime.utcnow().isoformat()
        self.save()
        return self
