# BPMN LLM Integration Guide: Variables, External Tasks, and RAG Workflows

## Overview

This document provides a comprehensive guide for integrating Large Language Models (LLMs) with Camunda BPMN workflows, based on lessons learned from implementing the RAG Query Process in ODRAS. This guide covers variable passing, external task management, API integration, and best practices for building robust LLM-powered BPMN workflows.

## Table of Contents

1. [BPMN Workflow Architecture](#bpmn-workflow-architecture)
2. [External Task Workers](#external-task-workers)
3. [Variable Passing Challenges](#variable-passing-challenges)
4. [LLM Integration Patterns](#llm-integration-patterns)
5. [API Integration](#api-integration)
6. [Debugging and Troubleshooting](#debugging-and-troubleshooting)
7. [Best Practices](#best-practices)
8. [Future Expansion Guidelines](#future-expansion-guidelines)

## BPMN Workflow Architecture

### RAG Query Process Flow

The RAG Query Process demonstrates a complete LLM-powered workflow with the following stages:

```
StartEvent_UserQuery
    ↓
Task_ProcessQuery (process-user-query)
    ↓
Task_RetrieveContext (retrieve-context)
    ↓
Task_RerankContext (rerank-context)
    ↓
Gateway_ContextQuality
    ↓ (good context)     ↓ (poor context)
Task_ConstructPrompt ← Task_FallbackSearch
    ↓
Task_LLMGeneration (llm-generation)
    ↓
Task_ProcessResponse (process-response)
    ↓
Task_LogInteraction (log-interaction)
    ↓
EndEvent_ResponseReady
```

### Key BPMN Elements

- **External Service Tasks**: All processing tasks use `camunda:type="external"` with specific topics
- **Exclusive Gateway**: Context quality check with conditional expressions
- **Variable Flow**: Process variables flow automatically between tasks via sequence flows
- **Documentation**: Each task includes comprehensive documentation for clarity

## External Task Workers

### Worker Architecture

The ODRAS system uses two specialized external task workers:

1. **Complex Worker** (`run_external_task_worker.py`): Handles RAG query processing
2. **Simple Worker** (`simple_external_worker.py`): Handles file upload processing

### Task Handler Pattern

Each external task follows this pattern:

```python
def handle_[task_name](self, variables: Dict) -> Dict:
    """Handle [task description]."""
    # 1. Extract input variables
    input_var = variables.get("input_variable", default_value)
    
    # 2. Process input (call services, LLMs, etc.)
    result = process_data(input_var)
    
    # 3. Return output variables
    return {
        "output_variable": result,
        "processing_status": "success",
        "errors": [],
    }
```

### Variable Type Handling

Camunda external tasks require proper variable type specification:

```python
def complete_task(self, task_id: str, result_variables: Dict):
    variables = {}
    for key, value in result_variables.items():
        if isinstance(value, (dict, list)):
            variables[key] = {"value": json.dumps(value), "type": "Json"}
        elif isinstance(value, bool):
            variables[key] = {"value": value, "type": "Boolean"}
        elif isinstance(value, int):
            variables[key] = {"value": value, "type": "Integer"}
        elif isinstance(value, float):
            variables[key] = {"value": value, "type": "Double"}
        else:
            variables[key] = {"value": str(value), "type": "String"}
```

## Variable Passing Challenges

### Common Issues Encountered

1. **Variable Loss Between Tasks**
   - **Problem**: Variables set by Task A not available to Task B
   - **Cause**: Camunda external task variable persistence issues
   - **Symptoms**: Debug logs show variable being set but not received

2. **Variable Type Mismatches**
   - **Problem**: JSON variables returned as metadata objects
   - **Cause**: Camunda history API returns different format than active process API
   - **Symptoms**: Variables appear as `{'dataFormatName': 'application/json', ...}` instead of actual data

3. **Variable Name Conflicts**
   - **Problem**: Generic variable names get overwritten
   - **Cause**: Multiple tasks setting same variable name
   - **Solution**: Use specific variable names (e.g., `llm_confidence` instead of `confidence`)

### Successful Variable Passing Patterns

#### Pattern 1: Structured Data Embedding

Instead of passing multiple separate variables, embed metadata in reliable variables:

```python
# ❌ Problematic approach
return {
    "response": answer,
    "confidence": confidence,
    "metadata": metadata
}

# ✅ Reliable approach
structured_response = {
    "answer": answer,
    "confidence": confidence,
    "metadata": metadata
}
return {
    "llm_response": json.dumps(structured_response)
}
```

#### Pattern 2: Variable Extraction in Subsequent Tasks

Extract embedded data in the next task:

```python
def handle_next_task(self, variables: Dict) -> Dict:
    llm_response_raw = variables.get("llm_response", "")
    
    try:
        structured_data = json.loads(llm_response_raw)
        confidence = structured_data.get("confidence")
        answer = structured_data.get("answer")
    except json.JSONDecodeError:
        # Fallback to raw response
        answer = llm_response_raw
        confidence = None
    
    return {"processed_response": answer, "extracted_confidence": confidence}
```

## LLM Integration Patterns

### Direct LLM Service Calls

The RAG service provides a template for calling external LLMs:

```python
async def call_llm_in_workflow(self, context_text: str, user_question: str):
    """Call external LLM from BPMN workflow task."""
    try:
        from services.rag_service import get_rag_service
        
        rag_service = get_rag_service()
        
        # Create fake chunks for LLM context
        fake_chunks = [{
            "payload": {
                "content": context_text,
                "asset_id": "workflow_context",
                "source_asset": "workflow_source",
                "document_type": "document"
            },
            "score": 0.8
        }]
        
        # Call actual LLM generation method
        llm_result = await rag_service._generate_response(
            question=user_question,
            relevant_chunks=fake_chunks,
            response_style="comprehensive"
        )
        
        return llm_result
        
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return {"answer": "Error", "confidence": "low"}
```

### LLM Response Schema

The LLM service expects structured responses with confidence evaluation:

```json
{
  "answer": "The main response to the user's question",
  "confidence": "high|medium|low",
  "key_points": ["Point 1", "Point 2", "Point 3"]
}
```

### Confidence Calculation

LLM confidence is based on:
- **High**: LLM has excellent context to answer accurately
- **Medium**: LLM has decent context but some limitations  
- **Low**: LLM has limited context, answer may be incomplete
- **null/n/a**: No LLM evaluation available (never use false confidence)

## API Integration

### Workflow Status Extraction

The API must properly extract variables from completed BPMN processes:

```python
async def extract_workflow_variables(process_instance_id: str):
    """Extract variables from completed Camunda process."""
    
    # Get process variables from Camunda history API
    var_response = await client.get(
        f"{camunda_rest}/history/variable-instance?processInstanceId={process_instance_id}"
    )
    
    if var_response.status_code == 200:
        history_vars = var_response.json()
        variables = {}
        
        for var in history_vars:
            var_name = var["name"]
            var_value = var["value"]
            var_type = var.get("type", "String")
            
            # Handle JSON variables properly
            if var_type == "Json" and isinstance(var_value, str):
                try:
                    var_value = json.loads(var_value)
                except:
                    pass
                    
            variables[var_name] = {"value": var_value, "type": var_type}
            
        return variables
```

### Metadata Extraction Strategies

#### Primary: Use Workflow Variables

```python
# Extract from properly processed workflow variables
confidence = workflow_variables.get("llm_confidence")
chunks_found = workflow_variables.get("chunks_found")
sources = workflow_variables.get("sources", [])
```

#### Fallback: Parse Response Text

```python
# Fallback extraction from response text
if not chunks_found:
    chunks_found = response_text.count('[Context ')
    
if not sources and 'Sources:' in response_text:
    source_matches = re.findall(r'\[(\d+)\] ([^\n]+)', response_text)
    sources = [{"title": name.strip()} for num, name in source_matches]
```

### Frontend Integration

The frontend must handle various confidence states:

```javascript
// Handle confidence display
const confidence = data.confidence;
const confidenceIcon = confidence === 'high' ? '🟢' : 
                      confidence === 'medium' ? '🟡' : 
                      confidence === 'low' ? '🟠' : '⚪';
const confidenceText = confidence || 'n/a';

// Display in header
metadataDiv.innerHTML = `
  ${confidenceIcon} ${confidenceText} confidence • ${chunksFound} sources • ${modelUsed}
`;
```

## Debugging and Troubleshooting

### Essential Debug Logging

#### Worker Level Debugging

```python
# In task handlers
print(f"TASK_NAME INPUT: Available variables = {list(variables.keys())}")
print(f"TASK_NAME OUTPUT: Setting {len(result)} variables: {list(result.keys())}")

# In complete_task method
print(f"COMPLETE_TASK: Setting {len(result_variables)} variables: {list(result_variables.keys())}")
for key, value in result_variables.items():
    if key in ["confidence", "chunks_found", "sources"]:
        print(f"COMPLETE_TASK: Setting {key} = {value}")
```

#### API Level Debugging

```python
# In API endpoints
print(f"API: Workflow variables available: {list(workflow_variables.keys())}")
for key in ["confidence", "chunks_found", "sources"]:
    if key in workflow_variables:
        print(f"API: Extracted {key} = {workflow_variables[key]}")
    else:
        print(f"API: {key} not found in workflow variables")
```

### Common Debugging Scenarios

#### Variable Not Passed Between Tasks

**Symptoms:**
```
COMPLETE_TASK: Setting confidence = high
NEXT_TASK DEBUG: confidence variable = None
```

**Investigation Steps:**
1. Check if variable name conflicts with existing process variables
2. Verify Camunda API response codes (should be 204 for success)
3. Check variable type handling in `complete_task` method
4. Consider using structured data embedding approach

#### API Getting Wrong Variable Format

**Symptoms:**
```
API: confidence variable = {'dataFormatName': 'application/json', ...}
```

**Solution:**
```python
# Handle Camunda metadata format
if isinstance(var_data, dict) and "value" in var_data:
    var_value = var_data.get("value")
    if var_type == "Json" and isinstance(var_value, str):
        var_value = json.loads(var_value)
```

#### LLM Not Being Called

**Symptoms:**
```
# Response looks like formatted context instead of LLM output
Response: "[Context 1]: ### Coverage Area..."
```

**Investigation:**
1. Check for OpenAI API calls in logs: `grep -i openai /tmp/odras_app.log`
2. Verify LLM service initialization and API keys
3. Check exception handling in LLM generation task

## Best Practices

### 1. Variable Naming Conventions

- Use **specific, descriptive names**: `llm_confidence` not `confidence`
- Include **task prefix**: `retrieval_chunks`, `llm_response`, `processed_query`
- Avoid **generic names** that might conflict: `data`, `result`, `output`

### 2. Variable Structure Design

```python
# ✅ Good: Structured data with embedded metadata
{
    "llm_response": json.dumps({
        "answer": "...",
        "confidence": "high",
        "metadata": {...}
    }),
    "processing_stats": {...}
}

# ❌ Problematic: Many separate variables
{
    "response": "...",
    "confidence": "high", 
    "answer_length": 100,
    "context_used": True,
    "llm_called": True
}
```

### 3. Error Handling and Fallbacks

Always provide graceful fallbacks for critical functionality:

```python
# Primary: Use workflow variables
confidence = workflow_variables.get("llm_confidence")

# Fallback: Extract from response text
if not confidence:
    if "high quality" in response_text:
        confidence = "high"
    elif "limited context" in response_text:
        confidence = "low"
    else:
        confidence = None  # Honest unknown

# Never: False confidence
# confidence = "high"  # ❌ Don't fake confidence
```

### 4. LLM Service Integration

#### Proper LLM Call Pattern

```python
async def call_llm_properly(self, context: str, question: str):
    """Call LLM service with proper error handling."""
    try:
        rag_service = get_rag_service()
        
        # Use the same method as hard-coded RAG
        llm_result = await rag_service._generate_response(
            question=question,
            relevant_chunks=context_chunks,
            response_style="comprehensive"
        )
        
        if llm_result and "answer" in llm_result:
            return {
                "answer": llm_result["answer"],
                "confidence": llm_result.get("confidence", None),
                "success": True
            }
        else:
            return {"answer": None, "confidence": None, "success": False}
            
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return {"answer": None, "confidence": None, "success": False}
```

#### Mock vs Real LLM Responses

```python
# ❌ Don't use mock responses in production workflows
mock_response = context_text.strip()

# ✅ Always call actual LLM service
llm_result = await rag_service._generate_response(...)
```

### 5. Frontend Integration

#### Metadata Display

```javascript
// Handle all confidence states properly
const confidence = data.confidence;
const confidenceIcon = confidence === 'high' ? '🟢' : 
                      confidence === 'medium' ? '🟡' : 
                      confidence === 'low' ? '🟠' : '⚪';
const confidenceText = confidence || 'n/a';

// Never show false confidence
// const confidence = data.confidence || 'medium'; // ❌ Wrong
```

#### Loading States

```javascript
// Show proper loading indicators
statusDiv.textContent = useWorkflow ? 'Processing via workflow...' : 'Thinking...';
responseContent.innerHTML = `
  <div class="loading-spinner" style="animation: spin 1s linear infinite;"></div>
  <div>${useWorkflow ? 'Running RAG workflow...' : 'Analyzing knowledge base...'}</div>
`;
```

## Variable Passing Challenges

### Challenge 1: External Task Variable Persistence

**Problem**: Variables set by external tasks don't always persist to process variables.

**Root Cause**: Camunda external task completion API may not immediately persist variables.

**Solution**: Use structured data embedding in reliable variables like `llm_response`.

**Example**:
```python
# Instead of separate variables
return {
    "response": answer,
    "confidence": confidence,
    "metadata": data
}

# Embed in single structured variable
return {
    "llm_response": json.dumps({
        "answer": answer,
        "confidence": confidence,
        "metadata": data
    })
}
```

### Challenge 2: Camunda History API Format

**Problem**: Variables retrieved from Camunda history have different format than active process variables.

**Symptoms**:
```python
# Active process format
{"variable_name": {"value": "actual_data", "type": "String"}}

# History API format  
{"variable_name": {"dataFormatName": "application/json", "nodeType": "ARRAY"}}
```

**Solution**: Handle both formats in variable extraction:
```python
def extract_variable_value(var_data, var_type):
    if isinstance(var_data, dict) and "value" in var_data:
        var_value = var_data["value"]
        if var_type == "Json" and isinstance(var_value, str):
            return json.loads(var_value)
        return var_value
    else:
        return var_data
```

### Challenge 3: Variable Timing Issues

**Problem**: Next task starts before previous task's variables are persisted.

**Investigation**: Check Camunda task completion response codes:
```python
if response.status_code != 204:
    logger.error(f"Failed to complete task: {response.status_code} - {response.text}")
```

**Solution**: Use reliable variable containers and extraction patterns.

## LLM Integration Patterns

### Pattern 1: Direct LLM Service Call

```python
async def handle_llm_generation(self, variables: Dict) -> Dict:
    """Generate LLM response with proper confidence evaluation."""
    
    # Extract context and question
    context_text = extract_context_from_variables(variables)
    user_question = variables.get("user_query", "")
    
    # Call actual LLM service (not mock)
    try:
        rag_service = get_rag_service()
        
        # Create chunks for LLM context
        fake_chunks = [{
            "payload": {
                "content": context_text,
                "asset_id": "workflow_context",
                "source_asset": "workflow_source",
                "document_type": "document"
            },
            "score": 0.8
        }] if context_text else []
        
        # Call LLM
        llm_result = await rag_service._generate_response(
            question=user_question,
            relevant_chunks=fake_chunks,
            response_style="comprehensive"
        )
        
        if llm_result and "answer" in llm_result:
            answer = llm_result["answer"]
            confidence = llm_result.get("confidence", None)
        else:
            answer = "I couldn't generate a response."
            confidence = None
            
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        answer = "Error generating response."
        confidence = None
    
    # Use structured embedding for reliable variable passing
    structured_response = {
        "answer": answer,
        "confidence": confidence,
        "metadata": {
            "llm_called": True,
            "context_length": len(context_text)
        }
    }
    
    return {
        "llm_response": json.dumps(structured_response),
        "processing_status": "success",
        "errors": []
    }
```

### Pattern 2: LLM Response Processing

```python
def handle_process_response(self, variables: Dict) -> Dict:
    """Process LLM response and extract metadata."""
    
    llm_response_raw = variables.get("llm_response", "")
    
    # Extract from structured response
    try:
        structured_data = json.loads(llm_response_raw)
        answer = structured_data.get("answer", "")
        confidence = structured_data.get("confidence")
        metadata = structured_data.get("metadata", {})
    except json.JSONDecodeError:
        # Handle unstructured response
        answer = llm_response_raw
        confidence = None
        metadata = {}
    
    # Process and format response
    final_response = format_response(answer, context_chunks)
    
    return {
        "final_response": final_response,
        "llm_confidence": confidence,  # Pass confidence forward
        "response_metadata": metadata,
        "processing_status": "success"
    }
```

## API Integration

### Workflow Status Polling

```python
async def poll_workflow_completion(process_instance_id: str, max_wait_time: int = 120):
    """Poll workflow until completion with proper timeout."""
    
    start_time = time.time()
    poll_interval = 1
    
    while time.time() - start_time < max_wait_time:
        try:
            status_response = await get_rag_query_status(process_instance_id)
            
            if status_response.get("status") == "completed":
                return status_response
            elif status_response.get("status") == "failed":
                raise HTTPException(status_code=500, detail="Workflow failed")
                
            await asyncio.sleep(poll_interval)
            
        except Exception as e:
            logger.error(f"Error polling workflow: {e}")
            await asyncio.sleep(poll_interval)
    
    raise HTTPException(status_code=408, detail="Workflow timeout")
```

### Variable Extraction from Workflow Response

```python
def extract_metadata_from_workflow(status_response: Dict) -> Dict:
    """Extract metadata from completed workflow."""
    
    workflow_variables = status_response.get("variables", {})
    final_response = status_response.get("final_response", "")
    
    # Primary: Extract from workflow variables
    confidence = workflow_variables.get("llm_confidence")
    chunks_found = workflow_variables.get("chunks_found", 0)
    sources = workflow_variables.get("sources", [])
    
    # Fallback: Parse from response text (reliable backup)
    if not chunks_found and final_response:
        chunks_found = final_response.count('[Context ')
        
    if not sources and 'Sources:' in final_response:
        source_matches = re.findall(r'\[(\d+)\] ([^\n]+)', final_response)
        sources = [{"title": name.strip()} for num, name in source_matches]
    
    return {
        "confidence": confidence,
        "chunks_found": chunks_found,
        "sources": sources
    }
```

## Debugging and Troubleshooting

### Debug Logging Strategy

#### 1. Worker Level Logs

```python
# At task start
logger.info(f"Executing task {task_id} for topic {topic}")
logger.info(f"Task variables: {variables}")

# At task completion  
logger.info(f"Successfully completed task {task_id}")
print(f"TASK_OUTPUT: {result}")
```

#### 2. Camunda API Logs

```python
# In complete_task method
print(f"COMPLETE_TASK: Setting {len(variables)} variables")
print(f"COMPLETE_TASK: Variables = {list(variables.keys())}")

# Check Camunda response
if response.status_code != 204:
    logger.error(f"Camunda API error: {response.status_code} - {response.text}")
```

#### 3. API Extraction Logs

```python
# In API endpoints
print(f"API: Workflow status = {status_response.get('status')}")
print(f"API: Available variables = {list(workflow_variables.keys())}")
print(f"API: Extracted metadata = confidence:{confidence}, chunks:{chunks_found}")
```

### Troubleshooting Checklist

When variables aren't passing correctly:

1. **Check worker logs**: Are variables being set by the task?
2. **Check Camunda completion**: Is the task completing successfully (204 response)?
3. **Check next task logs**: Are variables available to the next task?
4. **Check variable types**: Are complex objects being serialized properly?
5. **Check API extraction**: Is the API getting the right variable format?

### Log Analysis Commands

```bash
# Check variable flow between tasks
tail -100 /tmp/odras_complex_worker.log | grep -E "(COMPLETE_TASK|Available variables)"

# Check LLM calls
tail -100 /tmp/odras_complex_worker.log | grep -E "(openai|LLM)"

# Check API extraction
tail -50 /tmp/odras_app.log | grep -E "(API: Extracted|API:)"

# Check Camunda errors
tail -100 /tmp/odras_complex_worker.log | grep -E "(Failed to complete|ERROR)"
```

## Best Practices

### 1. BPMN Design Principles

- **Single Responsibility**: Each task should have one clear purpose
- **Clear Documentation**: Document expected inputs/outputs for each task
- **Error Handling**: Include error paths and fallback strategies
- **Variable Naming**: Use descriptive, conflict-free variable names

### 2. External Task Implementation

- **Async Operations**: Use proper async/await for LLM calls
- **Error Boundaries**: Wrap LLM calls in try-catch with meaningful fallbacks
- **Resource Management**: Properly initialize and cleanup services
- **Logging**: Comprehensive debug logging for troubleshooting

### 3. Variable Management

- **Structured Data**: Embed related data in single variables when possible
- **Type Safety**: Proper type handling for Camunda variable types
- **Fallback Extraction**: Always have backup methods for critical metadata
- **Validation**: Validate variable content before processing

### 4. API Integration

- **Timeout Handling**: Proper polling with reasonable timeouts
- **Error Responses**: Meaningful error messages for different failure modes
- **Metadata Extraction**: Multiple strategies for extracting workflow results
- **Response Formatting**: Consistent response format for frontend consumption

## Future Expansion Guidelines

### Adding New LLM-Powered Tasks

When adding new tasks to the RAG workflow:

1. **Follow the Pattern**:
   ```python
   async def handle_new_llm_task(self, variables: Dict) -> Dict:
       # Extract inputs
       # Call LLM service
       # Structure response with metadata
       # Return with proper variable names
   ```

2. **Variable Design**:
   - Use task-specific prefixes: `analysis_confidence`, `summary_confidence`
   - Embed metadata in structured responses
   - Provide fallback extraction methods

3. **Testing Strategy**:
   - Test variable passing between tasks
   - Verify LLM calls with debug logging
   - Test API metadata extraction
   - Validate frontend display

### Scaling BPMN Workflows

For complex multi-LLM workflows:

1. **Variable Namespacing**: Use prefixes to avoid conflicts
   ```python
   "retrieval_confidence", "analysis_confidence", "summary_confidence"
   ```

2. **State Management**: Track workflow state through variables
   ```python
   "workflow_stage": "analysis_complete",
   "processing_flags": {"llm_called": True, "context_validated": True}
   ```

3. **Performance Monitoring**: Add timing and performance metrics
   ```python
   "performance_stats": {
       "retrieval_time": 1.2,
       "llm_time": 3.4,
       "total_time": 5.8
   }
   ```

### Common Expansion Patterns

#### Multi-Stage LLM Processing

```
Query → Retrieval → LLM_Analysis → LLM_Summary → LLM_Validation → Response
```

Each stage should:
- Call external LLM with proper confidence evaluation
- Pass structured data to next stage
- Maintain confidence tracking throughout pipeline
- Provide fallback strategies for each stage

#### Parallel LLM Processing

```
Query → Retrieval → [LLM_Path_A, LLM_Path_B, LLM_Path_C] → Ensemble → Response
```

Considerations:
- Variable naming for parallel paths: `llm_a_confidence`, `llm_b_confidence`
- Ensemble confidence calculation
- Timeout handling for parallel tasks

## Lessons Learned

### Critical Insights

1. **BPMN Variable Passing is Fragile**: External task variables don't always persist reliably
2. **Structured Data Works Better**: Embedding metadata in reliable variables is more robust
3. **Fallback Strategies are Essential**: Always have backup extraction methods
4. **LLM Integration Requires Care**: Proper service calls, not mock responses
5. **Debug Logging is Crucial**: Comprehensive logging enables rapid troubleshooting

### What Doesn't Work

- **Separate confidence variables**: Often lost between tasks
- **Mock LLM responses**: Don't provide real confidence evaluation
- **Generic variable names**: Cause conflicts and overwrites
- **Complex variable hierarchies**: Difficult to pass through BPMN reliably
- **Assuming variable persistence**: External task variables can be lost

### What Works Well

- **Structured JSON embedding**: Reliable data transfer
- **Specific variable names**: Avoid conflicts
- **Real LLM service calls**: Proper confidence evaluation
- **Multiple extraction strategies**: Primary + fallback approaches
- **Comprehensive logging**: Enables effective debugging

## Conclusion

Building LLM-powered BPMN workflows requires understanding both Camunda's variable handling limitations and LLM service integration patterns. The key to success is:

1. **Use reliable variable passing patterns** (structured data embedding)
2. **Call actual LLM services** for real confidence evaluation
3. **Implement robust fallback strategies** for metadata extraction
4. **Add comprehensive debug logging** for troubleshooting
5. **Test variable flow thoroughly** between all tasks

This approach enables building sophisticated AI workflows that can scale and expand while maintaining reliability and proper metadata handling.

---

*Document created from RAG Query Process integration experience - September 2025*
