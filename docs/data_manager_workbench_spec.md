# Data Manager Workbench Specification<br>
<br>
## Overview<br>
<br>
The Data Manager Workbench is a new ODRAS component that bridges the gap between ontology data properties and real-world data sources. It enables users to create "data pipes" that connect semantic models to operational data, maintaining the benefits of ontological reasoning while working with live data.<br>
<br>
## Core Concepts<br>
<br>
### Data Properties in Ontologies<br>
In RDF/OWL ontologies, data properties link individuals to literal values (strings, numbers, dates, etc.). The Data Manager Workbench activates these properties by:<br>
- Automatically detecting data properties defined in the project ontology<br>
- Creating configurable connections to external data sources<br>
- Maintaining semantic consistency while enabling dynamic data integration<br>
<br>
### Data Pipes<br>
A data pipe is a configured connection between an ontology data property and an external data source. Each pipe defines:<br>
- Source connection (database, API, file, etc.)<br>
- Mapping rules (how external data maps to RDF literals)<br>
- Transformation logic (data type conversion, validation)<br>
- Refresh strategy (real-time, scheduled, manual)<br>
<br>
## Architecture<br>
<br>
```mermaid<br>
graph TB<br>
    subgraph "Project Ontology"<br>
        DP[Data Properties]<br>
        OP[Object Properties]<br>
        CL[Classes]<br>
    end<br>
<br>
    subgraph "Data Manager Workbench"<br>
        DD[Property Detector]<br>
        PC[Pipe Configuration]<br>
        ME[Mapping Engine]<br>
        TE[Transformation Engine]<br>
        SE[Sync Engine]<br>
    end<br>
<br>
    subgraph "External Sources"<br>
        DB[(Databases)]<br>
        API[REST/GraphQL APIs]<br>
        FL[Files/Documents]<br>
        ON[Other Ontologies]<br>
    end<br>
<br>
    subgraph "Storage"<br>
        TS[(Triple Store)]<br>
        VS[(Vector Store)]<br>
        MD[(Metadata DB)]<br>
    end<br>
<br>
    DP --> DD<br>
    DD --> PC<br>
    PC --> ME<br>
    ME --> TE<br>
    TE --> SE<br>
<br>
    SE --> DB<br>
    SE --> API<br>
    SE --> FL<br>
    SE --> ON<br>
<br>
    SE --> TS<br>
    SE --> MD<br>
```<br>
<br>
## Best Practices for Ontology Data Integration<br>
<br>
### 1. Semantic Consistency<br>
- **Maintain Domain/Range Constraints**: Ensure external data respects the ontology's domain and range definitions<br>
- **Type Safety**: Validate data types match RDF datatypes (xsd:string, xsd:integer, xsd:dateTime, etc.)<br>
- **Cardinality Rules**: Respect min/max cardinality constraints defined in the ontology<br>
<br>
### 2. Data Provenance<br>
- **Source Tracking**: Record the origin of each data value<br>
- **Timestamp Management**: Track when data was fetched and last updated<br>
- **Version Control**: Maintain history of data changes<br>
- **Quality Indicators**: Record confidence scores and validation results<br>
<br>
### 3. Integration Patterns<br>
<br>
#### R2RML (RDB to RDF Mapping Language)<br>
For relational databases, follow W3C R2RML standards:<br>
```turtle<br>
@prefix rr: <http://www.w3.org/ns/r2rml#> .<br>
@prefix odras: <http://odras.local/onto/> .<br>
<br>
:CustomerMapping a rr:TriplesMap ;<br>
    rr:logicalTable [ rr:tableName "customers" ] ;<br>
    rr:subjectMap [<br>
        rr:template "http://odras.local/data/customer/{id}" ;<br>
        rr:class odras:Customer<br>
    ] ;<br>
    rr:predicateObjectMap [<br>
        rr:predicate odras:customerName ;<br>
        rr:objectMap [ rr:column "name" ]<br>
    ] ;<br>
    rr:predicateObjectMap [<br>
        rr:predicate odras:revenue ;<br>
        rr:objectMap [<br>
            rr:column "annual_revenue" ;<br>
            rr:datatype xsd:decimal<br>
        ]<br>
    ] .<br>
```<br>
<br>
#### API Integration Pattern<br>
For REST/GraphQL APIs:<br>
```json<br>
{<br>
  "pipe_config": {<br>
    "source_type": "rest_api",<br>
    "endpoint": "https://api.example.com/sensors/{sensor_id}",<br>
    "auth": {<br>
      "type": "bearer",<br>
      "token_ref": "vault://api_tokens/sensor_api"<br>
    },<br>
    "mapping": {<br>
      "odras:temperature": "$.current_temp",<br>
      "odras:humidity": "$.current_humidity",<br>
      "odras:lastReading": {<br>
        "path": "$.timestamp",<br>
        "transform": "iso8601_to_xsd_datetime"<br>
      }<br>
    }<br>
  }<br>
}<br>
```<br>
<br>
### 4. Performance Optimization<br>
- **Lazy Loading**: Fetch data only when needed<br>
- **Caching Strategy**: Implement TTL-based caching for frequently accessed data<br>
- **Batch Operations**: Process multiple entities in single queries<br>
- **Incremental Updates**: Only sync changed data<br>
<br>
### 5. Error Handling<br>
- **Graceful Degradation**: System continues with cached data if source unavailable<br>
- **Validation Pipelines**: Validate data before committing to triple store<br>
- **Retry Logic**: Implement exponential backoff for transient failures<br>
- **Alert Mechanisms**: Notify users of persistent sync failures<br>
<br>
## Data Pipe Types<br>
<br>
### 1. Database Connections<br>
**Supported Databases:**<br>
- PostgreSQL, MySQL, SQLite (via R2RML)<br>
- MongoDB (via JSON-LD mapping)<br>
- Neo4j (direct RDF export)<br>
- TimescaleDB (time-series data)<br>
<br>
**Configuration Example:**<br>
```yaml<br>
pipe_type: database<br>
connection:<br>
  driver: postgresql<br>
  host: localhost<br>
  port: 5432<br>
  database: operational_data<br>
  credentials_ref: vault://db_creds/postgres_prod<br>
mapping:<br>
  query: |<br>
    SELECT id, name, value, updated_at<br>
    FROM sensor_readings<br>
    WHERE sensor_type = 'temperature'<br>
  bindings:<br>
    odras:sensorId: id<br>
    odras:sensorName: name<br>
    odras:temperatureValue: value<br>
    odras:readingTime: updated_at<br>
```<br>
<br>
### 2. API Integrations<br>
**Supported Protocols:**<br>
- REST (JSON, XML)<br>
- GraphQL<br>
- SOAP (legacy systems)<br>
- WebSocket (real-time)<br>
<br>
**Features:**<br>
- Authentication management (OAuth2, API keys, JWT)<br>
- Rate limiting and quota management<br>
- Response transformation<br>
- Error handling and retries<br>
<br>
### 3. File-Based Sources<br>
**Supported Formats:**<br>
- CSV/TSV with header mapping<br>
- Excel with sheet/range selection<br>
- JSON with JSONPath queries<br>
- XML with XPath queries<br>
- CAD metadata (via specialized parsers)<br>
<br>
**Processing:**<br>
- Change detection (file hash, modified date)<br>
- Incremental processing for large files<br>
- Schema validation<br>
- Format conversion<br>
<br>
### 4. Ontology-to-Ontology<br>
**Use Cases:**<br>
- Import instance data from published ontologies<br>
- Cross-project data sharing<br>
- Federation of distributed knowledge<br>
<br>
**Implementation:**<br>
- SPARQL Federation for live queries<br>
- Materialized views for performance<br>
- Access control integration<br>
<br>
## MVP Implementation Plan<br>
<br>
### Phase 1: Foundation (Week 1)<br>
1. **Database Schema**<br>
   - Create data_pipes table<br>
   - Design execution history tracking<br>
   - Implement credential management<br>
<br>
2. **Property Detection Service**<br>
   - Monitor ontology for data property changes<br>
   - Generate default pipe configurations<br>
   - Notify UI of new properties<br>
<br>
3. **Basic UI Components**<br>
   - Data property browser<br>
   - Pipe configuration form<br>
   - Connection test interface<br>
<br>
### Phase 2: Core Functionality (Week 1-2)<br>
1. **Database Integration**<br>
   - PostgreSQL connector<br>
   - Basic R2RML mapping<br>
   - Query builder UI<br>
<br>
2. **Mapping Engine**<br>
   - Simple field-to-property mapping<br>
   - Basic data type conversion<br>
   - Validation rules<br>
<br>
3. **Sync Execution**<br>
   - Manual sync trigger<br>
   - Progress monitoring<br>
   - Error reporting<br>
<br>
### Phase 3: MVP Completion (Week 2)<br>
1. **API Integration (Basic)**<br>
   - REST API connector<br>
   - JSON mapping<br>
   - Authentication support<br>
<br>
2. **Monitoring Dashboard**<br>
   - Sync history view<br>
   - Performance metrics<br>
   - Error logs<br>
<br>
3. **Testing & Documentation**<br>
   - Integration tests<br>
   - User documentation<br>
   - Best practices guide<br>
<br>
## Security Considerations<br>
<br>
### Credential Management<br>
- Use vault/secret management service<br>
- Encrypt credentials at rest<br>
- Audit credential access<br>
- Rotate credentials regularly<br>
<br>
### Data Access Control<br>
- Respect project boundaries<br>
- Implement row-level security where applicable<br>
- Log all data access<br>
- Support data masking/redaction<br>
<br>
### Network Security<br>
- Use SSL/TLS for all connections<br>
- Implement IP whitelisting<br>
- Support VPN/private endpoints<br>
- Monitor for anomalous access patterns<br>
<br>
## Test Data Integration<br>
<br>
The Data Manager Workbench includes comprehensive test data for validation and development:<br>
<br>
### Available Test Data<br>
1. **PostgreSQL Test Schema** (`odras_test`)<br>
   - Aircraft components table with 4 sample components<br>
   - Time-series sensor readings (1,344 data points)<br>
   - Compliance records linking to requirements<br>
<br>
2. **Mock REST API** (Port 8888)<br>
   - Maintenance history endpoint<br>
   - Weather conditions API<br>
   - Supply chain data service<br>
<br>
3. **CAD File Samples**<br>
   - STL files for 4 components<br>
   - JSON metadata with material properties<br>
   - Demonstrates file-based data extraction<br>
<br>
4. **Test Ontology Properties**<br>
   - 7 data properties for aerospace domain<br>
   - Covers various data types (string, decimal, date, integer)<br>
   - Includes units and constraints<br>
<br>
### Quick Test Setup<br>
```bash<br>
# Run complete test environment setup<br>
./scripts/setup_test_data.sh<br>
<br>
# This will:<br>
# 1. Create PostgreSQL test schema and data<br>
# 2. Start mock API server on port 8888<br>
# 3. Generate CAD test files<br>
# 4. Load test ontology properties<br>
# 5. Create sample data pipe configurations<br>
```<br>
<br>
For detailed setup instructions, see [Test Data Setup Guide](./test_data_setup_guide.md).<br>
<br>
## User Interface Design<br>
<br>
### Main Dashboard<br>
```<br>
┌─────────────────────────────────────────────────────┐<br>
│ Data Manager Workbench                              │<br>
├─────────────────────────────────────────────────────┤<br>
│ ┌─────────────┐ ┌─────────────────────────────────┐ │<br>
│ │ Properties  │ │ Data Pipe Configuration         │ │<br>
│ │             │ │                                 │ │<br>
│ │ ✓ revenue   │ │ Property: odras:revenue         │ │<br>
│ │ ○ temperat. │ │ Source: PostgreSQL Database     │ │<br>
│ │ ○ location  │ │ Status: ● Active                │ │<br>
│ │ + Add New   │ │                                 │ │<br>
│ └─────────────┘ │ Mapping:                        │ │<br>
│                 │ ┌─────────────┬───────────────┐ │ │<br>
│ Recent Syncs    │ │ DB Column   │ RDF Property  │ │ │<br>
│ ┌─────────────┐ │ ├─────────────┼───────────────┤ │ │<br>
│ │ ✓ Success   │ │ │ revenue     │ odras:revenue │ │ │<br>
│ │ ⚠ Warning   │ │ └─────────────┴───────────────┘ │ │<br>
│ │ ✗ Failed    │ │                                 │ │<br>
│ └─────────────┘ │ [Test] [Save] [Run Sync]        │ │<br>
│                 └─────────────────────────────────┘ │<br>
└─────────────────────────────────────────────────────┘<br>
```<br>
<br>
### Mapping Interface<br>
- Visual mapping between source and target<br>
- Drag-and-drop field connections<br>
- Transformation preview<br>
- Validation indicators<br>
<br>
## Future Enhancements<br>
<br>
### Advanced Features<br>
1. **Complex Transformations**<br>
   - Custom transformation functions<br>
   - Multi-source joins<br>
   - Aggregation operations<br>
<br>
2. **Real-time Streaming**<br>
   - WebSocket connections<br>
   - Change data capture (CDC)<br>
   - Event-driven updates<br>
<br>
3. **Machine Learning Integration**<br>
   - Data quality scoring<br>
   - Anomaly detection<br>
   - Automated mapping suggestions<br>
<br>
4. **Visualization**<br>
   - Data lineage graphs<br>
   - Impact analysis<br>
   - Quality dashboards<br>
<br>
### Integration Possibilities<br>
- BPMN workflow integration<br>
- Knowledge graph enrichment<br>
- Automated reasoning triggers<br>
- Cross-ontology federation<br>
<br>
## Success Metrics<br>
<br>
### MVP Metrics<br>
- Number of data properties successfully mapped<br>
- Sync success rate (target: >95%)<br>
- Average sync execution time<br>
- User task completion rate<br>
<br>
### Quality Indicators<br>
- Data validation pass rate<br>
- Mapping accuracy scores<br>
- System uptime<br>
- Error resolution time<br>
<br>
## Conclusion<br>
<br>
The Data Manager Workbench bridges the semantic and operational data worlds, enabling ODRAS to work with live data while maintaining ontological consistency. By following established best practices and standards, we ensure the system is robust, scalable, and semantically sound.<br>
<br>
This MVP focuses on core functionality with clear extension points for future enhancement, providing immediate value while building toward a comprehensive data integration platform.<br>

