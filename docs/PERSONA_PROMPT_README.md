# ODRAS Persona and Prompt Management<br>
<br>
This document describes the new persona and prompt management functionality added to ODRAS, allowing external control and testing of LLM personas and prompts.<br>
<br>
## Overview<br>
<br>
The system now provides a web interface with tabs for managing:<br>
- **Personas**: LLM system prompts that define different analysis roles<br>
- **Prompts**: Template-based prompts for requirement analysis with variable substitution<br>
- **Testing**: Ability to test prompts with sample data before use<br>
<br>
## Features<br>
<br>
### Persona Management<br>
- **Create/Edit/Delete** personas with custom system prompts<br>
- **Activate/Deactivate** personas to control which ones are used<br>
- **Persistent storage** via API endpoints<br>
- **Default personas** included: Extractor and Reviewer<br>
<br>
### Prompt Management<br>
- **Template-based prompts** with variable substitution using `{variable_name}` syntax<br>
- **Variable definition** for each prompt<br>
- **Prompt testing** with sample data to preview filled prompts<br>
- **Default prompt** included for requirement analysis<br>
<br>
### Testing Capabilities<br>
- **Prompt preview** with variable substitution<br>
- **Real-time testing** of prompts with custom data<br>
- **Validation** of prompt templates and variables<br>
<br>
## API Endpoints<br>
<br>
### Personas<br>
- `GET /api/personas` - List all personas<br>
- `POST /api/personas` - Create a new persona<br>
- `PUT /api/personas/{id}` - Update an existing persona<br>
- `DELETE /api/personas/{id}` - Delete a persona<br>
<br>
### Prompts<br>
- `GET /api/prompts` - List all prompts<br>
- `POST /api/prompts` - Create a new prompt<br>
- `PUT /api/prompts/{id}` - Update an existing prompt<br>
- `DELETE /api/prompts/{id}` - Delete a prompt<br>
- `POST /api/prompts/{id}/test` - Test a prompt with sample variables<br>
<br>
## Usage<br>
<br>
### Starting the System<br>
1. Start the ODRAS backend server:<br>
   ```bash<br>
   cd backend<br>
   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000<br>
   ```<br>
<br>
2. Open your browser to `http://localhost:8000`<br>
<br>
### Using the Interface<br>
<br>
#### Personas Tab<br>
1. Click on the "Personas" tab<br>
2. Use "Add New Persona" to create custom personas<br>
3. Edit existing personas by modifying their fields<br>
4. Toggle personas on/off using the Active checkbox<br>
5. Save changes using "Save All Personas"<br>
<br>
#### Prompts Tab<br>
1. Click on the "Prompts" tab<br>
2. Create new prompts with template syntax<br>
3. Define variables for the prompt template<br>
4. Test prompts with sample data using the test section<br>
5. Save changes using "Save All Prompts"<br>
<br>
### Prompt Template Syntax<br>
<br>
Prompts use a simple template syntax with variables enclosed in curly braces:<br>
<br>
```<br>
Analyze the following requirement: {requirement_text}<br>
Category: {category}<br>
Source: {source_file}<br>
Iteration: {iteration}<br>
```<br>
<br>
Variables are defined as a comma-separated list and will be replaced with actual values when the prompt is used.<br>
<br>
### Testing Prompts<br>
<br>
1. In the Prompts tab, find the prompt you want to test<br>
2. In the test section, enter JSON with test variables<br>
3. Click "Test Prompt" to see the filled prompt<br>
4. Review the result to ensure the prompt works as expected<br>
<br>
## Integration with LLM Processing<br>
<br>
The system integrates with the existing LLM processing pipeline:<br>
<br>
- **Personas** are used as system prompts for different LLM analysis roles<br>
- **Prompts** can be used for requirement analysis with variable substitution<br>
- **Active personas and prompts** are automatically used in processing<br>
<br>
## Configuration<br>
<br>
### Default Personas<br>
- **Extractor**: Extracts ontology-grounded entities from requirements<br>
- **Reviewer**: Validates and corrects extracted JSON to fit schemas<br>
<br>
### Default Prompts<br>
- **Default Analysis**: Standard requirement analysis prompt with entity extraction<br>
<br>
## Testing<br>
<br>
Run the test script to verify functionality:<br>
<br>
```bash<br>
python test_personas_prompts.py<br>
```<br>
<br>
This will test all API endpoints and verify the UI loads correctly.<br>
<br>
## Future Enhancements<br>
<br>
- **Persistent storage** with database backend<br>
- **Prompt versioning** and history<br>
- **Advanced testing** with actual LLM calls<br>
- **Prompt templates** library<br>
- **User permissions** and access control<br>
- **Prompt performance metrics**<br>
<br>
## Technical Details<br>
<br>
### Storage<br>
- Currently uses in-memory storage (MVP)<br>
- Designed for easy migration to Redis/database<br>
- API endpoints provide persistence layer<br>
<br>
### Architecture<br>
- **Frontend**: HTML/JavaScript with tabbed interface<br>
- **Backend**: FastAPI with REST endpoints<br>
- **Integration**: PersonaManager service for external access<br>
- **LLM Team**: Updated to use external personas and prompts<br>
<br>
### Error Handling<br>
- Graceful fallback to default personas/prompts<br>
- User-friendly error messages<br>
- Validation of prompt templates and variables<br>

