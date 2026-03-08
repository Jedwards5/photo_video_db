const BASE = ''

function getToken() {
  return localStorage.getItem('token')
}

async function request(path, options = {}) {
  const token = getToken()
  const res = await fetch(BASE + path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  if (res.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/login'
    return
  }
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export const api = {
  login: (password) =>
    request('/api/login', { method: 'POST', body: JSON.stringify({ password }) }),

  me: () => request('/api/me'),

  timeline: (page = 1) => request(`/api/timeline?page=${page}`),

  mediaDetail: (id) => request(`/api/media/${id}`),

  thumbnailUrl: (id) => `${BASE}/api/thumbnails/${id}?token=${getToken()}`,

  fileUrl: (id) => `${BASE}/api/files/${id}?token=${getToken()}`,

  people: () => request('/api/people'),

  personMedia: (id, page = 1) => request(`/api/people/${id}/media?page=${page}`),

  search: (q, mode = 'clip', top = 30) =>
    request(`/api/search?q=${encodeURIComponent(q)}&mode=${mode}&top=${top}`),
}
