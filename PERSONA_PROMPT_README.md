# ODRAS Persona and Prompt Management

This document describes the new persona and prompt management functionality added to ODRAS, allowing external control and testing of LLM personas and prompts.

## Overview

The system now provides a web interface with tabs for managing:
- **Personas**: LLM system prompts that define different analysis roles
- **Prompts**: Template-based prompts for requirement analysis with variable substitution
- **Testing**: Ability to test prompts with sample data before use

## Features

### Persona Management
- **Create/Edit/Delete** personas with custom system prompts
- **Activate/Deactivate** personas to control which ones are used
- **Persistent storage** via API endpoints
- **Default personas** included: Extractor and Reviewer

### Prompt Management
- **Template-based prompts** with variable substitution using `{variable_name}` syntax
- **Variable definition** for each prompt
- **Prompt testing** with sample data to preview filled prompts
- **Default prompt** included for requirement analysis

### Testing Capabilities
- **Prompt preview** with variable substitution
- **Real-time testing** of prompts with custom data
- **Validation** of prompt templates and variables

## API Endpoints

### Personas
- `GET /api/personas` - List all personas
- `POST /api/personas` - Create a new persona
- `PUT /api/personas/{id}` - Update an existing persona
- `DELETE /api/personas/{id}` - Delete a persona

### Prompts
- `GET /api/prompts` - List all prompts
- `POST /api/prompts` - Create a new prompt
- `PUT /api/prompts/{id}` - Update an existing prompt
- `DELETE /api/prompts/{id}` - Delete a prompt
- `POST /api/prompts/{id}/test` - Test a prompt with sample variables

## Usage

### Starting the System
1. Start the ODRAS backend server:
   ```bash
   cd backend
   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. Open your browser to `http://localhost:8000`

### Using the Interface

#### Personas Tab
1. Click on the "Personas" tab
2. Use "Add New Persona" to create custom personas
3. Edit existing personas by modifying their fields
4. Toggle personas on/off using the Active checkbox
5. Save changes using "Save All Personas"

#### Prompts Tab
1. Click on the "Prompts" tab
2. Create new prompts with template syntax
3. Define variables for the prompt template
4. Test prompts with sample data using the test section
5. Save changes using "Save All Prompts"

### Prompt Template Syntax

Prompts use a simple template syntax with variables enclosed in curly braces:

```
Analyze the following requirement: {requirement_text}
Category: {category}
Source: {source_file}
Iteration: {iteration}
```

Variables are defined as a comma-separated list and will be replaced with actual values when the prompt is used.

### Testing Prompts

1. In the Prompts tab, find the prompt you want to test
2. In the test section, enter JSON with test variables
3. Click "Test Prompt" to see the filled prompt
4. Review the result to ensure the prompt works as expected

## Integration with LLM Processing

The system integrates with the existing LLM processing pipeline:

- **Personas** are used as system prompts for different LLM analysis roles
- **Prompts** can be used for requirement analysis with variable substitution
- **Active personas and prompts** are automatically used in processing

## Configuration

### Default Personas
- **Extractor**: Extracts ontology-grounded entities from requirements
- **Reviewer**: Validates and corrects extracted JSON to fit schemas

### Default Prompts
- **Default Analysis**: Standard requirement analysis prompt with entity extraction

## Testing

Run the test script to verify functionality:

```bash
python test_personas_prompts.py
```

This will test all API endpoints and verify the UI loads correctly.

## Future Enhancements

- **Persistent storage** with database backend
- **Prompt versioning** and history
- **Advanced testing** with actual LLM calls
- **Prompt templates** library
- **User permissions** and access control
- **Prompt performance metrics**

## Technical Details

### Storage
- Currently uses in-memory storage (MVP)
- Designed for easy migration to Redis/database
- API endpoints provide persistence layer

### Architecture
- **Frontend**: HTML/JavaScript with tabbed interface
- **Backend**: FastAPI with REST endpoints
- **Integration**: PersonaManager service for external access
- **LLM Team**: Updated to use external personas and prompts

### Error Handling
- Graceful fallback to default personas/prompts
- User-friendly error messages
- Validation of prompt templates and variables
