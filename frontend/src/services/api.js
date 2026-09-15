// Use dynamic API URL from environment variable in production, defaulting to localhost for dev
const API_BASE = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

async function request(url, options = {}) {
  const targetUrl = `${API_BASE}${url}`;
  
  let res;
  try {
    res = await fetch(targetUrl, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  } catch (err) {
    console.error(`Network error requesting ${targetUrl}:`, err);
    throw new Error(`Unable to reach backend server at ${API_BASE}. Please ensure the FastAPI backend is running.`);
  }

  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const data = await res.json();
      errorDetail = data.detail || data.message || errorDetail;
    } catch (_) {
      try {
        const text = await res.text();
        if (text) errorDetail = text;
      } catch (_) {}
    }
    throw new Error(errorDetail);
  }

  if (res.status === 204) {
    return null;
  }

  return res.json();
}

export const api = {
  getHealth: () => request('/health'),
  getRepositories: () => request('/repositories'),
  getRepository: (id) => request(`/repositories/${id}`),
  connectRepository: (data) => request('/repositories', { method: 'POST', body: JSON.stringify(data) }),
  updateRepository: (id, data) => request(`/repositories/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteRepository: (id) => request(`/repositories/${id}`, { method: 'DELETE' }),
  syncRepository: (id) => request(`/repositories/${id}/sync`, { method: 'POST' }),
  analyzeRepository: (id, commitSha = null, force = false) => {
    let url = `/repositories/${id}/analyze?force=${force}`;
    if (commitSha) url += `&commit_sha=${commitSha}`;
    return request(url, { method: 'POST' });
  },
  getChanges: (repoId) => request(`/repositories/${repoId}/changes`),
  getChangeDetail: (repoId, changeId) => request(`/repositories/${repoId}/changes/${changeId}`),
  getDocumentation: (repoId) => request(`/repositories/${repoId}/documentation`),
  getSwaggerUrl: (repoId) => `${API_BASE}/repositories/${repoId}/docs`,
  getOpenApiJsonUrl: (repoId) => `${API_BASE}/repositories/${repoId}/openapi.json`,
};
