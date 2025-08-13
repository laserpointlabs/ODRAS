# User Task Integration in ODRAS BPMN Workflow

## Overview

The ODRAS BPMN workflow has been enhanced with a **user task** that allows users to review, edit, rerun, or approve extracted requirements before proceeding to the LLM extraction phase. This provides human oversight and quality control in the requirements analysis process.

## BPMN Workflow Changes

### New Process Flow

The updated BPMN workflow now includes:

```
Document Upload → Extract Requirements → [USER TASK] → LLM Processing → Storage → Complete
                                    ↑
                              User Review &
                              Decision Point
```

### User Task Details

**Task ID**: `Task_UserReview`  
**Task Type**: User Task  
**Description**: Review and approve extracted requirements

The user can choose from three actions:

1. **✅ Approve & Continue**: Proceed to LLM processing with current requirements
2. **✏️ Edit Requirements**: Modify requirements manually before continuing
3. **🔄 Rerun Extraction**: Re-extract requirements with different parameters

### Decision Gateway

After the user task, a decision gateway (`Gateway_UserChoice`) routes the process based on the user's choice:

- **Approve**: Direct path to LLM processing
- **Edit**: Process user edits, then merge back to LLM processing
- **Rerun**: Execute new extraction, then merge back to LLM processing

## Implementation Details

### New External Task Scripts

#### 1. `task_handle_user_edits.py`

Handles user modifications to extracted requirements:

- **Modify**: Change requirement text, category, confidence, etc.
- **Add**: Insert new requirements manually
- **Delete**: Soft-delete requirements with reason tracking
- **Validation**: Ensures edited requirements meet quality standards
- **Audit Trail**: Tracks all modifications with timestamps

#### 2. `task_rerun_extraction.py`

Re-executes requirements extraction with new parameters:

- **Custom Patterns**: User-defined regex patterns
- **Confidence Threshold**: Adjustable extraction sensitivity
- **Text Length Filters**: Minimum requirement text length
- **Category Filtering**: Focus on specific requirement types
- **Change Comparison**: Compare new vs. previous extractions

### Backend API Endpoints

#### User Task Management

- `GET /api/user-tasks/{process_instance_id}` - Get user tasks for a process
- `GET /api/user-tasks/{process_instance_id}/requirements` - Get requirements for review
- `POST /api/user-tasks/{process_instance_id}/complete` - Complete user task with decision
- `GET /api/user-tasks/{process_instance_id}/status` - Get current task status

#### User Decision API

```json
POST /api/user-tasks/{process_id}/complete
{
  "decision": "approve|edit|rerun",
  "user_edits": [...],           // For edit decisions
  "extraction_parameters": {...}  // For rerun decisions
}
```

### Frontend Interface

The web interface includes:

- **Requirements Display**: Grid view of extracted requirements with confidence scores
- **Edit Interface**: Inline editing for requirement text, category, and confidence
- **Rerun Interface**: Parameter adjustment for extraction rerun
- **Decision Buttons**: Clear action buttons for user choices
- **Real-time Monitoring**: Process state tracking and updates

## Usage Workflow

### 1. Document Upload & Extraction

1. User uploads document via web interface
2. System extracts requirements using regex patterns
3. Process pauses at user task

### 2. User Review

1. User reviews extracted requirements
2. User can:
   - **Approve**: Continue with current requirements
   - **Edit**: Modify specific requirements
   - **Rerun**: Adjust extraction parameters

### 3. Process Continuation

1. **Approve**: Process continues to LLM analysis
2. **Edit**: User edits are processed, then continue
3. **Rerun**: New extraction runs, then continue

### 4. Completion

Process continues through LLM processing and storage phases as before.

## Configuration Options

### Extraction Parameters

```json
{
  "confidence_threshold": 0.6,
  "min_text_length": 15,
  "categories_filter": ["Security", "Performance"],
  "custom_patterns": ["\\b(shall|must)\\b.*?[.!?]"]
}
```

### User Edit Options

- **Text Modification**: Change requirement content
- **Category Assignment**: Assign requirement categories
- **Confidence Adjustment**: Modify extraction confidence scores
- **Requirement Addition**: Add new requirements manually
- **Requirement Removal**: Mark requirements for deletion

## Benefits

### Quality Control

- **Human Oversight**: Users can review and validate extracted requirements
- **Error Correction**: Fix false positives or missed requirements
- **Context Awareness**: Human judgment for ambiguous cases

### Flexibility

- **Parameter Tuning**: Adjust extraction sensitivity without restarting
- **Manual Refinement**: Add domain-specific requirements
- **Iterative Improvement**: Refine extraction results

### Audit Trail

- **Change Tracking**: All modifications are logged with timestamps
- **Decision History**: Complete record of user choices
- **Process Transparency**: Clear visibility into workflow decisions

## Technical Architecture

### Camunda Integration

- **User Task**: Native Camunda user task implementation
- **External Tasks**: Python scripts for edit/rerun processing
- **Process Variables**: Dynamic variable passing between tasks
- **State Management**: Process instance state tracking

### Data Flow

1. **Extraction Results** → Stored in process variables
2. **User Decisions** → Captured via API endpoints
3. **Process Continuation** → Variables passed to next tasks
4. **Result Storage** → Final requirements stored in databases

### Error Handling

- **Validation Errors**: User edits are validated before processing
- **Process Failures**: Graceful handling of task failures
- **Rollback Support**: Process can be restarted from user task
- **Status Monitoring**: Real-time process state updates

## Testing

### Test Script

Run the test script to verify functionality:

```bash
cd scripts
python test_user_task_scripts.py
```

### Manual Testing

1. Start the backend server
2. Upload a test document
3. Navigate through the user review interface
4. Test all three decision paths
5. Verify process completion

## Future Enhancements

### Planned Features

- **Batch Editing**: Edit multiple requirements simultaneously
- **Template Support**: Pre-defined requirement templates
- **Collaborative Review**: Multiple user review support
- **Advanced Validation**: AI-powered requirement validation
- **Integration APIs**: Connect with external requirement management systems

### Performance Optimizations

- **Async Processing**: Non-blocking user task completion
- **Caching**: Requirement data caching for large documents
- **Parallel Processing**: Concurrent edit/rerun operations
- **Database Optimization**: Efficient storage and retrieval

## Troubleshooting

### Common Issues

1. **User Task Not Appearing**: Check Camunda process deployment
2. **Edit Failures**: Verify requirement ID format and data types
3. **Rerun Errors**: Check extraction parameter validation
4. **Process Hanging**: Monitor Camunda process instance status

### Debug Steps

1. Check Camunda Cockpit for process state
2. Review backend API logs for errors
3. Verify external task script execution
4. Check process variable values

## Conclusion

The user task integration provides a robust, user-friendly interface for requirements review and modification. It maintains the automated workflow benefits while adding essential human oversight and quality control capabilities.

This enhancement makes ODRAS more suitable for production use where human validation of extracted requirements is critical for accuracy and compliance.

