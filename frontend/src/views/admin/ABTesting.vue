<template>
  <div class="ab-testing-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">A/B Testing</h1>
        <p class="page-subtitle">Teste diferentes versoes de prompts</p>
      </div>
      <div class="header-right">
        <select v-model="selectedClient" class="client-select" @change="loadTests">
          <option value="">Selecione um cliente</option>
          <option v-for="client in clients" :key="client.slug" :value="client.slug">
            {{ client.name }}
          </option>
        </select>
        <button class="btn-primary" @click="showCreateModal = true" :disabled="!selectedClient">
          <i class="mdi mdi-plus"></i>
          Novo Teste
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <i class="mdi mdi-loading mdi-spin"></i>
      <span>Carregando testes...</span>
    </div>

    <!-- Empty State -->
    <div v-else-if="!selectedClient" class="empty-state">
      <div class="empty-icon">
        <i class="mdi mdi-ab-testing"></i>
      </div>
      <h3>Selecione um cliente</h3>
      <p>Escolha um cliente para gerenciar testes A/B</p>
    </div>

    <!-- Tests List -->
    <div v-else class="tests-grid">
      <div v-if="tests.length === 0" class="empty-state">
        <div class="empty-icon">
          <i class="mdi mdi-flask-outline"></i>
        </div>
        <h3>Nenhum teste ativo</h3>
        <p>Crie seu primeiro teste A/B para otimizar conversoes</p>
      </div>

      <div v-for="test in tests" :key="test.id" class="test-card">
        <div class="test-header">
          <div class="test-info">
            <h3>{{ test.name }}</h3>
            <span class="test-status" :class="test.status">{{ test.status }}</span>
          </div>
          <div class="test-actions">
            <button
              v-if="test.status === 'running'"
              class="btn-icon"
              @click="pauseTest(test.id)"
              title="Pausar teste"
            >
              <i class="mdi mdi-pause"></i>
            </button>
            <button
              v-if="test.status === 'running'"
              class="btn-icon"
              @click="stopTest(test.id)"
              title="Encerrar teste"
            >
              <i class="mdi mdi-stop"></i>
            </button>
            <button
              v-if="test.status === 'draft' || test.status === 'paused'"
              class="btn-icon"
              @click="startTest(test.id)"
              title="Iniciar teste"
            >
              <i class="mdi mdi-play"></i>
            </button>
            <button class="btn-icon danger" @click="deleteTest(test.id)" title="Excluir">
              <i class="mdi mdi-delete-outline"></i>
            </button>
          </div>
        </div>

        <div class="test-body">
          <p class="test-description">{{ test.description || 'Sem descricao' }}</p>

          <div class="variants">
            <div
              v-for="variant in test.variants"
              :key="variant.id"
              class="variant-card"
              :class="{ winner: variant.is_winner }"
            >
              <div class="variant-header">
                <span class="variant-name">{{ variant.name }}</span>
                <span class="variant-traffic">{{ variant.traffic_percentage }}%</span>
              </div>
              <div class="variant-stats">
                <div class="stat">
                  <span class="stat-value">{{ variant.impressions || 0 }}</span>
                  <span class="stat-label">Impressoes</span>
                </div>
                <div class="stat">
                  <span class="stat-value">{{ variant.conversions || 0 }}</span>
                  <span class="stat-label">Conversoes</span>
                </div>
                <div class="stat">
                  <span class="stat-value">{{ formatPercent(variant.conversion_rate) }}</span>
                  <span class="stat-label">Taxa</span>
                </div>
              </div>
              <div v-if="variant.is_winner" class="winner-badge">
                <i class="mdi mdi-trophy"></i> Vencedor
              </div>
            </div>
          </div>

          <div class="test-meta">
            <span><i class="mdi mdi-calendar"></i> Criado em {{ formatDate(test.created_at) }}</span>
            <span v-if="test.statistical_significance">
              <i class="mdi mdi-chart-bell-curve"></i> {{ test.statistical_significance }}% significancia
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal">
        <div class="modal-header">
          <h2>Novo Teste A/B</h2>
          <button class="btn-close" @click="showCreateModal = false">
            <i class="mdi mdi-close"></i>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>Nome do Teste</label>
            <input v-model="newTest.name" type="text" placeholder="Ex: Teste de Saudacao" />
          </div>
          <div class="form-group">
            <label>Descricao</label>
            <textarea v-model="newTest.description" placeholder="Descreva o objetivo do teste"></textarea>
          </div>

          <div class="variants-section">
            <h4>Variantes</h4>
            <div class="variant-inputs">
              <div class="variant-input">
                <label>Variante A (Controle)</label>
                <textarea v-model="newTest.variant_a" placeholder="Prompt da variante A"></textarea>
                <div class="traffic-input">
                  <label>Trafego:</label>
                  <input v-model.number="newTest.traffic_a" type="number" min="0" max="100" />%
                </div>
              </div>
              <div class="variant-input">
                <label>Variante B</label>
                <textarea v-model="newTest.variant_b" placeholder="Prompt da variante B"></textarea>
                <div class="traffic-input">
                  <label>Trafego:</label>
                  <input v-model.number="newTest.traffic_b" type="number" min="0" max="100" />%
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showCreateModal = false">Cancelar</button>
          <button class="btn-primary" @click="createTest" :disabled="!canCreate">
            <i class="mdi mdi-plus"></i>
            Criar Teste
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api, { clientsApi } from '@/api/client'

const loading = ref(false)
const clients = ref([])
const selectedClient = ref('')
const tests = ref([])
const showCreateModal = ref(false)

const newTest = ref({
  name: '',
  description: '',
  variant_a: '',
  variant_b: '',
  traffic_a: 50,
  traffic_b: 50
})

const canCreate = computed(() => {
  return newTest.value.name &&
         newTest.value.variant_a &&
         newTest.value.variant_b &&
         newTest.value.traffic_a + newTest.value.traffic_b === 100
})

const loadClients = async () => {
  try {
    const response = await clientsApi.list()
    const data = response.data
    if (data && typeof data === 'object' && !Array.isArray(data)) {
      clients.value = Object.values(data).filter(c => c && c.slug && c.name)
    } else if (Array.isArray(data)) {
      clients.value = data.filter(c => c && c.slug && c.name)
    } else {
      clients.value = []
    }
  } catch (error) {
    console.error('Erro ao carregar clientes:', error)
    clients.value = []
  }
}

const loadTests = async () => {
  if (!selectedClient.value) return

  loading.value = true
  try {
    const response = await api.get(`/ab-testing/${selectedClient.value}/ab-tests`)
    tests.value = response.data.tests || []
  } catch (error) {
    console.error('Erro ao carregar testes:', error)
    tests.value = []
  } finally {
    loading.value = false
  }
}

const createTest = async () => {
  try {
    await api.post(`/ab-testing/${selectedClient.value}/ab-tests`, {
      name: newTest.value.name,
      description: newTest.value.description,
      variants: [
        { name: 'Variante A', prompt: newTest.value.variant_a, traffic_percentage: newTest.value.traffic_a },
        { name: 'Variante B', prompt: newTest.value.variant_b, traffic_percentage: newTest.value.traffic_b }
      ]
    })
    showCreateModal.value = false
    newTest.value = { name: '', description: '', variant_a: '', variant_b: '', traffic_a: 50, traffic_b: 50 }
    loadTests()
  } catch (error) {
    console.error('Erro ao criar teste:', error)
  }
}

const startTest = async (testId) => {
  try {
    await api.post(`/ab-testing/${selectedClient.value}/ab-tests/${testId}/start`)
    loadTests()
  } catch (error) {
    console.error('Erro ao iniciar teste:', error)
  }
}

const pauseTest = async (testId) => {
  try {
    await api.post(`/ab-testing/${selectedClient.value}/ab-tests/${testId}/pause`)
    loadTests()
  } catch (error) {
    console.error('Erro ao pausar teste:', error)
  }
}

const stopTest = async (testId) => {
  try {
    await api.post(`/ab-testing/${selectedClient.value}/ab-tests/${testId}/stop`)
    loadTests()
  } catch (error) {
    console.error('Erro ao parar teste:', error)
  }
}

const deleteTest = async (testId) => {
  if (!confirm('Tem certeza que deseja excluir este teste?')) return
  try {
    await api.delete(`/ab-testing/${selectedClient.value}/ab-tests/${testId}`)
    loadTests()
  } catch (error) {
    console.error('Erro ao excluir teste:', error)
  }
}

const formatPercent = (num) => {
  if (!num) return '0%'
  return (num * 100).toFixed(1) + '%'
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('pt-BR')
}

onMounted(() => {
  loadClients()
})
</script>

<style lang="scss" scoped>
.ab-testing-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.header-left {
  .page-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 0.25rem 0;
  }

  .page-subtitle {
    color: var(--text-secondary);
    margin: 0;
    font-size: 0.875rem;
  }
}

.header-right {
  display: flex;
  gap: 0.75rem;
}

.client-select {
  padding: 0.625rem 1rem;
  background: var(--surface-primary);
  border: 1px solid var(--border-light);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 0.875rem;
  cursor: pointer;

  &:focus {
    outline: none;
    border-color: var(--primary-color);
  }
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  background: var(--primary-color);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover:not(:disabled) {
    background: var(--primary-dark);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.btn-secondary {
  padding: 0.625rem 1rem;
  background: var(--surface-secondary);
  border: none;
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;

  &:hover {
    background: var(--surface-tertiary);
  }
}

.btn-icon {
  width: 32px;
  height: 32px;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover {
    background: var(--surface-secondary);
    color: var(--primary-color);
  }

  &.danger:hover {
    color: #dc2626;
  }
}

// States
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
  color: var(--text-secondary);

  i {
    font-size: 3rem;
    margin-bottom: 1rem;
    opacity: 0.5;
  }

  h3 {
    margin: 0 0 0.5rem 0;
    color: var(--text-primary);
  }

  p {
    margin: 0;
  }
}

.empty-icon {
  width: 80px;
  height: 80px;
  background: var(--surface-secondary);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1rem;

  i {
    font-size: 2rem;
    margin: 0;
  }
}

// Tests Grid
.tests-grid {
  display: grid;
  gap: 1rem;
}

.test-card {
  background: var(--surface-primary);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  overflow: hidden;
}

.test-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border-light);
}

.test-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;

  h3 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
  }
}

.test-status {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: capitalize;

  &.running { background: #dcfce7; color: #166534; }
  &.draft { background: #fef3c7; color: #92400e; }
  &.paused { background: #fef3c7; color: #92400e; }
  &.completed { background: #dbeafe; color: #1e40af; }
  &.stopped { background: #f3f4f6; color: #6b7280; }
}

.test-actions {
  display: flex;
  gap: 0.25rem;
}

.test-body {
  padding: 1.25rem;
}

.test-description {
  margin: 0 0 1rem 0;
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.variants {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.variant-card {
  background: var(--surface-secondary);
  border-radius: 8px;
  padding: 1rem;
  position: relative;

  &.winner {
    border: 2px solid var(--success-color);
  }
}

.variant-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;

  .variant-name {
    font-weight: 600;
    color: var(--text-primary);
  }

  .variant-traffic {
    font-size: 0.75rem;
    color: var(--text-secondary);
    background: var(--surface-primary);
    padding: 0.125rem 0.5rem;
    border-radius: 4px;
  }
}

.variant-stats {
  display: flex;
  gap: 1rem;
}

.stat {
  display: flex;
  flex-direction: column;

  .stat-value {
    font-size: 1.125rem;
    font-weight: 700;
    color: var(--text-primary);
  }

  .stat-label {
    font-size: 0.625rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
}

.winner-badge {
  position: absolute;
  top: -8px;
  right: 8px;
  background: var(--success-color);
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.test-meta {
  display: flex;
  gap: 1rem;
  color: var(--text-secondary);
  font-size: 0.75rem;

  span {
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }
}

// Modal
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal {
  background: var(--surface-primary);
  border-radius: 12px;
  width: 100%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem;
  border-bottom: 1px solid var(--border-light);

  h2 {
    margin: 0;
    font-size: 1.125rem;
    font-weight: 600;
  }
}

.btn-close {
  width: 32px;
  height: 32px;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;

  &:hover {
    background: var(--surface-secondary);
  }
}

.modal-body {
  padding: 1.25rem;
}

.modal-footer {
  padding: 1.25rem;
  border-top: 1px solid var(--border-light);
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.form-group {
  margin-bottom: 1rem;

  label {
    display: block;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary);
    margin-bottom: 0.5rem;
  }

  input, textarea {
    width: 100%;
    padding: 0.625rem 0.875rem;
    background: var(--surface-secondary);
    border: 1px solid var(--border-light);
    border-radius: 8px;
    color: var(--text-primary);
    font-size: 0.875rem;

    &:focus {
      outline: none;
      border-color: var(--primary-color);
    }
  }

  textarea {
    min-height: 80px;
    resize: vertical;
  }
}

.variants-section {
  h4 {
    margin: 0 0 1rem 0;
    font-size: 0.9375rem;
    font-weight: 600;
  }
}

.variant-inputs {
  display: grid;
  gap: 1rem;
}

.variant-input {
  label {
    display: block;
    font-size: 0.8125rem;
    font-weight: 500;
    color: var(--text-primary);
    margin-bottom: 0.5rem;
  }

  textarea {
    width: 100%;
    min-height: 60px;
    padding: 0.625rem;
    background: var(--surface-secondary);
    border: 1px solid var(--border-light);
    border-radius: 8px;
    color: var(--text-primary);
    font-size: 0.8125rem;
    resize: vertical;
    margin-bottom: 0.5rem;

    &:focus {
      outline: none;
      border-color: var(--primary-color);
    }
  }
}

.traffic-input {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  color: var(--text-secondary);

  input {
    width: 60px;
    padding: 0.375rem 0.5rem;
    background: var(--surface-secondary);
    border: 1px solid var(--border-light);
    border-radius: 4px;
    color: var(--text-primary);
    text-align: center;
  }
}
</style>
