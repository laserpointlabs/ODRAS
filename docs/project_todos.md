This file contains data dumps of just one lines for want, needs, and nice to haves for the ODRAS MVP. Im just trying to keep a log of what I think we need so I dont lose it.<br>
<br>
## 🎯 COMPLETED TODAY (2025-09-02)<br>
<br>
- ✅ DONE: Create a more clean demo project (init-db now creates single Default Project with demo content)<br>
<br>
- ✅ DONE: Fixed clean and init-db for single default project<br>
  - Removed duplicate project creation from init-postgres.sql<br>
  - Fixed create_default_users being called twice<br>
  - Added -y flag for non-interactive cleaning: `./odras.sh clean -y`<br>
  - Added progress indicators during demo setup<br>
<br>
- ✅ DONE: Add complete ontology to default project during init-db<br>
  - Creates simplified but complete SE ontology with full traceability<br>
  - 6 Classes: Requirement → Component → Process → Function → CADFile (+ Constraint)<br>
  - 6 Object Properties: Creating complete traceable workflow<br>
  - 8 Data Properties: Properly assigned to relevant classes<br>
  - Fixed API to be graph-aware: `/api/ontology/?graph={iri}`<br>
  - Fixed UI to load from API when local storage is empty<br>
  - Ontology now shows in canvas with classes, edges, and data property nodes<br>
<br>
- ✅ DONE: Cleaned up 25+ debugging and temporary files from root directory<br>
  - Removed test_*.py, debug_*.py, check_*.py files<br>
  - Removed log files, SQL artifacts, and Python cache<br>
  - Directory now has 22 essential items vs 50+ before<br>
<br>
## 🎯 REMAINING TODO<br>
<br>
[] Add admin controls to user creation and project controls (user/project/type)<br>
[] data manager needs to be grouped by imports, and local project ontologies<br>
[] Ensure that the requirements.txt stays up to date.<br>
[] Add tabs to main screen to open more than one workbench at a time.<br>
[] Keep project questions as approved by the project and we can continue to test with these.<br>
[] Consider a task script registry to select known and tested scripts for the bpmn tool.<br>
[] Keep requirements.txt up to date as we install new packages.<br>
[] Manage Ontology URI per object<br>
[] Manage Ontology Attributes<br>
[] Manage Ontology base object names<br>
[] Add user task workbench<br>
[] Add nested ontology view by checkmark in imports<br>
[] Keep knowledge project specific<br>
[] Process driven projects<br>
[] Add users tasks page for wf/pl<br>
[] Eliminate hardcoded workers and use small scripts in the bpmn process<br>
<br>
## 🎯 NEXT PRIORITIES<br>
<br>
- Improve ontology capabiltities<br>
    - Mange URIs<br>
        - Show selected object uri<br>
        - Rename objects to more useful name rather then (class2)<br>
    - Enable addtributes<br>
- Data Manager Workbench (auto create data connectors based on ontology data properties)<br>
- User management UI for admins<br>
- Project management controls<br>
- Ontology import/export workflows<br>
- Future ontology capbilities<br>
    - Data Types Management<br>
    - Units Managment<br>
    - Validation<br>
    - Resoners<br>
    - SHAQL<br>

