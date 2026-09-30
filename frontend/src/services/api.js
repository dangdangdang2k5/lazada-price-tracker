import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 20000,
});

export const productService = {
  // Preview product from URL
  preview: async (url) => {
    const response = await api.post('/products/preview', { url });
    return response.data;
  },

  // Create tracked product
  create: async (payload) => {
    const response = await api.post('/products', payload);
    return response.data;
  },

  // List products with optional search, sort, filter
  list: async (params = {}) => {
    const response = await api.get('/products', { params });
    return response.data;
  },

  // Get single product
  getById: async (id) => {
    const response = await api.get(`/products/${id}`);
    return response.data;
  },

  // Delete product
  delete: async (id) => {
    await api.delete(`/products/${id}`);
  },

  // Instant refresh product price
  refresh: async (id) => {
    const response = await api.post(`/products/${id}/refresh`);
    return response.data;
  },

  // Get price history
  getHistory: async (id, range = 'all') => {
    const response = await api.get(`/products/${id}/history`, { params: { range } });
    return response.data;
  },
};

export const alertService = {
  // Create alert for product
  create: async (productId, payload) => {
    const response = await api.post(`/products/${productId}/alerts`, payload);
    return response.data;
  },

  // Get alerts for product
  getByProduct: async (productId) => {
    const response = await api.get(`/products/${productId}/alerts`);
    return response.data;
  },

  // Update alert
  update: async (alertId, payload) => {
    const response = await api.put(`/alerts/${alertId}`, payload);
    return response.data;
  },

  // Delete alert
  delete: async (alertId) => {
    await api.delete(`/alerts/${alertId}`);
  },

  // Enable alert
  enable: async (alertId) => {
    const response = await api.post(`/alerts/${alertId}/enable`);
    return response.data;
  },

  // Disable alert
  disable: async (alertId) => {
    const response = await api.post(`/alerts/${alertId}/disable`);
    return response.data;
  },
};

export const telegramService = {
  // Test telegram connection
  testConnection: async (payload = {}) => {
    const response = await api.post('/telegram/test', payload);
    return response.data;
  },

  // Get telegram configuration status
  getStatus: async () => {
    const response = await api.get('/telegram/status');
    return response.data;
  },
};

export const statsService = {
  // Get dashboard metrics
  getStats: async () => {
    const response = await api.get('/stats');
    return response.data;
  },
};

export const lazadaSessionService = {
  status: async () => (await api.get('/lazada/session')).data,
  save: async (cookies) => (await api.post('/lazada/session', { cookies })).data,
  clear: async () => (await api.delete('/lazada/session')).data,
};

export default api;
