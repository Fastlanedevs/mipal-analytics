from neomodel import (
    StructuredNode,
    StringProperty,
    DateTimeProperty,
    RelationshipTo,
    RelationshipFrom,
    JSONProperty,
    UniqueIdProperty,
    FloatProperty,
    IntegerProperty,
    ArrayProperty,
    BooleanProperty,
    StructuredRel,
    Relationship,
    db,
)
from datetime import datetime
from typing import List, Dict, Any


# =====================================
# Relationship Models
# =====================================

class EntityRelationship(StructuredRel):
    """Enhanced relationship properties for LightRAG"""

    # Core relationship properties
    relationship_type = StringProperty(required=True)
    description = StringProperty()

    # LightRAG features
    keywords = ArrayProperty(StringProperty())  # Relationship keywords
    strength = FloatProperty(default=1.0)  # Relationship strength (0-1)
    confidence = FloatProperty(default=0.5)  # Extraction confidence (0-1)
    weight = FloatProperty(default=1.0)  # Graph weight for algorithms

    # Global themes for high-level retrieval
    global_themes = ArrayProperty(StringProperty())

    # Source tracking
    source_chunks = ArrayProperty(StringProperty())  # PostgreSQL chunk IDs
    source_slices = ArrayProperty(IntegerProperty())  # Text slice indices
    occurrence_count = IntegerProperty(default=1)

    # Bidirectional flag
    is_bidirectional = BooleanProperty(default=False)

    # PostgreSQL reference
    postgres_id = StringProperty(unique=True)  # Reference to PostgreSQL relationship

    # Timestamps
    created_at = DateTimeProperty(default=datetime.now)
    updated_at = DateTimeProperty(default=datetime.now)


class DocumentContainment(StructuredRel):
    """Relationship between document and entities"""

    chunk_order = IntegerProperty()  # Order of chunk containing entity
    first_occurrence = BooleanProperty(default=False)  # First occurrence in document
    importance_score = FloatProperty(default=0.5)  # Entity importance in document

    created_at = DateTimeProperty(default=datetime.now)


class ThemeConnection(StructuredRel):
    """Connection between entities/relationships and global themes"""

    relevance_score = FloatProperty(default=1.0)  # How relevant to theme
    theme_type = StringProperty()  # entity_theme, relationship_theme

    created_at = DateTimeProperty(default=datetime.now)


# =====================================
# Node Models
# =====================================

class DocumentNode(StructuredNode):
    """Document representation in Neo4j for document-level relationships"""

    # Node label
    __label__ = "Document"

    # Core properties
    uid = UniqueIdProperty()
    document_title = StringProperty()
    file_type = StringProperty()

    # Processing metadata
    processing_status = StringProperty(default='PENDING')
    entities_count = IntegerProperty(default=0)
    relationships_count = IntegerProperty(default=0)
    chunks_count = IntegerProperty(default=0)

    # PostgreSQL reference
    postgres_id = StringProperty(unique=True, required=True)  # Reference to PostgreSQL document
    user_id = StringProperty(required=True, index=True)  # For user-specific queries

    # Document metrics for graph algorithms
    centrality_score = FloatProperty(default=0.0)  # Document centrality in knowledge graph

    # Timestamps
    created_at = DateTimeProperty(default=datetime.now)
    updated_at = DateTimeProperty(default=datetime.now)

    # Relationships
    contains_entity = RelationshipTo('DocumentEntityNode', 'DOC_CONTAINS', model=DocumentContainment)
    related_to_document = RelationshipTo('DocumentNode', 'DOCUMENT_RELATED')


class DocumentEntityNode(StructuredNode):
    """Enhanced entity node with full LightRAG support"""

    # Node label
    __label__ = "DocumentEntity"

    # Core properties
    uid = UniqueIdProperty()
    entity_name = StringProperty(required=True, index=True)
    entity_type = StringProperty(required=True, index=True)
    description = StringProperty()

    # LightRAG profiling features
    search_keys = ArrayProperty(StringProperty())  # Keys for low-level retrieval
    summary_value = StringProperty()  # Summarized value for generation

    # Confidence and metrics
    confidence = FloatProperty(default=0.5)  # Extraction confidence (0-1)
    occurrence_count = IntegerProperty(default=1)  # Frequency across documents
    importance_score = FloatProperty(default=0.5)  # Calculated importance

    # Graph analytics (computed by graph algorithms)
    pagerank_score = FloatProperty(default=0.0)
    betweenness_centrality = FloatProperty(default=0.0)
    closeness_centrality = FloatProperty(default=0.0)
    degree_centrality = FloatProperty(default=0.0)
    community_id = IntegerProperty()  # Community detection result

    # PostgreSQL references
    postgres_id = StringProperty(unique=True, required=True)  # Reference to PostgreSQL entity
    document_id = StringProperty(required=True, index=True)  # PostgreSQL document ID
    user_id = StringProperty(required=True, index=True)  # For user-specific filtering

    # Source tracking
    source_chunks = ArrayProperty(StringProperty())  # PostgreSQL chunk IDs

    # Timestamps
    created_at = DateTimeProperty(default=datetime.now)
    updated_at = DateTimeProperty(default=datetime.now)

    # Relationships - Different types for different semantic relationships
    entity_related_to = RelationshipTo('DocumentEntityNode', 'ENTITY_RELATED_TO', model=EntityRelationship)
    works_at = RelationshipTo('DocumentEntityNode', 'WORKS_AT', model=EntityRelationship)
    located_in = RelationshipTo('DocumentEntityNode', 'LOCATED_IN', model=EntityRelationship)
    part_of = RelationshipTo('DocumentEntityNode', 'PART_OF', model=EntityRelationship)
    collaborates_with = RelationshipTo('DocumentEntityNode', 'COLLABORATES_WITH', model=EntityRelationship)
    influences = RelationshipTo('DocumentEntityNode', 'INFLUENCES', model=EntityRelationship)
    created_by = RelationshipTo('DocumentEntityNode', 'CREATED_BY', model=EntityRelationship)

    # Generic relationship for custom types
    connected_to = RelationshipTo('DocumentEntityNode', 'CONNECTED_TO', model=EntityRelationship)

    # Relationships to other node types
    contained_in_document = RelationshipFrom('DocumentNode', 'DOC_CONTAINS', model=DocumentContainment)
    associated_with_theme = RelationshipTo('GlobalThemeNode', 'ASSOCIATED_WITH', model=ThemeConnection)


class GlobalThemeNode(StructuredNode):
    """Global themes for high-level retrieval"""

    # Node label
    __label__ = "GlobalTheme"

    # Core properties
    uid = UniqueIdProperty()
    theme_name = StringProperty(required=True, index=True)
    theme_type = StringProperty(default='concept')  # concept, domain, topic
    description = StringProperty()

    # Theme metadata
    frequency = IntegerProperty(default=1)  # How often theme appears
    confidence = FloatProperty(default=0.5)  # Theme extraction confidence
    scope = StringProperty(default='document')  # document, collection, global

    # Associated entity/relationship types
    related_entity_types = ArrayProperty(StringProperty())
    related_relationship_types = ArrayProperty(StringProperty())

    # PostgreSQL reference
    postgres_id = StringProperty()  # Reference to PostgreSQL global_themes table
    user_id = StringProperty(required=True, index=True)

    # Theme metrics
    centrality_score = FloatProperty(default=0.0)  # Theme importance in graph

    # Timestamps
    created_at = DateTimeProperty(default=datetime.now)
    updated_at = DateTimeProperty(default=datetime.now)

    # Relationships
    related_to_entity = RelationshipFrom('DocumentEntityNode', 'ASSOCIATED_WITH', model=ThemeConnection)
    contains_theme = RelationshipTo('GlobalThemeNode', 'CONTAINS_THEME')  # Hierarchical themes
    parent_theme = RelationshipFrom('GlobalThemeNode', 'CONTAINS_THEME')


class UserKnowledgeGraph(StructuredNode):
    """User-level knowledge graph metadata"""

    # Node label
    __label__ = "UserGraph"

    # Core properties
    uid = UniqueIdProperty()
    user_id = StringProperty(required=True, unique=True, index=True)

    # Graph statistics
    total_documents = IntegerProperty(default=0)
    total_entities = IntegerProperty(default=0)
    total_relationships = IntegerProperty(default=0)
    total_themes = IntegerProperty(default=0)

    # Graph metrics
    graph_density = FloatProperty(default=0.0)  # How connected the graph is
    avg_clustering_coefficient = FloatProperty(default=0.0)
    modularity = FloatProperty(default=0.0)  # Community structure quality

    # Processing metadata
    last_updated = DateTimeProperty(default=datetime.now)
    last_algorithm_run = DateTimeProperty()  # Last time graph algorithms were run

    # Timestamps
    created_at = DateTimeProperty(default=datetime.now)

    # Relationships
    owns_document = RelationshipTo('DocumentNode', 'OWNS')
    contains_entity = RelationshipTo('DocumentEntityNode', 'GRAPH_CONTAINS')
    includes_theme = RelationshipTo('GlobalThemeNode', 'INCLUDES')
