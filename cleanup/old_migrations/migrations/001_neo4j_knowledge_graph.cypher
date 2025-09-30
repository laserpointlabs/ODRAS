// Neo4j Knowledge Graph Schema Setup
// Migration 001: Core knowledge graph structure

// ========================================
// NODE CONSTRAINTS AND INDEXES
// ========================================

// Document nodes (representing source files)
CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;
CREATE INDEX doc_project_id IF NOT EXISTS FOR (d:Document) ON (d.project_id);
CREATE INDEX doc_type IF NOT EXISTS FOR (d:Document) ON (d.document_type);

// Knowledge Asset nodes (processed documents)
CREATE CONSTRAINT asset_id IF NOT EXISTS FOR (a:KnowledgeAsset) REQUIRE a.id IS UNIQUE;
CREATE INDEX asset_project_id IF NOT EXISTS FOR (a:KnowledgeAsset) ON (a.project_id);
CREATE INDEX asset_type IF NOT EXISTS FOR (a:KnowledgeAsset) ON (a.document_type);
CREATE INDEX asset_title IF NOT EXISTS FOR (a:KnowledgeAsset) ON (a.title);

// Chunk nodes (text segments)
CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE;
CREATE INDEX chunk_type IF NOT EXISTS FOR (c:Chunk) ON (c.chunk_type);
CREATE INDEX chunk_sequence IF NOT EXISTS FOR (c:Chunk) ON (c.sequence_number);

// Requirement nodes (extracted requirements)
CREATE CONSTRAINT req_id IF NOT EXISTS FOR (r:Requirement) REQUIRE r.id IS UNIQUE;
CREATE INDEX req_type IF NOT EXISTS FOR (r:Requirement) ON (r.requirement_type);
CREATE INDEX req_priority IF NOT EXISTS FOR (r:Requirement) ON (r.priority);

// Component nodes (system components)
CREATE CONSTRAINT comp_id IF NOT EXISTS FOR (c:Component) REQUIRE c.id IS UNIQUE;
CREATE INDEX comp_type IF NOT EXISTS FOR (c:Component) ON (c.component_type);

// Process nodes (system processes)
CREATE CONSTRAINT proc_id IF NOT EXISTS FOR (p:Process) REQUIRE p.id IS UNIQUE;
CREATE INDEX proc_type IF NOT EXISTS FOR (p:Process) ON (p.process_type);

// Function nodes (system functions)
CREATE CONSTRAINT func_id IF NOT EXISTS FOR (f:Function) REQUIRE f.id IS UNIQUE;
CREATE INDEX func_type IF NOT EXISTS FOR (f:Function) ON (f.function_type);

// Interface nodes (system interfaces)
CREATE CONSTRAINT iface_id IF NOT EXISTS FOR (i:Interface) REQUIRE i.id IS UNIQUE;
CREATE INDEX iface_type IF NOT EXISTS FOR (i:Interface) ON (i.interface_type);

// Condition nodes (operational conditions)
CREATE CONSTRAINT cond_id IF NOT EXISTS FOR (c:Condition) REQUIRE c.id IS UNIQUE;
CREATE INDEX cond_type IF NOT EXISTS FOR (c:Condition) ON (c.condition_type);

// ========================================
// RELATIONSHIP TYPES AND PROPERTIES
// ========================================

// Document structure relationships
// (:Document)-[:CONTAINS]->(:KnowledgeAsset)
// (:KnowledgeAsset)-[:DIVIDED_INTO]->(:Chunk)
// (:Chunk)-[:NEXT_CHUNK]->(:Chunk) // sequence ordering

// Knowledge extraction relationships  
// (:Chunk)-[:REFERENCES]->(:Requirement)
// (:Chunk)-[:MENTIONS]->(:Component)
// (:Chunk)-[:DESCRIBES]->(:Process)

// ODRAS Ontology relationships
// (:Requirement)-[:HAS_CONSTRAINT]->(:Constraint)
// (:Requirement)-[:DEPLOYS]->(:Component)
// (:Component)-[:PRESENTS]->(:Interface)
// (:Component)-[:PERFORMS]->(:Process)
// (:Process)-[:REALIZES]->(:Function)
// (:Function)-[:ACTIVATES_ON]->(:Condition)
// (:Function)-[:DEPENDS_UPON]->(:Component)

// Requirements traceability relationships
// (:Requirement)-[:DEPENDS_ON]->(:Requirement)
// (:Requirement)-[:IMPLEMENTS]->(:Requirement)
// (:Requirement)-[:DERIVES_FROM]->(:Requirement)
// (:Requirement)-[:VERIFIED_BY]->(:TestCase)

// Document cross-references
// (:Document)-[:CITES]->(:Document)
// (:KnowledgeAsset)-[:REFERENCES]->(:KnowledgeAsset)

// ========================================
// SAMPLE DATA STRUCTURE (for documentation)
// ========================================

// Example document and knowledge asset creation:
//
// CREATE (doc:Document {
//   id: "file-123",
//   filename: "GPS_Requirements_v2.1.pdf", 
//   project_id: "proj-456",
//   document_type: "requirements",
//   upload_date: datetime(),
//   file_size: 1024000,
//   content_type: "application/pdf"
// })
//
// CREATE (asset:KnowledgeAsset {
//   id: "asset-789",
//   title: "GPS Navigation Requirements",
//   project_id: "proj-456", 
//   document_type: "requirements",
//   created_at: datetime(),
//   chunk_count: 42,
//   token_count: 15000,
//   processing_status: "completed"
// })
//
// CREATE (chunk:Chunk {
//   id: "chunk-101",
//   content: "The GPS system shall provide location accuracy within ±3 meters...",
//   chunk_type: "text",
//   sequence_number: 1,
//   token_count: 84,
//   qdrant_point_id: "vector-uuid-here"
// })
//
// CREATE (req:Requirement {
//   id: "REQ-001",
//   text: "GPS accuracy shall be ±3 meters",
//   requirement_type: "functional",
//   priority: "high",
//   confidence_score: 0.95
// })
//
// // Create relationships
// CREATE (doc)-[:CONTAINS]->(asset)
// CREATE (asset)-[:DIVIDED_INTO]->(chunk)  
// CREATE (chunk)-[:REFERENCES]->(req)

// ========================================
// UTILITY QUERIES FOR ADMINISTRATION
// ========================================

// Query to check graph schema:
// CALL db.schema.visualization()

// Query to count nodes by type:
// MATCH (n) RETURN labels(n) as node_type, count(n) as count ORDER BY count DESC

// Query to find relationships between asset types:
// MATCH (a)-[r]->(b) 
// WHERE labels(a) <> labels(b)
// RETURN labels(a)[0] as from_type, type(r) as relationship, labels(b)[0] as to_type, count(*) as count
// ORDER BY count DESC

// ========================================
// CLEANUP UTILITIES (for development)
// ========================================

// Clear all knowledge management data (USE WITH CAUTION):
// MATCH (n) WHERE any(label IN labels(n) WHERE label IN ['Document', 'KnowledgeAsset', 'Chunk', 'Requirement', 'Component', 'Process', 'Function', 'Interface', 'Condition'])
// DETACH DELETE n

// ========================================
// PERFORMANCE OPTIMIZATIONS
// ========================================

// For production, consider these additional indexes based on query patterns:
// CREATE INDEX chunk_content_fulltext IF NOT EXISTS FOR (c:Chunk) ON (c.content)
// CREATE INDEX req_text_fulltext IF NOT EXISTS FOR (r:Requirement) ON (r.text)

// For relationship performance:
// CREATE INDEX rel_confidence IF NOT EXISTS FOR ()-[r:REFERENCES]-() ON (r.confidence_score)
// CREATE INDEX rel_created IF NOT EXISTS FOR ()-[r]-() ON (r.created_at)
