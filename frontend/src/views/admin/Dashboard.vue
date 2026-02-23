<template>
  <div class="dashboard-page">
    <!-- Welcome Section -->
    <div class="welcome-section">
      <div class="welcome-text">
        <h1>Bem-vindo ao Closefy</h1>
        <p>Seu agente de IA para vendas conversacionais</p>
      </div>
      <div class="welcome-actions">
        <button class="btn-primary" @click="$router.push('/admin/clientes')">
          <i class="mdi mdi-plus"></i>
          Novo Cliente
        </button>
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon clients">
          <i class="mdi mdi-domain"></i>
        </div>
        <div class="stat-data">
          <span class="stat-value">{{ stats.totalClients }}</span>
          <span class="stat-label">Clientes Ativos</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon ai">
          <i class="mdi mdi-robot"></i>
        </div>
        <div class="stat-data">
          <span class="stat-value">{{ stats.aiEnabled }}</span>
          <span class="stat-label">Com IA Ativa</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon conversations">
          <i class="mdi mdi-message-text-outline"></i>
        </div>
        <div class="stat-data">
          <span class="stat-value">{{ stats.conversations }}</span>
          <span class="stat-label">Conversas Hoje</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon conversion">
          <i class="mdi mdi-trending-up"></i>
        </div>
        <div class="stat-data">
          <span class="stat-value">{{ stats.conversionRate }}%</span>
          <span class="stat-label">Taxa de Conversao</span>
        </div>
      </div>
    </div>

    <!-- Main Content Grid -->
    <div class="content-grid">
      <!-- Quick Actions -->
      <div class="content-card">
        <div class="card-header">
          <h2>Acesso Rapido</h2>
        </div>
        <div class="quick-actions">
          <router-link to="/admin/analytics" class="action-item">
            <div class="action-icon analytics">
              <i class="mdi mdi-chart-line"></i>
            </div>
            <div class="action-info">
              <span class="action-title">Analytics</span>
              <span class="action-desc">Metricas e insights</span>
            </div>
            <i class="mdi mdi-chevron-right"></i>
          </router-link>

          <router-link to="/admin/ab-testing" class="action-item">
            <div class="action-icon testing">
              <i class="mdi mdi-ab-testing"></i>
            </div>
            <div class="action-info">
              <span class="action-title">A/B Testing</span>
              <span class="action-desc">Otimize seus prompts</span>
            </div>
            <i class="mdi mdi-chevron-right"></i>
          </router-link>

          <router-link to="/admin/integrations" class="action-item">
            <div class="action-icon integrations">
              <i class="mdi mdi-connection"></i>
            </div>
            <div class="action-info">
              <span class="action-title">Integracoes</span>
              <span class="action-desc">CRM e webhooks</span>
            </div>
            <i class="mdi mdi-chevron-right"></i>
          </router-link>

          <router-link to="/admin/lead-scoring" class="action-item">
            <div class="action-icon scoring">
              <i class="mdi mdi-trophy-outline"></i>
            </div>
            <div class="action-info">
              <span class="action-title">Lead Scoring</span>
              <span class="action-desc">Qualifique seus leads</span>
            </div>
            <i class="mdi mdi-chevron-right"></i>
          </router-link>
        </div>
      </div>

      <!-- Recent Clients -->
      <div class="content-card">
        <div class="card-header">
          <h2>Clientes Recentes</h2>
          <router-link to="/admin/clientes" class="link-btn">
            Ver todos
            <i class="mdi mdi-arrow-right"></i>
          </router-link>
        </div>

        <div v-if="loading" class="loading-state">
          <i class="mdi mdi-loading mdi-spin"></i>
        </div>

        <div v-else-if="recentClients.length > 0" class="clients-list">
          <router-link
            v-for="client in recentClients"
            :key="client.slug"
            :to="`/admin/cliente/${client.slug}`"
            class="client-item"
          >
            <div class="client-avatar" :style="{ background: getAvatarColor(client.name) }">
              {{ getInitials(client.name) }}
            </div>
            <div class="client-info">
              <span class="client-name">{{ client.name }}</span>
              <span class="client-slug">{{ client.slug }}</span>
            </div>
            <span class="client-status" :class="{ active: client.ai_enabled }">
              {{ client.ai_enabled ? 'Ativo' : 'Inativo' }}
            </span>
          </router-link>
        </div>

        <div v-else class="empty-state">
          <i class="mdi mdi-domain"></i>
          <p>Nenhum cliente cadastrado</p>
          <button class="btn-secondary-sm" @click="$router.push('/admin/clientes')">
            Adicionar Cliente
          </button>
        </div>
      </div>

      <!-- System Status -->
      <div class="content-card">
        <div class="card-header">
          <h2>Status do Sistema</h2>
          <span class="status-badge online">Operacional</span>
        </div>
        <div class="status-list">
          <div class="status-item">
            <div class="status-dot online"></div>
            <span class="status-name">API Backend</span>
            <span class="status-value">Online</span>
          </div>
          <div class="status-item">
            <div class="status-dot online"></div>
            <span class="status-name">Banco de Dados</span>
            <span class="status-value">Conectado</span>
          </div>
          <div class="status-item">
            <div class="status-dot online"></div>
            <span class="status-name">OpenAI API</span>
            <span class="status-value">Disponivel</span>
          </div>
          <div class="status-item">
            <div class="status-dot online"></div>
            <span class="status-name">Chatwoot</span>
            <span class="status-value">Sincronizado</span>
          </div>
        </div>
      </div>

      <!-- Features Overview -->
      <div class="content-card features-card">
        <div class="card-header">
          <h2>Recursos Enterprise</h2>
        </div>
        <div class="features-grid">
          <div class="feature-item">
            <i class="mdi mdi-shield-check"></i>
            <span>LGPD Compliance</span>
          </div>
          <div class="feature-item">
            <i class="mdi mdi-message-flash"></i>
            <span>Multi-channel</span>
          </div>
          <div class="feature-item">
            <i class="mdi mdi-brain"></i>
            <span>Sentiment Analysis</span>
          </div>
          <div class="feature-item">
            <i class="mdi mdi-lock"></i>
            <span>Encrypted Keys</span>
          </div>
          <div class="feature-item">
            <i class="mdi mdi-speedometer"></i>
            <span>Rate Limiting</span>
          </div>
          <div class="feature-item">
            <i class="mdi mdi-sync"></i>
            <span>CRM Sync</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { clientsApi } from '@/api/client'

const stats = ref({
  totalClients: 0,
  aiEnabled: 0,
  conversations: 0,
  conversionRate: 0
})

const recentClients = ref([])
const loading = ref(true)

const COLORS = [
  '#0066FF', '#10b981', '#f59e0b', '#ef4444',
  '#8b5cf6', '#06b6d4', '#ec4899', '#f97316'
]

const getAvatarColor = (name) => {
  let hash = 0
  for (let i = 0; i < (name || '').length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return COLORS[Math.abs(hash) % COLORS.length]
}

const getInitials = (name) => {
  if (!name) return '?'
  return name.split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase()
}

onMounted(async () => {
  try {
    const { data } = await clientsApi.list()
    const clientsArray = Object.values(data)
    recentClients.value = clientsArray.slice(0, 5)
    stats.value.totalClients = clientsArray.length
    stats.value.aiEnabled = clientsArray.filter(c => c.ai_enabled).length
    // Mock data for demo
    stats.value.conversations = Math.floor(Math.random() * 50) + 10
    stats.value.conversionRate = Math.floor(Math.random() * 20) + 15
  } catch (error) {
    console.error('Erro ao carregar dados:', error)
  } finally {
    loading.value = false
  }
})
</script>

<style lang="scss" scoped>
.dashboard-page {
  max-width: 1400px;
  margin: 0 auto;
}

// Welcome Section
.welcome-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.welcome-text {
  h1 {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 0.25rem 0;
  }

  p {
    color: var(--text-secondary);
    margin: 0;
    font-size: 0.875rem;
  }
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  background: var(--primary-color);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover {
    background: var(--primary-dark);
  }
}

// Stats Grid
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
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

  &.clients { background: var(--primary-color); }
  &.ai { background: #10b981; }
  &.conversations { background: #8b5cf6; }
  &.conversion { background: #f59e0b; }
}

.stat-data {
  display: flex;
  flex-direction: column;

  .stat-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.2;
  }

  .stat-label {
    font-size: 0.75rem;
    color: var(--text-secondary);
  }
}

// Content Grid
.content-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.content-card {
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

  h2 {
    margin: 0;
    font-size: 0.9375rem;
    font-weight: 600;
    color: var(--text-primary);
  }
}

.link-btn {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.8125rem;
  color: var(--primary-color);
  text-decoration: none;
  font-weight: 500;

  &:hover {
    text-decoration: underline;
  }
}

// Quick Actions
.quick-actions {
  padding: 0.5rem;
}

.action-item {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  padding: 0.875rem 1rem;
  border-radius: 8px;
  text-decoration: none;
  color: inherit;
  transition: all 0.15s ease;

  &:hover {
    background: var(--surface-secondary);

    .mdi-chevron-right {
      transform: translateX(4px);
      color: var(--primary-color);
    }
  }
}

.action-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  i {
    font-size: 1.25rem;
    color: white;
  }

  &.analytics { background: var(--primary-color); }
  &.testing { background: #8b5cf6; }
  &.integrations { background: #10b981; }
  &.scoring { background: #f59e0b; }
}

.action-info {
  flex: 1;
  display: flex;
  flex-direction: column;

  .action-title {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary);
  }

  .action-desc {
    font-size: 0.75rem;
    color: var(--text-secondary);
  }
}

.action-item .mdi-chevron-right {
  color: var(--text-secondary);
  transition: all 0.15s ease;
}

// Clients List
.clients-list {
  padding: 0.5rem;
}

.client-item {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  text-decoration: none;
  color: inherit;
  transition: all 0.15s ease;

  &:hover {
    background: var(--surface-secondary);
  }
}

.client-avatar {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8125rem;
  font-weight: 600;
  color: white;
  flex-shrink: 0;
}

.client-info {
  flex: 1;
  display: flex;
  flex-direction: column;

  .client-name {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary);
  }

  .client-slug {
    font-size: 0.75rem;
    color: var(--text-secondary);
  }
}

.client-status {
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  background: var(--surface-secondary);
  color: var(--text-secondary);

  &.active {
    background: #dcfce7;
    color: #166534;
  }
}

.loading-state {
  display: flex;
  justify-content: center;
  padding: 2rem;
  color: var(--text-secondary);

  i {
    font-size: 1.5rem;
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem;
  text-align: center;
  color: var(--text-secondary);

  i {
    font-size: 2rem;
    opacity: 0.5;
    margin-bottom: 0.5rem;
  }

  p {
    margin: 0 0 1rem 0;
    font-size: 0.875rem;
  }
}

.btn-secondary-sm {
  padding: 0.5rem 1rem;
  background: var(--surface-secondary);
  border: none;
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;

  &:hover {
    background: var(--surface-tertiary);
  }
}

// Status List
.status-badge {
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;

  &.online {
    background: #dcfce7;
    color: #166534;
  }
}

.status-list {
  padding: 1rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: var(--surface-secondary);
  border-radius: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;

  &.online {
    background: #10b981;
    box-shadow: 0 0 6px #10b981;
  }

  &.offline {
    background: #ef4444;
  }
}

.status-name {
  flex: 1;
  font-size: 0.8125rem;
  color: var(--text-primary);
}

.status-value {
  font-size: 0.75rem;
  color: var(--success-color);
  font-weight: 500;
}

// Features Card
.features-card {
  grid-column: span 2;
}

.features-grid {
  padding: 1.25rem;
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 1rem;
}

.feature-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  background: var(--surface-secondary);
  border-radius: 8px;
  text-align: center;

  i {
    font-size: 1.5rem;
    color: var(--primary-color);
  }

  span {
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--text-primary);
  }
}

// Responsive
@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .content-grid {
    grid-template-columns: 1fr;
  }

  .features-card {
    grid-column: span 1;
  }

  .features-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 640px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
