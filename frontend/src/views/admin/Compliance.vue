<template>
  <div class="compliance-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">Compliance LGPD</h1>
        <p class="page-subtitle">Gerencie consentimentos e dados pessoais</p>
      </div>
      <div class="header-right">
        <select v-model="selectedClient" class="client-select" @change="loadCompliance">
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
        <i class="mdi mdi-shield-check-outline"></i>
      </div>
      <h3>Selecione um cliente</h3>
      <p>Escolha um cliente para gerenciar compliance</p>
    </div>

    <!-- Content -->
    <div v-else class="compliance-content">
      <!-- Stats Cards -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon consents">
            <i class="mdi mdi-check-decagram"></i>
          </div>
          <div class="stat-data">
            <span class="stat-value">{{ stats.total_consents || 0 }}</span>
            <span class="stat-label">Consentimentos</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon requests">
            <i class="mdi mdi-file-document-outline"></i>
          </div>
          <div class="stat-data">
            <span class="stat-value">{{ stats.pending_requests || 0 }}</span>
            <span class="stat-label">DSAR Pendentes</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon retention">
            <i class="mdi mdi-clock-outline"></i>
          </div>
          <div class="stat-data">
            <span class="stat-value">{{ stats.days_retention || 365 }} dias</span>
            <span class="stat-label">Retencao de Dados</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon anonymized">
            <i class="mdi mdi-incognito"></i>
          </div>
          <div class="stat-data">
            <span class="stat-value">{{ stats.anonymized_records || 0 }}</span>
            <span class="stat-label">Anonimizados</span>
          </div>
        </div>
      </div>

      <!-- Data Retention Policy -->
      <div class="config-card">
        <div class="card-header">
          <h3>Politica de Retencao de Dados</h3>
        </div>
        <div class="card-body">
          <div class="retention-settings">
            <div class="setting-row">
              <div class="setting-info">
                <span class="setting-name">Periodo de retencao</span>
                <span class="setting-desc">Tempo que dados pessoais sao mantidos antes da anonimizacao</span>
              </div>
              <div class="setting-control">
                <select v-model="retention.period_days" @change="saveRetention">
                  <option :value="30">30 dias</option>
                  <option :value="90">90 dias</option>
                  <option :value="180">180 dias</option>
                  <option :value="365">1 ano</option>
                  <option :value="730">2 anos</option>
                </select>
              </div>
            </div>
            <div class="setting-row">
              <div class="setting-info">
                <span class="setting-name">Anonimizacao automatica</span>
                <span class="setting-desc">Anonimiza dados automaticamente apos o periodo de retencao</span>
              </div>
              <label class="toggle">
                <input v-model="retention.auto_anonymize" type="checkbox" @change="saveRetention" />
                <span class="toggle-slider"></span>
              </label>
            </div>
            <div class="setting-row">
              <div class="setting-info">
                <span class="setting-name">Notificar antes de anonimizar</span>
                <span class="setting-desc">Envia email de notificacao antes de anonimizar dados</span>
              </div>
              <label class="toggle">
                <input v-model="retention.notify_before" type="checkbox" @change="saveRetention" />
                <span class="toggle-slider"></span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- DSAR Requests -->
      <div class="config-card">
        <div class="card-header">
          <h3>Solicitacoes de Dados (DSAR)</h3>
          <button class="btn-primary-sm" @click="showDSARModal = true">
            <i class="mdi mdi-plus"></i>
            Nova Solicitacao
          </button>
        </div>
        <div class="card-body">
          <div class="dsar-table">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Tipo</th>
                  <th>Solicitante</th>
                  <th>Status</th>
                  <th>Data</th>
                  <th>Acoes</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="request in dsarRequests" :key="request.id">
                  <td class="request-id">#{{ request.id }}</td>
                  <td>
                    <span class="type-badge" :class="request.request_type">
                      {{ getTypeLabel(request.request_type) }}
                    </span>
                  </td>
                  <td>{{ request.contact_email || request.contact_phone }}</td>
                  <td>
                    <span class="status-badge" :class="request.status">
                      {{ getStatusLabel(request.status) }}
                    </span>
                  </td>
                  <td>{{ formatDate(request.created_at) }}</td>
                  <td class="actions">
                    <button
                      v-if="request.status === 'pending'"
                      class="btn-icon-sm"
                      @click="processRequest(request.id)"
                      title="Processar"
                    >
                      <i class="mdi mdi-play"></i>
                    </button>
                    <button
                      v-if="request.request_type === 'portability' && request.status === 'completed'"
                      class="btn-icon-sm"
                      @click="downloadExport(request)"
                      title="Download"
                    >
                      <i class="mdi mdi-download"></i>
                    </button>
                  </td>
                </tr>
                <tr v-if="dsarRequests.length === 0">
                  <td colspan="6" class="no-data">Nenhuma solicitacao</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Consent Log -->
      <div class="config-card">
        <div class="card-header">
          <h3>Registro de Consentimentos</h3>
        </div>
        <div class="card-body">
          <div class="consent-table">
            <table>
              <thead>
                <tr>
                  <th>Contato</th>
                  <th>Tipo</th>
                  <th>Status</th>
                  <th>IP</th>
                  <th>Data</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="consent in consents" :key="consent.id">
                  <td>{{ consent.contact_phone || consent.contact_identifier }}</td>
                  <td>{{ consent.consent_type }}</td>
                  <td>
                    <span class="consent-status" :class="consent.granted ? 'granted' : 'revoked'">
                      {{ consent.granted ? 'Concedido' : 'Revogado' }}
                    </span>
                  </td>
                  <td class="ip">{{ consent.ip_address || '-' }}</td>
                  <td>{{ formatDate(consent.created_at) }}</td>
                </tr>
                <tr v-if="consents.length === 0">
                  <td colspan="5" class="no-data">Nenhum consentimento registrado</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- DSAR Modal -->
    <div v-if="showDSARModal" class="modal-overlay" @click.self="showDSARModal = false">
      <div class="modal">
        <div class="modal-header">
          <h2>Nova Solicitacao DSAR</h2>
          <button class="btn-close" @click="showDSARModal = false">
            <i class="mdi mdi-close"></i>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>Tipo de Solicitacao</label>
            <select v-model="newDSAR.type">
              <option value="export">Exportar dados</option>
              <option value="delete">Excluir dados</option>
              <option value="rectify">Retificar dados</option>
            </select>
          </div>
          <div class="form-group">
            <label>Email do Solicitante</label>
            <input v-model="newDSAR.requester_email" type="email" placeholder="email@exemplo.com" />
          </div>
          <div class="form-group">
            <label>Identificador do Contato</label>
            <input v-model="newDSAR.contact_identifier" type="text" placeholder="Telefone ou email do contato" />
          </div>
          <div class="form-group">
            <label>Observacoes (opcional)</label>
            <textarea v-model="newDSAR.notes" placeholder="Informacoes adicionais"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showDSARModal = false">Cancelar</button>
          <button class="btn-primary" @click="createDSAR" :disabled="!canCreateDSAR">
            <i class="mdi mdi-plus"></i>
            Criar Solicitacao
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

const stats = ref({})
const retention = reactive({
  period_days: 365,
  auto_anonymize: true,
  notify_before: false
})
const dsarRequests = ref([])
const consents = ref([])

const showDSARModal = ref(false)
const newDSAR = reactive({
  type: 'export',
  requester_email: '',
  contact_identifier: '',
  notes: ''
})

const canCreateDSAR = computed(() => {
  return newDSAR.requester_email && newDSAR.contact_identifier
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

const loadCompliance = async () => {
  if (!selectedClient.value) return

  try {
    // Paths corretos baseados no backend (prefixo /compliance já está na rota)
    const [summaryRes, retentionRes, dsarRes] = await Promise.all([
      api.get(`/compliance/${selectedClient.value}/summary`),
      api.get(`/compliance/${selectedClient.value}/retention-policy`),
      api.get(`/compliance/${selectedClient.value}/dsar`)
    ])

    stats.value = summaryRes.data
    Object.assign(retention, {
      period_days: retentionRes.data.conversation_retention_days || 365,
      auto_anonymize: retentionRes.data.auto_anonymize || false,
      notify_before: false
    })
    dsarRequests.value = dsarRes.data.requests || []
    // Consents serão carregados do summary
    consents.value = summaryRes.data.recent_consents || []
  } catch (error) {
    console.error('Erro ao carregar compliance:', error)
  }
}

const saveRetention = async () => {
  try {
    await api.put(`/compliance/${selectedClient.value}/retention-policy`, {
      conversation_retention_days: retention.period_days,
      auto_anonymize: retention.auto_anonymize
    })
  } catch (error) {
    console.error('Erro ao salvar retencao:', error)
  }
}

const createDSAR = async () => {
  try {
    // Mapear tipos do frontend para backend
    const typeMapping = {
      'export': 'portability',
      'delete': 'deletion',
      'rectify': 'rectification'
    }

    await api.post(`/compliance/${selectedClient.value}/dsar`, {
      contact_phone: newDSAR.contact_identifier,
      request_type: typeMapping[newDSAR.type] || newDSAR.type,
      contact_email: newDSAR.requester_email,
      description: newDSAR.notes
    })
    showDSARModal.value = false
    newDSAR.type = 'export'
    newDSAR.requester_email = ''
    newDSAR.contact_identifier = ''
    newDSAR.notes = ''
    loadCompliance()
  } catch (error) {
    console.error('Erro ao criar DSAR:', error)
  }
}

const processRequest = async (requestId) => {
  try {
    await api.post(`/compliance/${selectedClient.value}/dsar/${requestId}/process`)
    loadCompliance()
  } catch (error) {
    console.error('Erro ao processar:', error)
  }
}

const downloadExport = async (request) => {
  try {
    // Backend usa /export/{contact_phone} para exportar dados
    const contactPhone = request.contact_phone || request.contact_identifier
    if (!contactPhone) {
      console.error('Telefone do contato nao encontrado')
      return
    }
    const response = await api.get(`/compliance/${selectedClient.value}/export/${encodeURIComponent(contactPhone)}`)
    const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `dsar-export-${request.id}.json`
    a.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Erro ao baixar:', error)
  }
}

const getTypeLabel = (type) => {
  const labels = {
    // Frontend types
    export: 'Exportar',
    delete: 'Excluir',
    rectify: 'Retificar',
    // Backend request_types
    access: 'Acessar',
    rectification: 'Retificar',
    deletion: 'Excluir',
    portability: 'Exportar',
    restriction: 'Restringir',
    objection: 'Objecao'
  }
  return labels[type] || type
}

const getStatusLabel = (status) => {
  const labels = {
    pending: 'Pendente',
    processing: 'Processando',
    completed: 'Concluido',
    failed: 'Falhou'
  }
  return labels[status] || status
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit'
  })
}

onMounted(() => {
  loadClients()
})
</script>

<style lang="scss" scoped>
.compliance-page {
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

.compliance-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

// Stats Grid
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

.stat-card {
  background: var(--surface-primary);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  padding: 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  i {
    font-size: 1.5rem;
    color: white;
  }

  &.consents { background: var(--success-color); }
  &.requests { background: var(--warning-color); }
  &.retention { background: var(--primary-color); }
  &.anonymized { background: var(--info-color); }
}

.stat-data {
  display: flex;
  flex-direction: column;

  .stat-value {
    font-size: 1.375rem;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.2;
  }

  .stat-label {
    font-size: 0.75rem;
    color: var(--text-secondary);
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

// Retention Settings
.retention-settings {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.875rem 1rem;
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

.setting-control {
  select {
    padding: 0.5rem 0.75rem;
    background: var(--surface-primary);
    border: 1px solid var(--border-light);
    border-radius: 6px;
    color: var(--text-primary);
    font-size: 0.875rem;

    &:focus {
      outline: none;
      border-color: var(--primary-color);
    }
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

// Tables
.dsar-table,
.consent-table {
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

.request-id {
  font-family: monospace;
  color: var(--text-secondary);
}

.ip {
  font-family: monospace;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.type-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;

  &.export, &.portability { background: #dbeafe; color: #1e40af; }
  &.delete, &.deletion { background: #fee2e2; color: #991b1b; }
  &.rectify, &.rectification { background: #fef3c7; color: #92400e; }
  &.access { background: #e0e7ff; color: #3730a3; }
  &.restriction { background: #fce7f3; color: #9d174d; }
  &.objection { background: #fef3c7; color: #92400e; }
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;

  &.pending { background: #fef3c7; color: #92400e; }
  &.processing { background: #dbeafe; color: #1e40af; }
  &.completed { background: #dcfce7; color: #166534; }
  &.failed { background: #fee2e2; color: #991b1b; }
}

.consent-status {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;

  &.granted { background: #dcfce7; color: #166534; }
  &.revoked { background: #fee2e2; color: #991b1b; }
}

.actions {
  display: flex;
  gap: 0.25rem;
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

.btn-primary-sm {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.875rem;
  background: var(--primary-color);
  border: none;
  border-radius: 6px;
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
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;

  &:hover {
    background: var(--surface-tertiary);
  }
}

.btn-icon-sm {
  width: 28px;
  height: 28px;
  background: transparent;
  border: none;
  border-radius: 4px;
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

  input, select, textarea {
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

// Responsive
@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
