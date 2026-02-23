<template>
  <div class="lead-scoring-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">Lead Scoring</h1>
        <p class="page-subtitle">Configure regras de pontuacao de leads</p>
      </div>
      <div class="header-right">
        <select v-model="selectedClient" class="client-select" @change="loadConfig">
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
        <i class="mdi mdi-trophy-outline"></i>
      </div>
      <h3>Selecione um cliente</h3>
      <p>Escolha um cliente para configurar o lead scoring</p>
    </div>

    <!-- Content -->
    <div v-else class="scoring-content">
      <!-- Scoring Rules -->
      <div class="config-card">
        <div class="card-header">
          <h3>Regras de Pontuacao</h3>
          <p>Define quantos pontos cada acao do lead vale</p>
        </div>
        <div class="card-body">
          <div class="rules-grid">
            <div v-for="(rule, key) in scoringRules" :key="key" class="rule-item">
              <div class="rule-info">
                <i :class="rule.icon"></i>
                <div class="rule-text">
                  <span class="rule-name">{{ rule.label }}</span>
                  <span class="rule-desc">{{ rule.description }}</span>
                </div>
              </div>
              <div class="rule-input">
                <input
                  v-model.number="config.rules[key]"
                  type="number"
                  min="0"
                  max="100"
                />
                <span class="points-label">pts</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Score Thresholds -->
      <div class="config-card">
        <div class="card-header">
          <h3>Classificacao de Leads</h3>
          <p>Define os limites de pontuacao para cada categoria</p>
        </div>
        <div class="card-body">
          <div class="thresholds-grid">
            <div class="threshold-item cold">
              <div class="threshold-header">
                <i class="mdi mdi-snowflake"></i>
                <span>Frio</span>
              </div>
              <div class="threshold-range">
                <span>0</span>
                <span>-</span>
                <input v-model.number="config.thresholds.cold" type="number" min="0" />
                <span>pts</span>
              </div>
            </div>
            <div class="threshold-item warm">
              <div class="threshold-header">
                <i class="mdi mdi-thermometer"></i>
                <span>Morno</span>
              </div>
              <div class="threshold-range">
                <span>{{ config.thresholds.cold + 1 }}</span>
                <span>-</span>
                <input v-model.number="config.thresholds.warm" type="number" :min="config.thresholds.cold + 1" />
                <span>pts</span>
              </div>
            </div>
            <div class="threshold-item hot">
              <div class="threshold-header">
                <i class="mdi mdi-fire"></i>
                <span>Quente</span>
              </div>
              <div class="threshold-range">
                <span>{{ config.thresholds.warm + 1 }}+</span>
                <span>pts</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Auto Actions -->
      <div class="config-card">
        <div class="card-header">
          <h3>Acoes Automaticas</h3>
          <p>Acoes executadas automaticamente baseadas no score</p>
        </div>
        <div class="card-body">
          <div class="actions-list">
            <div class="action-item">
              <div class="action-info">
                <i class="mdi mdi-account-switch"></i>
                <div class="action-text">
                  <span class="action-name">Transferir para humano</span>
                  <span class="action-desc">Leads quentes sao transferidos automaticamente</span>
                </div>
              </div>
              <label class="toggle">
                <input v-model="config.actions.auto_transfer" type="checkbox" />
                <span class="toggle-slider"></span>
              </label>
            </div>
            <div class="action-item">
              <div class="action-info">
                <i class="mdi mdi-bell-ring"></i>
                <div class="action-text">
                  <span class="action-name">Notificar equipe</span>
                  <span class="action-desc">Envia notificacao quando lead atinge score alto</span>
                </div>
              </div>
              <label class="toggle">
                <input v-model="config.actions.notify_team" type="checkbox" />
                <span class="toggle-slider"></span>
              </label>
            </div>
            <div class="action-item">
              <div class="action-info">
                <i class="mdi mdi-tag-plus"></i>
                <div class="action-text">
                  <span class="action-name">Adicionar tag no CRM</span>
                  <span class="action-desc">Adiciona tag com a classificacao do lead</span>
                </div>
              </div>
              <label class="toggle">
                <input v-model="config.actions.add_crm_tag" type="checkbox" />
                <span class="toggle-slider"></span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- Save Button -->
      <div class="save-section">
        <button class="btn-primary" @click="saveConfig" :disabled="saving">
          <i :class="saving ? 'mdi mdi-loading mdi-spin' : 'mdi mdi-content-save'"></i>
          {{ saving ? 'Salvando...' : 'Salvar Configuracoes' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import api, { clientsApi } from '@/api/client'

const clients = ref([])
const selectedClient = ref('')
const saving = ref(false)

const scoringRules = {
  product_view: {
    label: 'Visualizou produto',
    description: 'Lead visualizou detalhes de um produto',
    icon: 'mdi mdi-eye-outline'
  },
  price_inquiry: {
    label: 'Perguntou preco',
    description: 'Lead perguntou sobre precos',
    icon: 'mdi mdi-currency-usd'
  },
  financing_inquiry: {
    label: 'Perguntou financiamento',
    description: 'Lead perguntou sobre opcoes de financiamento',
    icon: 'mdi mdi-calculator'
  },
  schedule_visit: {
    label: 'Agendou visita',
    description: 'Lead agendou uma visita presencial',
    icon: 'mdi mdi-calendar-check'
  },
  transfer_request: {
    label: 'Solicitou transferencia',
    description: 'Lead pediu para falar com humano',
    icon: 'mdi mdi-account-switch'
  },
  multiple_messages: {
    label: 'Multiplas mensagens',
    description: 'Lead enviou mais de 5 mensagens',
    icon: 'mdi mdi-message-text'
  },
  return_visit: {
    label: 'Retornou a conversa',
    description: 'Lead voltou a conversar apos 24h',
    icon: 'mdi mdi-refresh'
  }
}

const config = reactive({
  rules: {
    product_view: 10,
    price_inquiry: 15,
    financing_inquiry: 20,
    schedule_visit: 30,
    transfer_request: 25,
    multiple_messages: 5,
    return_visit: 15
  },
  thresholds: {
    cold: 25,
    warm: 60
  },
  actions: {
    auto_transfer: true,
    notify_team: true,
    add_crm_tag: false
  }
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

const loadConfig = async () => {
  if (!selectedClient.value) return

  try {
    const response = await api.get(`/lead-scoring/${selectedClient.value}/config`)
    if (response.data) {
      Object.assign(config.rules, response.data.rules || {})
      Object.assign(config.thresholds, response.data.thresholds || {})
      // Mapear campos do backend para frontend
      config.actions.auto_transfer = response.data.actions?.auto_transfer_hot || false
      config.actions.notify_team = response.data.actions?.notify_on_hot || true
    }
  } catch (error) {
    console.error('Erro ao carregar config:', error)
  }
}

const saveConfig = async () => {
  if (!selectedClient.value) return

  saving.value = true
  try {
    // Mapear campos do frontend para backend
    const payload = {
      rules: config.rules,
      thresholds: {
        cold: config.thresholds.cold,
        warm: config.thresholds.warm,
        hot: config.thresholds.warm + 1  // hot threshold
      },
      actions: {
        notify_on_hot: config.actions.notify_team,
        auto_transfer_hot: config.actions.auto_transfer,
        transfer_threshold: config.thresholds.warm + 1
      }
    }
    await api.put(`/lead-scoring/${selectedClient.value}/config`, payload)
    alert('Configuracoes salvas com sucesso!')
  } catch (error) {
    console.error('Erro ao salvar config:', error)
    alert('Erro ao salvar configuracoes')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadClients()
})
</script>

<style lang="scss" scoped>
.lead-scoring-page {
  max-width: 900px;
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

.scoring-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.config-card {
  background: var(--surface-primary);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  overflow: hidden;
}

.card-header {
  padding: 1.25rem;
  border-bottom: 1px solid var(--border-light);

  h3 {
    margin: 0 0 0.25rem 0;
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  p {
    margin: 0;
    font-size: 0.8125rem;
    color: var(--text-secondary);
  }
}

.card-body {
  padding: 1.25rem;
}

// Scoring Rules
.rules-grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.rule-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.875rem 1rem;
  background: var(--surface-secondary);
  border-radius: 8px;
}

.rule-info {
  display: flex;
  align-items: center;
  gap: 0.875rem;

  i {
    font-size: 1.25rem;
    color: var(--primary-color);
    width: 24px;
    text-align: center;
  }
}

.rule-text {
  display: flex;
  flex-direction: column;

  .rule-name {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary);
  }

  .rule-desc {
    font-size: 0.75rem;
    color: var(--text-secondary);
  }
}

.rule-input {
  display: flex;
  align-items: center;
  gap: 0.375rem;

  input {
    width: 60px;
    padding: 0.5rem;
    background: var(--surface-primary);
    border: 1px solid var(--border-light);
    border-radius: 6px;
    color: var(--text-primary);
    font-size: 0.875rem;
    text-align: center;

    &:focus {
      outline: none;
      border-color: var(--primary-color);
    }
  }

  .points-label {
    font-size: 0.75rem;
    color: var(--text-secondary);
  }
}

// Thresholds
.thresholds-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.threshold-item {
  padding: 1rem;
  border-radius: 8px;
  text-align: center;

  &.cold {
    background: #dbeafe;
    .threshold-header i { color: #3b82f6; }
  }

  &.warm {
    background: #fef3c7;
    .threshold-header i { color: #f59e0b; }
  }

  &.hot {
    background: #fee2e2;
    .threshold-header i { color: #ef4444; }
  }
}

.threshold-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;

  i {
    font-size: 1.25rem;
  }

  span {
    font-weight: 600;
    color: var(--text-primary);
  }
}

.threshold-range {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  font-size: 0.875rem;
  color: var(--text-secondary);

  input {
    width: 50px;
    padding: 0.375rem;
    background: white;
    border: 1px solid var(--border-light);
    border-radius: 4px;
    text-align: center;
    font-size: 0.875rem;

    &:focus {
      outline: none;
      border-color: var(--primary-color);
    }
  }
}

// Actions
.actions-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.action-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.875rem 1rem;
  background: var(--surface-secondary);
  border-radius: 8px;
}

.action-info {
  display: flex;
  align-items: center;
  gap: 0.875rem;

  i {
    font-size: 1.25rem;
    color: var(--primary-color);
    width: 24px;
    text-align: center;
  }
}

.action-text {
  display: flex;
  flex-direction: column;

  .action-name {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary);
  }

  .action-desc {
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

// Save
.save-section {
  display: flex;
  justify-content: flex-end;
  padding-top: 0.5rem;
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
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
    opacity: 0.7;
    cursor: not-allowed;
  }
}

@media (max-width: 640px) {
  .thresholds-grid {
    grid-template-columns: 1fr;
  }
}
</style>
