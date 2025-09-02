#!/usr/bin/env python3
"""
Populate knowledge management system with sample assets for demonstration
"""
import requests
import json
import tempfile
import os
import time

# Sample documents with diverse content
SAMPLE_DOCUMENTS = {
    "aviation_safety_requirements.md": """# Aviation Safety Requirements - AS-9001

## Overview
This document outlines critical safety requirements for commercial aviation systems.

## Primary Safety Requirements

### Flight Control Systems
- **REQ-AS-001**: Primary flight control systems shall maintain 99.99% availability
- **REQ-AS-002**: Backup flight control systems must engage within 50ms of primary failure
- **REQ-AS-003**: Pilot override capability must be available at all times

### Navigation and Communication
- **REQ-AS-004**: GPS positioning accuracy shall be within 1 meter for precision approaches  
- **REQ-AS-005**: Communication systems shall support encrypted voice and data transmission
- **REQ-AS-006**: Navigation displays must update position data every 100ms

### Emergency Systems
- **REQ-AS-007**: Emergency oxygen systems shall provide 15+ minutes of breathable air
- **REQ-AS-008**: Emergency landing systems must deploy within 2 seconds when activated
- **REQ-AS-009**: Fire suppression systems shall activate automatically upon smoke detection

## Compliance Standards
All requirements must comply with FAA Part 25, EASA CS-25, and RTCA DO-178C standards.

## Testing and Validation
Each requirement must pass rigorous testing including:
- Unit testing with 100% code coverage
- Integration testing across all system interfaces  
- Hardware-in-the-loop simulation
- Flight test validation

*Document Classification: CONFIDENTIAL*
*Last Updated: March 2024*""",

    "cybersecurity_framework.md": """# Cybersecurity Framework Implementation Guide

## Executive Summary
This framework establishes cybersecurity standards for enterprise systems based on NIST Cybersecurity Framework v1.1.

## Core Functions

### 1. IDENTIFY (ID)
Asset management and risk assessment protocols:
- **ID.AM-1**: Physical devices and systems are inventoried and managed
- **ID.AM-2**: Software platforms and applications are inventoried and managed  
- **ID.AM-3**: Organizational communication and data flows are mapped
- **ID.RA-1**: Asset vulnerabilities are identified and documented

### 2. PROTECT (PR)
Access control and protective measures:
- **PR.AC-1**: Identities and credentials are issued, managed, verified, revoked
- **PR.AC-4**: Access permissions are managed, incorporating least privilege
- **PR.DS-1**: Data-at-rest is protected through encryption (AES-256 minimum)
- **PR.DS-2**: Data-in-transit is protected through TLS 1.3 or higher

### 3. DETECT (DE)
Continuous monitoring and anomaly detection:
- **DE.AE-1**: Network baseline is established and managed
- **DE.AE-2**: Detected events are analyzed to understand attack targets
- **DE.CM-1**: Network monitoring performs continuous surveillance
- **DE.CM-7**: Network monitoring detects unauthorized personnel, connections, devices

### 4. RESPOND (RS)
Incident response and communication:
- **RS.RP-1**: Response plan is executed during or after an incident
- **RS.CO-2**: Incidents are reported consistent with established criteria
- **RS.AN-1**: Notifications are sent to internal and external stakeholders
- **RS.MI-2**: Incidents are mitigated to prevent expansion and increase effectiveness

### 5. RECOVER (RC)
Recovery planning and improvements:
- **RC.RP-1**: Recovery plan is executed during or after a cybersecurity incident
- **RC.IM-1**: Recovery plans incorporate lessons learned into future activities
- **RC.CO-3**: Recovery activities are communicated to stakeholders

## Implementation Timeline
- Phase 1 (Months 1-3): Identity and Asset Management
- Phase 2 (Months 4-6): Protection and Access Controls
- Phase 3 (Months 7-9): Detection and Monitoring
- Phase 4 (Months 10-12): Response and Recovery

## Risk Assessment Matrix
| Risk Level | Impact | Likelihood | Response Time |
|------------|---------|------------|---------------|
| Critical   | High    | High       | 1 hour        |
| High       | High    | Medium     | 4 hours       |
| Medium     | Medium  | Medium     | 24 hours      |
| Low        | Low     | Low        | 72 hours      |

*Classification: INTERNAL USE ONLY*""",

    "agile_development_process.md": """# Agile Software Development Process Guide

## Introduction
This document defines our agile development methodology combining Scrum and Kanban practices for optimal team productivity.

## Development Lifecycle

### Sprint Planning (2-week sprints)
**Sprint Goals:**
- Deliver working software increments
- Maintain sustainable development pace
- Maximize business value delivery
- Ensure high code quality standards

**Planning Process:**
1. **Backlog Refinement** (2 hours)
   - Review user stories with Product Owner
   - Estimate story points using planning poker
   - Define acceptance criteria and definition of done
   
2. **Capacity Planning**
   - Team velocity: 25-35 story points per sprint
   - Account for holidays, meetings, and technical debt
   - Reserve 20% capacity for bug fixes and support

### Daily Operations

**Daily Standups (15 minutes)**
- What did I complete yesterday?
- What will I work on today?
- What blockers do I have?
- Update sprint burndown chart

**Code Quality Standards:**
- Test-driven development (TDD) required
- Minimum 80% code coverage for new features
- All code must pass peer review
- Automated testing in CI/CD pipeline

### Sprint Review and Retrospective

**Sprint Review (1 hour)**
- Demo completed features to stakeholders
- Gather feedback on product increment
- Update product backlog based on feedback

**Sprint Retrospective (1 hour)**
- What went well this sprint?
- What could be improved?
- What will we commit to improve next sprint?
- Update team working agreements

## Quality Assurance

### Definition of Done
- [ ] Feature functionality complete
- [ ] Unit tests written and passing
- [ ] Integration tests passing
- [ ] Code reviewed and approved
- [ ] Documentation updated
- [ ] Security review completed (if applicable)
- [ ] Performance testing completed (if applicable)

### Technical Debt Management
- Allocate 15% of each sprint to technical debt reduction
- Track technical debt in backlog with labels
- Regular architecture reviews to identify systemic issues

## Tools and Technology Stack

**Project Management:**
- Jira for backlog and sprint management
- Confluence for documentation
- Slack for team communication

**Development:**
- Git for version control with feature branch workflow
- Jenkins for continuous integration
- Docker for containerization
- Kubernetes for orchestration

**Quality Assurance:**
- Jest for JavaScript unit testing
- Cypress for end-to-end testing
- SonarQube for code quality analysis
- OWASP ZAP for security testing

## Team Roles and Responsibilities

**Product Owner:**
- Manages product backlog
- Defines user stories and acceptance criteria
- Makes prioritization decisions
- Serves as business stakeholder liaison

**Scrum Master:**
- Facilitates scrum ceremonies
- Removes blockers for development team
- Coaches team on agile practices
- Protects team from external distractions

**Development Team:**
- Self-organizing and cross-functional
- Estimates work and commits to sprint goals
- Delivers working software each sprint
- Continuously improves processes

*Document Version: 2.1*
*Effective Date: January 2024*""",

    "data_governance_policy.md": """# Enterprise Data Governance Policy

## Policy Statement
This policy establishes comprehensive data governance framework to ensure data quality, security, compliance, and strategic value across the organization.

## Data Classification Framework

### 1. Public Data
- Marketing materials and public website content
- Published research papers and whitepapers
- Job postings and corporate announcements
- **Security Requirements:** Basic integrity controls

### 2. Internal Data  
- Employee directories and organizational charts
- Internal process documentation
- Training materials and policies
- **Security Requirements:** Access authentication required

### 3. Confidential Data
- Customer personal information (PII)
- Financial records and business plans
- Strategic partnerships and contracts
- **Security Requirements:** Encryption at rest and in transit, role-based access

### 4. Highly Confidential Data
- Trade secrets and intellectual property
- Merger and acquisition information  
- Executive compensation details
- **Security Requirements:** Multi-factor authentication, data loss prevention, audit logging

## Data Quality Standards

### Accuracy Standards
- Financial data: 99.95% accuracy requirement
- Customer data: 99.9% accuracy requirement  
- Operational data: 99.5% accuracy requirement
- Reference data: 100% accuracy requirement

### Completeness Requirements
- Critical data fields: 100% completion required
- Important data fields: 95% completion target
- Optional data fields: No minimum requirement

### Data Validation Rules
1. **Format Validation**
   - Email addresses must follow RFC 5322 standard
   - Phone numbers must include country code
   - Dates must use ISO 8601 format (YYYY-MM-DD)

2. **Business Rule Validation**
   - Customer age must be between 13-120 years
   - Order amounts must be positive values
   - Employee start dates cannot be in the future

## Data Lifecycle Management

### Data Creation and Acquisition
- All new data sources must be approved by Data Governance Committee
- Data quality assessment required before production use
- Privacy impact assessment for personal data
- Service level agreements defined with external data providers

### Data Storage and Retention
- **Structured Data:** Minimum 7 years retention for financial records
- **Personal Data:** Retention based on business need and legal requirements
- **Log Data:** 13 months retention for security and audit purposes
- **Backup Data:** 3-2-1 backup strategy implementation

### Data Archival and Disposal
- Automated archival after retention period expires
- Secure disposal using NIST 800-88 guidelines
- Certificate of destruction for highly confidential data
- Legal hold procedures for litigation support

## Privacy and Compliance

### GDPR Compliance (European customers)
- Lawful basis documented for all personal data processing
- Data subject rights implemented (access, rectification, erasure)
- Privacy by design principles in all system development
- Data Protection Impact Assessments for high-risk processing

### CCPA Compliance (California residents)  
- Consumer rights to know, delete, and opt-out implemented
- Third-party data sharing disclosures maintained
- Verified consumer request processes established
- Annual compliance training for all employees

### Industry-Specific Regulations
- **Healthcare (HIPAA):** PHI protection and breach notification
- **Financial (SOX):** Financial data integrity and audit trails
- **Education (FERPA):** Student record privacy protection

## Data Governance Organization

### Data Governance Committee
- **Chair:** Chief Data Officer
- **Members:** Legal, IT, Privacy, Security, Business Unit Representatives
- **Meetings:** Monthly steering committee, quarterly full committee
- **Responsibilities:** Policy oversight, issue escalation, strategic decisions

### Data Stewards (by domain)
- **Customer Data:** Marketing and Sales leadership
- **Financial Data:** Finance and Accounting leadership  
- **Employee Data:** Human Resources leadership
- **Product Data:** Engineering and Product leadership

### Data Custodians (technical implementation)
- Database administrators
- System administrators  
- Application developers
- Security engineers

## Metrics and Reporting

### Key Performance Indicators
- Data quality score: Target >95% across all domains
- Privacy compliance: Zero material breaches annually
- Data governance maturity: Level 4 (Managed) by end of year
- Time to resolve data issues: <48 hours for critical issues

### Monthly Reporting Dashboard
- Data quality trends by business domain
- Privacy request fulfillment metrics  
- Security incident summaries
- Compliance audit findings status

*Policy Owner: Chief Data Officer*
*Next Review Date: December 2024*
*Classification: INTERNAL*""",

    "disaster_recovery_plan.md": """# IT Disaster Recovery Plan (DRP)

## Executive Summary
This document outlines procedures for maintaining IT services during disasters and ensuring rapid recovery of critical business operations.

## Business Impact Analysis

### Critical Systems (RTO: 4 hours, RPO: 1 hour)
1. **Customer-facing Web Applications**
   - E-commerce platform
   - Customer support portal
   - Mobile applications
   - **Impact:** Direct revenue loss, customer satisfaction

2. **Financial Systems**
   - Accounting and ERP system
   - Payment processing systems
   - Payroll system
   - **Impact:** Regulatory compliance, cash flow

3. **Communication Systems**  
   - Email infrastructure
   - VoIP phone systems
   - Instant messaging platforms
   - **Impact:** Internal/external communication breakdown

### Important Systems (RTO: 24 hours, RPO: 4 hours)
- Human Resources Information System (HRIS)
- Project management tools
- Development and testing environments
- **Impact:** Productivity reduction, project delays

### Non-Critical Systems (RTO: 72 hours, RPO: 24 hours)
- Training and learning management systems
- Archive and document management
- Secondary reporting systems
- **Impact:** Minor operational inconvenience

## Disaster Scenarios and Response

### Scenario 1: Data Center Outage
**Probability:** Medium | **Impact:** High

**Immediate Response (0-1 hour):**
1. Activate Incident Commander (IT Director)
2. Assess scope and estimated duration
3. Notify Crisis Management Team
4. Initiate failover to backup data center

**Short-term Response (1-8 hours):**
1. Execute application failover procedures
2. Redirect network traffic to backup site
3. Verify system functionality and performance
4. Communicate status to stakeholders

**Recovery Actions:**
1. Coordinate with data center provider
2. Test primary systems before failback
3. Schedule maintenance window for failback
4. Conduct post-incident review

### Scenario 2: Cyberattack/Ransomware
**Probability:** High | **Impact:** Critical

**Immediate Response (0-2 hours):**
1. Isolate affected systems from network
2. Activate Cybersecurity Incident Response Team
3. Preserve forensic evidence
4. Assess encryption/data loss scope

**Containment (2-24 hours):**
1. Implement network segmentation
2. Reset all administrative credentials  
3. Deploy additional monitoring tools
4. Engage external cybersecurity experts

**Recovery Actions:**
1. Rebuild systems from clean backups
2. Apply all security patches and updates
3. Implement additional security controls
4. File required regulatory notifications

### Scenario 3: Natural Disaster
**Probability:** Low | **Impact:** Critical

**Immediate Response:**
1. Ensure employee safety first
2. Assess facility damage and accessibility
3. Activate alternate work locations
4. Deploy mobile equipment as needed

**Business Continuity:**
1. Implement work-from-home procedures
2. Activate backup communication channels
3. Utilize cloud-based systems and services
4. Coordinate with emergency services

## Recovery Procedures

### Database Recovery
1. **Assessment Phase**
   - Verify backup integrity and timestamp
   - Determine last known good state
   - Calculate acceptable data loss window

2. **Restoration Phase**
   - Restore database to clean environment
   - Apply transaction log backups if available
   - Verify data consistency and integrity

3. **Validation Phase**
   - Execute data validation scripts
   - Perform application connectivity tests
   - Confirm with business stakeholders

### Application Recovery
1. **Infrastructure Preparation**
   - Provision compute and storage resources
   - Configure network connectivity
   - Install and configure operating systems

2. **Application Deployment**
   - Deploy application code from repository
   - Configure application settings
   - Establish database connections

3. **Testing and Validation**
   - Execute smoke tests and health checks
   - Perform user acceptance testing
   - Load testing for performance validation

## Communication Plan

### Internal Communications
- **Executive Team:** Immediate notification via SMS/call
- **IT Staff:** Slack channel #disaster-response
- **All Employees:** Email and company intranet
- **Update Frequency:** Every 2 hours during active incident

### External Communications
- **Customers:** Website banner, email notifications, social media
- **Vendors/Partners:** Direct phone calls to primary contacts  
- **Regulatory Bodies:** Formal notification per compliance requirements
- **Media:** Only through designated spokesperson

### Communication Templates
Pre-approved message templates stored in multiple locations:
- Initial incident notification
- Status update during recovery
- Service restoration announcement
- Post-incident summary report

## Testing and Maintenance

### Quarterly Tests
- **Backup Restoration:** Full restore of critical databases
- **Failover Testing:** Application and network failover procedures
- **Communication Testing:** Notification systems and contact lists

### Annual Tests  
- **Full-Scale Simulation:** Complete disaster scenario exercise
- **Tabletop Exercises:** Cross-team coordination and decision-making
- **Third-Party Assessment:** Independent review of plan effectiveness

### Plan Updates
- Review and update after each test or actual incident
- Annual comprehensive plan review and approval
- Immediate updates for infrastructure or personnel changes

## Recovery Resources

### Emergency Contacts
- **Incident Commander:** [REDACTED] - Cell: [REDACTED]
- **IT Director:** [REDACTED] - Cell: [REDACTED]  
- **Security Manager:** [REDACTED] - Cell: [REDACTED]
- **Facilities Manager:** [REDACTED] - Cell: [REDACTED]

### Vendor Contacts
- **Data Center Provider:** 24/7 NOC - [REDACTED]
- **Internet Service Provider:** Enterprise Support - [REDACTED]
- **Cloud Provider:** Premium Support - [REDACTED]
- **Security Consultant:** Emergency Line - [REDACTED]

### Equipment Inventory
- **Backup Equipment Location:** Secure storage facility
- **Laptop Inventory:** 50 units configured with VPN access
- **Mobile Devices:** 25 smartphones with company accounts
- **Network Equipment:** Spare routers, switches, and firewalls

*Document Classification: CONFIDENTIAL*
*Plan Owner: IT Director*
*Last Updated: February 2024*
*Next Review: August 2024*"""
}

def populate_knowledge_assets():
    print("🧠 Populating Knowledge Management System")
    print("=" * 60)
    
    try:
        # Step 1: Login
        print("🔐 Step 1: Authentication...")
        login_data = {"username": "jdehart", "password": "jdehart"}
        response = requests.post("http://localhost:8000/api/auth/login", json=login_data, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code}")
            return False
        
        token = response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Login successful")
        
        # Step 2: Get project
        print("\n📁 Step 2: Getting project...")
        response = requests.get("http://localhost:8000/api/projects", headers=headers, timeout=10)
        projects_data = response.json()
        projects = projects_data.get("projects", [])
        
        if not projects:
            print("❌ No projects found")
            return False
            
        project_id = projects[0]["project_id"]
        print(f"✅ Using project: {project_id}")
        
        # Step 3: Upload each sample document
        print(f"\n📚 Step 3: Uploading {len(SAMPLE_DOCUMENTS)} knowledge documents...")
        
        success_count = 0
        for filename, content in SAMPLE_DOCUMENTS.items():
            print(f"\n📄 Processing: {filename}")
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(content)
                temp_file_path = f.name
            
            try:
                with open(temp_file_path, 'rb') as f:
                    files = {'file': (filename, f, 'text/markdown')}
                    data = {
                        'project_id': project_id,
                        'process_for_knowledge': True,
                        'embedding_model': 'all-MiniLM-L6-v2',
                        'chunking_strategy': 'hybrid'
                    }
                    
                    response = requests.post(
                        "http://localhost:8000/api/files/upload", 
                        files=files, 
                        data=data,
                        headers=headers, 
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        print(f"  ✅ Uploaded successfully")
                        print(f"  📄 File ID: {result['file_id']}")
                        success_count += 1
                    else:
                        print(f"  ❌ Upload failed: {response.status_code}")
                        print(f"  Error: {response.text}")
            finally:
                os.unlink(temp_file_path)
            
            # Small delay between uploads to avoid overwhelming the system
            time.sleep(1)
        
        # Step 4: Wait for processing and verify
        print(f"\n⏳ Step 4: Waiting for knowledge processing...")
        time.sleep(5)  # Give time for background processing
        
        # Check knowledge assets
        response = requests.get(
            f"http://localhost:8000/api/knowledge/assets?project_id={project_id}", 
            headers=headers, 
            timeout=10
        )
        
        if response.status_code == 200:
            assets_data = response.json()
            assets = assets_data.get("assets", [])
            print(f"📊 Knowledge assets created: {len(assets)}")
            
            # Show some sample search capabilities
            print(f"\n🔍 Step 5: Testing sample searches...")
            
            test_queries = [
                "aviation safety requirements",
                "cybersecurity framework",
                "disaster recovery procedures",
                "data governance policy"
            ]
            
            for query in test_queries:
                search_data = {
                    "query": query,
                    "project_id": project_id,
                    "limit": 3,
                    "min_score": 0.1
                }
                
                response = requests.post(
                    "http://localhost:8000/api/knowledge/search", 
                    json=search_data,
                    headers=headers, 
                    timeout=10
                )
                
                if response.status_code == 200:
                    results = response.json()
                    print(f"  🎯 '{query}': {results['total_found']} results")
                else:
                    print(f"  ❌ Search failed for '{query}'")
        
        print(f"\n🎉 Knowledge Population Complete!")
        print(f"✅ Successfully uploaded {success_count} out of {len(SAMPLE_DOCUMENTS)} documents")
        print(f"📚 Your knowledge base now contains:")
        print(f"  • Aviation Safety Requirements")
        print(f"  • Cybersecurity Framework") 
        print(f"  • Agile Development Process")
        print(f"  • Data Governance Policy")
        print(f"  • IT Disaster Recovery Plan")
        print(f"\n💡 You can now search across these documents using semantic queries!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    populate_knowledge_assets()

