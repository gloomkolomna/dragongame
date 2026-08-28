import axios from 'axios';

const API_BASE = window.location.origin + '/dragons/api';

const client = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
});

let vkSignParams: Record<string, string> = {};

export function setVkLaunchParams(params: Record<string, string>) {
  vkSignParams = Object.fromEntries(
    Object.entries(params).filter(([k]) => k.startsWith('vk_') || k === 'sign'),
  );
}

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  const url = config.url || '';
  if (url.startsWith('/collection/') || url.startsWith('/dragon/')) {
    config.params = { ...vkSignParams, ...(config.params || {}) };
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
    if (error.response?.status === 401 && window.location.pathname.startsWith('/dragons/admin')) {
      localStorage.removeItem('token');
      window.location.href = '/dragons/admin/login';
    }
    return Promise.reject(error);
  },
);

export default client;
