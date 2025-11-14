/**
 * ODRAS API Adapter
 *
 * Adapter layer that wraps ODRAS API client to provide a clean interface
 * for the ontology workbench. This allows the workbench to be independent
 * of ODRAS-specific API implementation details.
 */

/**
 * Creates an API adapter that wraps the ODRAS apiClient
 * @param {Object} apiClient - The ODRAS API client instance
 * @returns {ApiAdapter} Adapter implementing the API interface
 */
export function createOdrasApiAdapter(apiClient) {
  return {
    /**
     * GET request
     * @param {string} uri - Request URI
     * @param {Object} options - Request options
     * @returns {Promise<Response>}
     */
    async get(uri, options = {}) {
      const response = await apiClient.get(uri);
      return {
        ok: response.ok,
        status: response.status,
        data: response.data,
        json: async () => response.data,
        text: async () => JSON.stringify(response.data)
      };
    },

    /**
     * POST request
     * @param {string} uri - Request URI
     * @param {Object} data - Request body
     * @param {Object} options - Request options
     * @returns {Promise<Response>}
     */
    async post(uri, data, options = {}) {
      const response = await apiClient.post(uri, data);
      return {
        ok: response.ok,
        status: response.status,
        data: response.data,
        json: async () => response.data,
        text: async () => JSON.stringify(response.data)
      };
    },

    /**
     * PUT request
     * @param {string} uri - Request URI
     * @param {Object} data - Request body
     * @param {Object} options - Request options
     * @returns {Promise<Response>}
     */
    async put(uri, data, options = {}) {
      const response = await apiClient.put(uri, data);
      return {
        ok: response.ok,
        status: response.status,
        data: response.data,
        json: async () => response.data,
        text: async () => JSON.stringify(response.data)
      };
    },

    /**
     * DELETE request
     * @param {string} uri - Request URI
     * @param {Object} options - Request options
     * @returns {Promise<Response>}
     */
    async delete(uri, options = {}) {
      const response = await apiClient.delete(uri);
      return {
        ok: response.ok,
        status: response.status,
        data: response.data,
        json: async () => response.data,
        text: async () => JSON.stringify(response.data)
      };
    }
  };
}
