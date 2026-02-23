import axios from 'axios'

// URL base da API - configuravel via .env (VITE_API_URL)
// Em producao: deixe vazio para usar o mesmo dominio do frontend
// Em desenvolvimento: coloque a URL do backend (ngrok, localhost, etc)
const API_BASE_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    'ngrok-skip-browser-warning': 'true'  // Pular aviso do ngrok (conta gratuita)
  }
})

// Exportar base URL para uso em outros lugares (ex: webhook)
// Se vazio, usa o dominio atual do frontend
export const getApiBaseUrl = () => API_BASE_URL || window.location.origin

// Interceptor para tratamento de erros
api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export default api

// ===== Clientes =====
export const clientsApi = {
  list: () => api.get('/clients'),
  get: (slug) => api.get(`/clients/${slug}`),
  create: (data) => api.post('/clients', data),
  update: (slug, data) => api.put(`/clients/${slug}`, data),
  delete: (slug) => api.delete(`/clients/${slug}`),
  setSchema: (slug, schemaId) => api.put(`/clients/${slug}/schema?schema_id=${schemaId}`)
}

// ===== Schemas =====
export const schemasApi = {
  list: (activeOnly = false) => api.get('/schemas', { params: { active_only: activeOnly } }),
  get: (id) => api.get(`/schemas/${id}`),
  create: (data) => api.post('/schemas', data),
  update: (id, data) => api.put(`/schemas/${id}`, data),
  delete: (id) => api.delete(`/schemas/${id}`),
  setDefault: (id) => api.post(`/schemas/${id}/set-default`),
  seed: () => api.post('/schemas/seed'),
  assignToClient: (slug, schemaId) => api.put(`/clients/${slug}/schema`, null, {
    params: { schema_id: schemaId }
  })
}

// ===== AI Config =====
export const aiApi = {
  getConfig: (slug) => api.get(`/${slug}/ai-config`),
  saveConfig: (slug, data) => api.post(`/${slug}/ai-config`, data),
  testAI: (slug, message) => api.post(`/${slug}/ai-test`, { message }),
  setupWebhook: (slug, webhookUrl) => api.post(`/${slug}/ai-setup-webhook`, { webhookUrl }),

  // Knowledge Base
  listKnowledge: (slug) => api.get(`/${slug}/ai-knowledge`),
  uploadKnowledge: (slug, file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/${slug}/ai-knowledge`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  deleteKnowledge: (slug, fileId) => api.delete(`/${slug}/ai-knowledge/${fileId}`)
}

// ===== Produtos =====
export const productsApi = {
  list: (slug, params = {}) => api.get(`/${slug}/products`, { params }),
  get: (slug, id) => api.get(`/${slug}/products/${id}`),
  create: (slug, data) => api.post(`/${slug}/products`, data),
  update: (slug, id, data) => api.put(`/${slug}/products/${id}`, data),
  delete: (slug, id) => api.delete(`/${slug}/products/${id}`),

  // Schema do cliente (para form dinamico)
  getSchema: (slug) => api.get(`/${slug}/products/schema`),

  // Images
  uploadImage: (slug, productId, file, isMain = false) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('is_main', isMain)
    return api.post(`/${slug}/products/${productId}/images`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  deleteImage: (slug, productId, imageIndex) =>
    api.delete(`/${slug}/products/${productId}/images/${imageIndex}`),

  // Embeddings
  generateEmbedding: (slug, productId) =>
    api.post(`/${slug}/products/${productId}/generate-embedding`),
  generateAllEmbeddings: (slug) =>
    api.post(`/${slug}/products/generate-all-embeddings`),

  // Search
  search: (slug, query, topK = 5) =>
    api.post(`/${slug}/products/search`, null, { params: { query, top_k: topK } })
}

// ===== Chatwoot Proxy =====
export const chatwootApi = {
  getInboxes: (slug) => api.get(`/${slug}/inboxes`)
}

// ===== Batch Testing (Testes em Lote de IA) =====
export const batchTestingApi = {
  // Casos de Teste
  listTestCases: (slug, category = null) => {
    const params = category ? { category } : {}
    return api.get(`/${slug}/batch-tests/cases`, { params })
  },
  getTestCase: (slug, id) => api.get(`/${slug}/batch-tests/cases/${id}`),
  createTestCase: (slug, data) => api.post(`/${slug}/batch-tests/cases`, data),
  updateTestCase: (slug, id, data) => api.put(`/${slug}/batch-tests/cases/${id}`, data),
  deleteTestCase: (slug, id) => api.delete(`/${slug}/batch-tests/cases/${id}`),
  seedTemplates: (slug) => api.post(`/${slug}/batch-tests/cases/seed`),
  generateTests: (slug, numTests = 10, saveTests = true) => api.post(`/${slug}/batch-tests/cases/generate`, {
    num_tests: numTests,
    save_tests: saveTests
  }, {
    timeout: 120000  // 2 minutos para gerar testes
  }),

  // Execucao de Testes
  runBatch: (slug, testCaseIds, concurrentTests = 10) => api.post(`/${slug}/batch-tests/run`, {
    test_case_ids: testCaseIds,
    concurrent_tests: concurrentTests
  }),
  getRunStatus: (slug, runId) => api.get(`/${slug}/batch-tests/runs/${runId}`),
  listRuns: (slug, limit = 10) => api.get(`/${slug}/batch-tests/runs`, { params: { limit } }),

  // Simulacao de Conversas (timeout maior pois cada turno faz 2 chamadas de API)
  runConversation: (slug, numConversations = 5, turnsPerConversation = 5, clientProfile = null) =>
    api.post(`/${slug}/batch-tests/conversation`, {
      num_conversations: numConversations,
      turns_per_conversation: turnsPerConversation,
      client_profile: clientProfile
    }, {
      timeout: 300000  // 5 minutos (cada conversa pode levar ~30s)
    }),
  getClientProfiles: (slug) => api.get(`/${slug}/batch-tests/client-profiles`)
}
