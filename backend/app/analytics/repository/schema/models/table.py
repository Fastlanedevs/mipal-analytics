"""
Table model for Neo4j database schema representation.
"""
from typing import Dict, Any, Optional, List
from neomodel import (
    StructuredNode, StringProperty, RelationshipTo, RelationshipFrom,
    ZeroOrMore, One, JSONProperty, BooleanProperty, IntegerProperty, UniqueIdProperty
)
from app.analytics.repository.schema.models.relationships import ForeignKeyRel, SharedColumnRel
from pkg.log.logger import get_logger

# Initialize logger
logger = get_logger("table_model")

class Table(StructuredNode):
    """Node representing a database table"""
    uid = UniqueIdProperty()  # Add UID
    name = StringProperty(required=True, index=True)  # Table name within its own database - NOT unique globally
    database_uid = StringProperty(index=True)  # Store the parent database's UID 
    full_name = StringProperty(index=True)  # Not unique anymore, just indexed for search
    unique_key = StringProperty(unique_index=True)  # Compound key: database_uid + name
    description = StringProperty(default="")
    embedding = JSONProperty(default=[])  # Store table embedding as JSON array for semantic search
    schema = StringProperty(required=True)  # The schema this table belongs to (e.g., 'public')
    storage_url = StringProperty(default="")  # S3 URL for CSV files
    storage_bucket = StringProperty(default="")  # S3 bucket name
    storage_path = StringProperty(default="")  # S3 object path
    row_count = IntegerProperty(default=0)  # Store number of rows
    last_updated = StringProperty()  # ISO format datetime of last update
    is_deleted = BooleanProperty(default=False)  # Add is_deleted field
    
    # Relationships
    columns = RelationshipTo('app.analytics.repository.schema.models.column.Column', 'HAS_COLUMN', cardinality=ZeroOrMore)
    foreign_keys = RelationshipTo('Table', 'FOREIGN_KEY', model=ForeignKeyRel, cardinality=ZeroOrMore)
    relates_to = RelationshipTo('Table', 'RELATED_TO', model=SharedColumnRel, cardinality=ZeroOrMore)
    database = RelationshipFrom('app.analytics.repository.schema.models.database.Database', 'HAS_TABLE', cardinality=One)

    def get_or_create_column(self, name: str, data_type: str, **kwargs):
        """Get existing column or create new one"""
        # Import here to avoid circular imports
        from app.analytics.repository.schema.models.column import Column
        
        # Create a unique name that includes database_uid for isolation
        unique_name = f"{self.database_uid}:{self.name}.{name}"
        
        try:
            # First try to find by unique_name
            column = Column.nodes.get(unique_name=unique_name)
            
            # Update properties if provided
            updated = False
            if 'is_primary_key' in kwargs and column.is_primary_key != kwargs['is_primary_key']:
                column.is_primary_key = kwargs['is_primary_key']
                updated = True
                
            if 'is_nullable' in kwargs and column.is_nullable != kwargs['is_nullable']:
                column.is_nullable = kwargs['is_nullable']
                updated = True
                
            if 'description' in kwargs and column.description != kwargs['description']:
                column.description = kwargs['description']
                updated = True
                
            if 'default' in kwargs and column.default != kwargs['default']:
                column.default = kwargs['default']
                updated = True
                
            if updated:
                column.save()
                
            return column
            
        except Column.DoesNotExist:
            # If not found, create a new column
            # Ensure database_uid is set
            kwargs['database_uid'] = self.database_uid
            kwargs['table_uid'] = self.uid
            kwargs['table_name'] = self.name
            
            column = Column(
                name=name,
                data_type=data_type,
                unique_name=unique_name,
                **kwargs
            ).save()
            
            # Connect column to this table
            self.columns.connect(column)
            
            return column

    def add_foreign_key(self, target_table: 'Table', source_column: str, target_column: str, rel_type: str = 'ONE_TO_MANY'):
        """Add a foreign key relationship to another table"""
        # Validate relationship type
        valid_types = ['ONE_TO_ONE', 'ONE_TO_MANY', 'MANY_TO_MANY']
        if rel_type not in valid_types:
            raise ValueError(f"Invalid relationship type: {rel_type}. Must be one of {valid_types}")
            
        # Log the relationship being added
        logger.info(f"Adding relationship: {self.name}.{source_column} -> {target_table.name}.{target_column} [{rel_type}]")
        
        # First, find the source column in this table
        source_col = None
        for col in self.columns.all():
            if col.name == source_column:
                source_col = col
                break
                
        if not source_col:
            raise ValueError(f"Source column '{source_column}' not found in table '{self.name}'")
            
        # Next, find the target column in the target table
        target_col = None
        for col in target_table.columns.all():
            if col.name == target_column:
                target_col = col
                break
                
        if not target_col:
            raise ValueError(f"Target column '{target_column}' not found in table '{target_table.name}'")
            
        # Update source column's foreign key metadata
        source_col.is_foreign_key = True
        source_col.references_table = target_table.name
        source_col.references_column = target_column
        source_col.save()
        
        # Add a REFERENCES relationship between the columns
        try:
            source_col.references.connect(target_col)
        except Exception as e:
            logger.warning(f"Could not connect columns with REFERENCES relationship: {e}")
        
        # Check if relationship already exists
        for rel in self.foreign_keys.all():
            try:
                target = rel.end_node()
                props = rel.properties()
                if (target.uid == target_table.uid and 
                    props.get('from_column') == source_column and 
                    props.get('to_column') == target_column):
                    # Relationship already exists, update it
                    rel.type = rel_type
                    return rel
            except Exception as e:
                logger.warning(f"Error checking existing relationship: {e}")
        
        # Create the relationship if it doesn't exist
        try:
            rel = self.foreign_keys.connect(
                target_table,
                {
                    'type': rel_type,
                    'from_column': source_column,
                    'to_column': target_column
                }
            )
            logger.info(f"Added relationship: {self.name}.{source_column} -> {target_table.name}.{target_column} [{rel_type}]")
            return rel
        except Exception as e:
            logger.error(f"Error adding foreign key relationship: {e}")
            raise
            
    def add_shared_column_relationship(self, target_table: 'Table', shared_column: str):
        """Add a shared column relationship to another table"""
        # Find the specified column in this table
        source_col = None
        for col in self.columns.all():
            if col.name == shared_column:
                source_col = col
                break
                
        if not source_col:
            raise ValueError(f"Column '{shared_column}' not found in table '{self.name}'")
            
        # Find a column with the same name in the target table
        target_col = None
        for col in target_table.columns.all():
            if col.name == shared_column:
                target_col = col
                break
                
        if not target_col:
            raise ValueError(f"Column '{shared_column}' not found in target table '{target_table.name}'")
            
        # Create a RELATED_TO relationship via the shared column
        try:
            rel = self.relates_to.connect(
                target_table,
                {'via': shared_column}
            )
            logger.info(f"Added RELATED_TO relationship: {self.name} -> {target_table.name} via {shared_column}")
            return rel
        except Exception as e:
            logger.error(f"Error adding RELATED_TO relationship: {e}")
            raise
            
    def add_many_to_many_relationship(self, target_table: 'Table', junction_table: 'Table',
                                     source_junction_column: str, target_junction_column: str) -> ForeignKeyRel:
        """Add a many-to-many relationship using a junction table"""
        # Validate that the junction table has the required columns
        source_col_exists = False
        target_col_exists = False
        
        for col in junction_table.columns.all():
            if col.name == source_junction_column:
                source_col_exists = True
            if col.name == target_junction_column:
                target_col_exists = True
                
        if not source_col_exists:
            raise ValueError(f"Source junction column '{source_junction_column}' not found in table '{junction_table.name}'")
            
        if not target_col_exists:
            raise ValueError(f"Target junction column '{target_junction_column}' not found in table '{junction_table.name}'")
            
        # Create the many-to-many relationship
        try:
            rel = self.foreign_keys.connect(
                target_table,
                {
                    'type': 'MANY_TO_MANY',
                    'from_column': source_junction_column,
                    'to_column': target_junction_column,
                    'junction_table': junction_table.name,
                    'junction_source_column': source_junction_column,
                    'junction_target_column': target_junction_column
                }
            )
            logger.info(f"Added MANY_TO_MANY relationship: {self.name} <-> {target_table.name} via {junction_table.name}")
            return rel
        except Exception as e:
            logger.error(f"Error adding MANY_TO_MANY relationship: {e}")
            raise
            
    def preserve_relationships(self):
        """Save all relationships into metadata that can be restored later"""
        logger.info(f"Preserving relationships for table {self.name}")
        
        try:
            # Save foreign key relationships
            fk_relationships = []
            for rel in self.foreign_keys.all():
                target_table = rel.end_node()
                props = rel.properties()
                
                fk_relationships.append({
                    'target_table': target_table.name,
                    'target_uid': target_table.uid,
                    'from_column': props.get('from_column'),
                    'to_column': props.get('to_column'),
                    'type': props.get('type', 'ONE_TO_MANY'),
                    'junction_table': props.get('junction_table'),
                    'junction_source_column': props.get('junction_source_column'),
                    'junction_target_column': props.get('junction_target_column')
                })
                
                # Also preserve foreign key info at the column level
                source_column = props.get('from_column')
                for col in self.columns.all():
                    if col.name == source_column:
                        col.is_foreign_key = True
                        col.references_table = target_table.name
                        col.references_column = props.get('to_column')
                        col.save()
                        logger.info(f"Preserved column FK info: {source_column} -> {target_table.name}.{props.get('to_column')}")
                        break
                        
            # Store the preserved relationships as metadata on the table
            self._preserved_relationships = fk_relationships
            
            # Clear the actual relationships to avoid duplicate keys
            for rel in self.foreign_keys.all():
                self.foreign_keys.disconnect(rel.end_node())
                
            logger.info(f"Preserved and cleared {len(fk_relationships)} relationships for table {self.name}")
            
            return fk_relationships
        except Exception as e:
            logger.error(f"Error preserving relationships for table {self.name}: {str(e)}")
            return []
            
    def restore_relationships(self, database: 'Database'):
        """Restore all relationships from preserved metadata"""
        logger.info(f"Restoring relationships for table {self.name}")
        
        if not hasattr(self, '_preserved_relationships') or not self._preserved_relationships:
            logger.info(f"No preserved relationships found for table {self.name}")
            return 0
            
        fk_relationships = self._preserved_relationships
        logger.info(f"Restoring {len(fk_relationships)} foreign key relationships for table {self.name}")
        
        restored_count = 0
        
        for rel_data in fk_relationships:
            try:
                # Get the target table
                target_table = database.get_table_by_name(rel_data['target_table'])
                
                if not target_table:
                    logger.warning(f"Target table {rel_data['target_table']} not found, cannot restore relationship")
                    continue
                    
                # Restore the relationship
                rel_type = rel_data.get('type', 'ONE_TO_MANY')
                from_column = rel_data['from_column']
                to_column = rel_data['to_column']
                
                logger.info(f"Restoring FK: {self.name}.{from_column} -> {target_table.name}.{to_column} [{rel_type}]")
                
                self.add_foreign_key(
                    target_table,
                    from_column,
                    to_column,
                    rel_type
                )
                
                # Also add a RELATED_TO relationship for better visualization
                try:
                    self.relates_to.connect(target_table, {'via': from_column})
                except Exception as rel_e:
                    logger.warning(f"Error adding RELATED_TO relationship during restore: {str(rel_e)}")
                
                restored_count += 1
                
                # If it's a many-to-many relationship, restore the junction table info
                if rel_type == 'MANY_TO_MANY' and rel_data.get('junction_table'):
                    # Update the relationship with junction table info
                    for rel in self.foreign_keys.all():
                        try:
                            target = rel.end_node()
                            props = rel.properties()
                            if (target.name == target_table.name and 
                                props.get('from_column') == from_column and 
                                props.get('to_column') == to_column):
                                # Update junction table info
                                rel.junction_table = rel_data['junction_table']
                                rel.junction_source_column = rel_data['junction_source_column']
                                rel.junction_target_column = rel_data['junction_target_column']
                                break
                        except Exception as e:
                            logger.warning(f"Error updating junction table info: {e}")
                
            except Exception as e:
                logger.error(f"Error restoring relationship to {rel_data['target_table']}: {str(e)}")
                
        # Now restore column-level foreign key info
        logger.info(f"Restoring {restored_count} column-level foreign keys for table {self.name}")
        for rel_data in fk_relationships:
            from_column = rel_data['from_column']
            for col in self.columns.all():
                if col.name == from_column:
                    if col.is_foreign_key and col.references_table == rel_data['target_table']:
                        logger.info(f"Column FK {from_column} already restored - skipping")
                        continue
                        
                    col.is_foreign_key = True
                    col.references_table = rel_data['target_table']
                    col.references_column = rel_data['to_column']
                    col.save()
                    break
                    
        logger.info(f"Restored {restored_count} relationships for table {self.name}")
        return restored_count
        
    def update_storage_info(self, bucket: str, path: str, url: str | None = None):
        """Update storage information for this table"""
        self.storage_bucket = bucket
        self.storage_path = path
        if url:
            self.storage_url = url
        else:
            # Store a permanent S3 URI instead of a temporary presigned URL
            self.storage_url = f"s3://{bucket}/{path}"
        self.save()
        
    def soft_delete(self):
        """Mark table as deleted instead of physically removing it"""
        self.is_deleted = True
        self.save()
        logger.info(f"Soft deleted table {self.name}")
        
    def restore(self):
        """Restore a soft-deleted table"""
        self.is_deleted = False
        self.save()
        logger.info(f"Restored table {self.name}")
        
    def get_column_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all columns"""
        result = {}
        for col in self.columns.all():
            result[col.name] = col.stats
        return result
