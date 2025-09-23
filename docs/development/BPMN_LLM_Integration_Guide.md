# BPMN LLM Integration Guide: Variables, External Tasks, and RAG Workflows<br>
<br>
## Overview<br>
<br>
This document provides a comprehensive guide for integrating Large Language Models (LLMs) with Camunda BPMN workflows, based on lessons learned from implementing the RAG Query Process in ODRAS. This guide covers variable passing, external task management, API integration, and best practices for building robust LLM-powered BPMN workflows.<br>
<br>
## Table of Contents<br>
<br>
1. [BPMN Workflow Architecture](#bpmn-workflow-architecture)<br>
2. [External Task Workers](#external-task-workers)<br>
3. [Variable Passing Challenges](#variable-passing-challenges)<br>
4. [LLM Integration Patterns](#llm-integration-patterns)<br>
5. [API Integration](#api-integration)<br>
6. [Debugging and Troubleshooting](#debugging-and-troubleshooting)<br>
7. [Best Practices](#best-practices)<br>
8. [Future Expansion Guidelines](#future-expansion-guidelines)<br>
<br>
## BPMN Workflow Architecture<br>
<br>
### RAG Query Process Flow<br>
<br>
The RAG Query Process demonstrates a complete LLM-powered workflow with the following stages:<br>
<br>
```<br>
StartEvent_UserQuery<br>
    ↓<br>
Task_ProcessQuery (process-user-query)<br>
    ↓<br>
Task_RetrieveContext (retrieve-context)<br>
    ↓<br>
Task_RerankContext (rerank-context)<br>
    ↓<br>
Gateway_ContextQuality<br>
    ↓ (good context)     ↓ (poor context)<br>
Task_ConstructPrompt ← Task_FallbackSearch<br>
    ↓<br>
Task_LLMGeneration (llm-generation)<br>
    ↓<br>
Task_ProcessResponse (process-response)<br>
    ↓<br>
Task_LogInteraction (log-interaction)<br>
    ↓<br>
EndEvent_ResponseReady<br>
```<br>
<br>
### Key BPMN Elements<br>
<br>
- **External Service Tasks**: All processing tasks use `camunda:type="external"` with specific topics<br>
- **Exclusive Gateway**: Context quality check with conditional expressions<br>
- **Variable Flow**: Process variables flow automatically between tasks via sequence flows<br>
- **Documentation**: Each task includes comprehensive documentation for clarity<br>
<br>
## External Task Workers<br>
<br>
### Worker Architecture<br>
<br>
The ODRAS system uses two specialized external task workers:<br>
<br>
1. **Complex Worker** (`run_external_task_worker.py`): Handles RAG query processing<br>
2. **Simple Worker** (`simple_external_worker.py`): Handles file upload processing<br>
<br>
### Task Handler Pattern<br>
<br>
Each external task follows this pattern:<br>
<br>
```python<br>
def handle_[task_name](self, variables: Dict) -> Dict:<br>
    """Handle [task description]."""<br>
    # 1. Extract input variables<br>
    input_var = variables.get("input_variable", default_value)<br>
<br>
    # 2. Process input (call services, LLMs, etc.)<br>
    result = process_data(input_var)<br>
<br>
    # 3. Return output variables<br>
    return {<br>
        "output_variable": result,<br>
        "processing_status": "success",<br>
        "errors": [],<br>
    }<br>
```<br>
<br>
### Variable Type Handling<br>
<br>
Camunda external tasks require proper variable type specification:<br>
<br>
```python<br>
def complete_task(self, task_id: str, result_variables: Dict):<br>
    variables = {}<br>
    for key, value in result_variables.items():<br>
        if isinstance(value, (dict, list)):<br>
            variables[key] = {"value": json.dumps(value), "type": "Json"}<br>
        elif isinstance(value, bool):<br>
            variables[key] = {"value": value, "type": "Boolean"}<br>
        elif isinstance(value, int):<br>
            variables[key] = {"value": value, "type": "Integer"}<br>
        elif isinstance(value, float):<br>
            variables[key] = {"value": value, "type": "Double"}<br>
        else:<br>
            variables[key] = {"value": str(value), "type": "String"}<br>
```<br>
<br>
## Variable Passing Challenges<br>
<br>
### Common Issues Encountered<br>
<br>
1. **Variable Loss Between Tasks**<br>
   - **Problem**: Variables set by Task A not available to Task B<br>
   - **Cause**: Camunda external task variable persistence issues<br>
   - **Symptoms**: Debug logs show variable being set but not received<br>
<br>
2. **Variable Type Mismatches**<br>
   - **Problem**: JSON variables returned as metadata objects<br>
   - **Cause**: Camunda history API returns different format than active process API<br>
   - **Symptoms**: Variables appear as `{'dataFormatName': 'application/json', ...}` instead of actual data<br>
<br>
3. **Variable Name Conflicts**<br>
   - **Problem**: Generic variable names get overwritten<br>
   - **Cause**: Multiple tasks setting same variable name<br>
   - **Solution**: Use specific variable names (e.g., `llm_confidence` instead of `confidence`)<br>
<br>
### Successful Variable Passing Patterns<br>
<br>
#### Pattern 1: Structured Data Embedding<br>
<br>
Instead of passing multiple separate variables, embed metadata in reliable variables:<br>
<br>
```python<br>
# ❌ Problematic approach<br>
return {<br>
    "response": answer,<br>
    "confidence": confidence,<br>
    "metadata": metadata<br>
}<br>
<br>
# ✅ Reliable approach<br>
structured_response = {<br>
    "answer": answer,<br>
    "confidence": confidence,<br>
    "metadata": metadata<br>
}<br>
return {<br>
    "llm_response": json.dumps(structured_response)<br>
}<br>
```<br>
<br>
#### Pattern 2: Variable Extraction in Subsequent Tasks<br>
<br>
Extract embedded data in the next task:<br>
<br>
```python<br>
def handle_next_task(self, variables: Dict) -> Dict:<br>
    llm_response_raw = variables.get("llm_response", "")<br>
<br>
    try:<br>
        structured_data = json.loads(llm_response_raw)<br>
        confidence = structured_data.get("confidence")<br>
        answer = structured_data.get("answer")<br>
    except json.JSONDecodeError:<br>
        # Fallback to raw response<br>
        answer = llm_response_raw<br>
        confidence = None<br>
<br>
    return {"processed_response": answer, "extracted_confidence": confidence}<br>
```<br>
<br>
## LLM Integration Patterns<br>
<br>
### Direct LLM Service Calls<br>
<br>
The RAG service provides a template for calling external LLMs:<br>
<br>
```python<br>
async def call_llm_in_workflow(self, context_text: str, user_question: str):<br>
    """Call external LLM from BPMN workflow task."""<br>
    try:<br>
        from services.rag_service import get_rag_service<br>
<br>
        rag_service = get_rag_service()<br>
<br>
        # Create fake chunks for LLM context<br>
        fake_chunks = [{<br>
            "payload": {<br>
                "content": context_text,<br>
                "asset_id": "workflow_context",<br>
                "source_asset": "workflow_source",<br>
                "document_type": "document"<br>
            },<br>
            "score": 0.8<br>
        }]<br>
<br>
        # Call actual LLM generation method<br>
        llm_result = await rag_service._generate_response(<br>
            question=user_question,<br>
            relevant_chunks=fake_chunks,<br>
            response_style="comprehensive"<br>
        )<br>
<br>
        return llm_result<br>
<br>
    except Exception as e:<br>
        logger.error(f"LLM call failed: {e}")<br>
        return {"answer": "Error", "confidence": "low"}<br>
```<br>
<br>
### LLM Response Schema<br>
<br>
The LLM service expects structured responses with confidence evaluation:<br>
<br>
```json<br>
{<br>
  "answer": "The main response to the user's question",<br>
  "confidence": "high|medium|low",<br>
  "key_points": ["Point 1", "Point 2", "Point 3"]<br>
}<br>
```<br>
<br>
### Confidence Calculation<br>
<br>
LLM confidence is based on:<br>
- **High**: LLM has excellent context to answer accurately<br>
- **Medium**: LLM has decent context but some limitations<br>
- **Low**: LLM has limited context, answer may be incomplete<br>
- **null/n/a**: No LLM evaluation available (never use false confidence)<br>
<br>
## API Integration<br>
<br>
### Workflow Status Extraction<br>
<br>
The API must properly extract variables from completed BPMN processes:<br>
<br>
```python<br>
async def extract_workflow_variables(process_instance_id: str):<br>
    """Extract variables from completed Camunda process."""<br>
<br>
    # Get process variables from Camunda history API<br>
    var_response = await client.get(<br>
        f"{camunda_rest}/history/variable-instance?processInstanceId={process_instance_id}"<br>
    )<br>
<br>
    if var_response.status_code == 200:<br>
        history_vars = var_response.json()<br>
        variables = {}<br>
<br>
        for var in history_vars:<br>
            var_name = var["name"]<br>
            var_value = var["value"]<br>
            var_type = var.get("type", "String")<br>
<br>
            # Handle JSON variables properly<br>
            if var_type == "Json" and isinstance(var_value, str):<br>
                try:<br>
                    var_value = json.loads(var_value)<br>
                except:<br>
                    pass<br>
<br>
            variables[var_name] = {"value": var_value, "type": var_type}<br>
<br>
        return variables<br>
```<br>
<br>
### Metadata Extraction Strategies<br>
<br>
#### Primary: Use Workflow Variables<br>
<br>
```python<br>
# Extract from properly processed workflow variables<br>
confidence = workflow_variables.get("llm_confidence")<br>
chunks_found = workflow_variables.get("chunks_found")<br>
sources = workflow_variables.get("sources", [])<br>
```<br>
<br>
#### Fallback: Parse Response Text<br>
<br>
```python<br>
# Fallback extraction from response text<br>
if not chunks_found:<br>
    chunks_found = response_text.count('[Context ')<br>
<br>
if not sources and 'Sources:' in response_text:<br>
    source_matches = re.findall(r'\[(\d+)\] ([^\n]+)', response_text)<br>
    sources = [{"title": name.strip()} for num, name in source_matches]<br>
```<br>
<br>
### Frontend Integration<br>
<br>
The frontend must handle various confidence states:<br>
<br>
```javascript<br>
// Handle confidence display<br>
const confidence = data.confidence;<br>
const confidenceIcon = confidence === 'high' ? '🟢' :<br>
                      confidence === 'medium' ? '🟡' :<br>
                      confidence === 'low' ? '🟠' : '⚪';<br>
const confidenceText = confidence || 'n/a';<br>
<br>
// Display in header<br>
metadataDiv.innerHTML = `<br>
  ${confidenceIcon} ${confidenceText} confidence • ${chunksFound} sources • ${modelUsed}<br>
`;<br>
```<br>
<br>
## Debugging and Troubleshooting<br>
<br>
### Essential Debug Logging<br>
<br>
#### Worker Level Debugging<br>
<br>
```python<br>
# In task handlers<br>
print(f"TASK_NAME INPUT: Available variables = {list(variables.keys())}")<br>
print(f"TASK_NAME OUTPUT: Setting {len(result)} variables: {list(result.keys())}")<br>
<br>
# In complete_task method<br>
print(f"COMPLETE_TASK: Setting {len(result_variables)} variables: {list(result_variables.keys())}")<br>
for key, value in result_variables.items():<br>
    if key in ["confidence", "chunks_found", "sources"]:<br>
        print(f"COMPLETE_TASK: Setting {key} = {value}")<br>
```<br>
<br>
#### API Level Debugging<br>
<br>
```python<br>
# In API endpoints<br>
print(f"API: Workflow variables available: {list(workflow_variables.keys())}")<br>
for key in ["confidence", "chunks_found", "sources"]:<br>
    if key in workflow_variables:<br>
        print(f"API: Extracted {key} = {workflow_variables[key]}")<br>
    else:<br>
        print(f"API: {key} not found in workflow variables")<br>
```<br>
<br>
### Common Debugging Scenarios<br>
<br>
#### Variable Not Passed Between Tasks<br>
<br>
**Symptoms:**<br>
```<br>
COMPLETE_TASK: Setting confidence = high<br>
NEXT_TASK DEBUG: confidence variable = None<br>
```<br>
<br>
**Investigation Steps:**<br>
1. Check if variable name conflicts with existing process variables<br>
2. Verify Camunda API response codes (should be 204 for success)<br>
3. Check variable type handling in `complete_task` method<br>
4. Consider using structured data embedding approach<br>
<br>
#### API Getting Wrong Variable Format<br>
<br>
**Symptoms:**<br>
```<br>
API: confidence variable = {'dataFormatName': 'application/json', ...}<br>
```<br>
<br>
**Solution:**<br>
```python<br>
# Handle Camunda metadata format<br>
if isinstance(var_data, dict) and "value" in var_data:<br>
    var_value = var_data.get("value")<br>
    if var_type == "Json" and isinstance(var_value, str):<br>
        var_value = json.loads(var_value)<br>
```<br>
<br>
#### LLM Not Being Called<br>
<br>
**Symptoms:**<br>
```<br>
# Response looks like formatted context instead of LLM output<br>
Response: "[Context 1]: ### Coverage Area..."<br>
```<br>
<br>
**Investigation:**<br>
1. Check for OpenAI API calls in logs: `grep -i openai /tmp/odras_app.log`<br>
2. Verify LLM service initialization and API keys<br>
3. Check exception handling in LLM generation task<br>
<br>
## Best Practices<br>
<br>
### 1. Variable Naming Conventions<br>
<br>
- Use **specific, descriptive names**: `llm_confidence` not `confidence`<br>
- Include **task prefix**: `retrieval_chunks`, `llm_response`, `processed_query`<br>
- Avoid **generic names** that might conflict: `data`, `result`, `output`<br>
<br>
### 2. Variable Structure Design<br>
<br>
```python<br>
# ✅ Good: Structured data with embedded metadata<br>
{<br>
    "llm_response": json.dumps({<br>
        "answer": "...",<br>
        "confidence": "high",<br>
        "metadata": {...}<br>
    }),<br>
    "processing_stats": {...}<br>
}<br>
<br>
# ❌ Problematic: Many separate variables<br>
{<br>
    "response": "...",<br>
    "confidence": "high",<br>
    "answer_length": 100,<br>
    "context_used": True,<br>
    "llm_called": True<br>
}<br>
```<br>
<br>
### 3. Error Handling and Fallbacks<br>
<br>
Always provide graceful fallbacks for critical functionality:<br>
<br>
```python<br>
# Primary: Use workflow variables<br>
confidence = workflow_variables.get("llm_confidence")<br>
<br>
# Fallback: Extract from response text<br>
if not confidence:<br>
    if "high quality" in response_text:<br>
        confidence = "high"<br>
    elif "limited context" in response_text:<br>
        confidence = "low"<br>
    else:<br>
        confidence = None  # Honest unknown<br>
<br>
# Never: False confidence<br>
# confidence = "high"  # ❌ Don't fake confidence<br>
```<br>
<br>
### 4. LLM Service Integration<br>
<br>
#### Proper LLM Call Pattern<br>
<br>
```python<br>
async def call_llm_properly(self, context: str, question: str):<br>
    """Call LLM service with proper error handling."""<br>
    try:<br>
        rag_service = get_rag_service()<br>
<br>
        # Use the same method as hard-coded RAG<br>
        llm_result = await rag_service._generate_response(<br>
            question=question,<br>
            relevant_chunks=context_chunks,<br>
            response_style="comprehensive"<br>
        )<br>
<br>
        if llm_result and "answer" in llm_result:<br>
            return {<br>
                "answer": llm_result["answer"],<br>
                "confidence": llm_result.get("confidence", None),<br>
                "success": True<br>
            }<br>
        else:<br>
            return {"answer": None, "confidence": None, "success": False}<br>
<br>
    except Exception as e:<br>
        logger.error(f"LLM call failed: {e}")<br>
        return {"answer": None, "confidence": None, "success": False}<br>
```<br>
<br>
#### Mock vs Real LLM Responses<br>
<br>
```python<br>
# ❌ Don't use mock responses in production workflows<br>
mock_response = context_text.strip()<br>
<br>
# ✅ Always call actual LLM service<br>
llm_result = await rag_service._generate_response(...)<br>
```<br>
<br>
### 5. Frontend Integration<br>
<br>
#### Metadata Display<br>
<br>
```javascript<br>
// Handle all confidence states properly<br>
const confidence = data.confidence;<br>
const confidenceIcon = confidence === 'high' ? '🟢' :<br>
                      confidence === 'medium' ? '🟡' :<br>
                      confidence === 'low' ? '🟠' : '⚪';<br>
const confidenceText = confidence || 'n/a';<br>
<br>
// Never show false confidence<br>
// const confidence = data.confidence || 'medium'; // ❌ Wrong<br>
```<br>
<br>
#### Loading States<br>
<br>
```javascript<br>
// Show proper loading indicators<br>
statusDiv.textContent = useWorkflow ? 'Processing via workflow...' : 'Thinking...';<br>
responseContent.innerHTML = `<br>
  <div class="loading-spinner" style="animation: spin 1s linear infinite;"></div><br>
  <div>${useWorkflow ? 'Running RAG workflow...' : 'Analyzing knowledge base...'}</div><br>
`;<br>
```<br>
<br>
## Variable Passing Challenges<br>
<br>
### Challenge 1: External Task Variable Persistence<br>
<br>
**Problem**: Variables set by external tasks don't always persist to process variables.<br>
<br>
**Root Cause**: Camunda external task completion API may not immediately persist variables.<br>
<br>
**Solution**: Use structured data embedding in reliable variables like `llm_response`.<br>
<br>
**Example**:<br>
```python<br>
# Instead of separate variables<br>
return {<br>
    "response": answer,<br>
    "confidence": confidence,<br>
    "metadata": data<br>
}<br>
<br>
# Embed in single structured variable<br>
return {<br>
    "llm_response": json.dumps({<br>
        "answer": answer,<br>
        "confidence": confidence,<br>
        "metadata": data<br>
    })<br>
}<br>
```<br>
<br>
### Challenge 2: Camunda History API Format<br>
<br>
**Problem**: Variables retrieved from Camunda history have different format than active process variables.<br>
<br>
**Symptoms**:<br>
```python<br>
# Active process format<br>
{"variable_name": {"value": "actual_data", "type": "String"}}<br>
<br>
# History API format<br>
{"variable_name": {"dataFormatName": "application/json", "nodeType": "ARRAY"}}<br>
```<br>
<br>
**Solution**: Handle both formats in variable extraction:<br>
```python<br>
def extract_variable_value(var_data, var_type):<br>
    if isinstance(var_data, dict) and "value" in var_data:<br>
        var_value = var_data["value"]<br>
        if var_type == "Json" and isinstance(var_value, str):<br>
            return json.loads(var_value)<br>
        return var_value<br>
    else:<br>
        return var_data<br>
```<br>
<br>
### Challenge 3: Variable Timing Issues<br>
<br>
**Problem**: Next task starts before previous task's variables are persisted.<br>
<br>
**Investigation**: Check Camunda task completion response codes:<br>
```python<br>
if response.status_code != 204:<br>
    logger.error(f"Failed to complete task: {response.status_code} - {response.text}")<br>
```<br>
<br>
**Solution**: Use reliable variable containers and extraction patterns.<br>
<br>
## LLM Integration Patterns<br>
<br>
### Pattern 1: Direct LLM Service Call<br>
<br>
```python<br>
async def handle_llm_generation(self, variables: Dict) -> Dict:<br>
    """Generate LLM response with proper confidence evaluation."""<br>
<br>
    # Extract context and question<br>
    context_text = extract_context_from_variables(variables)<br>
    user_question = variables.get("user_query", "")<br>
<br>
    # Call actual LLM service (not mock)<br>
    try:<br>
        rag_service = get_rag_service()<br>
<br>
        # Create chunks for LLM context<br>
        fake_chunks = [{<br>
            "payload": {<br>
                "content": context_text,<br>
                "asset_id": "workflow_context",<br>
                "source_asset": "workflow_source",<br>
                "document_type": "document"<br>
            },<br>
            "score": 0.8<br>
        }] if context_text else []<br>
<br>
        # Call LLM<br>
        llm_result = await rag_service._generate_response(<br>
            question=user_question,<br>
            relevant_chunks=fake_chunks,<br>
            response_style="comprehensive"<br>
        )<br>
<br>
        if llm_result and "answer" in llm_result:<br>
            answer = llm_result["answer"]<br>
            confidence = llm_result.get("confidence", None)<br>
        else:<br>
            answer = "I couldn't generate a response."<br>
            confidence = None<br>
<br>
    except Exception as e:<br>
        logger.error(f"LLM generation failed: {e}")<br>
        answer = "Error generating response."<br>
        confidence = None<br>
<br>
    # Use structured embedding for reliable variable passing<br>
    structured_response = {<br>
        "answer": answer,<br>
        "confidence": confidence,<br>
        "metadata": {<br>
            "llm_called": True,<br>
            "context_length": len(context_text)<br>
        }<br>
    }<br>
<br>
    return {<br>
        "llm_response": json.dumps(structured_response),<br>
        "processing_status": "success",<br>
        "errors": []<br>
    }<br>
```<br>
<br>
### Pattern 2: LLM Response Processing<br>
<br>
```python<br>
def handle_process_response(self, variables: Dict) -> Dict:<br>
    """Process LLM response and extract metadata."""<br>
<br>
    llm_response_raw = variables.get("llm_response", "")<br>
<br>
    # Extract from structured response<br>
    try:<br>
        structured_data = json.loads(llm_response_raw)<br>
        answer = structured_data.get("answer", "")<br>
        confidence = structured_data.get("confidence")<br>
        metadata = structured_data.get("metadata", {})<br>
    except json.JSONDecodeError:<br>
        # Handle unstructured response<br>
        answer = llm_response_raw<br>
        confidence = None<br>
        metadata = {}<br>
<br>
    # Process and format response<br>
    final_response = format_response(answer, context_chunks)<br>
<br>
    return {<br>
        "final_response": final_response,<br>
        "llm_confidence": confidence,  # Pass confidence forward<br>
        "response_metadata": metadata,<br>
        "processing_status": "success"<br>
    }<br>
```<br>
<br>
## API Integration<br>
<br>
### Workflow Status Polling<br>
<br>
```python<br>
async def poll_workflow_completion(process_instance_id: str, max_wait_time: int = 120):<br>
    """Poll workflow until completion with proper timeout."""<br>
<br>
    start_time = time.time()<br>
    poll_interval = 1<br>
<br>
    while time.time() - start_time < max_wait_time:<br>
        try:<br>
            status_response = await get_rag_query_status(process_instance_id)<br>
<br>
            if status_response.get("status") == "completed":<br>
                return status_response<br>
            elif status_response.get("status") == "failed":<br>
                raise HTTPException(status_code=500, detail="Workflow failed")<br>
<br>
            await asyncio.sleep(poll_interval)<br>
<br>
        except Exception as e:<br>
            logger.error(f"Error polling workflow: {e}")<br>
            await asyncio.sleep(poll_interval)<br>
<br>
    raise HTTPException(status_code=408, detail="Workflow timeout")<br>
```<br>
<br>
### Variable Extraction from Workflow Response<br>
<br>
```python<br>
def extract_metadata_from_workflow(status_response: Dict) -> Dict:<br>
    """Extract metadata from completed workflow."""<br>
<br>
    workflow_variables = status_response.get("variables", {})<br>
    final_response = status_response.get("final_response", "")<br>
<br>
    # Primary: Extract from workflow variables<br>
    confidence = workflow_variables.get("llm_confidence")<br>
    chunks_found = workflow_variables.get("chunks_found", 0)<br>
    sources = workflow_variables.get("sources", [])<br>
<br>
    # Fallback: Parse from response text (reliable backup)<br>
    if not chunks_found and final_response:<br>
        chunks_found = final_response.count('[Context ')<br>
<br>
    if not sources and 'Sources:' in final_response:<br>
        source_matches = re.findall(r'\[(\d+)\] ([^\n]+)', final_response)<br>
        sources = [{"title": name.strip()} for num, name in source_matches]<br>
<br>
    return {<br>
        "confidence": confidence,<br>
        "chunks_found": chunks_found,<br>
        "sources": sources<br>
    }<br>
```<br>
<br>
## Debugging and Troubleshooting<br>
<br>
### Debug Logging Strategy<br>
<br>
#### 1. Worker Level Logs<br>
<br>
```python<br>
# At task start<br>
logger.info(f"Executing task {task_id} for topic {topic}")<br>
logger.info(f"Task variables: {variables}")<br>
<br>
# At task completion<br>
logger.info(f"Successfully completed task {task_id}")<br>
print(f"TASK_OUTPUT: {result}")<br>
```<br>
<br>
#### 2. Camunda API Logs<br>
<br>
```python<br>
# In complete_task method<br>
print(f"COMPLETE_TASK: Setting {len(variables)} variables")<br>
print(f"COMPLETE_TASK: Variables = {list(variables.keys())}")<br>
<br>
# Check Camunda response<br>
if response.status_code != 204:<br>
    logger.error(f"Camunda API error: {response.status_code} - {response.text}")<br>
```<br>
<br>
#### 3. API Extraction Logs<br>
<br>
```python<br>
# In API endpoints<br>
print(f"API: Workflow status = {status_response.get('status')}")<br>
print(f"API: Available variables = {list(workflow_variables.keys())}")<br>
print(f"API: Extracted metadata = confidence:{confidence}, chunks:{chunks_found}")<br>
```<br>
<br>
### Troubleshooting Checklist<br>
<br>
When variables aren't passing correctly:<br>
<br>
1. **Check worker logs**: Are variables being set by the task?<br>
2. **Check Camunda completion**: Is the task completing successfully (204 response)?<br>
3. **Check next task logs**: Are variables available to the next task?<br>
4. **Check variable types**: Are complex objects being serialized properly?<br>
5. **Check API extraction**: Is the API getting the right variable format?<br>
<br>
### Log Analysis Commands<br>
<br>
```bash<br>
# Check variable flow between tasks<br>
tail -100 /tmp/odras_complex_worker.log | grep -E "(COMPLETE_TASK|Available variables)"<br>
<br>
# Check LLM calls<br>
tail -100 /tmp/odras_complex_worker.log | grep -E "(openai|LLM)"<br>
<br>
# Check API extraction<br>
tail -50 /tmp/odras_app.log | grep -E "(API: Extracted|API:)"<br>
<br>
# Check Camunda errors<br>
tail -100 /tmp/odras_complex_worker.log | grep -E "(Failed to complete|ERROR)"<br>
```<br>
<br>
## Best Practices<br>
<br>
### 1. BPMN Design Principles<br>
<br>
- **Single Responsibility**: Each task should have one clear purpose<br>
- **Clear Documentation**: Document expected inputs/outputs for each task<br>
- **Error Handling**: Include error paths and fallback strategies<br>
- **Variable Naming**: Use descriptive, conflict-free variable names<br>
<br>
### 2. External Task Implementation<br>
<br>
- **Async Operations**: Use proper async/await for LLM calls<br>
- **Error Boundaries**: Wrap LLM calls in try-catch with meaningful fallbacks<br>
- **Resource Management**: Properly initialize and cleanup services<br>
- **Logging**: Comprehensive debug logging for troubleshooting<br>
<br>
### 3. Variable Management<br>
<br>
- **Structured Data**: Embed related data in single variables when possible<br>
- **Type Safety**: Proper type handling for Camunda variable types<br>
- **Fallback Extraction**: Always have backup methods for critical metadata<br>
- **Validation**: Validate variable content before processing<br>
<br>
### 4. API Integration<br>
<br>
- **Timeout Handling**: Proper polling with reasonable timeouts<br>
- **Error Responses**: Meaningful error messages for different failure modes<br>
- **Metadata Extraction**: Multiple strategies for extracting workflow results<br>
- **Response Formatting**: Consistent response format for frontend consumption<br>
<br>
## Future Expansion Guidelines<br>
<br>
### Adding New LLM-Powered Tasks<br>
<br>
When adding new tasks to the RAG workflow:<br>
<br>
1. **Follow the Pattern**:<br>
   ```python<br>
   async def handle_new_llm_task(self, variables: Dict) -> Dict:<br>
       # Extract inputs<br>
       # Call LLM service<br>
       # Structure response with metadata<br>
       # Return with proper variable names<br>
   ```<br>
<br>
2. **Variable Design**:<br>
   - Use task-specific prefixes: `analysis_confidence`, `summary_confidence`<br>
   - Embed metadata in structured responses<br>
   - Provide fallback extraction methods<br>
<br>
3. **Testing Strategy**:<br>
   - Test variable passing between tasks<br>
   - Verify LLM calls with debug logging<br>
   - Test API metadata extraction<br>
   - Validate frontend display<br>
<br>
### Scaling BPMN Workflows<br>
<br>
For complex multi-LLM workflows:<br>
<br>
1. **Variable Namespacing**: Use prefixes to avoid conflicts<br>
   ```python<br>
   "retrieval_confidence", "analysis_confidence", "summary_confidence"<br>
   ```<br>
<br>
2. **State Management**: Track workflow state through variables<br>
   ```python<br>
   "workflow_stage": "analysis_complete",<br>
   "processing_flags": {"llm_called": True, "context_validated": True}<br>
   ```<br>
<br>
3. **Performance Monitoring**: Add timing and performance metrics<br>
   ```python<br>
   "performance_stats": {<br>
       "retrieval_time": 1.2,<br>
       "llm_time": 3.4,<br>
       "total_time": 5.8<br>
   }<br>
   ```<br>
<br>
### Common Expansion Patterns<br>
<br>
#### Multi-Stage LLM Processing<br>
<br>
```<br>
Query → Retrieval → LLM_Analysis → LLM_Summary → LLM_Validation → Response<br>
```<br>
<br>
Each stage should:<br>
- Call external LLM with proper confidence evaluation<br>
- Pass structured data to next stage<br>
- Maintain confidence tracking throughout pipeline<br>
- Provide fallback strategies for each stage<br>
<br>
#### Parallel LLM Processing<br>
<br>
```<br>
Query → Retrieval → [LLM_Path_A, LLM_Path_B, LLM_Path_C] → Ensemble → Response<br>
```<br>
<br>
Considerations:<br>
- Variable naming for parallel paths: `llm_a_confidence`, `llm_b_confidence`<br>
- Ensemble confidence calculation<br>
- Timeout handling for parallel tasks<br>
<br>
## Lessons Learned<br>
<br>
### Critical Insights<br>
<br>
1. **BPMN Variable Passing is Fragile**: External task variables don't always persist reliably<br>
2. **Structured Data Works Better**: Embedding metadata in reliable variables is more robust<br>
3. **Fallback Strategies are Essential**: Always have backup extraction methods<br>
4. **LLM Integration Requires Care**: Proper service calls, not mock responses<br>
5. **Debug Logging is Crucial**: Comprehensive logging enables rapid troubleshooting<br>
<br>
### What Doesn't Work<br>
<br>
- **Separate confidence variables**: Often lost between tasks<br>
- **Mock LLM responses**: Don't provide real confidence evaluation<br>
- **Generic variable names**: Cause conflicts and overwrites<br>
- **Complex variable hierarchies**: Difficult to pass through BPMN reliably<br>
- **Assuming variable persistence**: External task variables can be lost<br>
<br>
### What Works Well<br>
<br>
- **Structured JSON embedding**: Reliable data transfer<br>
- **Specific variable names**: Avoid conflicts<br>
- **Real LLM service calls**: Proper confidence evaluation<br>
- **Multiple extraction strategies**: Primary + fallback approaches<br>
- **Comprehensive logging**: Enables effective debugging<br>
<br>
## Conclusion<br>
<br>
Building LLM-powered BPMN workflows requires understanding both Camunda's variable handling limitations and LLM service integration patterns. The key to success is:<br>
<br>
1. **Use reliable variable passing patterns** (structured data embedding)<br>
2. **Call actual LLM services** for real confidence evaluation<br>
3. **Implement robust fallback strategies** for metadata extraction<br>
4. **Add comprehensive debug logging** for troubleshooting<br>
5. **Test variable flow thoroughly** between all tasks<br>
<br>
This approach enables building sophisticated AI workflows that can scale and expand while maintaining reliability and proper metadata handling.<br>
<br>
---<br>
<br>
*Document created from RAG Query Process integration experience - September 2025*<br>

