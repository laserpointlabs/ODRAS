"""
Requirements Review Interface HTML Generator
"""


def generate_review_interface_html(task_id: str = None, process_instance_id: str = None) -> str:
    """Generate the HTML for requirements review interface"""

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ODRAS - Requirements Review</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            
            .review-container {{
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.2);
                overflow: hidden;
            }}
            
            .review-header {{
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                color: white;
                padding: 30px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            
            .review-header h1 {{
                font-size: 28px;
                font-weight: 600;
            }}
            
            .process-info {{
                background: rgba(255,255,255,0.2);
                padding: 10px 20px;
                border-radius: 8px;
                font-size: 14px;
            }}
            
            .review-content {{
                padding: 30px;
            }}
            
            .document-info {{
                background: #f8f9fa;
                border-left: 4px solid #3b82f6;
                padding: 20px;
                margin-bottom: 30px;
                border-radius: 8px;
            }}
            
            .document-info h3 {{
                color: #1e293b;
                margin-bottom: 10px;
            }}
            
            .requirements-section {{
                margin-bottom: 30px;
            }}
            
            .requirements-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }}
            
            .requirements-count {{
                background: #3b82f6;
                color: white;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 14px;
            }}
            
            .requirement-card {{
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 15px;
                transition: all 0.3s ease;
                position: relative;
            }}
            
            .requirement-card:hover {{
                border-color: #3b82f6;
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
            }}
            
            .requirement-header {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 15px;
            }}
            
            .requirement-id {{
                background: #eff6ff;
                color: #2563eb;
                padding: 4px 12px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 14px;
            }}
            
            .confidence-badge {{
                padding: 4px 12px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
            }}
            
            .confidence-high {{
                background: #d1fae5;
                color: #065f46;
            }}
            
            .confidence-medium {{
                background: #fed7aa;
                color: #92400e;
            }}
            
            .confidence-low {{
                background: #fee2e2;
                color: #991b1b;
            }}
            
            .requirement-text {{
                color: #1e293b;
                line-height: 1.6;
                margin-bottom: 15px;
                font-size: 15px;
            }}
            
            .requirement-metadata {{
                display: flex;
                gap: 20px;
                flex-wrap: wrap;
                padding-top: 15px;
                border-top: 1px solid #f1f5f9;
            }}
            
            .metadata-item {{
                display: flex;
                align-items: center;
                gap: 8px;
                color: #64748b;
                font-size: 13px;
            }}
            
            .metadata-icon {{
                width: 16px;
                height: 16px;
                fill: currentColor;
            }}
            
            .action-buttons {{
                background: #f8f9fa;
                padding: 30px;
                border-top: 2px solid #e5e7eb;
                display: flex;
                gap: 15px;
                justify-content: center;
                flex-wrap: wrap;
            }}
            
            .action-button {{
                padding: 12px 30px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            
            .btn-approve {{
                background: #10b981;
                color: white;
            }}
            
            .btn-approve:hover {{
                background: #059669;
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
            }}
            
            .btn-rerun {{
                background: #f59e0b;
                color: white;
            }}
            
            .btn-rerun:hover {{
                background: #d97706;
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
            }}
            
            .btn-edit {{
                background: #6366f1;
                color: white;
            }}
            
            .btn-edit:hover {{
                background: #4f46e5;
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
            }}
            
            .btn-edit:disabled {{
                background: #9ca3af;
                cursor: not-allowed;
                opacity: 0.6;
            }}
            
            .loading {{
                text-align: center;
                padding: 60px;
                color: #64748b;
            }}
            
            .spinner {{
                border: 3px solid #f3f4f6;
                border-top: 3px solid #3b82f6;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto 20px;
            }}
            
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            
            .error-message {{
                background: #fee2e2;
                border: 1px solid #fecaca;
                color: #991b1b;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            }}
            
            .success-message {{
                background: #d1fae5;
                border: 1px solid #a7f3d0;
                color: #065f46;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            }}
            
            /* Modal for rerun options */
            .modal {{
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.5);
                animation: fadeIn 0.3s ease;
            }}
            
            @keyframes fadeIn {{
                from {{ opacity: 0; }}
                to {{ opacity: 1; }}
            }}
            
            .modal-content {{
                background-color: white;
                margin: 10% auto;
                padding: 30px;
                border-radius: 12px;
                width: 90%;
                max-width: 500px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                animation: slideIn 0.3s ease;
            }}
            
            @keyframes slideIn {{
                from {{ 
                    transform: translateY(-50px);
                    opacity: 0;
                }}
                to {{ 
                    transform: translateY(0);
                    opacity: 1;
                }}
            }}
            
            .modal-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }}
            
            .modal-header h2 {{
                color: #1e293b;
            }}
            
            .close {{
                color: #94a3b8;
                font-size: 28px;
                font-weight: bold;
                cursor: pointer;
                line-height: 20px;
            }}
            
            .close:hover {{
                color: #475569;
            }}
            
            .form-group {{
                margin-bottom: 20px;
            }}
            
            .form-group label {{
                display: block;
                margin-bottom: 8px;
                color: #475569;
                font-weight: 500;
            }}
            
            .form-group input, .form-group select, .form-group textarea {{
                width: 100%;
                padding: 10px;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                font-size: 14px;
            }}
            
            .form-group input:focus, .form-group select:focus, .form-group textarea:focus {{
                outline: none;
                border-color: #3b82f6;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
            }}
        </style>
    </head>
    <body>
        <div class="review-container">
            <div class="review-header">
                <div>
                    <h1>📋 Requirements Review</h1>
                    <div style="margin-top: 10px; opacity: 0.9;">
                        Review and approve extracted requirements before processing
                    </div>
                </div>
                <div class="process-info">
                    <div>Task ID: <span id="taskId">{task_id or 'Loading...'}</span></div>
                    <div>Process: <span id="processId">{process_instance_id or 'Loading...'}</span></div>
                </div>
            </div>
            
            <div class="review-content">
                <div id="loading" class="loading">
                    <div class="spinner"></div>
                    <div>Loading requirements...</div>
                </div>
                
                <div id="error-container"></div>
                
                <div id="requirements-container" style="display: none;">
                    <div class="document-info">
                        <h3>📄 Document Information</h3>
                        <div id="document-details">
                            <!-- Document details will be loaded here -->
                        </div>
                    </div>
                    
                    <div class="requirements-section">
                        <div class="requirements-header">
                            <h2>Extracted Requirements</h2>
                            <span class="requirements-count" id="req-count">0 Requirements</span>
                        </div>
                        
                        <div id="requirements-list">
                            <!-- Requirements will be loaded here -->
                        </div>
                    </div>
                </div>
            </div>
            
            <div id="action-buttons" class="action-buttons" style="display: none;">
                <button class="action-button btn-approve" onclick="approveRequirements()">
                    ✅ Approve & Continue
                </button>
                <button class="action-button btn-rerun" onclick="showRerunModal()">
                    🔄 Rerun Extraction
                </button>
                <button class="action-button btn-edit" disabled title="Coming soon">
                    ✏️ Edit Requirements
                </button>
            </div>
        </div>
        
        <!-- Rerun Modal -->
        <div id="rerunModal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Rerun Extraction Options</h2>
                    <span class="close" onclick="closeRerunModal()">&times;</span>
                </div>
                
                <div class="form-group">
                    <label for="extraction-method">Extraction Method</label>
                    <select id="extraction-method">
                        <option value="default">Default (Regex + NLP)</option>
                        <option value="strict">Strict Pattern Matching</option>
                        <option value="nlp-only">NLP Only</option>
                        <option value="custom">Custom Patterns</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="confidence-threshold">Minimum Confidence Threshold</label>
                    <input type="number" id="confidence-threshold" min="0" max="1" step="0.1" value="0.5">
                </div>
                
                <div class="form-group">
                    <label for="custom-patterns">Custom Patterns (optional)</label>
                    <textarea id="custom-patterns" rows="3" placeholder="Enter custom regex patterns, one per line"></textarea>
                </div>
                
                <div class="form-group">
                    <label for="rerun-reason">Reason for Rerun</label>
                    <textarea id="rerun-reason" rows="2" placeholder="Why are you rerunning the extraction?"></textarea>
                </div>
                
                <div style="display: flex; gap: 10px; justify-content: flex-end;">
                    <button class="action-button" style="background: #94a3b8;" onclick="closeRerunModal()">
                        Cancel
                    </button>
                    <button class="action-button btn-rerun" onclick="rerunExtraction()">
                        Rerun Extraction
                    </button>
                </div>
            </div>
        </div>
        
        <script>
            let currentProcessId = '{process_instance_id or ""}';
            let currentTaskId = '{task_id or ""}';
            let requirementsData = null;
            
            // Get process ID from URL if not provided
            const urlParams = new URLSearchParams(window.location.search);
            if (!currentTaskId) {{
                currentTaskId = urlParams.get('taskId');
            }}
            if (!currentProcessId) {{
                currentProcessId = urlParams.get('process_instance_id');
            }}
            
            async function loadRequirements() {{
                if (!currentTaskId && !currentProcessId) {{
                    showError('No task ID or process instance ID provided');
                    return;
                }}
                
                try {{
                    // First, get the task details to find process instance ID
                    if (currentTaskId && !currentProcessId) {{
                        const taskResponse = await fetch(`/api/user-tasks`);
                        const taskData = await taskResponse.json();
                        const task = taskData.tasks?.find(t => t.id === currentTaskId);
                        if (task) {{
                            currentProcessId = task.processInstanceId;
                            document.getElementById('processId').textContent = currentProcessId;
                        }}
                    }}
                    
                    if (!currentProcessId) {{
                        showError('Could not determine process instance ID');
                        return;
                    }}
                    
                    // Fetch requirements - try regular endpoint first, then test endpoint
                    let response = await fetch(`/api/user-tasks/${{currentProcessId}}/requirements`);
                    if (!response.ok) {{
                        console.log('Regular endpoint failed, trying test endpoint...');
                        response = await fetch(`/api/test/user-tasks/${{currentProcessId}}/requirements`);
                        if (!response.ok) {{
                            throw new Error(`Failed to load requirements: ${{response.statusText}}`);
                        }}
                    }}
                    
                    requirementsData = await response.json();
                    displayRequirements(requirementsData);
                    
                }} catch (error) {{
                    showError(`Error loading requirements: ${{error.message}}`);
                }}
            }}
            
            function displayRequirements(data) {{
                document.getElementById('loading').style.display = 'none';
                document.getElementById('requirements-container').style.display = 'block';
                document.getElementById('action-buttons').style.display = 'flex';
                
                // Display document info
                const docDetails = document.getElementById('document-details');
                docDetails.innerHTML = `
                    <div style="display: grid; grid-template-columns: auto 1fr; gap: 10px;">
                        <strong>Filename:</strong> <span>${{data.document_filename || 'Unknown'}}</span>
                        <strong>Total Requirements:</strong> <span>${{data.total_requirements || 0}}</span>
                        <strong>Process Instance:</strong> <span style="font-family: monospace; font-size: 12px;">${{data.process_instance_id}}</span>
                    </div>
                `;
                
                // Update requirements count
                document.getElementById('req-count').textContent = `${{data.total_requirements || 0}} Requirements`;
                
                // Display requirements
                const reqList = document.getElementById('requirements-list');
                if (data.requirements && data.requirements.length > 0) {{
                    reqList.innerHTML = data.requirements.map((req, index) => {{
                        const confidence = req.confidence || 0;
                        const confidenceClass = confidence >= 0.8 ? 'confidence-high' : 
                                               confidence >= 0.5 ? 'confidence-medium' : 'confidence-low';
                        const confidencePercent = Math.round(confidence * 100);
                        
                        return `
                            <div class="requirement-card">
                                <div class="requirement-header">
                                    <span class="requirement-id">REQ-${{String(index + 1).padStart(3, '0')}}</span>
                                    <span class="confidence-badge ${{confidenceClass}}">
                                        Confidence: ${{confidencePercent}}%
                                    </span>
                                </div>
                                
                                <div class="requirement-text">
                                    ${{escapeHtml(req.text || req.requirement_text || 'No text available')}}
                                </div>
                                
                                <div class="requirement-metadata">
                                    <div class="metadata-item">
                                        <svg class="metadata-icon" viewBox="0 0 20 20" fill="currentColor">
                                            <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"/>
                                        </svg>
                                        <span>${{req.category || 'Uncategorized'}}</span>
                                    </div>
                                    
                                    <div class="metadata-item">
                                        <svg class="metadata-icon" viewBox="0 0 20 20" fill="currentColor">
                                            <path fill-rule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clip-rule="evenodd"/>
                                        </svg>
                                        <span>Source: ${{req.source || data.document_filename || 'Unknown'}}</span>
                                    </div>
                                    
                                    ${{req.priority ? `
                                    <div class="metadata-item">
                                        <svg class="metadata-icon" viewBox="0 0 20 20" fill="currentColor">
                                            <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"/>
                                        </svg>
                                        <span>Priority: ${{req.priority}}</span>
                                    </div>
                                    ` : ''}}
                                </div>
                            </div>
                        `;
                    }}).join('');
                }} else {{
                    reqList.innerHTML = '<div class="error-message">No requirements found in the document.</div>';
                }}
            }}
            
            function escapeHtml(text) {{
                const map = {{
                    '&': '&amp;',
                    '<': '&lt;',
                    '>': '&gt;',
                    '"': '&quot;',
                    "'": '&#039;'
                }};
                return text.replace(/[&<>"']/g, m => map[m]);
            }}
            
            function showError(message) {{
                document.getElementById('loading').style.display = 'none';
                document.getElementById('error-container').innerHTML = 
                    `<div class="error-message">❌ ${{message}}</div>`;
            }}
            
            function showSuccess(message) {{
                document.getElementById('error-container').innerHTML = 
                    `<div class="success-message">✅ ${{message}}</div>`;
            }}
            
            async function approveRequirements() {{
                if (!currentProcessId) {{
                    showError('No process instance ID available');
                    return;
                }}
                
                try {{
                    let response = await fetch(`/api/user-tasks/${{currentProcessId}}/complete`, {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            decision: 'approve',
                            approved_requirements: requirementsData?.requirements || []
                        }})
                    }});
                    
                    if (!response.ok) {{
                        console.log('Regular complete endpoint failed, trying test endpoint...');
                        response = await fetch(`/api/test/user-tasks/${{currentProcessId}}/complete`, {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{
                                decision: 'approve',
                                approved_requirements: requirementsData?.requirements || []
                            }})
                        }});
                        if (!response.ok) {{
                            throw new Error(`Failed to approve: ${{response.statusText}}`);
                        }}
                    }}
                    
                    const result = await response.json();
                    showSuccess('Requirements approved successfully! Proceeding to LLM processing...');
                    
                    // Disable buttons after approval
                    document.querySelectorAll('.action-button').forEach(btn => {{
                        btn.disabled = true;
                        btn.style.opacity = '0.5';
                    }});
                    
                    // Redirect after 2 seconds
                    setTimeout(() => {{
                        window.location.href = '/?tab=tasks';
                    }}, 2000);
                    
                }} catch (error) {{
                    showError(`Error approving requirements: ${{error.message}}`);
                }}
            }}
            
            function showRerunModal() {{
                document.getElementById('rerunModal').style.display = 'block';
            }}
            
            function closeRerunModal() {{
                document.getElementById('rerunModal').style.display = 'none';
            }}
            
            async function rerunExtraction() {{
                if (!currentProcessId) {{
                    showError('No process instance ID available');
                    return;
                }}
                
                const extractionMethod = document.getElementById('extraction-method').value;
                const confidenceThreshold = parseFloat(document.getElementById('confidence-threshold').value);
                const customPatterns = document.getElementById('custom-patterns').value;
                const rerunReason = document.getElementById('rerun-reason').value;
                
                try {{
                    let response = await fetch(`/api/user-tasks/${{currentProcessId}}/complete`, {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            decision: 'rerun',
                            extraction_parameters: {{
                                method: extractionMethod,
                                confidence_threshold: confidenceThreshold,
                                custom_patterns: customPatterns ? customPatterns.split('\\n').filter(p => p.trim()) : [],
                                reason: rerunReason
                            }}
                        }})
                    }});
                    
                    if (!response.ok) {{
                        console.log('Regular complete endpoint failed, trying test endpoint...');
                        response = await fetch(`/api/test/user-tasks/${{currentProcessId}}/complete`, {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{
                                decision: 'rerun',
                                extraction_parameters: {{
                                    method: extractionMethod,
                                    confidence_threshold: confidenceThreshold,
                                    custom_patterns: customPatterns ? customPatterns.split('\\n').filter(p => p.trim()) : [],
                                    reason: rerunReason
                                }}
                            }})
                        }});
                        if (!response.ok) {{
                            throw new Error(`Failed to rerun: ${{response.statusText}}`);
                        }}
                    }}
                    
                    const result = await response.json();
                    showSuccess('Rerun initiated! Requirements will be re-extracted with new parameters...');
                    closeRerunModal();
                    
                    // Disable buttons after rerun
                    document.querySelectorAll('.action-button').forEach(btn => {{
                        btn.disabled = true;
                        btn.style.opacity = '0.5';
                    }});
                    
                    // Redirect after 2 seconds
                    setTimeout(() => {{
                        window.location.href = '/?tab=tasks';
                    }}, 2000);
                    
                }} catch (error) {{
                    showError(`Error rerunning extraction: ${{error.message}}`);
                }}
            }}
            
            // Close modal when clicking outside
            window.onclick = function(event) {{
                const modal = document.getElementById('rerunModal');
                if (event.target === modal) {{
                    closeRerunModal();
                }}
            }}
            
            // Load requirements on page load
            document.addEventListener('DOMContentLoaded', loadRequirements);
        </script>
    </body>
    </html>
    """
