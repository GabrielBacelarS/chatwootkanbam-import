<template>
  <div class="integrations-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">Integracoes CRM</h1>
        <p class="page-subtitle">Conecte seu CRM para sincronizar leads automaticamente</p>
      </div>
      <div class="header-right">
        <select v-model="selectedClient" class="client-select" @change="loadIntegrations">
          <option value="">Selecione um cliente</option>
          <option v-for="client in clients" :key="client.slug" :value="client.slug">
            {{ client.name }}
          </option>
        </select>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="!selectedClient" class="empty-state">
      <div class="empty-icon">
        <i class="mdi mdi-connection"></i>
      </div>
      <h3>Selecione um cliente</h3>
      <p>Escolha um cliente para configurar integracoes</p>
    </div>

    <!-- Loading -->
    <div v-else-if="loading" class="loading-state">
      <i class="mdi mdi-loading mdi-spin"></i>
      <span>Carregando integracoes...</span>
    </div>

    <!-- Content -->
    <div v-else class="integrations-content">
      <!-- CRM Conectado -->
      <div v-if="crmConfig.configured" class="connected-crm">
        <div class="crm-card connected">
          <div class="crm-header">
            <div class="crm-logo" :class="crmConfig.provider">
              <i :class="crmConfig.provider === 'hubspot' ? 'mdi mdi-hubspot' : 'mdi mdi-pipe'"></i>
            </div>
            <div class="crm-info">
              <h3>{{ crmConfig.provider === 'hubspot' ? 'HubSpot' : 'Pipedrive' }}</h3>
              <span class="crm-status" :class="{ active: crmConfig.connected }">
                <i :class="crmConfig.connected ? 'mdi mdi-check-circle' : 'mdi mdi-alert-circle'"></i>
                {{ crmConfig.connected ? 'Conectado' : 'Erro de conexao' }}
              </span>
            </div>
            <div class="crm-actions">
              <button class="btn-secondary" @click="testConnection" :disabled="testing">
                <i :class="testing ? 'mdi mdi-loading mdi-spin' : 'mdi mdi-connection'"></i>
                Testar
              </button>
              <button class="btn-danger" @click="disconnectIntegration">
                <i class="mdi mdi-link-off"></i>
                Desconectar
              </button>
            </div>
          </div>

          <!-- Config Options -->
          <div class="crm-settings">
            <div class="setting-item">
              <div class="setting-info">
                <span class="setting-name">Habilitado</span>
                <span class="setting-desc">Ativa sincronizacao automatica</span>
              </div>
              <label class="toggle">
                <input type="checkbox" :checked="crmConfig.enabled" @change="updateCrmConfig({ enabled: $event.target.checked })" />
                <span class="toggle-slider"></span>
              </label>
            </div>
            <div class="setting-item">
              <div class="setting-info">
                <span class="setting-name">Criar contatos automaticamente</span>
                <span class="setting-desc">Cria contatos no CRM ao final da conversa</span>
              </div>
              <label class="toggle">
                <input type="checkbox" :checked="crmConfig.auto_create_contacts" @change="updateCrmConfig({ auto_create_contacts: $event.target.checked })" />
                <span class="toggle-slider"></span>
              </label>
            </div>
            <div class="setting-item">
              <div class="setting-info">
                <span class="setting-name">Criar deals automaticamente</span>
                <span class="setting-desc">Cria deals/negocios para cada lead</span>
              </div>
              <label class="toggle">
                <input type="checkbox" :checked="crmConfig.auto_create_deals" @change="updateCrmConfig({ auto_create_deals: $event.target.checked })" />
                <span class="toggle-slider"></span>
              </label>
            </div>
            <div class="setting-item">
              <div class="setting-info">
                <span class="setting-name">Sincronizar notas</span>
                <span class="setting-desc">Adiciona resumo da conversa como nota</span>
              </div>
              <label class="toggle">
                <input type="checkbox" :checked="crmConfig.sync_notes" @change="updateCrmConfig({ sync_notes: $event.target.checked })" />
                <span class="toggle-slider"></span>
              </label>
            </div>
          </div>

          <!-- Pipelines -->
          <div v-if="pipelines.length > 0" class="crm-pipelines">
            <h4>Pipeline Padrao</h4>
            <select @change="updateCrmConfig({ default_pipeline_id: $event.target.value })">
              <option value="">Selecione um pipeline</option>
              <option v-for="pipeline in pipelines" :key="pipeline.id" :value="pipeline.id" :selected="pipeline.id === crmConfig.default_pipeline_id">
                {{ pipeline.name }}
              </option>
            </select>
          </div>
        </div>
      </div>

      <!-- Conectar CRM -->
      <div v-else class="available-crms">
        <h3 class="section-title">Conectar CRM</h3>
        <p class="section-desc">Escolha um CRM para sincronizar seus leads automaticamente</p>

        <div class="integrations-grid">
          <!-- HubSpot -->
          <div class="integration-card">
            <div class="integration-header">
              <div class="integration-logo hubspot">
                <i class="mdi mdi-hubspot"></i>
              </div>
              <div class="integration-info">
                <h3>HubSpot</h3>
                <span class="integration-status">Nao conectado</span>
              </div>
            </div>
            <p class="integration-desc">
              Sincronize leads e contatos automaticamente com o HubSpot CRM.
            </p>
            <div class="integration-actions">
              <button class="btn-primary" @click="showHubspotModal = true">
                <i class="mdi mdi-link"></i>
                Conectar
              </button>
            </div>
          </div>

          <!-- Pipedrive -->
          <div class="integration-card">
            <div class="integration-header">
              <div class="integration-logo pipedrive">
                <i class="mdi mdi-pipe"></i>
              </div>
              <div class="integration-info">
                <h3>Pipedrive</h3>
                <span class="integration-status">Nao conectado</span>
              </div>
            </div>
            <p class="integration-desc">
              Crie deals e gerencie seu pipeline de vendas no Pipedrive.
            </p>
            <div class="integration-actions">
              <button class="btn-primary" @click="showPipedriveModal = true">
                <i class="mdi mdi-link"></i>
                Conectar
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- HubSpot Modal -->
    <div v-if="showHubspotModal" class="modal-overlay" @click.self="showHubspotModal = false">
      <div class="modal">
        <div class="modal-header">
          <h2>Conectar HubSpot</h2>
          <button class="btn-close" @click="showHubspotModal = false">
            <i class="mdi mdi-close"></i>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>API Key do HubSpot</label>
            <input v-model="hubspotConfig.api_key" type="password" placeholder="Sua API Key" />
            <small>Encontre sua API Key em Settings > Integrations > Private Apps</small>
          </div>
          <div class="form-group">
            <label class="checkbox-label">
              <input v-model="hubspotConfig.auto_create_contacts" type="checkbox" />
              <span>Criar contatos automaticamente</span>
            </label>
          </div>
          <div class="form-group">
            <label class="checkbox-label">
              <input v-model="hubspotConfig.auto_create_deals" type="checkbox" />
              <span>Criar deals automaticamente</span>
            </label>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showHubspotModal = false">Cancelar</button>
          <button class="btn-primary" @click="connectHubspot" :disabled="!hubspotConfig.api_key">
            <i class="mdi mdi-link"></i>
            Conectar
          </button>
        </div>
      </div>
    </div>

    <!-- Pipedrive Modal -->
    <div v-if="showPipedriveModal" class="modal-overlay" @click.self="showPipedriveModal = false">
      <div class="modal">
        <div class="modal-header">
          <h2>Conectar Pipedrive</h2>
          <button class="btn-close" @click="showPipedriveModal = false">
            <i class="mdi mdi-close"></i>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>API Token do Pipedrive</label>
            <input v-model="pipedriveConfig.api_key" type="password" placeholder="Seu API Token" />
            <small>Encontre seu API Token em Settings > Personal Preferences > API</small>
          </div>
          <div class="form-group">
            <label class="checkbox-label">
              <input v-model="pipedriveConfig.auto_create_contacts" type="checkbox" />
              <span>Criar contatos automaticamente</span>
            </label>
          </div>
          <div class="form-group">
            <label class="checkbox-label">
              <input v-model="pipedriveConfig.auto_create_deals" type="checkbox" />
              <span>Criar deals automaticamente</span>
            </label>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showPipedriveModal = false">Cancelar</button>
          <button class="btn-primary" @click="connectPipedrive" :disabled="!pipedriveConfig.api_key">
            <i class="mdi mdi-link"></i>
            Conectar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import api, { clientsApi } from '@/api/client'

const clients = ref([])
const selectedClient = ref('')

const crmConfig = ref({
  configured: false,
  provider: null,
  enabled: false,
  connected: false
})

const pipelines = ref([])
const pipelineStages = ref([])
const testing = ref(false)
const loading = ref(false)

const showHubspotModal = ref(false)
const showPipedriveModal = ref(false)

const hubspotConfig = reactive({ api_key: '', auto_create_contacts: true, auto_create_deals: false })
const pipedriveConfig = reactive({ api_key: '', auto_create_contacts: true, auto_create_deals: false })

const hasAnyIntegration = computed(() => {
  return crmConfig.value.configured && crmConfig.value.connected
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

const loadIntegrations = async () => {
  if (!selectedClient.value) return

  loading.value = true
  try {
    const response = await api.get(`/integrations/${selectedClient.value}/crm`)
    crmConfig.value = response.data || { configured: false }

    // Se configurado, carregar pipelines
    if (crmConfig.value.configured && crmConfig.value.connected) {
      loadPipelines()
    }
  } catch (error) {
    console.error('Erro ao carregar integracoes:', error)
    crmConfig.value = { configured: false, provider: null, enabled: false }
  } finally {
    loading.value = false
  }
}

const loadPipelines = async () => {
  if (!selectedClient.value || !crmConfig.value.configured) return

  try {
    const response = await api.get(`/integrations/${selectedClient.value}/crm/pipelines`)
    pipelines.value = response.data.pipelines || []
  } catch (error) {
    console.error('Erro ao carregar pipelines:', error)
    pipelines.value = []
  }
}

const loadPipelineStages = async (pipelineId) => {
  if (!selectedClient.value || !pipelineId) return

  try {
    const response = await api.get(`/integrations/${selectedClient.value}/crm/pipelines/${pipelineId}/stages`)
    pipelineStages.value = response.data.stages || []
  } catch (error) {
    console.error('Erro ao carregar stages:', error)
    pipelineStages.value = []
  }
}

const connectHubspot = async () => {
  try {
    await api.post(`/integrations/${selectedClient.value}/crm/connect`, {
      provider: 'hubspot',
      api_key: hubspotConfig.api_key,
      auto_create_contacts: hubspotConfig.auto_create_contacts,
      auto_create_deals: hubspotConfig.auto_create_deals
    })
    showHubspotModal.value = false
    hubspotConfig.api_key = ''
    loadIntegrations()
  } catch (error) {
    console.error('Erro ao conectar HubSpot:', error)
    alert('Erro ao conectar. Verifique suas credenciais.')
  }
}

const connectPipedrive = async () => {
  try {
    await api.post(`/integrations/${selectedClient.value}/crm/connect`, {
      provider: 'pipedrive',
      api_key: pipedriveConfig.api_key,
      auto_create_contacts: pipedriveConfig.auto_create_contacts,
      auto_create_deals: pipedriveConfig.auto_create_deals
    })
    showPipedriveModal.value = false
    pipedriveConfig.api_key = ''
    loadIntegrations()
  } catch (error) {
    console.error('Erro ao conectar Pipedrive:', error)
    alert('Erro ao conectar. Verifique suas credenciais.')
  }
}

const testConnection = async () => {
  if (!selectedClient.value || !crmConfig.value.configured) return

  testing.value = true
  try {
    const response = await api.post(`/integrations/${selectedClient.value}/crm/test`)
    if (response.data.connected) {
      alert('Conexao bem sucedida!')
    } else {
      alert('Falha na conexao: ' + (response.data.error || 'Erro desconhecido'))
    }
    loadIntegrations()
  } catch (error) {
    console.error('Erro ao testar conexao:', error)
    alert('Erro ao testar conexao')
  } finally {
    testing.value = false
  }
}

const disconnectIntegration = async () => {
  if (!confirm('Deseja desconectar o CRM?')) return

  try {
    await api.delete(`/integrations/${selectedClient.value}/crm`)
    crmConfig.value = { configured: false, provider: null, enabled: false }
    pipelines.value = []
  } catch (error) {
    console.error('Erro ao desconectar:', error)
  }
}

const updateCrmConfig = async (updates) => {
  try {
    await api.put(`/integrations/${selectedClient.value}/crm`, updates)
    loadIntegrations()
  } catch (error) {
    console.error('Erro ao atualizar configuracoes:', error)
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(() => {
  loadClients()
})
</script>

<style lang="scss" scoped>
.integrations-page {
  max-width: 1200px;
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

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
  color: var(--text-secondary);

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
    opacity: 0.5;
  }
}

.integrations-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

// Loading State
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  color: var(--text-secondary);

  i {
    font-size: 2rem;
    color: var(--primary-color);
    margin-bottom: 1rem;
  }
}

// Section titles
.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.25rem 0;
}

.section-desc {
  color: var(--text-secondary);
  font-size: 0.875rem;
  margin: 0 0 1.5rem 0;
}

// Connected CRM
.connected-crm {
  .crm-card {
    background: var(--surface-primary);
    border: 2px solid var(--success-color);
    border-radius: 12px;
    overflow: hidden;

    &.connected {
      box-shadow: 0 0 20px rgba(16, 185, 129, 0.1);
    }
  }
}

.crm-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem;
  border-bottom: 1px solid var(--border-light);
}

.crm-logo {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  i {
    font-size: 1.75rem;
    color: white;
  }

  &.hubspot { background: #ff7a59; }
  &.pipedrive { background: #21313c; }
}

.crm-info {
  flex: 1;

  h3 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary);
  }
}

.crm-status {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.875rem;
  color: var(--text-secondary);

  i {
    font-size: 1rem;
  }

  &.active {
    color: var(--success-color);
  }
}

.crm-actions {
  display: flex;
  gap: 0.5rem;
}

.crm-settings {
  padding: 1.25rem;
  border-bottom: 1px solid var(--border-light);
}

.crm-pipelines {
  padding: 1.25rem;

  h4 {
    margin: 0 0 0.75rem 0;
    font-size: 0.9375rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  select {
    width: 100%;
    padding: 0.625rem 1rem;
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
}

// Integrations Grid
.integrations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
}

.integration-card {
  background: var(--surface-primary);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  padding: 1.25rem;
  transition: all 0.15s ease;

  &.connected {
    border-color: var(--success-color);
  }
}

.integration-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.integration-logo {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;

  i {
    font-size: 1.5rem;
    color: white;
  }

  &.hubspot { background: #ff7a59; }
  &.pipedrive { background: #21313c; }
  &.webhook { background: var(--primary-color); }
}

.integration-info {
  h3 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
  }
}

.integration-status {
  font-size: 0.75rem;
  color: var(--text-secondary);

  &.active {
    color: var(--success-color);
  }
}

.integration-desc {
  margin: 0 0 1rem 0;
  font-size: 0.8125rem;
  color: var(--text-secondary);
  line-height: 1.5;
}

.integration-actions {
  display: flex;
  gap: 0.5rem;
}

// Buttons
.btn-primary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  background: var(--primary-color);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover {
    background: var(--primary-dark);
  }
}

.btn-secondary {
  padding: 0.625rem 1rem;
  background: var(--surface-secondary);
  border: none;
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;

  &:hover {
    background: var(--surface-tertiary);
  }
}

.btn-danger {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  background: var(--error-color);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;

  &:hover {
    opacity: 0.9;
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
}

// Config Card
.config-card {
  background: var(--surface-primary);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border-light);

  h3 {
    margin: 0;
    font-size: 0.9375rem;
    font-weight: 600;
    color: var(--text-primary);
  }
}

.card-body {
  padding: 1rem 1.25rem;
}

// Settings
.settings-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: var(--surface-secondary);
  border-radius: 8px;
}

.setting-info {
  display: flex;
  flex-direction: column;

  .setting-name {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary);
  }

  .setting-desc {
    font-size: 0.75rem;
    color: var(--text-secondary);
  }
}

// Toggle
.toggle {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;

  input {
    opacity: 0;
    width: 0;
    height: 0;

    &:checked + .toggle-slider {
      background: var(--primary-color);
    }

    &:checked + .toggle-slider:before {
      transform: translateX(20px);
    }
  }
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background: var(--border-light);
  border-radius: 24px;
  transition: 0.2s;

  &:before {
    position: absolute;
    content: "";
    height: 18px;
    width: 18px;
    left: 3px;
    bottom: 3px;
    background: white;
    border-radius: 50%;
    transition: 0.2s;
  }
}

// Sync Table
.sync-table {
  overflow-x: auto;

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th, td {
    padding: 0.75rem 1rem;
    text-align: left;
    border-bottom: 1px solid var(--border-light);
  }

  th {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-secondary);
    background: var(--surface-secondary);
  }

  td {
    font-size: 0.875rem;
    color: var(--text-primary);
  }

  .no-data {
    text-align: center;
    color: var(--text-secondary);
    padding: 2rem;
  }
}

.crm-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: capitalize;

  &.hubspot { background: #fff1ee; color: #ff7a59; }
  &.pipedrive { background: #e8ebed; color: #21313c; }
  &.webhook { background: #dbeafe; color: var(--primary-color); }
}

.sync-status {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.8125rem;

  &.success { color: var(--success-color); }
  &.error { color: var(--error-color); }
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
  max-width: 480px;
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

  input {
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

  small {
    display: block;
    margin-top: 0.375rem;
    font-size: 0.75rem;
    color: var(--text-secondary);
  }
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;

  input {
    width: auto;
  }

  span {
    font-size: 0.875rem;
    color: var(--text-primary);
  }
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-weight: 400 !important;

  input[type="checkbox"] {
    width: 18px;
    height: 18px;
    accent-color: var(--primary-color);
  }

  span {
    font-size: 0.875rem;
    color: var(--text-primary);
  }
}

.btn-primary:disabled,
.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
