# Competency Question and Microtheory Workbench Specification

## Executive Summary

The Competency Question and Microtheory (CQ/MT) Workbench is a Test-Driven Ontology Development (TDOD) tool that enables users to evaluate ontology effectiveness through executable competency questions and isolated microtheory contexts. This specification defines the complete system requirements, architecture, and implementation approach for building a robust CQ/MT management platform within ODRAS.

## Core Concepts

### Competency Questions (CQs)

A **Competency Question (CQ)** represents a fundamental shift in ontology development from building structures in isolation to building systems that answer real questions. Unlike traditional ontology development where engineers focus on creating classes, properties, and relationships, competency questions force developers to think about what questions their ontology needs to answer and how users will interact with the knowledge contained within it. This approach ensures that ontologies are not just technically correct but practically useful.

At its core, a competency question is an executable specification that bridges the gap between human understanding and machine processing. It begins with a natural language question that captures the essence of what information should be retrievable from the ontology. This natural language component serves as both documentation and validation criteria - if the ontology cannot answer the question in human terms, it has failed its primary purpose. The natural language question acts as a contract between the ontology developers and the end users, ensuring that the technical implementation serves real-world needs.

The SPARQL query component transforms the natural language question into an executable form that can be run against the ontology. This query must be carefully crafted to use the ontology's classes, properties, and relationships correctly, ensuring that it accurately represents the intent of the natural language question. The SPARQL query serves as both a test case and a usage example, demonstrating how the ontology should be queried to retrieve the desired information. This executable nature means that competency questions can be automatically validated, providing immediate feedback on whether the ontology meets its requirements.

The validation contract is perhaps the most critical component, as it defines what constitutes a successful answer to the competency question. This contract goes beyond simple query execution to specify the expected structure, content, and quality of the results. It may require specific columns to be present in the results, define minimum or maximum numbers of results, specify performance requirements, or include data quality constraints. The validation contract ensures that the ontology not only returns results but returns the right kind of results in the right format and within acceptable performance parameters.

#### Example
```
Natural Language: "What aircraft types are available for transport missions?"

SPARQL Query: 
SELECT ?aircraft ?type WHERE {
  ?aircraft rdf:type :Aircraft .
  ?aircraft :hasRole :Transport .
  ?aircraft :hasType ?type .
}

Validation Contract:
{
  "require_columns": ["aircraft", "type"],
  "min_rows": 1,
  "max_execution_time_ms": 5000
}
```

#### Key Characteristics
- **Executable**: Must be runnable against an ontology to produce results
- **Validatable**: Must have clear success/failure criteria
- **Parameterizable**: Can accept parameters for flexible testing
- **Traceable**: Linked to specific ontology requirements or use cases

### Microtheories (MTs)

A **Microtheory (MT)** represents a fundamental innovation in ontology testing and validation by providing isolated, controlled environments for evaluating competency questions. Unlike traditional ontology testing approaches that rely on a single, monolithic dataset, microtheories create separate named graph contexts within a Fuseki triplestore, each containing specific test data tailored to particular scenarios or use cases. This isolation ensures that tests are reproducible, predictable, and free from interference from other data or test cases.

The concept of microtheories draws inspiration from the philosophical notion of microtheories in knowledge representation, where complex domains are broken down into smaller, manageable theories that can be independently validated and understood. In the context of ontology development, each microtheory serves as a self-contained knowledge base that represents a specific scenario, domain subset, or test case. This approach allows developers to create highly targeted test environments that focus on particular aspects of their ontology without the complexity and potential conflicts that arise from testing against a large, heterogeneous dataset.

The named graph architecture of microtheories provides both technical and conceptual benefits. From a technical perspective, named graphs in RDF stores like Fuseki allow for precise targeting of queries to specific datasets, enabling developers to run competency questions against exactly the data they want to test. This precision is crucial for debugging ontology issues, as it allows developers to isolate problems to specific data scenarios or ontology components. From a conceptual perspective, named graphs provide a natural way to organize test data into logical, meaningful contexts that correspond to real-world scenarios or domain subsets.

The isolation provided by microtheories is particularly valuable in complex ontology development projects where multiple teams may be working on different aspects of the same domain. Each team can create their own microtheories containing data relevant to their specific work, allowing them to test and validate their contributions without affecting other teams' work. This isolation also enables parallel development and testing, as different microtheories can be developed, modified, and tested independently without coordination overhead.

The clonable nature of microtheories supports iterative development and testing workflows. Developers can start with a baseline microtheory containing fundamental domain data and then create specialized versions for specific test scenarios. This cloning capability enables the creation of test suites that systematically explore different aspects of the ontology, from basic functionality to edge cases and complex scenarios. The ability to clone and modify microtheories also supports the creation of regression test suites that can be run against ontology changes to ensure that modifications don't break existing functionality.

#### Example
```
Microtheory: "Transport Aircraft Baseline"
IRI: http://localhost:8000/mt/project123/transport-baseline
Purpose: Contains baseline data for testing transport aircraft CQs

Content:
:aircraft1 rdf:type :Aircraft .
:aircraft1 :hasRole :Transport .
:aircraft1 :hasType "C-130" .
:aircraft1 :hasCapacity 92 .

:aircraft2 rdf:type :Aircraft .
:aircraft2 :hasRole :Transport .
:aircraft2 :hasType "C-17" .
:aircraft2 :hasCapacity 102 .
```

#### Key Characteristics
- **Isolated**: Each MT is independent and doesn't affect others
- **Named**: Identified by a unique IRI for precise targeting
- **Clonable**: Can be created by copying from existing microtheories
- **Defaultable**: One MT per project can be set as the default context

### Relationship Between CQs and MTs

CQs and MTs work together in a complementary relationship:

1. **CQs Define What**: They specify what questions the ontology should answer
2. **MTs Provide Context**: They provide the specific data context for testing those questions
3. **Execution**: CQs are executed against MTs to validate ontology effectiveness
4. **Evaluation**: Results are compared against validation contracts to determine success

#### Workflow Example
```
1. Define CQ: "What aircraft can carry 100+ passengers?"
2. Create MT: "Passenger Aircraft Test Data" with relevant triples
3. Execute CQ against MT: Run SPARQL query in MT context
4. Validate Results: Check if results meet contract requirements
5. Analyze: Determine if ontology effectively answers the question
```

### Test-Driven Ontology Development (TDOD)

The CQ/MT Workbench implements Test-Driven Ontology Development, where:

1. **CQs Come First**: Define what the ontology should do before building it
2. **MTs Provide Test Data**: Create realistic test scenarios
3. **Ontology Development**: Build ontology to satisfy the CQs
4. **Continuous Testing**: Regularly run CQs to validate ontology changes
5. **Iterative Improvement**: Refine ontology based on CQ results

This approach ensures that ontologies are built to answer real questions and can be validated against specific criteria.

## 1. System Overview

### 1.1 Purpose
The CQ/MT Workbench provides a systematic approach to ontology validation through:
- **Competency Questions (CQs)**: Executable SPARQL queries with validation contracts
- **Microtheories (MTs)**: Isolated named graph contexts for testing CQs
- **Ontology Evaluation**: Running CQs against specific ontologies to measure effectiveness
- **Test-Driven Development**: Building ontologies to satisfy predefined competency questions

### 1.2 Core Workflow
1. **Define Competency Questions**: Create SPARQL-based questions that represent ontology requirements
2. **Establish Microtheories**: Create isolated contexts for testing (baseline, test data, versions)
3. **Select Ontology Context**: Choose which ontology (including imports) to evaluate against
4. **Execute Evaluation**: Run CQs against selected ontology within microtheory context
5. **Analyze Results**: Review pass/fail status, performance metrics, and coverage
6. **Iterate**: Refine ontology based on CQ results

## 2. Functional Requirements

### 2.1 Competency Question Management

#### 2.1.1 CRUD Operations
- **Create**: Define new CQs with name, problem statement, SPARQL template, and validation contract
- **Read**: Display CQs in organized lists with status, last run results, and metadata
- **Update**: Modify existing CQs (all fields editable)
- **Delete**: Remove CQs with confirmation and cascade deletion of run history

#### 2.1.2 CQ Properties
- **Name**: Human-readable identifier
- **Problem Statement**: Natural language description of what the CQ should answer
- **SPARQL Template**: Parameterized SPARQL query with placeholders
- **Validation Contract**: JSON specification defining success criteria
  - Required columns
  - Minimum/maximum row counts
  - Performance thresholds
  - Data quality constraints
- **Default Microtheory**: Preferred MT context for execution
- **Status**: Draft, Active, Deprecated
- **Parameters**: Dynamic parameter definitions for SPARQL templates

#### 2.1.3 Advanced Features
- **Parameter Binding**: Support for dynamic parameter substitution in SPARQL
- **Template Validation**: Syntax checking and ontology compatibility validation
- **Version History**: Track changes to CQs over time
- **Bulk Operations**: Import/export multiple CQs
- **Search and Filter**: Find CQs by name, status, or content

### 2.2 Microtheory Management

#### 2.2.1 CRUD Operations
- **Create**: Define new MTs with label, description, and optional cloning source
- **Read**: Display MTs with triple counts, creation dates, and default status
- **Update**: Modify MT metadata (label, description, default status)
- **Delete**: Remove MTs with confirmation and cleanup of associated data

#### 2.2.2 MT Properties
- **Label**: Human-readable name
- **Description**: Detailed explanation of MT purpose
- **IRI**: Unique identifier (auto-generated or custom)
- **Parent IRI**: Source MT for cloned microtheories
- **Default Status**: Whether this MT is the project default
- **Triple Count**: Number of triples in the named graph
- **Creation Metadata**: Timestamp, creator, project association

#### 2.2.3 Advanced Features
- **Cloning**: Create new MTs based on existing ones
- **Default Management**: Set project-wide default MT
- **Bulk Operations**: Import/export MT definitions
- **Content Management**: View and edit triple content
- **Performance Metrics**: Track MT size and query performance

### 2.3 Ontology Context Management

#### 2.3.1 Ontology Selection
- **Project Ontologies**: List all ontologies registered in the current project
- **Import Handling**: Support for ontologies with imported dependencies
- **Context Switching**: Change evaluation context without losing CQ/MT state
- **Validation**: Ensure selected ontology is accessible and valid

#### 2.3.2 Import Resolution
- **Dependency Tracking**: Understand ontology import relationships
- **Graph Merging**: Handle queries across multiple imported graphs
- **Namespace Management**: Resolve prefixes and namespaces correctly
- **Version Compatibility**: Handle different versions of imported ontologies

### 2.4 CQ Execution and Evaluation

#### 2.4.1 Execution Engine
- **SPARQL Runner**: Execute CQs against selected ontology context
- **Parameter Binding**: Substitute parameters into SPARQL templates
- **Microtheory Context**: Confine queries to specific named graphs
- **Error Handling**: Graceful handling of query failures and timeouts

#### 2.4.2 Validation Framework
- **Contract Validation**: Check results against defined success criteria
- **Performance Monitoring**: Track query execution time and resource usage
- **Result Analysis**: Compare expected vs. actual results
- **Coverage Metrics**: Measure how well CQs exercise the ontology

#### 2.4.3 Execution Features
- **Single CQ Execution**: Run individual CQs with custom parameters
- **Batch Execution**: Run multiple CQs against same context
- **Scheduled Execution**: Automatically run CQs on ontology changes
- **Result Caching**: Store and retrieve previous execution results

### 2.5 Coverage Analysis

#### 2.5.1 Coverage Metrics
- **CQ Coverage**: Percentage of CQs passing/failing
- **Ontology Coverage**: How much of the ontology is exercised by CQs
- **Microtheory Coverage**: CQ success rates across different MTs
- **Temporal Coverage**: Track coverage changes over time

#### 2.5.2 Analysis Features
- **Dashboard**: Visual representation of coverage metrics
- **Trend Analysis**: Track coverage improvements over time
- **Gap Identification**: Identify areas of ontology not covered by CQs
- **Recommendations**: Suggest new CQs based on coverage gaps

### 2.6 AI-Assisted Features

#### 2.6.1 DAS Integration
- **CQ Generation**: Use DAS to generate CQs from natural language requirements
- **SPARQL Assistance**: Get help writing and debugging SPARQL queries
- **Contract Suggestions**: AI-powered validation contract recommendations
- **Ontology Analysis**: DAS-powered analysis of ontology effectiveness

#### 2.6.2 LLM Integration
- **Query Optimization**: AI suggestions for improving SPARQL performance
- **Contract Validation**: LLM-based validation of contract specifications
- **Documentation Generation**: Auto-generate CQ documentation
- **Best Practices**: AI recommendations for CQ/MT design patterns

## 3. Technical Architecture

### 3.1 Frontend Architecture

#### 3.1.1 Component Structure
```
CQMTWorkbench/
├── CQManager/
│   ├── CQList
│   ├── CQEditor
│   ├── CQRunner
│   └── CQHistory
├── MTManager/
│   ├── MTList
│   ├── MTEditor
│   ├── MTContent
│   └── MTCloner
├── OntologyContext/
│   ├── OntologySelector
│   ├── ImportViewer
│   └── ContextSwitcher
├── CoverageAnalysis/
│   ├── CoverageDashboard
│   ├── TrendAnalysis
│   └── GapAnalysis
└── AIAssistant/
    ├── CQGenerator
    ├── SPARQLHelper
    └── ContractValidator
```

#### 3.1.2 State Management
- **Global State**: Project context, selected ontology, active MT
- **CQ State**: Current CQs, selected CQ, execution results
- **MT State**: Current MTs, selected MT, default MT
- **UI State**: Active tabs, modal states, form data

#### 3.1.3 Data Flow
1. **Initialization**: Load project, ontologies, CQs, MTs
2. **Context Selection**: Update ontology context, refresh relevant data
3. **CQ Operations**: CRUD operations with real-time UI updates
4. **MT Operations**: CRUD operations with dependency management
5. **Execution**: Run CQs, update results, refresh coverage
6. **Analysis**: Calculate metrics, update dashboards

### 3.2 Backend Architecture

#### 3.2.1 API Endpoints
```
/api/cqmt/
├── projects/{project_id}/
│   ├── cqs/                    # CQ CRUD operations
│   ├── microtheories/          # MT CRUD operations
│   └── coverage/               # Coverage analysis
├── cqs/{cq_id}/
│   ├── runs/                   # CQ execution history
│   └── execute/                # Execute CQ
├── microtheories/{mt_id}/
│   ├── content/                # MT triple content
│   └── set-default/           # Set as project default
└── ontologies/{ontology_id}/
    └── evaluate/               # Evaluate against ontology
```

#### 3.2.2 Service Layer
- **CQService**: CQ CRUD operations, validation, execution
- **MTService**: MT CRUD operations, content management
- **ExecutionService**: SPARQL execution, result validation
- **CoverageService**: Coverage calculation, trend analysis
- **AIService**: DAS/LLM integration for assistance

#### 3.2.3 Data Models
```sql
-- Competency Questions
CREATE TABLE cqs (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL,
    cq_name VARCHAR(255) NOT NULL,
    problem_text TEXT,
    sparql_template TEXT NOT NULL,
    contract_json JSONB NOT NULL,
    mt_iri_default VARCHAR(500),
    status VARCHAR(50) DEFAULT 'draft',
    params_json JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100)
);

-- Microtheories
CREATE TABLE microtheories (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL,
    label VARCHAR(255) NOT NULL,
    iri VARCHAR(500) NOT NULL UNIQUE,
    description TEXT,
    parent_iri VARCHAR(500),
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100)
);

-- CQ Execution History
CREATE TABLE cq_runs (
    id UUID PRIMARY KEY,
    cq_id UUID NOT NULL,
    mt_iri VARCHAR(500),
    ontology_iri VARCHAR(500),
    params_json JSONB DEFAULT '{}',
    result_json JSONB,
    success BOOLEAN,
    execution_time_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 3.3 Integration Points

#### 3.3.1 Fuseki Integration
- **Named Graphs**: Each MT maps to a Fuseki named graph
- **SPARQL Execution**: Direct Fuseki SPARQL endpoint integration
- **Graph Management**: Create, update, delete named graphs
- **Import Resolution**: Handle ontology imports through Fuseki

#### 3.3.2 DAS Integration
- **CQ Generation**: Natural language to SPARQL conversion
- **Query Assistance**: SPARQL debugging and optimization
- **Contract Validation**: AI-powered contract specification
- **Ontology Analysis**: Effectiveness analysis and recommendations

#### 3.3.3 LLM Integration
- **Query Optimization**: Performance improvement suggestions
- **Documentation**: Auto-generate CQ and MT documentation
- **Best Practices**: Design pattern recommendations
- **Error Analysis**: Intelligent error diagnosis and resolution

## 4. Implementation Plan

### 4.1 Phase 1: Core CRUD Operations (Weeks 1-2)

#### 4.1.1 Backend Implementation
- [ ] Implement CQ CRUD API endpoints
- [ ] Implement MT CRUD API endpoints
- [ ] Create database schema and migrations
- [ ] Implement basic SPARQL execution service
- [ ] Add authentication and authorization

#### 4.1.2 Frontend Implementation
- [ ] Create CQ list and editor components
- [ ] Create MT list and editor components
- [ ] Implement modal-based CRUD operations
- [ ] Add form validation and error handling
- [ ] Integrate with backend APIs

#### 4.1.3 Testing
- [ ] Unit tests for CRUD operations
- [ ] Integration tests for API endpoints
- [ ] Frontend component tests
- [ ] End-to-end CRUD workflow tests

### 4.2 Phase 2: Execution Engine (Weeks 3-4)

#### 4.2.1 Backend Implementation
- [ ] Implement SPARQL execution service
- [ ] Add parameter binding functionality
- [ ] Implement contract validation framework
- [ ] Add execution history tracking
- [ ] Create coverage calculation service

#### 4.2.2 Frontend Implementation
- [ ] Create CQ execution interface
- [ ] Implement result display components
- [ ] Add execution history viewer
- [ ] Create coverage dashboard
- [ ] Add performance monitoring

#### 4.2.3 Testing
- [ ] SPARQL execution tests
- [ ] Contract validation tests
- [ ] Performance benchmarking
- [ ] Error handling tests
- [ ] Coverage calculation validation

### 4.3 Phase 3: Ontology Context Management (Weeks 5-6)

#### 4.3.1 Backend Implementation
- [ ] Implement ontology selection service
- [ ] Add import resolution functionality
- [ ] Create context switching logic
- [ ] Implement namespace management
- [ ] Add ontology validation

#### 4.3.2 Frontend Implementation
- [ ] Create ontology selector component
- [ ] Implement import viewer
- [ ] Add context switching interface
- [ ] Create namespace display
- [ ] Add ontology validation feedback

#### 4.3.3 Testing
- [ ] Ontology selection tests
- [ ] Import resolution tests
- [ ] Context switching tests
- [ ] Namespace handling tests
- [ ] Validation accuracy tests

### 4.4 Phase 4: Advanced Features (Weeks 7-8)

#### 4.4.1 Backend Implementation
- [ ] Implement MT cloning functionality
- [ ] Add bulk import/export features
- [ ] Create advanced search and filtering
- [ ] Implement scheduled execution
- [ ] Add performance optimization

#### 4.4.2 Frontend Implementation
- [ ] Create MT cloning interface
- [ ] Implement bulk operations UI
- [ ] Add advanced search functionality
- [ ] Create scheduling interface
- [ ] Add performance monitoring

#### 4.4.3 Testing
- [ ] Cloning functionality tests
- [ ] Bulk operations tests
- [ ] Search and filter tests
- [ ] Scheduling tests
- [ ] Performance optimization tests

### 4.5 Phase 5: AI Integration (Weeks 9-10)

#### 4.5.1 Backend Implementation
- [ ] Integrate DAS for CQ generation
- [ ] Add LLM-based query optimization
- [ ] Implement AI contract validation
- [ ] Create intelligent error analysis
- [ ] Add recommendation engine

#### 4.5.2 Frontend Implementation
- [ ] Create AI assistant interface
- [ ] Implement CQ generation UI
- [ ] Add query optimization suggestions
- [ ] Create contract validation feedback
- [ ] Add recommendation display

#### 4.5.3 Testing
- [ ] AI integration tests
- [ ] CQ generation accuracy tests
- [ ] Query optimization tests
- [ ] Contract validation tests
- [ ] Recommendation quality tests

## 5. Testing Strategy

### 5.1 Unit Testing
- **Backend Services**: Test individual service methods
- **Frontend Components**: Test component behavior and state
- **API Endpoints**: Test request/response handling
- **Data Models**: Test data validation and constraints

### 5.2 Integration Testing
- **API Integration**: Test frontend-backend communication
- **Database Integration**: Test data persistence and retrieval
- **Fuseki Integration**: Test SPARQL execution and graph management
- **DAS Integration**: Test AI service integration

### 5.3 End-to-End Testing
- **Complete Workflows**: Test full user journeys
- **Cross-Browser Testing**: Ensure compatibility
- **Performance Testing**: Measure response times and resource usage
- **Error Scenario Testing**: Test error handling and recovery

### 5.4 Validation Testing
- **CQ Validation**: Ensure CQs execute correctly
- **MT Validation**: Verify MT content integrity
- **Coverage Validation**: Confirm coverage calculations
- **Contract Validation**: Test validation logic accuracy

## 6. Success Criteria

### 6.1 Functional Requirements
- [ ] All CRUD operations work correctly for CQs and MTs
- [ ] CQ execution produces accurate results
- [ ] Contract validation works as specified
- [ ] Coverage analysis provides meaningful insights
- [ ] AI integration enhances user experience

### 6.2 Performance Requirements
- [ ] CQ execution completes within 30 seconds
- [ ] UI responds within 2 seconds for all operations
- [ ] Coverage calculations complete within 10 seconds
- [ ] System supports 100+ CQs and 20+ MTs per project

### 6.3 Usability Requirements
- [ ] Intuitive user interface for all operations
- [ ] Clear error messages and guidance
- [ ] Comprehensive documentation and help
- [ ] Responsive design for different screen sizes

### 6.4 Reliability Requirements
- [ ] 99.9% uptime for CQ execution
- [ ] Graceful error handling and recovery
- [ ] Data integrity and consistency
- [ ] Backup and recovery procedures

## 7. Risk Mitigation

### 7.1 Technical Risks
- **SPARQL Complexity**: Provide templates and examples
- **Performance Issues**: Implement caching and optimization
- **Integration Failures**: Add fallback mechanisms
- **Data Loss**: Implement backup and versioning

### 7.2 User Experience Risks
- **Learning Curve**: Provide tutorials and documentation
- **Error Confusion**: Implement clear error messages
- **Performance Perception**: Add loading indicators
- **Feature Overload**: Implement progressive disclosure

### 7.3 Business Risks
- **Scope Creep**: Stick to defined requirements
- **Timeline Delays**: Implement agile development
- **Quality Issues**: Implement comprehensive testing
- **User Adoption**: Provide training and support

## 8. Maintenance and Evolution

### 8.1 Ongoing Maintenance
- **Bug Fixes**: Address issues as they arise
- **Performance Optimization**: Continuous improvement
- **Security Updates**: Regular security patches
- **Documentation Updates**: Keep documentation current

### 8.2 Future Enhancements
- **Advanced Analytics**: Deeper coverage analysis
- **Collaboration Features**: Multi-user support
- **Integration Expansion**: Additional ontology tools
- **AI Improvements**: Enhanced AI capabilities

### 8.3 Monitoring and Metrics
- **Usage Analytics**: Track feature usage
- **Performance Metrics**: Monitor system performance
- **Error Tracking**: Identify and resolve issues
- **User Feedback**: Collect and act on feedback

## 9. Conclusion

The CQ/MT Workbench specification provides a comprehensive roadmap for building a robust Test-Driven Ontology Development tool. By following this specification, we can create a system that effectively supports ontology evaluation through competency questions and microtheories, with AI assistance and comprehensive coverage analysis.

The phased implementation approach ensures that core functionality is delivered early while allowing for iterative improvement and feature enhancement. The testing strategy ensures quality and reliability, while the success criteria provide clear metrics for measuring achievement.

This specification serves as the foundation for building a tool that will significantly enhance the ontology development process within ODRAS, providing users with the means to validate and improve their ontologies through systematic testing and evaluation.
