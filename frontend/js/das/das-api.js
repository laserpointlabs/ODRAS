/**
 * DAS API Client Module
 * 
 * Handles all API communication with the DAS backend.
 * Provides functions for chat, streaming, thread management, and history.
 */

import { apiClient } from '../core/api-client.js';
import { getCurrentProjectId } from '../core/utils.js';

// Use apiClient as ApiClient
const ApiClient = apiClient;

/**
 * Get or create project thread
 */
export async function getProjectThread(projectId = null) {
  const pid = projectId || getCurrentProjectId();
  if (!pid) {
    throw new Error('No project ID available');
  }

  const response = await ApiClient.get(`/api/das/project/${pid}/thread`);
  return response;
}

/**
 * Get conversation history for a project
 */
export async function getProjectHistory(projectId = null) {
  const pid = projectId || getCurrentProjectId();
  if (!pid) {
    throw new Error('No project ID available');
  }

  const response = await ApiClient.get(`/api/das/project/${pid}/history`);
  return response;
}

/**
 * Send a message to DAS with streaming support
 * Returns a ReadableStream for streaming responses
 */
export async function sendDASMessageStream(message, projectThreadId, context = {}) {
  const projectId = getCurrentProjectId();
  
  if (!projectId) {
    throw new Error('No project ID available');
  }

  const response = await fetch('/api/das/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...ApiClient.getHeaders()
    },
    body: JSON.stringify({
      message: message,
      project_thread_id: projectThreadId,
      project_id: projectId,
      ...context
    })
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || 'Failed to send message');
  }

  return response.body;
}

/**
 * Delete last conversation from project thread
 */
export async function deleteLastConversation(projectId = null) {
  const pid = projectId || getCurrentProjectId();
  if (!pid) {
    throw new Error('No project ID available');
  }

  const response = await ApiClient.delete(`/api/das/project/${pid}/conversation/last`);
  return response;
}

/**
 * Get assumptions for a project
 */
export async function getProjectAssumptions(projectId = null) {
  const pid = projectId || getCurrentProjectId();
  if (!pid) {
    throw new Error('No project ID available');
  }

  const response = await ApiClient.get(`/api/das/project/${pid}/assumptions`);
  return response;
}

/**
 * Load RAG configuration for DAS
 * This is a helper function that may be called from other modules
 */
export async function loadRagConfigForDAS() {
  try {
    const config = await ApiClient.get('/api/admin/rag-config');
    return config;
  } catch (error) {
    console.warn('Failed to load RAG config for DAS:', error);
    return null;
  }
}
