"""
Column model for Neo4j database schema representation.
"""
from typing import Dict, Any, Optional
from neomodel import (
    StructuredNode, StringProperty, RelationshipTo, RelationshipFrom,
    ZeroOrMore, One, JSONProperty, BooleanProperty, UniqueIdProperty
)

class Column(StructuredNode):
    """Node representing a database column"""
    uid = UniqueIdProperty()  # Add UID
    name = StringProperty(required=True)  # Not unique globally, only within table
    data_type = StringProperty(required=True)
    description = StringProperty(default="")
    is_primary_key = BooleanProperty(default=False)
    is_nullable = BooleanProperty(default=True)
    default = StringProperty()  # Add default value property
    database_uid = StringProperty(index=True)  # Reference to parent database UID
    table_uid = StringProperty(index=True)  # Reference to parent table UID
    unique_name = StringProperty(unique_index=True)  # Globally unique identifier
    stats = JSONProperty(default={})  # Store column statistics as JSON
    
    # Foreign key metadata
    is_foreign_key = BooleanProperty(default=False)  # Whether this column is a foreign key
    references_table = StringProperty()  # Name of referenced table
    references_column = StringProperty()  # Name of referenced column
    
    # Relationships
    table = RelationshipFrom('app.analytics.repository.schema.models.table.Table', 'HAS_COLUMN', cardinality=One)
    references = RelationshipTo('Column', 'REFERENCES', cardinality=ZeroOrMore)
    referenced_by = RelationshipFrom('Column', 'REFERENCES', cardinality=ZeroOrMore)
    
    def __init__(self, *args, **kwargs):
        # Extract table_name if provided
        table_name = kwargs.pop('table_name', None)
        super().__init__(*args, **kwargs)
        
        # If table_name is provided, set the unique_name
        if table_name and hasattr(self, 'name'):
            if 'database_uid' in kwargs:
                # Ensure database isolation by prefixing with database_uid
                self.unique_name = f"{kwargs['database_uid']}:{table_name}.{self.name}"
            else:
                # Backwards compatibility - just table_name
                self.unique_name = f"{table_name}.{self.name}"
