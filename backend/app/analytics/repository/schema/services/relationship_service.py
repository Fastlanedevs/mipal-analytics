"""
Service for handling relationship operations in Neo4j schema.
"""
from typing import Dict, List, Any, Optional
from app.analytics.repository.schema.utils import singular_form, plural_form
from pkg.log.logger import get_logger

# Initialize logger
logger = get_logger("relationship_service")

def infer_foreign_key_relationships(database):
    """
    Infer foreign key relationships between tables based on column naming patterns.
    Returns the number of relationships inferred.
    
    Args:
        database: Database object containing tables to analyze
        
    Returns:
        int: Number of relationships inferred
    """
    # Initialize the count
    inferred_count = 0
    
    try:
        # First we need to get all tables
        try:
            tables = list(database.tables.all())
            logger.info(f"[FK Inference] Starting foreign key inference for database {database.name} with {len(tables)} tables")
            logger.info(f"[FK Inference] Tables found: {', '.join([table.name for table in tables])}")
        except Exception as e:
            logger.error(f"[FK Inference] Error getting tables: {str(e)}")
            return 0
            
        if not tables:
            logger.warning(f"[FK Inference] No tables found for database {database.name}")
            return 0
            
        # Create a lookup dictionary for tables
        table_dict = {table.name.lower(): table for table in tables}
        
        # Step 1: Find primary keys for each table
        table_pk = {}
        
        # Create a dict to track all columns by name for direct matching
        column_to_tables = {}
        
        for table in tables:
            # Get all columns for this table
            columns = list(table.columns.all())
            logger.info(f"[FK Inference] Table '{table.name}' has {len(columns)} columns")
            
            # Track primary key(s)
            primary_keys = [col for col in columns if col.is_primary_key]
            
            # If no primary keys found, try to infer them
            if not primary_keys:
                # First, check for a column named 'id'
                id_col = next((col for col in columns if col.name.lower() == 'id'), None)
                if id_col:
                    logger.info(f"[FK Inference] Using column 'id' as primary key for table {table.name}")
                    primary_keys = [id_col]
                    
                # Next, check for {table_name}_id
                if not primary_keys:
                    table_id_col = next((col for col in columns if col.name.lower() == f"{table.name.lower()}_id"), None)
                    if table_id_col:
                        logger.info(f"[FK Inference] Using column '{table.name}_id' as primary key for table {table.name}")
                        primary_keys = [table_id_col]
                
                # If still no primary keys, look for any column with 'id' in the name that might be a PK
                if not primary_keys:
                    potential_id_cols = [col for col in columns if '_id' in col.name.lower()]
                    if potential_id_cols:
                        # Prefer columns that exactly match the pattern '{table_name}_id'
                        exact_match = next((col for col in potential_id_cols if col.name.lower() == f"{table.name.lower()}_id"), None)
                        if exact_match:
                            primary_keys = [exact_match]
                            logger.info(f"[FK Inference] Inferred '{exact_match.name}' as primary key for table {table.name}")
                        else:
                            # Use the first id column as a fallback
                            primary_keys = [potential_id_cols[0]]
                            logger.info(f"[FK Inference] Using '{potential_id_cols[0].name}' as fallback primary key for table {table.name}")
            
            # Store the primary keys
            if primary_keys:
                table_pk[table.name.lower()] = primary_keys
                logger.info(f"[FK Inference] Primary key(s) for {table.name}: {', '.join([pk.name for pk in primary_keys])}")
            else:
                # IMPORTANT CHANGE: If we still can't find a PK, use the first column as a fallback
                # This ensures we always have something to link to
                if columns:
                    fallback_pk = columns[0]
                    table_pk[table.name.lower()] = [fallback_pk]
                    logger.warning(f"[FK Inference] No obvious primary key found for table {table.name}, using '{fallback_pk.name}' as fallback")
                else:
                    logger.warning(f"[FK Inference] No columns found for table {table.name}, cannot infer relationships")
                
            # Track all columns for direct matching
            for col in columns:
                if col.name not in column_to_tables:
                    column_to_tables[col.name] = []
                column_to_tables[col.name].append(table)
                
                # Also store lowercase version for case-insensitive matching
                if col.name.lower() != col.name:
                    if col.name.lower() not in column_to_tables:
                        column_to_tables[col.name.lower()] = []
                    column_to_tables[col.name.lower()].append(table)
        
        # To avoid duplicates in Neo4j, keep track of relationships already added
        existing_relations = set()
        for table in tables:
            for rel in table.foreign_keys.all():
                try:
                    target_table = rel.end_node()
                    props = rel.properties()
                    existing_relations.add((table.name, target_table.name, props['from_column'], props['to_column']))
                except:
                    continue
                    
        logger.info(f"[FK Inference] Found {len(existing_relations)} existing relationships")
        
        # First pass: Look for direct column name matches
        logger.info("[FK Inference] Starting first pass: direct column name matches")
        for source_table in tables:
            source_columns = list(source_table.columns.all())
            
            for source_col in source_columns:
                # Skip if it's a primary key - more likely to be referenced than to reference
                if source_col.is_primary_key:
                    continue
                    
                # Look for columns ending with _id - common foreign key naming pattern
                if source_col.name.endswith('_id'):
                    # Extract the prefix (table name without _id)
                    prefix = source_col.name[:-3].lower()
                    
                    # Check if this matches a table name directly
                    if prefix in table_dict:
                        target_table = table_dict[prefix]
                        
                        # Skip self-references for now (we'll handle these specially)
                        if target_table.name.lower() == source_table.name.lower():
                            logger.info(f"[FK Inference] Found potential self-reference: {source_table.name}.{source_col.name}")
                            continue
                        
                        # Find the primary key of the target table
                        if prefix in table_pk and table_pk[prefix]:
                            target_col = table_pk[prefix][0]  # Use the first primary key
                            
                            # Check if relationship already exists
                            rel_key = (source_table.name, target_table.name, source_col.name, target_col.name)
                            if rel_key in existing_relations:
                                logger.info(f"[FK Inference] Relationship already exists: {source_table.name}.{source_col.name} -> {target_table.name}.{target_col.name}")
                                continue
                                
                            # Add relationship
                            try:
                                source_table.add_foreign_key(
                                    target_table, 
                                    source_col.name, 
                                    target_col.name, 
                                    'ONE_TO_MANY'
                                )
                                
                                # Also add a RELATED_TO relationship for better visualization
                                try:
                                    source_table.relates_to.connect(target_table, {'via': source_col.name})
                                except Exception as rel_e:
                                    logger.warning(f"[FK Inference] Error adding RELATED_TO relationship: {str(rel_e)}")
                                
                                logger.info(f"[FK Inference] Added relationship: {source_table.name}.{source_col.name} -> {target_table.name}.{target_col.name}")
                                existing_relations.add(rel_key)
                                inferred_count += 1
                            except Exception as e:
                                logger.warning(f"[FK Inference] Error adding relationship {source_table.name}.{source_col.name} -> {target_table.name}.{target_col.name}: {str(e)}")
        
        # New pass: Check for matching column names between tables (e.g., customer_id in orders matching primary ID in customers)
        logger.info("[FK Inference] Starting additional pass: matching column names across tables")
        for source_table in tables:
            source_columns = list(source_table.columns.all())
            
            for source_col in source_columns:
                # Skip if it's a primary key or already a foreign key
                if source_col.is_primary_key or source_col.is_foreign_key:
                    continue
                    
                # Only consider columns ending with _id
                if not source_col.name.endswith('_id'):
                    continue
                
                # For each potential foreign key column, check if any table's primary key matches
                for target_table_name, target_pks in table_pk.items():
                    # Skip self-reference (handled separately)
                    if target_table_name == source_table.name.lower():
                        continue
                        
                    if not target_pks:
                        continue
                        
                    target_table = table_dict[target_table_name]
                    
                    # Check if source column refers to this table
                    # For example: customer_id (in orders) should match with an ID in the customers table
                    prefix = source_col.name[:-3].lower()  # Remove the _id suffix
                    if prefix == target_table_name or prefix == singular_form(target_table_name):
                        target_col = target_pks[0]  # Use the first primary key
                        
                        # Check if relationship already exists
                        rel_key = (source_table.name, target_table.name, source_col.name, target_col.name)
                        if rel_key in existing_relations:
                            continue
                            
                        # Add relationship
                        try:
                            source_table.add_foreign_key(
                                target_table, 
                                source_col.name, 
                                target_col.name, 
                                'ONE_TO_MANY'
                            )
                            
                            # Also add a RELATED_TO relationship for better visualization
                            try:
                                source_table.relates_to.connect(target_table, {'via': source_col.name})
                            except Exception as rel_e:
                                logger.warning(f"[FK Inference] Error adding RELATED_TO relationship: {str(rel_e)}")
                            
                            logger.info(f"[FK Inference] Added relationship through column match: {source_table.name}.{source_col.name} -> {target_table.name}.{target_col.name}")
                            existing_relations.add(rel_key)
                            inferred_count += 1
                        except Exception as e:
                            logger.warning(f"[FK Inference] Error adding relationship {source_table.name}.{source_col.name} -> {target_table.name}.{target_col.name}: {str(e)}")
        
        # Second pass: Try singular/plural form matching for table names
        logger.info("[FK Inference] Starting second pass: singular/plural form matching")
        for source_table in tables:
            source_columns = list(source_table.columns.all())
            
            # Get singular and plural forms of the table name
            singular_table = singular_form(source_table.name.lower())
            plural_table = plural_form(source_table.name.lower())
            
            for source_col in source_columns:
                # Skip if already a foreign key
                if source_col.is_foreign_key:
                    continue
                
                # Try to find matching target table based on column name
                for target_table in tables:
                    # Skip self-reference
                    if target_table.name.lower() == source_table.name.lower():
                        continue
                        
                    # Check different naming patterns
                    target_singular = singular_form(target_table.name.lower())
                    
                    patterns = [
                        f"{target_singular}_id",
                        f"{target_table.name.lower()}_id"
                    ]
                    
                    if source_col.name.lower() in patterns:
                        # Find the primary key of the target table
                        if target_table.name.lower() in table_pk and table_pk[target_table.name.lower()]:
                            target_col = table_pk[target_table.name.lower()][0]  # Use the first primary key
                            
                            # Check if relationship already exists
                            rel_key = (source_table.name, target_table.name, source_col.name, target_col.name)
                            if rel_key in existing_relations:
                                continue
                                
                            # Add relationship
                            try:
                                source_table.add_foreign_key(
                                    target_table, 
                                    source_col.name, 
                                    target_col.name, 
                                    'ONE_TO_MANY'
                                )
                                
                                # Also add a RELATED_TO relationship for better visualization
                                try:
                                    source_table.relates_to.connect(target_table, {'via': source_col.name})
                                except Exception as rel_e:
                                    logger.warning(f"[FK Inference] Error adding RELATED_TO relationship: {str(rel_e)}")
                                
                                logger.info(f"[FK Inference] Added relationship through name pattern: {source_table.name}.{source_col.name} -> {target_table.name}.{target_col.name}")
                                existing_relations.add(rel_key)
                                inferred_count += 1
                            except Exception as e:
                                logger.warning(f"[FK Inference] Error adding relationship {source_table.name}.{source_col.name} -> {target_table.name}.{target_col.name}: {str(e)}")
        
        # Third pass: Try to find relationships based on column name suffix
        logger.info("[FK Inference] Starting third pass: column suffix matching")
        for source_table in tables:
            source_columns = list(source_table.columns.all())
            
            for source_col in source_columns:
                # Skip if already a foreign key
                if source_col.is_foreign_key:
                    continue
                    
                # Skip if not ending with _id
                if not source_col.name.lower().endswith('_id'):
                    continue
                    
                # Try to match with any table's primary key that has the same name
                for target_table in tables:
                    # Skip self-reference (handled separately)
                    if target_table.name.lower() == source_table.name.lower():
                        continue
                        
                    target_pks = table_pk.get(target_table.name.lower(), [])
                    for target_pk in target_pks:
                        # Check if the source column matches the target primary key name
                        if source_col.name.lower() == target_pk.name.lower():
                            # Check if relationship already exists
                            rel_key = (source_table.name, target_table.name, source_col.name, target_pk.name)
                            if rel_key in existing_relations:
                                continue
                                
                            # Add relationship
                            try:
                                source_table.add_foreign_key(
                                    target_table, 
                                    source_col.name, 
                                    target_pk.name, 
                                    'ONE_TO_MANY'
                                )
                                
                                # Also add a RELATED_TO relationship for better visualization
                                try:
                                    source_table.relates_to.connect(target_table, {'via': source_col.name})
                                except Exception as rel_e:
                                    logger.warning(f"[FK Inference] Error adding RELATED_TO relationship: {str(rel_e)}")
                                
                                logger.info(f"[FK Inference] Added relationship through column matching: {source_table.name}.{source_col.name} -> {target_table.name}.{target_pk.name}")
                                existing_relations.add(rel_key)
                                inferred_count += 1
                            except Exception as e:
                                logger.warning(f"[FK Inference] Error adding relationship {source_table.name}.{source_col.name} -> {target_table.name}.{target_pk.name}: {str(e)}")
        
        # Fourth pass: Handle self-references (e.g., categories.parent_id -> categories.id)
        logger.info("[FK Inference] Starting fourth pass: self-reference detection")
        for table in tables:
            columns = list(table.columns.all())
            primary_keys = table_pk.get(table.name.lower(), [])
            
            if not primary_keys:
                continue
                
            # Find potential self-reference columns
            for col in columns:
                # Skip if already a foreign key
                if col.is_foreign_key:
                    continue
                    
                # Common self-reference patterns
                self_ref_patterns = ['parent_id', 'parent', 'parent_key', 'superior_id', 'manager_id']
                
                if col.name.lower() in self_ref_patterns:
                    pk = primary_keys[0]
                    
                    # Check if relationship already exists
                    rel_key = (table.name, table.name, col.name, pk.name)
                    if rel_key in existing_relations:
                        continue
                        
                    # Add self-reference relationship
                    try:
                        table.add_foreign_key(
                            table, 
                            col.name, 
                            pk.name, 
                            'ONE_TO_MANY'
                        )
                        
                        # Also add a RELATED_TO relationship for better visualization
                        try:
                            table.relates_to.connect(table, {'via': col.name})
                        except Exception as rel_e:
                            logger.warning(f"[FK Inference] Error adding self-reference RELATED_TO relationship: {str(rel_e)}")
                        
                        logger.info(f"[FK Inference] Added self-reference: {table.name}.{col.name} -> {table.name}.{pk.name}")
                        existing_relations.add(rel_key)
                        inferred_count += 1
                    except Exception as e:
                        logger.warning(f"[FK Inference] Error adding self-reference {table.name}.{col.name} -> {table.name}.{pk.name}: {str(e)}")
        
        logger.info(f"[FK Inference] Completed - inferred {inferred_count} relationships")
        return inferred_count
        
    except Exception as e:
        logger.error(f"[FK Inference] Error in foreign key inference: {str(e)}")
        return inferred_count
