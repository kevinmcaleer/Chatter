/**
 * Account Management API Client
 *
 * Reusable JavaScript module for interacting with the account management API.
 * Can be embedded in Jekyll pages or any static site.
 *
 * Usage:
 *   <script src="/assets/js/account-api.js"></script>
 *   <script>
 *     AccountAPI.login('username', 'password')
 *       .then(data => console.log('Logged in!', data))
 *       .catch(error => console.error('Login failed', error));
 *   </script>
 */

const AccountAPI = (function() {
  // Configuration
  const config = {
    baseURL: window.location.origin, // Use same origin, or set to API URL
    endpoints: {
      login: '/auth/login',
      register: '/accounts/register',
      getAccount: '/accounts/me',
      updateAccount: '/accounts/me',
      resetPassword: '/accounts/reset-password',
      deleteAccount: '/accounts/me'
    }
  };

  // Token management
  const TokenManager = {
    get: function() {
      return localStorage.getItem('access_token');
    },
    set: function(token) {
      localStorage.setItem('access_token', token);
    },
    remove: function() {
      localStorage.removeItem('access_token');
    },
    isLoggedIn: function() {
      return !!this.get();
    }
  };

  // HTTP request helper
  async function request(url, options = {}) {
    const token = TokenManager.get();
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(config.baseURL + url, {
      ...options,
      headers
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Public API
  return {
    /**
     * Check if user is currently logged in
     */
    isLoggedIn: function() {
      return TokenManager.isLoggedIn();
    },

    /**
     * Login with username and password
     * @param {string} username
     * @param {string} password
     * @returns {Promise<Object>} User data with access token
     */
    login: async function(username, password) {
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);

      const response = await fetch(config.baseURL + config.endpoints.login, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formData
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Login failed' }));
        throw new Error(error.detail || 'Login failed');
      }

      const data = await response.json();
      TokenManager.set(data.access_token);
      return data;
    },

    /**
     * Logout current user
     */
    logout: function() {
      TokenManager.remove();
    },

    /**
     * Register a new user account
     * @param {Object} userData - User registration data
     * @param {string} userData.username
     * @param {string} userData.firstname
     * @param {string} userData.lastname
     * @param {string} userData.email
     * @param {string} userData.password
     * @param {string} [userData.date_of_birth] - Optional date of birth
     * @returns {Promise<Object>} Created user data
     */
    register: async function(userData) {
      return request(config.endpoints.register, {
        method: 'POST',
        body: JSON.stringify(userData)
      });
    },

    /**
     * Get current user's account information
     * @returns {Promise<Object>} User account data
     */
    getAccount: async function() {
      return request(config.endpoints.getAccount);
    },

    /**
     * Update current user's account information
     * @param {Object} updates - Fields to update
     * @param {string} [updates.firstname]
     * @param {string} [updates.lastname]
     * @param {string} [updates.email]
     * @param {string} [updates.date_of_birth]
     * @returns {Promise<Object>} Updated user data
     */
    updateAccount: async function(updates) {
      return request(config.endpoints.updateAccount, {
        method: 'PATCH',
        body: JSON.stringify(updates)
      });
    },

    /**
     * Reset user's password
     * @param {string} oldPassword
     * @param {string} newPassword
     * @returns {Promise<Object>} Success message
     */
    resetPassword: async function(oldPassword, newPassword) {
      return request(config.endpoints.resetPassword, {
        method: 'POST',
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPassword
        })
      });
    },

    /**
     * Delete current user's account
     * @returns {Promise<Object>} Success message
     */
    deleteAccount: async function() {
      const result = await request(config.endpoints.deleteAccount, {
        method: 'DELETE'
      });
      TokenManager.remove();
      return result;
    },

    /**
     * Get authentication token
     * @returns {string|null} Current access token
     */
    getToken: function() {
      return TokenManager.get();
    },

    /**
     * Set custom API base URL
     * @param {string} url - API base URL
     */
    setBaseURL: function(url) {
      config.baseURL = url;
    }
  };
})();

// Export for use in modules (optional, for modern JS environments)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = AccountAPI;
}
