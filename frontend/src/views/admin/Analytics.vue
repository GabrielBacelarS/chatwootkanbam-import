<template>
  <div class="analytics-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">Analytics</h1>
        <p class="page-subtitle">Metricas e insights de conversas</p>
      </div>
      <div class="header-right">
        <select v-model="selectedClient" class="client-select" @change="loadAnalytics">
          <option value="">Selecione um cliente</option>
          <option v-for="client in clients" :key="client.slug" :value="client.slug">
            {{ client.name }}
          </option>
        </select>
        <select v-model="dateRange" class="date-select" @change="loadAnalytics">
          <option value="7">Ultimos 7 dias</option>
          <option value="30">Ultimos 30 dias</option>
          <option value="90">Ultimos 90 dias</option>
        </select>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <i class="mdi mdi-loading mdi-spin"></i>
      <span>Carregando metricas...</span>
    </div>

    <!-- Empty State -->
    <div v-else-if="!selectedClient" class="empty-state">
      <div class="empty-icon">
        <i class="mdi mdi-chart-line"></i>
      </div>
      <h3>Selecione um cliente</h3>
      <p>Escolha um cliente para visualizar as metricas</p>
    </div>

    <!-- Analytics Content -->
    <div v-else class="analytics-content">
      <!-- Quick Summary -->
      <div class="summary-grid">
        <div class="summary-card">
          <div class="summary-header">
            <i class="mdi mdi-calendar-today"></i>
            <span>Hoje</span>
          </div>
          <div class="summary-stats">
            <div class="summary-stat">
              <span class="stat-value">{{ summary.today?.conversations || 0 }}</span>
              <span class="stat-label">conversas</span>
            </div>
            <div class="summary-stat">
              <span class="stat-value">{{ summary.today?.conversions || 0 }}</span>
              <span class="stat-label">conversoes</span>
            </div>
          </div>
        </div>
        <div class="summary-card">
          <div class="summary-header">
            <i class="mdi mdi-calendar-minus"></i>
            <span>Ontem</span>
          </div>
          <div class="summary-stats">
            <div class="summary-stat">
              <span class="stat-value">{{ summary.yesterday?.conversations || 0 }}</span>
              <span class="stat-label">conversas</span>
            </div>
            <div class="summary-stat">
              <span class="stat-value">{{ summary.yesterday?.conversions || 0 }}</span>
              <span class="stat-label">conversoes</span>
            </div>
          </div>
        </div>
        <div class="summary-card">
          <div class="summary-header">
            <i class="mdi mdi-calendar-week"></i>
            <span>Esta Semana</span>
          </div>
          <div class="summary-stats">
            <div class="summary-stat">
              <span class="stat-value">{{ summary.week?.conversations || 0 }}</span>
              <span class="stat-label">conversas</span>
            </div>
            <div class="summary-stat">
              <span class="stat-value">{{ summary.week?.conversions || 0 }}</span>
              <span class="stat-label">conversoes</span>
            </div>
          </div>
        </div>
        <div class="summary-card">
          <div class="summary-header">
            <i class="mdi mdi-calendar-month"></i>
            <span>Este Mes</span>
          </div>
          <div class="summary-stats">
            <div class="summary-stat">
              <span class="stat-value">{{ summary.month?.conversations || 0 }}</span>
              <span class="stat-label">conversas</span>
            </div>
            <div class="summary-stat">
              <span class="stat-value">{{ summary.month?.conversions || 0 }}</span>
              <span class="stat-label">conversoes</span>
            </div>
          </div>
        </div>
      </div>

      <!-- KPI Cards -->
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-icon conversations">
            <i class="mdi mdi-message-text-outline"></i>
          </div>
          <div class="kpi-data">
            <span class="kpi-value">{{ overview.conversations?.total || 0 }}</span>
            <span class="kpi-label">Conversas</span>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-icon conversions">
            <i class="mdi mdi-check-circle-outline"></i>
          </div>
          <div class="kpi-data">
            <span class="kpi-value">{{ formatPercent(overview.rates?.conversion) }}</span>
            <span class="kpi-label">Taxa de Conversao</span>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-icon tokens">
            <i class="mdi mdi-chip"></i>
          </div>
          <div class="kpi-data">
            <span class="kpi-value">{{ formatNumber(overview.tokens?.total) }}</span>
            <span class="kpi-label">Tokens Usados</span>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-icon cost">
            <i class="mdi mdi-currency-usd"></i>
          </div>
          <div class="kpi-data">
            <span class="kpi-value">${{ formatCost(overview.costs?.total) }}</span>
            <span class="kpi-label">Custo Total</span>
          </div>
        </div>
      </div>

      <!-- Charts Row -->
      <div class="charts-row">
        <!-- Conversations Chart -->
        <div class="chart-card">
          <div class="chart-header">
            <h3>Conversas por Dia</h3>
          </div>
          <div class="chart-body">
            <div class="simple-chart">
              <div
                v-for="(day, index) in dailyMetrics"
                :key="index"
                class="chart-bar"
                :style="{ height: getBarHeight(day.conversations) + '%' }"
                :title="`${day.date}: ${day.conversations} conversas`"
              >
                <span class="bar-value">{{ day.conversations }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Funnel Chart -->
        <div class="chart-card">
          <div class="chart-header">
            <h3>Funil de Conversao</h3>
          </div>
          <div class="chart-body">
            <div class="funnel">
              <div
                v-for="(stage, index) in funnel"
                :key="index"
                class="funnel-stage"
                :style="{ width: getFunnelWidth(stage.count) + '%' }"
              >
                <span class="stage-label">{{ stage.label }}</span>
                <span class="stage-count">{{ stage.count }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Products & Costs Row -->
      <div class="charts-row">
        <!-- Popular Products -->
        <div class="chart-card">
          <div class="chart-header">
            <h3>Produtos Mais Consultados</h3>
          </div>
          <div class="chart-body">
            <div v-if="popularProducts.length === 0" class="no-data-small">
              <i class="mdi mdi-package-variant"></i>
              <span>Nenhum produto consultado</span>
            </div>
            <div v-else class="products-list">
              <div v-for="(product, index) in popularProducts" :key="index" class="product-item">
                <div class="product-rank">{{ index + 1 }}</div>
                <div class="product-info">
                  <span class="product-name">{{ product.name }}</span>
                  <span class="product-category">{{ product.category || 'Sem categoria' }}</span>
                </div>
                <div class="product-stats">
                  <div class="product-stat">
                    <span class="stat-value">{{ product.views || 0 }}</span>
                    <span class="stat-label">views</span>
                  </div>
                  <div class="product-stat">
                    <span class="stat-value">{{ formatPercent(product.interest_rate) }}</span>
                    <span class="stat-label">interesse</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Cost Breakdown -->
        <div class="chart-card">
          <div class="chart-header">
            <h3>Breakdown de Custos</h3>
          </div>
          <div class="chart-body">
            <div class="costs-breakdown">
              <div class="cost-item">
                <div class="cost-info">
                  <i class="mdi mdi-calendar-today"></i>
                  <span>Hoje</span>
                </div>
                <span class="cost-value">${{ formatCost(costs.today?.total) }}</span>
              </div>
              <div class="cost-item">
                <div class="cost-info">
                  <i class="mdi mdi-calendar-week"></i>
                  <span>Esta Semana</span>
                </div>
                <span class="cost-value">${{ formatCost(costs.week?.total) }}</span>
              </div>
              <div class="cost-item">
                <div class="cost-info">
                  <i class="mdi mdi-calendar-month"></i>
                  <span>Este Mes</span>
                </div>
                <span class="cost-value">${{ formatCost(costs.month?.total) }}</span>
              </div>
              <div class="cost-item highlight">
                <div class="cost-info">
                  <i class="mdi mdi-chart-timeline-variant"></i>
                  <span>Projecao Mensal</span>
                </div>
                <span class="cost-value">${{ formatCost(costs.projection?.monthly) }}</span>
              </div>
              <div class="cost-per-conv">
                <span class="label">Custo medio por conversa:</span>
                <span class="value">${{ formatCost(costs.average_per_conversation) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Details Section -->
      <div class="details-section">
        <div class="section-header">
          <h3>Conversas Recentes</h3>
          <button class="btn-export" @click="exportData">
            <i class="mdi mdi-download"></i>
            Exportar
          </button>
        </div>
        <div class="conversations-table">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Contato</th>
                <th>Canal</th>
                <th>Mensagens</th>
                <th>Tokens</th>
                <th>Resultado</th>
                <th>Data</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="conv in conversations" :key="conv.conversation_id">
                <td class="conv-id">#{{ conv.conversation_id }}</td>
                <td>{{ conv.contact_name || 'Anonimo' }}</td>
                <td>
                  <span class="channel-badge" :class="conv.channel">
                    {{ conv.channel || 'web' }}
                  </span>
                </td>
                <td>{{ conv.total_messages || 0 }}</td>
                <td>{{ formatNumber(conv.tokens_total) }}</td>
                <td>
                  <span class="outcome-badge" :class="conv.outcome || 'pending'">
                    {{ getOutcomeLabel(conv.outcome) }}
                  </span>
                </td>
                <td>{{ formatDate(conv.started_at) }}</td>
              </tr>
              <tr v-if="conversations.length === 0">
                <td colspan="7" class="no-data">Nenhuma conversa encontrada</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api, { clientsApi } from '@/api/client'

const loading = ref(false)
const clients = ref([])
const selectedClient = ref('')
const dateRange = ref('30')

const overview = ref({})
const dailyMetrics = ref([])
const funnel = ref([])
const conversations = ref([])
const summary = ref({})
const popularProducts = ref([])
const costs = ref({})

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

const loadAnalytics = async () => {
  if (!selectedClient.value) return

  loading.value = true
  try {
    const [overviewRes, dailyRes, funnelRes, conversationsRes, summaryRes, productsRes, costsRes] = await Promise.all([
      api.get(`/analytics/${selectedClient.value}/overview?days=${dateRange.value}`),
      api.get(`/analytics/${selectedClient.value}/daily?days=${dateRange.value}`),
      api.get(`/analytics/${selectedClient.value}/funnel?days=${dateRange.value}`),
      api.get(`/analytics/${selectedClient.value}/conversations?limit=20`),
      api.get(`/analytics/${selectedClient.value}/summary`),
      api.get(`/analytics/${selectedClient.value}/products?days=${dateRange.value}&limit=5`),
      api.get(`/analytics/${selectedClient.value}/costs?days=${dateRange.value}`)
    ])

    overview.value = overviewRes.data
    dailyMetrics.value = dailyRes.data.daily || []
    funnel.value = funnelRes.data.funnel || []
    conversations.value = conversationsRes.data.conversations || []
    summary.value = summaryRes.data || {}
    popularProducts.value = productsRes.data.products || []
    costs.value = costsRes.data || {}
  } catch (error) {
    console.error('Erro ao carregar analytics:', error)
  } finally {
    loading.value = false
  }
}

const exportData = async () => {
  if (!selectedClient.value) return

  try {
    const response = await api.get(`/analytics/${selectedClient.value}/export`)
    const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `analytics-${selectedClient.value}-${new Date().toISOString().split('T')[0]}.json`
    a.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Erro ao exportar:', error)
  }
}

const formatNumber = (num) => {
  if (!num) return '0'
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toString()
}

const formatPercent = (num) => {
  if (!num) return '0%'
  return (num * 100).toFixed(1) + '%'
}

const formatCost = (num) => {
  if (!num) return '0.00'
  return num.toFixed(2)
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

const getOutcomeLabel = (outcome) => {
  const labels = {
    converted: 'Convertido',
    transferred: 'Transferido',
    abandoned: 'Abandonado',
    pending: 'Em andamento'
  }
  return labels[outcome] || 'Em andamento'
}

const getBarHeight = (value) => {
  if (!dailyMetrics.value.length) return 0
  const max = Math.max(...dailyMetrics.value.map(d => d.conversations || 0))
  return max > 0 ? (value / max) * 100 : 0
}

const getFunnelWidth = (value) => {
  if (!funnel.value.length) return 0
  const max = funnel.value[0]?.count || 1
  return Math.max((value / max) * 100, 20)
}

onMounted(() => {
  loadClients()
})
</script>

<style lang="scss" scoped>
.analytics-page {
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

.client-select,
.date-select {
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

// Loading & Empty States
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

.loading-state i {
  color: var(--primary-color);
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

// Quick Summary
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.summary-card {
  background: var(--surface-primary);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  padding: 1rem;
}

.summary-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: 500;

  i {
    font-size: 1rem;
    color: var(--primary-color);
  }
}

.summary-stats {
  display: flex;
  gap: 1.5rem;
}

.summary-stat {
  display: flex;
  flex-direction: column;

  .stat-value {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text-primary);
  }

  .stat-label {
    font-size: 0.6875rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }
}

// KPI Cards
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.kpi-card {
  background: var(--surface-primary);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  padding: 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.kpi-icon {
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

  &.conversations { background: var(--primary-color); }
  &.conversions { background: var(--success-color); }
  &.tokens { background: var(--warning-color); }
  &.cost { background: var(--info-color); }
}

.kpi-data {
  display: flex;
  flex-direction: column;

  .kpi-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.2;
  }

  .kpi-label {
    font-size: 0.75rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
}

// Charts
.charts-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.chart-card {
  background: var(--surface-primary);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  overflow: hidden;
}

.chart-header {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border-light);

  h3 {
    margin: 0;
    font-size: 0.9375rem;
    font-weight: 600;
    color: var(--text-primary);
  }
}

.chart-body {
  padding: 1.25rem;
  min-height: 200px;
}

.simple-chart {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 180px;
}

.chart-bar {
  flex: 1;
  background: var(--primary-color);
  border-radius: 4px 4px 0 0;
  min-height: 4px;
  position: relative;
  transition: height 0.3s ease;

  &:hover {
    background: var(--primary-dark);
  }

  .bar-value {
    position: absolute;
    top: -20px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 0.625rem;
    color: var(--text-secondary);
    opacity: 0;
  }

  &:hover .bar-value {
    opacity: 1;
  }
}

// Funnel
.funnel {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.funnel-stage {
  background: var(--primary-color);
  border-radius: 4px;
  padding: 0.75rem 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: white;
  min-width: 20%;
  transition: width 0.3s ease;

  &:nth-child(2) { background: #3b82f6; }
  &:nth-child(3) { background: #6366f1; }
  &:nth-child(4) { background: #8b5cf6; }
  &:nth-child(5) { background: #10b981; }

  .stage-label {
    font-size: 0.8125rem;
    font-weight: 500;
  }

  .stage-count {
    font-weight: 700;
  }
}

// Products List
.products-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.product-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: var(--surface-secondary);
  border-radius: 8px;
}

.product-rank {
  width: 28px;
  height: 28px;
  background: var(--primary-color);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 700;
  flex-shrink: 0;
}

.product-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;

  .product-name {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .product-category {
    font-size: 0.75rem;
    color: var(--text-secondary);
  }
}

.product-stats {
  display: flex;
  gap: 1rem;
}

.product-stat {
  display: flex;
  flex-direction: column;
  align-items: flex-end;

  .stat-value {
    font-size: 0.875rem;
    font-weight: 700;
    color: var(--text-primary);
  }

  .stat-label {
    font-size: 0.625rem;
    color: var(--text-secondary);
    text-transform: uppercase;
  }
}

.no-data-small {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  color: var(--text-secondary);
  text-align: center;

  i {
    font-size: 2rem;
    margin-bottom: 0.5rem;
    opacity: 0.5;
  }

  span {
    font-size: 0.875rem;
  }
}

// Cost Breakdown
.costs-breakdown {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.cost-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: var(--surface-secondary);
  border-radius: 8px;

  &.highlight {
    background: var(--primary-color);
    color: white;

    .cost-info i,
    .cost-info span {
      color: rgba(255, 255, 255, 0.9);
    }

    .cost-value {
      color: white;
      font-size: 1.125rem;
    }
  }
}

.cost-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;

  i {
    font-size: 1rem;
    color: var(--primary-color);
  }

  span {
    font-size: 0.875rem;
    color: var(--text-primary);
  }
}

.cost-value {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
}

.cost-per-conv {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  margin-top: 0.5rem;
  border-top: 1px solid var(--border-light);

  .label {
    font-size: 0.8125rem;
    color: var(--text-secondary);
  }

  .value {
    font-size: 1rem;
    font-weight: 700;
    color: var(--success-color);
  }
}

// Details Section
.details-section {
  background: var(--surface-primary);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  overflow: hidden;
}

.section-header {
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

.btn-export {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: var(--surface-secondary);
  border: none;
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover {
    background: var(--surface-tertiary);
  }
}

.conversations-table {
  overflow-x: auto;

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th, td {
    padding: 0.875rem 1rem;
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

  .conv-id {
    font-family: monospace;
    color: var(--text-secondary);
  }

  .no-data {
    text-align: center;
    color: var(--text-secondary);
    padding: 2rem;
  }
}

.channel-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: capitalize;
  background: var(--surface-secondary);
  color: var(--text-secondary);

  &.whatsapp { background: #dcfce7; color: #166534; }
  &.web { background: #dbeafe; color: #1e40af; }
  &.sms { background: #fef3c7; color: #92400e; }
}

.outcome-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;

  &.converted { background: #dcfce7; color: #166534; }
  &.transferred { background: #dbeafe; color: #1e40af; }
  &.abandoned { background: #fee2e2; color: #991b1b; }
  &.pending { background: #fef3c7; color: #92400e; }
}

// Responsive
@media (max-width: 1024px) {
  .summary-grid,
  .kpi-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .charts-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .summary-grid,
  .kpi-grid {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
  }

  .header-right {
    width: 100%;

    select {
      flex: 1;
    }
  }

  .product-stats {
    flex-direction: column;
    gap: 0.25rem;
  }
}
</style>
