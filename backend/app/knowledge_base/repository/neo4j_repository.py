from typing import List, Optional, Dict, Any, Tuple
import uuid, asyncio
from uuid import UUID
from datetime import datetime, timezone
from neomodel import db as neodb_db
from concurrent.futures import ThreadPoolExecutor
from app.knowledge_base.repository.schema.user_document import (
    DocumentNode,DocumentEntityNode,GlobalThemeNode,UserKnowledgeGraph,
    EntityRelationship, DocumentContainment, ThemeConnection,
)
from app.knowledge_base.entity.entity import DocumentEntity as DocumentEntityPydantic, EntityRelationship as EntityRelationshipPydantic
from pkg.log.logger import Logger
from pkg.db_util.neo4j_conn import Neo4jConnection


class Neo4jRepository:
    def __init__(self, neo4j_conn: Neo4jConnection, logger: Logger):
        self.neo4j_conn = neo4j_conn
        self.logger = logger
        self.executor = ThreadPoolExecutor(max_workers=4)  # For async operations

        self._initialize_neo4j_indexes()  # Add index initialization

    def _initialize_neo4j_indexes(self):
        """Create essential indexes and constraints for LightRAG"""
        index_queries = [
            # Entity indexes
            "CREATE INDEX IF NOT EXISTS FOR (e:DocumentEntity) ON (e.entity_name)",
            "CREATE INDEX IF NOT EXISTS FOR (e:DocumentEntity) ON (e.entity_type)",
            "CREATE INDEX IF NOT EXISTS FOR (e:DocumentEntity) ON (e.user_id)",

            # Theme indexes
            "CREATE INDEX IF NOT EXISTS FOR (t:GlobalTheme) ON (t.theme_name)",
            "CREATE INDEX IF NOT EXISTS FOR (t:GlobalTheme) ON (t.user_id)",
            "CREATE CONSTRAINT global_theme_user_unique IF NOT EXISTS FOR (t:GlobalTheme) REQUIRE (t.user_id, t.theme_name) IS UNIQUE",

            # Document indexes
            "CREATE INDEX IF NOT EXISTS FOR (d:DocumentNode) ON (d.user_id)",

            # Relationship indexes
            "CREATE INDEX IF NOT EXISTS FOR ()-[r:CONNECTED_TO]-() ON (r.relationship_type)",
            "CREATE INDEX IF NOT EXISTS FOR ()-[r:ASSOCIATED_WITH]-() ON (r.theme_type)"
        ]

        try:
            # Check if Neo4j connection is available
            if not self.neo4j_conn:
                self.logger.warning("Neo4j connection not available, skipping index initialization")
                return
                
            # Test connection with a simple query
            try:
                self.neo4j_conn.cypher_query("RETURN 1")
            except Exception as conn_test:
                self.logger.warning(f"Neo4j connection test failed, skipping index initialization: {conn_test}")
                return
                
            for query in index_queries:
                try:
                    self.neo4j_conn.cypher_query(query)
                except Exception as idx_err:
                    self.logger.warning(f"Failed to create Neo4j index: {idx_err}")
                    continue
                    
            self.logger.info("Neo4j indexes initialized successfully")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Neo4j indexes: {str(e)}")
            # Don't raise - Neo4j issues shouldn't block PostgreSQL ingestion

    async def initialize_user_graph(self, user_id: str) -> UserKnowledgeGraph:
        """Initialize or get user's knowledge graph metadata"""

        def _create_user_graph():
            try:
                # Check if user graph already exists
                existing: Optional[UserKnowledgeGraph] = None
                try:
                    existing = UserKnowledgeGraph.nodes.filter(user_id=user_id).first()
                except UserKnowledgeGraph.DoesNotExist:
                    self.logger.info(f"User knowledge graph for user {user_id} does not exist. Creating a new one.")
                    existing = None # Explicitly set to None, though not strictly necessary here

                if existing:
                    return existing

                # Create new user graph
                user_graph = UserKnowledgeGraph(
                    user_id=user_id,
                    total_documents=0,
                    total_entities=0,
                    total_relationships=0,
                    total_themes=0,
                    graph_density=0.0,
                    avg_clustering_coefficient=0.0,
                    modularity=0.0,
                    last_updated=datetime.now(),
                    created_at=datetime.now()
                ).save()

                self.logger.info(f"Created user knowledge graph for user {user_id}")
                return user_graph

            except Exception as e:
                self.logger.error(f"Error creating user graph for {user_id}: {e}")
                raise

        return await asyncio.get_event_loop().run_in_executor(self.executor, _create_user_graph)

    async def create_document_node(self, document_id: UUID, user_id: str,
                                   title: str = None, file_type: str = None) -> DocumentNode:
        """Create document node in Neo4j"""

        def _create_document():
            try:
                # Check if document already exists
                existing: Optional[DocumentNode] = None
                try:
                    existing = DocumentNode.nodes.filter(postgres_id=str(document_id)).first()
                except DocumentNode.DoesNotExist:
                    self.logger.debug(f"DocumentNode with postgres_id {document_id} does not exist. Creating a new one.")
                    existing = None # Explicitly set to None

                if existing:
                    return existing

                document_node = DocumentNode(
                    postgres_id=str(document_id),
                    user_id=user_id,
                    document_title=title or "",
                    file_type=file_type or "",
                    processing_status='PROCESSING',
                    entities_count=0,
                    relationships_count=0,
                    chunks_count=0,
                    centrality_score=0.0,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                ).save()

                self.logger.debug(f"Created document node for document {document_id}")
                return document_node

            except Exception as e:
                self.logger.error(f"Error creating document node {document_id}: {e}")
                raise

        return await asyncio.get_event_loop().run_in_executor(self.executor, _create_document)

    async def create_entities(self, entities: List[DocumentEntityPydantic]) -> List[DocumentEntityNode]:
        """Create entity nodes in Neo4j with batch processing"""

        def _create_entities_batch():
            created_entities = []

            try:
                for entity in entities:
                    # Check if entity already exists
                    existing: Optional[DocumentEntityNode] = None
                    try:
                        existing = DocumentEntityNode.nodes.filter(postgres_id=str(entity.id)).first()
                    except DocumentEntityNode.DoesNotExist:
                        self.logger.debug(f"DocumentEntityNode with postgres_id {entity.id} does not exist. Creating a new one.")
                        existing = None # Explicitly set to None

                    if existing:
                        created_entities.append(existing)
                        continue

                    # Create new entity node
                    entity_node = DocumentEntityNode(
                        postgres_id=str(entity.id),
                        entity_name=entity.entity_name,
                        entity_type=entity.entity_type,
                        description=entity.description or "",
                        search_keys=entity.keys or [],
                        summary_value=entity.value or "",
                        confidence=entity.confidence,
                        occurrence_count=entity.occurrence_count,
                        importance_score=entity.confidence,  # Initial importance = confidence
                        pagerank_score=0.0,
                        betweenness_centrality=0.0,
                        closeness_centrality=0.0,
                        degree_centrality=0.0,
                        document_id=str(entity.document_id),
                        user_id=entity.user_id,
                        source_chunks=[str(chunk_id) for chunk_id in entity.source_chunks],
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    ).save()

                    created_entities.append(entity_node)

                self.logger.info(f"Created {len(created_entities)} entity nodes")
                return created_entities

            except Exception as e:
                self.logger.error(f"Error creating entity nodes: {e}")
                raise

        return await asyncio.get_event_loop().run_in_executor(self.executor, _create_entities_batch)

    async def create_relationships(self, relationships: List[EntityRelationshipPydantic],
                                   entity_nodes: List[DocumentEntityNode]) -> None:
        """Create relationships between entities in Neo4j"""

        def _create_relationships_batch():
            try:
                # Create mapping of postgres_id to entity nodes for quick lookup
                entity_map = {node.postgres_id: node for node in entity_nodes}

                relationships_created = 0

                for rel in relationships:
                    source_node = entity_map.get(str(rel.source_entity_id))
                    target_node = entity_map.get(str(rel.target_entity_id))

                    if not source_node or not target_node:
                        self.logger.warning(
                            f"Skipping relationship - entities not found: {rel.source_entity_id} -> {rel.target_entity_id}")
                        continue

                    # Create relationship based on type
                    rel_type = rel.relationship_type.upper().replace(' ', '_')

                    # Prepare relationship properties
                    rel_props = {
                        'relationship_type': rel.relationship_type,
                        'description': rel.description or "",
                        'keywords': rel.keywords or [],
                        'strength': rel.strength,
                        'confidence': rel.confidence,
                        'weight': rel.strength,  # Use strength as weight
                        'global_themes': rel.global_themes or [],
                        'source_chunks': [str(chunk_id) for chunk_id in rel.source_chunks],
                        'source_slices': rel.source_slices or [],
                        'occurrence_count': rel.occurrence_count,
                        'is_bidirectional': rel.is_bidirectional,
                        'postgres_id': str(rel.id),
                        'created_at': datetime.now(),
                        'updated_at': datetime.now()
                    }

                    # Create relationship using appropriate method based on type
                    if rel_type == 'WORKS_AT':
                        source_node.works_at.connect(target_node, rel_props)
                    elif rel_type == 'LOCATED_IN':
                        source_node.located_in.connect(target_node, rel_props)
                    elif rel_type == 'PART_OF':
                        source_node.part_of.connect(target_node, rel_props)
                    elif rel_type == 'COLLABORATES_WITH':
                        source_node.collaborates_with.connect(target_node, rel_props)
                    elif rel_type == 'INFLUENCES':
                        source_node.influences.connect(target_node, rel_props)
                    elif rel_type == 'CREATED_BY':
                        source_node.created_by.connect(target_node, rel_props)
                    else:
                        # Use generic relationship for other types
                        source_node.connected_to.connect(target_node, rel_props)

                    relationships_created += 1

                    # If bidirectional, create reverse relationship
                    if rel.is_bidirectional:
                        target_node.connected_to.connect(source_node, rel_props)

                self.logger.info(f"Created {relationships_created} relationships")

            except Exception as e:
                self.logger.error(f"Error creating relationships: {e}")
                raise

        return await asyncio.get_event_loop().run_in_executor(self.executor, _create_relationships_batch)

    async def create_global_themes(self, themes: Dict[str, List[str]], user_id: str,
                                   document_id: UUID) -> List[GlobalThemeNode]:
        """Create global theme nodes for high-level retrieval"""

        def _create_themes():
            created_themes = []

            try:
                for theme_type, theme_names in themes.items():
                    for theme_name in theme_names:
                        # Check if theme already exists
                        existing: Optional[GlobalThemeNode] = None
                        try:
                            existing = GlobalThemeNode.nodes.filter(
                                theme_name=theme_name, user_id=user_id
                            ).first()
                        except GlobalThemeNode.DoesNotExist:
                            self.logger.debug(f"GlobalThemeNode with theme_name '{theme_name}' for user_id '{user_id}' does not exist. Creating a new one.")
                            existing = None # Ensure 'existing' is None if not found

                        if existing:
                            # Update frequency
                            existing.frequency += 1
                            existing.updated_at = datetime.now()
                            existing.save()
                            created_themes.append(existing)
                        else:
                            # Create new theme
                            theme_node = GlobalThemeNode(
                                theme_name=theme_name,
                                theme_type='relationship',  # Since these come from relationships
                                description=f"Global theme: {theme_name}",
                                frequency=1,
                                confidence=0.7,  # Default confidence for generated themes
                                scope='document',
                                related_entity_types=[],
                                related_relationship_types=[theme_type],
                                user_id=user_id,
                                centrality_score=0.0,
                                created_at=datetime.now(),
                                updated_at=datetime.now()
                            ).save()

                            created_themes.append(theme_node)

                self.logger.info(f"Created/updated {len(created_themes)} global themes")
                return created_themes

            except Exception as e:
                self.logger.error(f"Error creating global themes: {e}")
                raise

        return await asyncio.get_event_loop().run_in_executor(self.executor, _create_themes)

    async def connect_entities_to_themes(self, entity_nodes: List[DocumentEntityNode],
                                         theme_nodes: List[GlobalThemeNode]) -> None:
        """Connect entities to relevant global themes"""

        def _connect_themes():
            try:
                connections_created = 0

                for entity_node in entity_nodes:
                    for theme_node in theme_nodes:
                        # Simple relevance check based on entity type and theme
                        is_relevant = False

                        # Check if entity type is related to theme
                        if entity_node.entity_type in theme_node.related_entity_types:
                            is_relevant = True

                        # Check if any of the entity's search keys match theme name
                        if any(theme_node.theme_name.lower() in key.lower()
                               for key in entity_node.search_keys):
                            is_relevant = True

                        if is_relevant:
                            # Connect entity to theme
                            connection_props = {
                                'relevance_score': 0.8,  # Default relevance
                                'theme_type': 'entity_theme',
                                'created_at': datetime.now()
                            }

                            entity_node.associated_with_theme.connect(theme_node, connection_props)
                            connections_created += 1

                self.logger.info(f"Created {connections_created} entity-theme connections")

            except Exception as e:
                self.logger.error(f"Error connecting entities to themes: {e}")
                raise

        return await asyncio.get_event_loop().run_in_executor(self.executor, _connect_themes)

    async def update_document_status(self, document_id: UUID, status: str,
                                     entity_count: int = 0, relationship_count: int = 0) -> None:
        """Update document processing status"""

        def _update_status():
            try:
                doc_node = DocumentNode.nodes.filter(postgres_id=str(document_id)).first()
                if doc_node:
                    doc_node.processing_status = status
                    doc_node.entities_count = entity_count
                    doc_node.relationships_count = relationship_count
                    doc_node.updated_at = datetime.now()
                    doc_node.save()

                    self.logger.debug(f"Updated document {document_id} status to {status}")

            except Exception as e:
                self.logger.error(f"Error updating document status: {e}")
                raise

        return await asyncio.get_event_loop().run_in_executor(self.executor, _update_status)

    # =============================================
    # RETRIEVAL METHODS FOR DUAL-LEVEL LIGHTRAG
    # =============================================
    async def find_entities_by_keywords(self, user_id: str, keywords: List[str],
                                                  limit: int = 10, include_related: bool = True) -> List[Dict[str, Any]]:
        """Optimized entity search with optional relationship expansion"""

        def _find_entities():
            try:
                # Use more sophisticated matching with fuzzy search
                query = """
                MATCH (e:DocumentEntity {user_id: $user_id})
                WITH e, 
                     [k IN e.search_keys WHERE any(keyword IN $keywords WHERE 
                        k CONTAINS keyword OR 
                        apoc.text.levenshteinSimilarity(k, keyword) > 0.8)] as matched_keys,
                     [keyword IN $keywords WHERE 
                        e.entity_name CONTAINS keyword OR 
                        apoc.text.levenshteinSimilarity(e.entity_name, keyword) > 0.8] as matched_names
                WHERE size(matched_keys) > 0 OR size(matched_names) > 0

                WITH e, (size(matched_keys) + size(matched_names) * 2) as relevance_score
                """

                if include_related:
                    query += """
                    OPTIONAL MATCH (e)-[r:CONNECTED_TO]-(related:DocumentEntity)
                    WHERE related.user_id = $user_id
                    WITH e, relevance_score, collect(DISTINCT {
                        id: related.postgres_id,
                        name: related.entity_name,
                        relationship: r.relationship_type,
                        strength: r.strength
                    })[..5] as related_entities
                    """
                else:
                    query += "WITH e, relevance_score, [] as related_entities"

                query += """
                RETURN e.postgres_id as entity_id,
                       e.entity_name as name,
                       e.entity_type as type,
                       e.description as description,
                       e.confidence as confidence,
                       e.pagerank_score as importance,
                       e.search_keys as keys,
                       e.summary_value as value,
                       relevance_score,
                       related_entities
                ORDER BY relevance_score DESC, e.pagerank_score DESC, e.confidence DESC
                LIMIT $limit
                """

                results = self.neo4j_conn.cypher_query(query, {
                    'user_id': user_id,
                    'keywords': keywords,
                    'limit': limit
                })

                entities = []
                for row in results:
                    entities.append({
                        'entity_id': row[0],
                        'name': row[1],
                        'type': row[2],
                        'description': row[3],
                        'confidence': row[4],
                        'importance': row[5],
                        'keys': row[6],
                        'value': row[7],
                        'relevance_score': row[8],
                        'related_entities': row[9]
                    })

                return entities

            except Exception as e:
                self.logger.error(f"Error in optimized entity search: {e}")
                return []

        return await asyncio.get_event_loop().run_in_executor(self.executor, _find_entities)

    async def find_themes_by_keywords(self, user_id: str, keywords: List[str],
                                      limit: int = 10) -> List[Dict[str, Any]]:
        """High-level retrieval: Find global themes matching abstract concepts"""

        def _find_themes():
            try:
                query = """
                MATCH (t:GlobalTheme {user_id: $user_id})
                WHERE any(keyword IN $keywords WHERE t.theme_name CONTAINS keyword)
                   OR any(keyword IN $keywords WHERE t.description CONTAINS keyword)
                RETURN t.theme_name as name,
                       t.description as description,
                       t.theme_type as type,
                       t.frequency as frequency,
                       t.confidence as confidence,
                       t.centrality_score as importance
                ORDER BY t.frequency DESC, t.confidence DESC
                LIMIT $limit
                """

                results = self.neo4j_conn.cypher_query(query, {
                    'user_id': user_id,
                    'keywords': keywords,
                    'limit': limit
                })

                themes = []
                for row in results:
                    themes.append({
                        'name': row[0],
                        'description': row[1],
                        'type': row[2],
                        'frequency': row[3],
                        'confidence': row[4],
                        'importance': row[5]
                    })

                return themes

            except Exception as e:
                self.logger.error(f"Error finding themes by keywords: {e}")
                return []

        return await asyncio.get_event_loop().run_in_executor(self.executor, _find_themes)

    async def get_entity_neighborhood(self, entity_postgres_id: str,
                                      max_depth: int = 2, limit: int = 10) -> Dict[str, Any]:
        """Get entities related to a specific entity within specified depth"""

        def _get_neighborhood():
            try:
                query = """
                MATCH (start:DocumentEntity {postgres_id: $entity_id})
                CALL apoc.path.subgraphNodes(start, {
                    relationshipFilter: 'ENTITY_RELATED_TO>|WORKS_AT>|LOCATED_IN>|PART_OF>|COLLABORATES_WITH>|INFLUENCES>|CREATED_BY>|CONNECTED_TO>',
                    minLevel: 1,
                    maxLevel: $max_depth,
                    limit: $limit
                })
                YIELD node
                RETURN node.postgres_id as entity_id,
                       node.entity_name as name,
                       node.entity_type as type,
                       node.confidence as confidence,
                       node.pagerank_score as importance
                ORDER BY node.pagerank_score DESC
                """

                results = self.neo4j_conn.cypher_query(query, {
                    'entity_id': entity_postgres_id,
                    'max_depth': max_depth,
                    'limit': limit
                })

                related_entities = []
                for row in results:
                    related_entities.append({
                        'entity_id': row[0],
                        'name': row[1],
                        'type': row[2],
                        'confidence': row[3],
                        'importance': row[4]
                    })

                return {
                    'center_entity_id': entity_postgres_id,
                    'related_entities': related_entities,
                    'total_found': len(related_entities)
                }

            except Exception as e:
                self.logger.error(f"Error getting entity neighborhood: {e}")
                return {'center_entity_id': entity_postgres_id, 'related_entities': [], 'total_found': 0}

        return await asyncio.get_event_loop().run_in_executor(self.executor, _get_neighborhood)

    async def get_shortest_path(self, entity1_id: str, entity2_id: str) -> List[Dict[str, Any]]:
        """Find shortest path between two entities"""

        def _get_shortest_path():
            try:
                query = """
                MATCH (start:DocumentEntity {postgres_id: $entity1_id}),
                      (end:DocumentEntity {postgres_id: $entity2_id})
                CALL apoc.algo.dijkstra(start, end, 'ENTITY_RELATED_TO>|WORKS_AT>|LOCATED_IN>|PART_OF>|COLLABORATES_WITH>|INFLUENCES>|CREATED_BY>|CONNECTED_TO>', 'weight')
                YIELD path, weight
                UNWIND nodes(path) as node
                RETURN node.postgres_id as entity_id,
                       node.entity_name as name,
                       node.entity_type as type
                """

                results = self.neo4j_conn.cypher_query(query, {
                    'entity1_id': entity1_id,
                    'entity2_id': entity2_id
                })

                path_entities = []
                for row in results:
                    path_entities.append({
                        'entity_id': row[0],
                        'name': row[1],
                        'type': row[2]
                    })

                return path_entities

            except Exception as e:
                self.logger.error(f"Error finding shortest path: {e}")
                return []

        return await asyncio.get_event_loop().run_in_executor(self.executor, _get_shortest_path)

    # =============================================
    # GRAPH ANALYTICS METHODS
    # =============================================

    async def run_pagerank_algorithm(self, user_id: str) -> None:
        """Run PageRank algorithm to compute entity importance"""

        def _run_pagerank():
            try:
                # Create a temporary graph projection for this user
                projection_query = f"""
                CALL gds.graph.project(
                    'userGraph_{user_id}',
                    {{
                        DocumentEntity: {{
                            label: 'DocumentEntity',
                            properties: ['pagerank_score']
                        }}
                    }},
                    {{
                        RELATIONSHIP: {{
                            type: '*',
                            orientation: 'NATURAL',
                            properties: ['weight']
                        }}
                    }},
                    {{
                        nodeQuery: 'MATCH (n:DocumentEntity {{user_id: "{user_id}"}}) RETURN id(n) AS id',
                        relationshipQuery: 'MATCH (s:DocumentEntity {{user_id: "{user_id}"}})-[r]->(t:DocumentEntity {{user_id: "{user_id}"}}) WHERE type(r) IN ["ENTITY_RELATED_TO", "WORKS_AT", "LOCATED_IN", "PART_OF", "COLLABORATES_WITH", "INFLUENCES", "CREATED_BY", "CONNECTED_TO"] RETURN id(s) AS source, id(t) AS target, r.weight AS weight'
                    }}
                )
                """

                # Run PageRank
                pagerank_query = f"""
                CALL gds.pageRank.write('userGraph_{user_id}', {{
                    writeProperty: 'pagerank_score',
                    relationshipWeightProperty: 'weight'
                }})
                YIELD nodePropertiesWritten
                RETURN nodePropertiesWritten
                """

                # Clean up projection
                cleanup_query = f"CALL gds.graph.drop('userGraph_{user_id}')"

                # Execute queries
                self.neo4j_conn.cypher_query(projection_query)
                results = self.neo4j_conn.cypher_query(pagerank_query)
                self.neo4j_conn.cypher_query(cleanup_query)

                self.logger.info(f"PageRank completed for user {user_id}")

            except Exception as e:
                self.logger.error(f"Error running PageRank: {e}")
                # Try to clean up in case of error
                try:
                    cleanup_query = f"CALL gds.graph.drop('userGraph_{user_id}')"
                    self.neo4j_conn.cypher_query(cleanup_query)
                except:
                    pass

        return await asyncio.get_event_loop().run_in_executor(self.executor, _run_pagerank)

    async def get_user_graph_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about user's knowledge graph"""

        def _get_stats():
            try:
                query = """
                MATCH (e:DocumentEntity {user_id: $user_id})
                WITH count(DISTINCT e) as entity_count
                MATCH (e:DocumentEntity {user_id: $user_id})-[r]-(other:DocumentEntity {user_id: $user_id})
                WITH entity_count, count(DISTINCT r) as relationship_count
                MATCH (t:GlobalTheme {user_id: $user_id})
                WITH entity_count, relationship_count, count(t) as theme_count
                MATCH (d:Document {user_id: $user_id})
                RETURN entity_count, relationship_count, theme_count, count(d) as document_count
                """

                results = self.neo4j_conn.cypher_query(query, {'user_id': user_id})

                if results:
                    row = results[0]
                    return {
                        'entity_count': row[0],
                        'relationship_count': row[1],
                        'theme_count': row[2],
                        'document_count': row[3],
                        'graph_density': row[1] / max(row[0] * (row[0] - 1), 1) if row[0] > 1 else 0
                    }
                else:
                    return {
                        'entity_count': 0,
                        'relationship_count': 0,
                        'theme_count': 0,
                        'document_count': 0,
                        'graph_density': 0
                    }

            except Exception as e:
                self.logger.error(f"Error getting graph stats: {e}")
                return {
                    'entity_count': 0,
                    'relationship_count': 0,
                    'theme_count': 0,
                    'document_count': 0,
                    'graph_density': 0
                }

        return await asyncio.get_event_loop().run_in_executor(self.executor, _get_stats)

    async def cleanup_user_data(self, user_id: str) -> None:
        """Clean up all data for a user"""

        def _cleanup():
            try:
                # Delete all user data
                query = """
                MATCH (n {user_id: $user_id})
                DETACH DELETE n
                """

                self.neo4j_conn.cypher_query(query, {'user_id': user_id})
                self.logger.info(f"Cleaned up Neo4j data for user {user_id}")

            except Exception as e:
                self.logger.error(f"Error cleaning up user data: {e}")
                raise

        return await asyncio.get_event_loop().run_in_executor(self.executor, _cleanup)



    async def get_entity_subgraph(self, entity_postgres_id: str, max_depth: int = 2,
                                  min_strength: float = 0.5) -> Dict[str, Any]:
        """Get entity subgraph with relationship strength filtering"""

        def _get_subgraph():
            try:
                query = """
                MATCH (center:DocumentEntity {postgres_id: $entity_id})
                CALL apoc.path.subgraphAll(center, {
                    relationshipFilter: 'ENTITY_RELATED_TO>|WORKS_AT>|LOCATED_IN>|PART_OF>|COLLABORATES_WITH>|INFLUENCES>|CREATED_BY>|CONNECTED_TO>',
                    minLevel: 0,
                    maxLevel: $max_depth,
                    filterStartNode: false
                })
                YIELD nodes, relationships

                WITH [n IN nodes | {
                    id: n.postgres_id,
                    name: n.entity_name,
                    type: n.entity_type,
                    confidence: n.confidence,
                    importance: n.pagerank_score,
                    distance: apoc.path.nodeDistance(center, n)
                }] as node_data,
                [r IN relationships WHERE r.strength >= $min_strength | {
                    source: startNode(r).postgres_id,
                    target: endNode(r).postgres_id,
                    type: r.relationship_type,
                    strength: r.strength,
                    description: r.description
                }] as edge_data

                RETURN node_data, edge_data
                """

                results = self.neo4j_conn.cypher_query(query, {
                    'entity_id': entity_postgres_id,
                    'max_depth': max_depth,
                    'min_strength': min_strength
                })

                if results:
                    nodes, edges = results[0]
                    return {
                        'nodes': nodes,
                        'edges': edges,
                        'node_count': len(nodes),
                        'edge_count': len(edges)
                    }
                else:
                    return {'nodes': [], 'edges': [], 'node_count': 0, 'edge_count': 0}

            except Exception as e:
                self.logger.error(f"Error getting entity subgraph: {e}")
                return {'nodes': [], 'edges': [], 'node_count': 0, 'edge_count': 0}

        return await asyncio.get_event_loop().run_in_executor(self.executor, _get_subgraph)

    async def find_entity_communities(self, user_id: str, algorithm: str = "louvain") -> Dict[str, List[str]]:
        """Detect communities in the user's knowledge graph"""

        def _find_communities():
            try:
                # Create graph projection
                projection_query = f"""
                CALL gds.graph.project(
                    'userCommunities_{user_id}',
                    {{
                        DocumentEntity: {{
                            label: 'DocumentEntity',
                            properties: ['pagerank_score', 'confidence']
                        }}
                    }},
                    {{
                        RELATIONSHIP: {{
                            type: '*',
                            orientation: 'NATURAL',
                            properties: ['strength']
                        }}
                    }},
                    {{
                        nodeQuery: 'MATCH (n:DocumentEntity {{user_id: "{user_id}"}}) RETURN id(n) AS id',
                        relationshipQuery: 'MATCH (s:DocumentEntity {{user_id: "{user_id}"}})-[r]->(t:DocumentEntity {{user_id: "{user_id}"}}) WHERE type(r) IN ["ENTITY_RELATED_TO", "WORKS_AT", "LOCATED_IN", "PART_OF", "COLLABORATES_WITH", "INFLUENCES", "CREATED_BY", "CONNECTED_TO"] RETURN id(s) AS source, id(t) AS target, r.strength AS strength'
                    }}
                )
                """

                # Run community detection
                if algorithm == "louvain":
                    community_query = f"""
                    CALL gds.louvain.write('userCommunities_{user_id}', {{
                        writeProperty: 'community_id',
                        relationshipWeightProperty: 'strength'
                    }})
                    YIELD communityCount, modularity
                    RETURN communityCount, modularity
                    """
                else:  # label propagation
                    community_query = f"""
                    CALL gds.labelPropagation.write('userCommunities_{user_id}', {{
                        writeProperty: 'community_id',
                        relationshipWeightProperty: 'strength'
                    }})
                    YIELD communityCount
                    RETURN communityCount, 0.0 as modularity
                    """

                # Get community assignments
                assignment_query = f"""
                MATCH (e:DocumentEntity {{user_id: $user_id}})
                WHERE exists(e.community_id)
                RETURN e.community_id as community, collect(e.entity_name) as members
                ORDER BY community
                """

                # Clean up projection
                cleanup_query = f"CALL gds.graph.drop('userCommunities_{user_id}')"

                # Execute queries
                self.neo4j_conn.cypher_query(projection_query)
                community_results = self.neo4j_conn.cypher_query(community_query)
                assignment_results = self.neo4j_conn.cypher_query(assignment_query, {'user_id': user_id})
                self.neo4j_conn.cypher_query(cleanup_query)

                communities = {}
                for row in assignment_results:
                    communities[f"community_{row[0]}"] = row[1]

                return communities

            except Exception as e:
                self.logger.error(f"Error finding communities: {e}")
                return {}

        return await asyncio.get_event_loop().run_in_executor(self.executor, _find_communities)

    def close(self):
        """Close the repository and executor"""
        self.executor.shutdown(wait=True)
