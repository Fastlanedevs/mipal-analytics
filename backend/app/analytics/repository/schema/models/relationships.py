"""
Relationship models for the Neo4j schema.
"""
from neomodel import StructuredRel, StringProperty

class ForeignKeyRel(StructuredRel):
    """Foreign key relationship properties"""
    type = StringProperty(required=True)  # ONE_TO_ONE, ONE_TO_MANY, or MANY_TO_MANY
    from_column = StringProperty(required=True)
    to_column = StringProperty(required=True)
    # For many-to-many relationships
    junction_table = StringProperty()  # Name of the junction table for many-to-many
    junction_source_column = StringProperty()  # Column in junction table referencing source
    junction_target_column = StringProperty()  # Column in junction table referencing target


class SharedColumnRel(StructuredRel):
    """Shared column relationship properties"""
    via = StringProperty(required=True)  # Name of the shared column
