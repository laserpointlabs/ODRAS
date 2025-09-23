# User Task Integration in ODRAS BPMN Workflow<br>
<br>
## Overview<br>
<br>
The ODRAS BPMN workflow has been enhanced with a **user task** that allows users to review, edit, rerun, or approve extracted requirements before proceeding to the LLM extraction phase. This provides human oversight and quality control in the requirements analysis process.<br>
<br>
## BPMN Workflow Changes<br>
<br>
### New Process Flow<br>
<br>
The updated BPMN workflow now includes:<br>
<br>
```<br>
Document Upload → Extract Requirements → [USER TASK] → LLM Processing → Storage → Complete<br>
                                    ↑<br>
                              User Review &<br>
                              Decision Point<br>
```<br>
<br>
### User Task Details<br>
<br>
**Task ID**: `Task_UserReview`<br>
**Task Type**: User Task<br>
**Description**: Review and approve extracted requirements<br>
<br>
The user can choose from three actions:<br>
<br>
1. **✅ Approve & Continue**: Proceed to LLM processing with current requirements<br>
2. **✏️ Edit Requirements**: Modify requirements manually before continuing<br>
3. **🔄 Rerun Extraction**: Re-extract requirements with different parameters<br>
<br>
### Decision Gateway<br>
<br>
After the user task, a decision gateway (`Gateway_UserChoice`) routes the process based on the user's choice:<br>
<br>
- **Approve**: Direct path to LLM processing<br>
- **Edit**: Process user edits, then merge back to LLM processing<br>
- **Rerun**: Execute new extraction, then merge back to LLM processing<br>
<br>
## Implementation Details<br>
<br>
### New External Task Scripts<br>
<br>
#### 1. `task_handle_user_edits.py`<br>
<br>
Handles user modifications to extracted requirements:<br>
<br>
- **Modify**: Change requirement text, category, confidence, etc.<br>
- **Add**: Insert new requirements manually<br>
- **Delete**: Soft-delete requirements with reason tracking<br>
- **Validation**: Ensures edited requirements meet quality standards<br>
- **Audit Trail**: Tracks all modifications with timestamps<br>
<br>
#### 2. `task_rerun_extraction.py`<br>
<br>
Re-executes requirements extraction with new parameters:<br>
<br>
- **Custom Patterns**: User-defined regex patterns<br>
- **Confidence Threshold**: Adjustable extraction sensitivity<br>
- **Text Length Filters**: Minimum requirement text length<br>
- **Category Filtering**: Focus on specific requirement types<br>
- **Change Comparison**: Compare new vs. previous extractions<br>
<br>
### Backend API Endpoints<br>
<br>
#### User Task Management<br>
<br>
- `GET /api/user-tasks/{process_instance_id}` - Get user tasks for a process<br>
- `GET /api/user-tasks/{process_instance_id}/requirements` - Get requirements for review<br>
- `POST /api/user-tasks/{process_instance_id}/complete` - Complete user task with decision<br>
- `GET /api/user-tasks/{process_instance_id}/status` - Get current task status<br>
<br>
#### User Decision API<br>
<br>
```json<br>
POST /api/user-tasks/{process_id}/complete<br>
{<br>
  "decision": "approve|edit|rerun",<br>
  "user_edits": [...],           // For edit decisions<br>
  "extraction_parameters": {...}  // For rerun decisions<br>
}<br>
```<br>
<br>
### Frontend Interface<br>
<br>
The web interface includes:<br>
<br>
- **Requirements Display**: Grid view of extracted requirements with confidence scores<br>
- **Edit Interface**: Inline editing for requirement text, category, and confidence<br>
- **Rerun Interface**: Parameter adjustment for extraction rerun<br>
- **Decision Buttons**: Clear action buttons for user choices<br>
- **Real-time Monitoring**: Process state tracking and updates<br>
<br>
## Usage Workflow<br>
<br>
### 1. Document Upload & Extraction<br>
<br>
1. User uploads document via web interface<br>
2. System extracts requirements using regex patterns<br>
3. Process pauses at user task<br>
<br>
### 2. User Review<br>
<br>
1. User reviews extracted requirements<br>
2. User can:<br>
   - **Approve**: Continue with current requirements<br>
   - **Edit**: Modify specific requirements<br>
   - **Rerun**: Adjust extraction parameters<br>
<br>
### 3. Process Continuation<br>
<br>
1. **Approve**: Process continues to LLM analysis<br>
2. **Edit**: User edits are processed, then continue<br>
3. **Rerun**: New extraction runs, then continue<br>
<br>
### 4. Completion<br>
<br>
Process continues through LLM processing and storage phases as before.<br>
<br>
## Configuration Options<br>
<br>
### Extraction Parameters<br>
<br>
```json<br>
{<br>
  "confidence_threshold": 0.6,<br>
  "min_text_length": 15,<br>
  "categories_filter": ["Security", "Performance"],<br>
  "custom_patterns": ["\\b(shall|must)\\b.*?[.!?]"]<br>
}<br>
```<br>
<br>
### User Edit Options<br>
<br>
- **Text Modification**: Change requirement content<br>
- **Category Assignment**: Assign requirement categories<br>
- **Confidence Adjustment**: Modify extraction confidence scores<br>
- **Requirement Addition**: Add new requirements manually<br>
- **Requirement Removal**: Mark requirements for deletion<br>
<br>
## Benefits<br>
<br>
### Quality Control<br>
<br>
- **Human Oversight**: Users can review and validate extracted requirements<br>
- **Error Correction**: Fix false positives or missed requirements<br>
- **Context Awareness**: Human judgment for ambiguous cases<br>
<br>
### Flexibility<br>
<br>
- **Parameter Tuning**: Adjust extraction sensitivity without restarting<br>
- **Manual Refinement**: Add domain-specific requirements<br>
- **Iterative Improvement**: Refine extraction results<br>
<br>
### Audit Trail<br>
<br>
- **Change Tracking**: All modifications are logged with timestamps<br>
- **Decision History**: Complete record of user choices<br>
- **Process Transparency**: Clear visibility into workflow decisions<br>
<br>
## Technical Architecture<br>
<br>
### Camunda Integration<br>
<br>
- **User Task**: Native Camunda user task implementation<br>
- **External Tasks**: Python scripts for edit/rerun processing<br>
- **Process Variables**: Dynamic variable passing between tasks<br>
- **State Management**: Process instance state tracking<br>
<br>
### Data Flow<br>
<br>
1. **Extraction Results** → Stored in process variables<br>
2. **User Decisions** → Captured via API endpoints<br>
3. **Process Continuation** → Variables passed to next tasks<br>
4. **Result Storage** → Final requirements stored in databases<br>
<br>
### Error Handling<br>
<br>
- **Validation Errors**: User edits are validated before processing<br>
- **Process Failures**: Graceful handling of task failures<br>
- **Rollback Support**: Process can be restarted from user task<br>
- **Status Monitoring**: Real-time process state updates<br>
<br>
## Testing<br>
<br>
### Test Script<br>
<br>
Run the test script to verify functionality:<br>
<br>
```bash<br>
cd scripts<br>
python test_user_task_scripts.py<br>
```<br>
<br>
### Manual Testing<br>
<br>
1. Start the backend server<br>
2. Upload a test document<br>
3. Navigate through the user review interface<br>
4. Test all three decision paths<br>
5. Verify process completion<br>
<br>
## Future Enhancements<br>
<br>
### Planned Features<br>
<br>
- **Batch Editing**: Edit multiple requirements simultaneously<br>
- **Template Support**: Pre-defined requirement templates<br>
- **Collaborative Review**: Multiple user review support<br>
- **Advanced Validation**: AI-powered requirement validation<br>
- **Integration APIs**: Connect with external requirement management systems<br>
<br>
### Performance Optimizations<br>
<br>
- **Async Processing**: Non-blocking user task completion<br>
- **Caching**: Requirement data caching for large documents<br>
- **Parallel Processing**: Concurrent edit/rerun operations<br>
- **Database Optimization**: Efficient storage and retrieval<br>
<br>
## Troubleshooting<br>
<br>
### Common Issues<br>
<br>
1. **User Task Not Appearing**: Check Camunda process deployment<br>
2. **Edit Failures**: Verify requirement ID format and data types<br>
3. **Rerun Errors**: Check extraction parameter validation<br>
4. **Process Hanging**: Monitor Camunda process instance status<br>
<br>
### Debug Steps<br>
<br>
1. Check Camunda Cockpit for process state<br>
2. Review backend API logs for errors<br>
3. Verify external task script execution<br>
4. Check process variable values<br>
<br>
## Conclusion<br>
<br>
The user task integration provides a robust, user-friendly interface for requirements review and modification. It maintains the automated workflow benefits while adding essential human oversight and quality control capabilities.<br>
<br>
This enhancement makes ODRAS more suitable for production use where human validation of extracted requirements is critical for accuracy and compliance.<br>
<br>

