/**
 * API Client Module
 * 
 * Centralized API communication for ODRAS frontend.
 * Handles authentication, request/response interceptors, and error handling.
 */

class APIClient {
  constructor(baseURL = '') {
    this.baseURL = baseURL;
    this.token = null;
    this.loadToken();
  }

  /**
   * Load authentication token from localStorage
   */
  loadToken() {
    this.token = localStorage.getItem('odras_token');
  }

  /**
   * Save authentication token to localStorage
   */
  saveToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem('odras_token', token);
    } else {
      localStorage.removeItem('odras_token');
    }
  }

  /**
   * Get default headers for API requests
   */
  getHeaders(customHeaders = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...customHeaders
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    return headers;
  }

  /**
   * Handle API response
   */
  async handleResponse(response) {
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      
      // Handle authentication errors
      if (response.status === 401) {
        this.saveToken(null);
        window.dispatchEvent(new CustomEvent('auth:unauthorized'));
        throw new Error('Unauthorized');
      }

      throw new Error(error.detail || error.message || `HTTP ${response.status}`);
    }

    // Handle empty responses
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }
    
    return await response.text();
  }

  /**
   * Make GET request
   */
  async get(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const response = await fetch(url, {
      method: 'GET',
      headers: this.getHeaders(options.headers),
      ...options
    });

    return this.handleResponse(response);
  }

  /**
   * Make POST request
   */
  async post(endpoint, data = null, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const body = data ? JSON.stringify(data) : null;

    const response = await fetch(url, {
      method: 'POST',
      headers: this.getHeaders(options.headers),
      body,
      ...options
    });

    return this.handleResponse(response);
  }

  /**
   * Make PUT request
   */
  async put(endpoint, data = null, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const body = data ? JSON.stringify(data) : null;

    const response = await fetch(url, {
      method: 'PUT',
      headers: this.getHeaders(options.headers),
      body,
      ...options
    });

    return this.handleResponse(response);
  }

  /**
   * Make DELETE request
   */
  async delete(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;

    const response = await fetch(url, {
      method: 'DELETE',
      headers: this.getHeaders(options.headers),
      ...options
    });

    return this.handleResponse(response);
  }

  /**
   * Upload file
   */
  async upload(endpoint, formData, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const headers = { ...this.getHeaders() };
    delete headers['Content-Type']; // Let browser set Content-Type for FormData

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
      ...options
    });

    return this.handleResponse(response);
  }

  /**
   * Login and save token
   */
  async login(username, password) {
    const response = await this.post('/api/auth/login', { username, password });
    if (response.token) {
      this.saveToken(response.token);
    }
    return response;
  }

  /**
   * Logout and clear token
   */
  async logout() {
    try {
      await this.post('/api/auth/logout');
    } finally {
      this.saveToken(null);
    }
  }

  /**
   * Get current user
   */
  async getCurrentUser() {
    return await this.get('/api/auth/me');
  }
}

// Create singleton instance
const apiClient = new APIClient();

// Export for use in other modules
export { APIClient, apiClient };

// Make available globally for backwards compatibility
if (typeof window !== 'undefined') {
  window.ApiClient = apiClient;
}
