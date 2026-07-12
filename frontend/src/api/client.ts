import axios from 'axios';

const API_BASE = '/dragons/api';

const client = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => {
    const method = (response.config.method || '').toLowerCase();
    const url = response.config.url || '';
    const isMutation = ['post', 'put', 'patch', 'delete'].includes(method);
    const isSilent = url.includes('/upload-image') || url.includes('/auth');
    if (isMutation && !isSilent) {
      window.dispatchEvent(new CustomEvent('admin:saved'));
    }
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/dragons/admin/login';
    }
    return Promise.reject(error);
  },
);

export default client;
