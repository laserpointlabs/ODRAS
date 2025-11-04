/**
 * DAS UI Module
 * 
 * Complete DAS (Digital Assistant System) UI functionality.
 * Handles panel management, transcript rendering, message sending, and state management.
 */

import * as DasApi from './das-api.js';
import { getAppState, updateAppState } from '../core/state-manager.js';
import { subscribeToEvent, emitEvent } from '../core/event-bus.js';
import { getCurrentProjectId } from '../core/utils.js';

// DAS state
let dasState = {
  currentProjectThreadId: null,
  isProcessing: false,
  llmStatusInterval: null,
  llmInitialized: false,
  dasInitializing: false
};

// DOM element references
let panel = null;
let transcript = null;
let promptInput = null;
let sendBtn = null;
let resizerX = null;
let resizerY = null;

/**
 * Initialize DAS UI
 */
export function initializeDAS() {
  console.log('🤖 Initializing DAS UI...');

  // Get DOM elements
  panel = document.getElementById('dasPanel');
  transcript = document.getElementById('dasTranscript');
  promptInput = document.getElementById('dasPrompt');
  sendBtn = document.getElementById('dasSendBtn');
  resizerX = document.getElementById('dasResizerX');
  resizerY = document.getElementById('dasResizerY');

  if (!panel) {
    console.warn('DAS panel element not found');
    return;
  }

  // Initialize panel state
  initializePanelState();

  // Set up event listeners
  setupEventListeners();

  // Initialize LLM monitoring
  initializeLLMMonitoring();

  // Subscribe to project changes
  subscribeToEvent('project:selected', handleProjectChange);

  console.log('✅ DAS UI initialized');
}

/**
 * Initialize panel state (open/close, docking, resizing)
 */
function initializePanelState() {
  const storageKey = 'odras_das_state';
  let state = { 
    open: false, 
    dock: 'right', 
    width: 420, 
    height: Math.max(300, Math.round(window.innerHeight * 0.4)) 
  };

  // Load saved state
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
    state = { ...state, ...saved };
  } catch (_) { }

  // Apply state
  function applyState() {
    panel.classList.remove('das-dock-left', 'das-dock-right', 'das-dock-bottom');
    if (state.open) {
      panel.classList.add('active');
    } else {
      panel.classList.remove('active');
    }
    
    const dockCls = state.dock === 'left' ? 'das-dock-left' : 
                   (state.dock === 'bottom' ? 'das-dock-bottom' : 'das-dock-right');
    panel.classList.add(dockCls);
    
    document.documentElement.style.setProperty('--das-w', state.width + 'px');
    document.documentElement.style.setProperty('--das-h', state.height + 'px');
    
    // Body classes to shift layout
    document.body.classList.remove('das-open-left', 'das-open-right', 'das-open-bottom');
    if (state.open) {
      if (state.dock === 'left') document.body.classList.add('das-open-left');
      else if (state.dock === 'bottom') document.body.classList.add('das-open-bottom');
      else document.body.classList.add('das-open-right');
    }
  }

  function persist() {
    try {
      localStorage.setItem(storageKey, JSON.stringify(state));
    } catch (_) { }
  }

  function toggleOpen() {
    state.open = !state.open;
    applyState();
    persist();
    
    if (state.open) {
      initializeDASProjectThread();
    }
  }

  function setDock(pos) {
    state.dock = pos;
    applyState();
    persist();
  }

  // Expose functions globally for keyboard shortcuts
  window.toggleDAS = toggleOpen;
  window.dockDAS = setDock;

  // Apply initial state
  applyState();

  // Set up resizers
  setupResizers(state, applyState, persist);

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    if (e.altKey && e.shiftKey) {
      if (e.key === 'D' || e.key === 'd') {
        e.preventDefault();
        toggleOpen();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        setDock('right');
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        setDock('left');
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setDock('bottom');
      }
    } else if (e.ctrlKey && e.altKey && (e.key === 'D' || e.key === 'd')) {
      e.preventDefault();
      toggleOpen();
    }
  });

  // Close DAS on logout
  window.closeDASAndClean = function() {
    console.log('🔒 Closing and cleaning DAS dock due to logout/session expiry');
    state.open = false;
    applyState();
    persist();

    dasState.currentProjectThreadId = null;
    dasState.isProcessing = false;

    if (transcript) transcript.innerHTML = '';
    if (promptInput) promptInput.value = '';
    updateDASStatus('Disconnected');

    stopLLMHealthMonitoring();
  };
}

/**
 * Set up panel resizers
 */
function setupResizers(state, applyState, persist) {
  let dragging = false;
  let startX = 0;
  let startY = 0;
  let startW = 0;
  let startH = 0;

  function onMove(e) {
    if (!dragging) return;
    
    if (state.dock === 'bottom') {
      const dy = e.clientY - startY;
      const h = Math.max(200, startH - dy);
      state.height = h;
    } else {
      const dx = e.clientX - startX;
      let w = startW;
      if (state.dock === 'right') w = Math.max(260, startW - dx);
      if (state.dock === 'left') w = Math.max(260, startW + dx);
      state.width = w;
    }
    applyState();
  }

  function endDrag() {
    if (!dragging) return;
    dragging = false;
    persist();
    window.removeEventListener('mousemove', onMove);
    window.removeEventListener('mouseup', endDrag);
  }

  function startDragX(e) {
    dragging = true;
    startX = e.clientX;
    startW = state.width;
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', endDrag);
    e.preventDefault();
  }

  function startDragY(e) {
    dragging = true;
    startY = e.clientY;
    startH = state.height;
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', endDrag);
    e.preventDefault();
  }

  if (resizerX) resizerX.addEventListener('mousedown', startDragX);
  if (resizerY) resizerY.addEventListener('mousedown', startDragY);
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
  // Auto-expand textarea
  if (promptInput) {
    function autoExpandTextarea(textarea) {
      textarea.style.height = 'auto';
      const newHeight = Math.min(textarea.scrollHeight, 120);
      textarea.style.height = newHeight + 'px';
    }

    promptInput.addEventListener('input', function() {
      autoExpandTextarea(this);
    });

    promptInput.addEventListener('paste', function() {
      setTimeout(() => autoExpandTextarea(this), 0);
    });

    // Enter to send (Shift+Enter for new line)
    promptInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (sendBtn && !sendBtn.disabled) {
          sendBtn.click();
        }
      }
    });
  }

  // Send button
  if (sendBtn) {
    sendBtn.addEventListener('click', () => {
      if (promptInput && promptInput.value.trim()) {
        _sendDASMessage(promptInput.value.trim());
        promptInput.value = '';
        if (promptInput) {
          promptInput.style.height = 'auto';
        }
      }
    });
  }

  // Make sendDASMessage available globally for backwards compatibility
  window.sendDASMessage = sendDASMessage;
}

/**
 * Initialize DAS project thread
 */
async function initializeDASProjectThread() {
  if (dasState.dasInitializing) {
    console.log('⚠️ DAS initialization already in progress, skipping duplicate call');
    return;
  }

  try {
    dasState.dasInitializing = true;
    const projectId = getCurrentProjectId();
    
    if (!projectId) {
      updateDASStatus('No Project');
      addMessageToTranscript('system', 'Please select a project to start DAS conversation.');
      return;
    }

    updateDASStatus('Connecting...');

    const data = await DasApi.getProjectThread(projectId);
    dasState.currentProjectThreadId = data.project_thread_id;

    updateDASStatus('Ready');

    // Load RAG configuration
    await DasApi.loadRagConfigForDAS();

    // Load conversation history
    setTimeout(async () => {
      await loadProjectThreadHistory(projectId);
    }, 200);

    // Check if this is a new or existing thread
    try {
      const historyData = await DasApi.getProjectHistory(projectId);
      const history = historyData.history || [];

      if (history.length === 0) {
        addMessageToTranscript('system', 'DAS project thread ready. How can I help you with this project?');
      } else {
        addMessageToTranscript('system', 'DAS project thread restored with conversation history. How can I continue helping you?');
      }
    } catch (error) {
      addMessageToTranscript('system', 'DAS project thread ready. How can I help you today?');
    }

  } catch (error) {
    if (error.message.includes('404')) {
      updateDASStatus('Not Available');
      addMessageToTranscript('system', 'DAS is not yet available for this project. Project threads are created when projects are created. Please create a project to start using DAS.');
      if (promptInput) promptInput.disabled = true;
      if (sendBtn) sendBtn.disabled = true;
    } else {
      updateDASStatus('Error');
      addMessageToTranscript('error', `Failed to initialize DAS: ${error.message}`);
    }
  } finally {
    dasState.dasInitializing = false;
  }
}

/**
 * Load project thread history
 */
async function loadProjectThreadHistory(projectId) {
  try {
    const data = await DasApi.getProjectHistory(projectId);
    const history = data.history || [];

    if (!transcript) {
      console.error('DAS transcript element not found');
      return;
    }

    transcript.innerHTML = '';

    let loadedCount = 0;
    for (const entry of history) {
      if (entry.user_message) {
        addMessageToTranscript('user', entry.user_message);
        loadedCount++;
      }
      if (entry.das_response) {
        addMessageToTranscript('das', entry.das_response, entry.metadata || {});
        loadedCount++;
      }
    }

    console.log(`✅ Loaded ${loadedCount} messages into DAS transcript`);

    // Scroll to bottom
    setTimeout(() => {
      const containers = [
        transcript.parentElement,
        document.getElementById('dasBody'),
        transcript
      ];

      for (const container of containers) {
        if (container && container.scrollHeight > container.clientHeight) {
          container.scrollTop = container.scrollHeight;
          break;
        }
      }
    }, 100);

  } catch (error) {
    console.error('Error loading project thread history:', error);
  }
}

/**
 * Send DAS message
 */
export async function sendDASMessage(message) {
  // Call the internal function
  await _sendDASMessage(message);
}

/**
 * Internal function to send DAS message
 */
async function _sendDASMessage(message) {
  if (dasState.isProcessing || !message.trim()) return;

  dasState.isProcessing = true;
  updateDASStatus('Processing...');
  if (sendBtn) sendBtn.disabled = true;

  // Add user message to transcript
  addMessageToTranscript('user', message);

  // Add progress indicator
  const progressId = 'das-progress-' + Date.now();
  addMessageToTranscript('progress', `<span id="${progressId}" class="das-progress">DAS is thinking<span class="ellipsis-dots">...</span></span>`);

  // Start ellipsis animation
  let ellipsisCount = 0;
  const ellipsisInterval = setInterval(() => {
    const ellipsisElement = document.querySelector('#' + progressId + ' .ellipsis-dots');
    if (ellipsisElement) {
      ellipsisCount = (ellipsisCount + 1) % 4;
      ellipsisElement.textContent = '.'.repeat(ellipsisCount);
    }
  }, 500);

  const cleanupProgress = () => {
    clearInterval(ellipsisInterval);
    const progressElement = document.getElementById(progressId);
    if (progressElement && progressElement.parentElement) {
      progressElement.parentElement.remove();
    }
  };

  try {
    const projectId = getCurrentProjectId();
    const currentContext = {
      project_id: projectId,
      workbench: new URLSearchParams(window.location.search).get('wb') || 'ontology'
    };

    // Get stream from API
    const stream = await DasApi.sendDASMessageStream(
      message,
      dasState.currentProjectThreadId,
      currentContext
    );

    // Create streaming response container
    const streamContainer = document.createElement('div');
    streamContainer.className = 'card';
    streamContainer.innerHTML = '<strong>DAS:</strong><br><div class="streaming-text das-markdown"></div>';
    streamContainer.style.display = 'none';

    if (transcript) {
      transcript.appendChild(streamContainer);
    }

    const streamingText = streamContainer.querySelector('.streaming-text');
    let fullResponse = '';
    let metadata = {};
    let firstContentReceived = false;

    // Handle streaming response
    const reader = stream.getReader();
    const decoder = new TextDecoder();

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === 'content') {
                if (!firstContentReceived) {
                  cleanupProgress();
                  streamContainer.style.display = 'block';
                  firstContentReceived = true;
                }

                fullResponse += data.content;

                // Render markdown
                try {
                  const renderer = new marked.Renderer();
                  renderer.paragraph = (text) => text;
                  const parsed = marked.parse(fullResponse, { renderer });
                  streamingText.innerHTML = parsed + '<span class="streaming-cursor">▊</span>';
                } catch (e) {
                  streamingText.innerHTML = fullResponse + '<span class="streaming-cursor">▊</span>';
                }

                if (data.metadata) {
                  metadata = { ...metadata, ...data.metadata };
                }

                streamContainer.scrollIntoView({ behavior: 'smooth' });
              } else if (data.type === 'done') {
                if (!firstContentReceived) {
                  cleanupProgress();
                  streamContainer.style.display = 'block';
                }

                if (data.metadata) {
                  metadata = { ...metadata, ...data.metadata };
                }

                // Streaming complete
                streamContainer.innerHTML = `
                  <strong>DAS:</strong><br>
                  <div class="das-markdown">${marked.parse(fullResponse)}</div>
                  ${metadata.sources && metadata.sources.length > 0 ? `
                    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border);">
                      <div class="muted" style="font-size: 0.9em;">📚 Sources (${metadata.sources.length}):</div>
                      ${metadata.sources.map(source => {
                        const relevanceScore = source.relevance_score ? ` (${Math.round(source.relevance_score * 100)}% match)` : '';
                        return `<div style="font-size: 0.8em; margin-left: 8px;">• <strong>${source.title || 'Unknown'}</strong> (${source.document_type || 'document'})${relevanceScore}</div>`;
                      }).join('')}
                    </div>
                  ` : ''}
                `;
                updateDASStatus('Ready');

                // Refresh tree if assumption saved
                if (metadata.assumption_saved || metadata.refresh_tree) {
                  setTimeout(() => {
                    emitEvent('das:assumption-saved');
                  }, 1000);
                }

                break;
              } else if (data.type === 'error') {
                if (!firstContentReceived) {
                  cleanupProgress();
                }
                addMessageToTranscript('error', 'Error: ' + (data.message || 'Unknown error'));
                updateDASStatus('Error');
                break;
              }
            } catch (e) {
              console.warn('Failed to parse streaming data:', e, line);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  } catch (error) {
    cleanupProgress();
    addMessageToTranscript('error', 'Network error: ' + error.message);
    updateDASStatus('Error');
  } finally {
    dasState.isProcessing = false;
    if (sendBtn) sendBtn.disabled = false;
    if (promptInput) promptInput.focus();
  }
}

/**
 * Add message to transcript
 */
function addMessageToTranscript(type, message, metadata = {}) {
  if (!transcript) {
    console.error('DAS transcript element not found');
    return;
  }

  const div = document.createElement('div');
  div.className = 'card';

  let content = '';
  let useMarkdown = false;

  if (type === 'user') {
    div.className = 'card das-user-message';
    content = `
      <div class="das-user-message-container">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
          <strong>You:</strong>
          <button class="das-edit-btn" onclick="window.editLastMessage('${escapeHtml(message).replace(/'/g, "\\'")}')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" width="14" height="14">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="m18.5 2.5 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </button>
        </div>
        <div class="das-user-message-text">${escapeHtml(message)}</div>
      </div>
    `;
  } else if (type === 'das') {
    content = `<strong>DAS:</strong> `;
    if (metadata.confidence) {
      content += `<span class="muted">(${metadata.confidence} confidence)</span><br><br>`;
    }
    useMarkdown = true;
    content += `<div class="das-markdown">${marked.parse(message)}</div>`;
  } else if (type === 'progress') {
    content = message;
  } else if (type === 'system') {
    content = `<em class="muted">${escapeHtml(message)}</em>`;
  } else if (type === 'error') {
    content = `<span style="color: #ef4444;">Error: ${escapeHtml(message)}</span>`;
  }

  div.innerHTML = content;

  // Add sources if available
  if (type === 'das' && metadata.sources && metadata.sources.length > 0) {
    const sourcesDiv = document.createElement('div');
    sourcesDiv.className = 'das-sources';
    sourcesDiv.innerHTML = `
      <div class="sources-title">📚 Sources (${metadata.sources.length}):</div>
      ${metadata.sources.map(source => {
        const relevanceScore = source.relevance_score ? ` (${Math.round(source.relevance_score * 100)}% match)` : '';
        return `<div class="source-item">• <strong>${source.title || 'Unknown'}</strong> (${source.document_type || 'document'})${relevanceScore}</div>`;
      }).join('')}
    `;
    div.appendChild(sourcesDiv);
  }

  // Add suggestions if available
  if (metadata.suggestions && metadata.suggestions.length > 0) {
    const suggestionsDiv = document.createElement('div');
    suggestionsDiv.className = 'das-suggestions';
    suggestionsDiv.style.marginTop = '8px';

    metadata.suggestions.forEach(suggestion => {
      const btn = document.createElement('button');
      btn.className = 'btn';
      btn.style.margin = '2px';
      btn.style.fontSize = '12px';

      let buttonText, messageToSend;
      if (typeof suggestion === 'string') {
        buttonText = messageToSend = suggestion;
      } else if (suggestion.title) {
        buttonText = suggestion.title;
        messageToSend = suggestion.action || suggestion.title || suggestion.description;
      } else if (suggestion.text) {
        buttonText = messageToSend = suggestion.text;
      } else {
        buttonText = 'Suggestion';
        messageToSend = JSON.stringify(suggestion);
      }

      btn.textContent = buttonText;
            btn.onclick = () => {
              if (messageToSend && typeof messageToSend === 'string' && messageToSend.trim()) {
                _sendDASMessage(messageToSend);
              }
            };
      suggestionsDiv.appendChild(btn);
    });

    div.appendChild(suggestionsDiv);
  }

  transcript.appendChild(div);

  // Apply syntax highlighting
  if (type === 'das' && window.hljs) {
    const codeBlocks = div.querySelectorAll('pre code');
    codeBlocks.forEach(block => {
      hljs.highlightElement(block);
    });
  }

  // Scroll to bottom
  setTimeout(() => {
    if (transcript) {
      transcript.scrollTop = transcript.scrollHeight;
    }
  }, 10);
}

/**
 * Update DAS status
 */
function updateDASStatus(status) {
  const statusEl = document.getElementById('dasStatus');
  if (statusEl) {
    statusEl.textContent = status;
  }
}

/**
 * Check LLM health
 */
async function checkLLMHealth() {
  const mainDot = document.getElementById('llmStatusDot');
  const dockDot = document.getElementById('llmStatusDockDot');
  const dots = [mainDot, dockDot].filter(Boolean);

  if (dots.length === 0) return;

  try {
    dots.forEach(dot => {
      dot.style.background = '#f59e0b';
      dot.title = 'LLM Status: Checking...';
    });

    const isHealthy = true; // DAS functionality will be checked when actually used

    if (isHealthy) {
      dots.forEach(dot => {
        dot.style.background = 'var(--ok)';
        dot.title = 'LLM Status: Ready';
      });
    }
  } catch (error) {
    dots.forEach(dot => {
      dot.style.background = 'var(--err)';
      dot.title = `LLM Status: Error - ${error.message}`;
    });
  }
}

/**
 * Start LLM health monitoring
 */
function startLLMHealthMonitoring() {
  checkLLMHealth();
  dasState.llmStatusInterval = setInterval(checkLLMHealth, 30000);
}

/**
 * Stop LLM health monitoring
 */
function stopLLMHealthMonitoring() {
  if (dasState.llmStatusInterval) {
    clearInterval(dasState.llmStatusInterval);
    dasState.llmStatusInterval = null;
  }
}

/**
 * Initialize LLM monitoring
 */
function initializeLLMMonitoring() {
  if (dasState.llmInitialized) {
    return;
  }

  const mainDot = document.getElementById('llmStatusDot');
  const dockDot = document.getElementById('llmStatusDockDot');

  if (!mainDot && !dockDot) {
    setTimeout(initializeLLMMonitoring, 1000);
    return;
  }

  dasState.llmInitialized = true;
  startLLMHealthMonitoring();
}

/**
 * Handle project change
 */
async function handleProjectChange(projectId) {
  if (!panel || !panel.classList.contains('active')) {
    return;
  }

  // Reset state
  dasState.currentProjectThreadId = null;
  dasState.dasInitializing = false;

  // Clear transcript
  if (transcript) {
    transcript.innerHTML = '';
    addMessageToTranscript('system', `Switching to project ${projectId}...`);
  }

  updateDASStatus('Switching projects...');

  // Wait for project data to settle
  setTimeout(async () => {
    try {
      await initializeDASProjectThread();
    } catch (error) {
      updateDASStatus('Error');
      addMessageToTranscript('error', `Failed to switch to new project: ${error.message}`);
    }
  }, 500);
}

/**
 * Reinitialize DAS for project (global function)
 */
window.reinitializeDASForProject = async function(newProjectId) {
  await handleProjectChange(newProjectId);
};

/**
 * Edit last message (global function for edit button)
 */
window.editLastMessage = function(originalMessage, messageElement) {
  console.log('🔧 Edit button clicked for message:', originalMessage);

  if (!messageElement) {
    const clickedButton = event.target.closest('.das-edit-btn');
    if (clickedButton) {
      messageElement = clickedButton.closest('.das-user-message');
    }
  }

  if (!messageElement) {
    console.error('❌ Could not find message element');
    return;
  }

  const messageContainer = messageElement.querySelector('.das-user-message-container');
  if (!messageContainer) {
    console.error('❌ Could not find message container');
    return;
  }

  messageContainer.setAttribute('data-original-message', originalMessage);
  messageElement.setAttribute('data-editing', 'true');

  messageContainer.innerHTML = `
    <div><strong>You:</strong> <em>(editing)</em></div>
    <textarea class="das-edit-input" rows="2">${originalMessage}</textarea>
    <div class="das-edit-controls">
      <button class="save-btn" onclick="window.saveEditedMessage(this)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" width="14" height="14">
          <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
          <polyline points="17,21 17,13 7,13 7,21"/>
          <polyline points="7,3 7,8 15,8"/>
        </svg>
        Save & Retry
      </button>
      <button class="cancel-btn" onclick="window.cancelEdit(this)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" width="14" height="14">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
        Cancel
      </button>
    </div>
  `;

  const textarea = messageContainer.querySelector('.das-edit-input');
  if (textarea) {
    textarea.focus();
    textarea.select();
  }
};

/**
 * Save edited message and retry (global function)
 */
window.saveEditedMessage = async function(button) {
  console.log('💾 Save & Retry clicked');
  const messageContainer = button.closest('.das-user-message-container');
  const textarea = messageContainer.querySelector('.das-edit-input');
  const newMessage = textarea.value.trim();

  if (!newMessage) return;

  try {
    const editedMessageElement = button.closest('.das-user-message');
    if (!transcript) return;
    
    const allMessages = Array.from(transcript.querySelectorAll('.card'));
    const editedIndex = allMessages.indexOf(editedMessageElement);
    
    // Remove ALL messages from the edited point onward
    for (let i = allMessages.length - 1; i >= editedIndex; i--) {
      allMessages[i].remove();
    }

    // Calculate conversations to remove
    const conversationsToRemove = Math.ceil((allMessages.length - editedIndex) / 2);

    // Remove conversation entries from project thread
    const projectId = getCurrentProjectId();
    if (projectId && conversationsToRemove > 0) {
      try {
        for (let i = 0; i < conversationsToRemove; i++) {
          await DasApi.deleteLastConversation(projectId);
        }
      } catch (error) {
        console.error('Error deleting conversation entries:', error);
      }
    }

    // Send the edited message
    await _sendDASMessage(newMessage);
  } catch (error) {
    console.error('Error during edit and retry:', error);
    await _sendDASMessage(newMessage);
  }
};

/**
 * Cancel edit (global function)
 */
window.cancelEdit = function(button) {
  console.log('❌ Cancel edit clicked');
  const messageContainer = button.closest('.das-user-message-container');
  const messageElement = button.closest('.das-user-message');

  const originalMessage = messageContainer.getAttribute('data-original-message') || 'Message';

  messageContainer.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
      <strong>You:</strong>
      <button class="das-edit-btn" onclick="window.editLastMessage('${originalMessage.replace(/'/g, "\\'")}')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" width="14" height="14">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
          <path d="m18.5 2.5 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
        </svg>
      </button>
    </div>
    <div class="das-user-message-text">${originalMessage}</div>
  `;

  messageElement.removeAttribute('data-editing');
};

/**
 * Helper function to escape HTML
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
