const API_BASE = '/api';

class ApiService {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('token');
  }

  setToken(token: string | null) {
    this.token = token;
    if (token) localStorage.setItem('token', token);
    else localStorage.removeItem('token');
  }

  getToken() { return this.token; }

  private async request(path: string, options: RequestInit = {}) {
    const headers: Record<string, string> = { 'Content-Type': 'application/json', ...options.headers as Record<string, string> };
    if (this.token) headers['Authorization'] = `Bearer ${this.token}`;

    // Don't set Content-Type for FormData (let browser set it)
    if (options.body instanceof FormData) delete headers['Content-Type'];

    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

    if (res.status === 204) return null;
    if (res.status === 401) { this.setToken(null); throw new Error('请先登录'); }

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '请求失败');
    return data;
  }

  // Auth
  login(username: string, password: string) { return this.request('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }); }
  register(name: string, username: string, password: string) { return this.request('/auth/register', { method: 'POST', body: JSON.stringify({ name, username, password }) }); }
  guest() { return this.request('/auth/guest', { method: 'POST' }); }
  me() { return this.request('/auth/me'); }

  // Users (admin)
  listUsers() { return this.request('/users'); }
  updateUser(id: number, data: { role?: string; is_active?: boolean }) { return this.request(`/users/${id}`, { method: 'PATCH', body: JSON.stringify(data) }); }
  deleteUser(id: number) { return this.request(`/users/${id}`, { method: 'DELETE' }); }

  // Documents (admin)
  listDocuments() { return this.request('/documents'); }
  uploadDocument(title: string, file: File) {
    const form = new FormData();
    form.append('title', title);
    form.append('file', file);
    return this.request('/documents', { method: 'POST', body: form });
  }
  deleteDocument(id: number) { return this.request(`/documents/${id}`, { method: 'DELETE' }); }
  reprocessDocument(id: number) { return this.request(`/documents/${id}/reprocess`, { method: 'POST' }); }

  // Chat
  async* streamChat(question: string, conversationId?: number) {
    const headers: Record<string, string> = {};
    if (this.token) headers['Authorization'] = `Bearer ${this.token}`;

    const res = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, conversation_id: conversationId }),
    });

    if (!res.ok) throw new Error('聊天请求失败');

    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const events = buffer.split('\n\n');
      buffer = events.pop() || '';

      for (const event of events) {
        const lines = event.split('\n');
        const eventType = lines.find(l => l.startsWith('event: '))?.slice(7);
        const dataLine = lines.find(l => l.startsWith('data: '))?.slice(6);
        if (eventType && dataLine) yield { type: eventType, data: JSON.parse(dataLine) };
      }
    }
  }

  // Conversations
  listConversations() { return this.request('/conversations'); }
  getConversation(id: number) { return this.request(`/conversations/${id}`); }
  deleteConversation(id: number) { return this.request(`/conversations/${id}`, { method: 'DELETE' }); }

  // Roles (admin)
  listRoles() { return this.request('/roles'); }
  getRole(name: string) { return this.request(`/roles/${encodeURIComponent(name)}`); }
  createRole(name: string, description: string) { return this.request('/roles', { method: 'POST', body: JSON.stringify({ name, description }) }); }
  updateRole(name: string, description: string) { return this.request(`/roles/${encodeURIComponent(name)}`, { method: 'PATCH', body: JSON.stringify({ description }) }); }
  deleteRole(name: string) { return this.request(`/roles/${encodeURIComponent(name)}`, { method: 'DELETE' }); }

  // Cache (admin)
  listCache() { return this.request('/cache'); }
  deleteCacheEntry(id: number) { return this.request(`/cache/${id}`, { method: 'DELETE' }); }
  flushCache() { return this.request('/cache', { method: 'DELETE' }); }

  // Stats
  getStats() { return this.request('/stats'); }
}

export const api = new ApiService();
