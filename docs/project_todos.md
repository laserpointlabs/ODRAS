This file contains data dumps of just one lines for want, needs, and nice to haves for the ODRAS MVP. Im just trying to keep a log of what I think we need so I dont lose it.

## 🎯 COMPLETED TODAY (2025-09-02)

- ✅ DONE: Create a more clean demo project (init-db now creates single Default Project with demo content)

- ✅ DONE: Fixed clean and init-db for single default project 
  - Removed duplicate project creation from init-postgres.sql
  - Fixed create_default_users being called twice
  - Added -y flag for non-interactive cleaning: `./odras.sh clean -y`
  - Added progress indicators during demo setup

- ✅ DONE: Add complete ontology to default project during init-db
  - Creates simplified but complete SE ontology with full traceability
  - 6 Classes: Requirement → Component → Process → Function → CADFile (+ Constraint)
  - 6 Object Properties: Creating complete traceable workflow
  - 8 Data Properties: Properly assigned to relevant classes
  - Fixed API to be graph-aware: `/api/ontology/?graph={iri}`
  - Fixed UI to load from API when local storage is empty
  - Ontology now shows in canvas with classes, edges, and data property nodes

- ✅ DONE: Cleaned up 25+ debugging and temporary files from root directory
  - Removed test_*.py, debug_*.py, check_*.py files  
  - Removed log files, SQL artifacts, and Python cache
  - Directory now has 22 essential items vs 50+ before

## 🎯 REMAINING TODO

[] Add admin controls to user creation and project controls (user/project/type)
[] data manager needs to be grouped by imports, and local project ontologies
[] Ensure that the requirements.txt stays up to date.
[] Add tabs to main screen to open more than one workbench at a time. 

## 🎯 NEXT PRIORITIES

- Improve ontology capabiltities
    - Mange URIs
        - Show selected object uri
        - Rename objects to more useful name rather then (class2)
    - Enable addtributes
- Data Manager Workbench (auto create data connectors based on ontology data properties)
- User management UI for admins
- Project management controls
- Ontology import/export workflows
- Future ontology capbilities
    - Data Types Management
    - Units Managment
    - Validation
    - Resoners
    - SHAQL