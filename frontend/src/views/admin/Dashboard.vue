<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1>Dashboard</h1>
        <p class="subtitle">Bem-vindo ao painel de controle</p>
      </div>
      <div class="actions">
        <va-button @click="$router.push('/admin/clientes')">
          <i class="mdi mdi-plus"></i>
          Novo Cliente
        </va-button>
      </div>
    </div>

    <!-- Bento Grid Stats -->
    <div class="bento-grid mb-6">
      <!-- Hero Card - Total Clientes -->
      <div class="card stat-card stat-card-hero bento-item span-2 animate-in stagger-1">
        <div class="stat-icon">
          <i class="mdi mdi-account-group"></i>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ stats.totalClients }}</span>
          <span class="stat-label">Total de Clientes</span>
          <span v-if="stats.totalClients > 0" class="stat-trend trend-up">
            <i class="mdi mdi-arrow-up"></i>
            Ativo
          </span>
        </div>
        <div class="hero-decoration"></div>
      </div>

      <!-- IA Ativa -->
      <div class="card stat-card stat-success bento-item animate-in stagger-2">
        <div class="stat-icon icon-success">
          <i class="mdi mdi-flash"></i>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ stats.aiEnabled }}</span>
          <span class="stat-label">IA Ativa</span>
        </div>
      </div>

      <!-- Produtos -->
      <div class="card stat-card stat-purple bento-item animate-in stagger-3">
        <div class="stat-icon icon-purple">
          <i class="mdi mdi-package-variant"></i>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ stats.totalProducts }}</span>
          <span class="stat-label">Produtos</span>
        </div>
      </div>

      <!-- Quick Actions Card -->
      <div class="card bento-item span-2 animate-in stagger-4">
        <div class="card-header">
          <h2>Acesso Rapido</h2>
        </div>
        <div class="quick-actions">
          <router-link to="/admin/clientes" class="quick-action-item">
            <div class="action-icon" style="background: linear-gradient(135deg, #6366f1, #8b5cf6);">
              <i class="mdi mdi-domain"></i>
            </div>
            <div class="action-text">
              <span class="action-title">Clientes</span>
              <span class="action-desc">Gerenciar clientes</span>
            </div>
            <i class="mdi mdi-chevron-right"></i>
          </router-link>
          <router-link v-if="recentClients.length > 0" :to="`/admin/cliente/${recentClients[0].slug}`" class="quick-action-item">
            <div class="action-icon" style="background: linear-gradient(135deg, #10b981, #34d399);">
              <i class="mdi mdi-robot"></i>
            </div>
            <div class="action-text">
              <span class="action-title">Config IA</span>
              <span class="action-desc">Configurar agente</span>
            </div>
            <i class="mdi mdi-chevron-right"></i>
          </router-link>
          <router-link to="/admin/schemas" class="quick-action-item">
            <div class="action-icon" style="background: linear-gradient(135deg, #f59e0b, #fbbf24);">
              <i class="mdi mdi-shape"></i>
            </div>
            <div class="action-text">
              <span class="action-title">Schemas</span>
              <span class="action-desc">Tipos de produto</span>
            </div>
            <i class="mdi mdi-chevron-right"></i>
          </router-link>
        </div>
      </div>

      <!-- Clientes Recentes -->
      <div class="card bento-item span-2 row-2 animate-in stagger-6">
        <div class="card-header">
          <h2>Clientes Recentes</h2>
          <router-link to="/admin/clientes">
            <va-button preset="plain" size="small">
              Ver todos
              <i class="mdi mdi-arrow-right"></i>
            </va-button>
          </router-link>
        </div>

        <!-- Loading Skeleton -->
        <div v-if="loading" class="clients-list">
          <div v-for="i in 4" :key="i" class="client-item skeleton-item">
            <div class="skeleton skeleton-avatar"></div>
            <div class="flex-1">
              <div class="skeleton skeleton-text" style="width: 60%; margin-bottom: 0.5rem;"></div>
              <div class="skeleton skeleton-text" style="width: 40%;"></div>
            </div>
          </div>
        </div>

        <!-- Clients List -->
        <div v-else-if="recentClients.length > 0" class="clients-list">
          <router-link v-for="client in recentClients" :key="client.slug"
                       :to="`/admin/cliente/${client.slug}`"
                       class="client-item">
            <div class="client-avatar" :style="{ background: getAvatarGradient(client.name) }">
              {{ getInitials(client.name) }}
            </div>
            <div class="client-info">
              <span class="client-name">{{ client.name }}</span>
              <span class="client-slug">{{ client.slug }}</span>
            </div>
            <va-chip :color="client.ai_enabled ? 'success' : 'secondary'" size="small">
              {{ client.ai_enabled ? 'IA' : 'Off' }}
            </va-chip>
          </router-link>
        </div>

        <!-- Empty State -->
        <div v-else class="empty-state">
          <i class="mdi mdi-account-group"></i>
          <h3>Nenhum cliente</h3>
          <p>Comece adicionando seu primeiro cliente</p>
          <va-button size="small" @click="$router.push('/admin/clientes')">
            <i class="mdi mdi-plus"></i>
            Adicionar Cliente
          </va-button>
        </div>
      </div>

      <!-- Status Card -->
      <div class="card bento-item span-2 animate-in" style="animation-delay: 0.35s;">
        <div class="card-header">
          <h2>Status do Sistema</h2>
          <span class="badge badge-success">Online</span>
        </div>
        <div class="status-grid">
          <div class="status-item">
            <div class="status-indicator online"></div>
            <span class="status-name">API Backend</span>
            <span class="status-value">Operacional</span>
          </div>
          <div class="status-item">
            <div class="status-indicator online"></div>
            <span class="status-name">Banco de Dados</span>
            <span class="status-value">Conectado</span>
          </div>
          <div class="status-item">
            <div class="status-indicator online"></div>
            <span class="status-name">Chatwoot</span>
            <span class="status-value">Sincronizado</span>
          </div>
          <div class="status-item">
            <div class="status-indicator online"></div>
            <span class="status-name">OpenAI</span>
            <span class="status-value">Disponivel</span>
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
  totalProducts: 0
})

const recentClients = ref([])
const loading = ref(true)

const GRADIENTS = [
  'linear-gradient(135deg, #6366f1, #8b5cf6)',
  'linear-gradient(135deg, #10b981, #34d399)',
  'linear-gradient(135deg, #f59e0b, #fbbf24)',
  'linear-gradient(135deg, #ef4444, #f87171)',
  'linear-gradient(135deg, #ec4899, #f472b6)',
  'linear-gradient(135deg, #06b6d4, #22d3ee)',
  'linear-gradient(135deg, #8b5cf6, #a78bfa)',
  'linear-gradient(135deg, #f97316, #fb923c)'
]

const getAvatarGradient = (name) => {
  let hash = 0
  for (let i = 0; i < (name || '').length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return GRADIENTS[Math.abs(hash) % GRADIENTS.length]
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
  } catch (error) {
    console.error('Erro ao carregar dados:', error)
  } finally {
    loading.value = false
  }
})
</script>

<style lang="scss" scoped>
.hero-decoration {
  position: absolute;
  top: -50%;
  right: -20%;
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, rgba(255,255,255,0.2) 0%, transparent 70%);
  border-radius: 50%;
  pointer-events: none;
}

.stat-card-hero {
  position: relative;
  min-height: 160px;

  .stat-value {
    font-size: 3rem !important;
  }
}

// Quick Actions
.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.quick-action-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: var(--surface-light);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-normal);
  text-decoration: none;
  color: inherit;

  &:hover {
    background: var(--surface-hover);
    transform: translateX(4px);

    .mdi-chevron-right {
      transform: translateX(4px);
      color: var(--primary-color);
    }
  }

  .action-icon {
    width: 44px;
    height: 44px;
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;

    i {
      font-size: 1.25rem;
      color: white;
    }
  }

  .action-text {
    flex: 1;
    display: flex;
    flex-direction: column;

    .action-title {
      font-weight: 600;
      color: var(--text-dark);
    }

    .action-desc {
      font-size: 0.8rem;
      color: var(--text-muted);
    }
  }

  .mdi-chevron-right {
    color: var(--text-muted);
    transition: all var(--transition-normal);
  }
}

// Clients List
.clients-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.client-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.875rem 1rem;
  border-radius: var(--radius-md);
  transition: all var(--transition-normal);
  text-decoration: none;
  color: inherit;

  &:hover {
    background: var(--surface-light);
  }

  .client-avatar {
    width: 40px;
    height: 40px;
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.875rem;
    font-weight: 700;
    color: white;
    flex-shrink: 0;
  }

  .client-info {
    flex: 1;
    display: flex;
    flex-direction: column;

    .client-name {
      font-weight: 600;
      color: var(--text-dark);
      font-size: 0.9rem;
    }

    .client-slug {
      font-size: 0.75rem;
      color: var(--text-muted);
    }
  }
}

.skeleton-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.875rem 1rem;
}

// Status Grid
.status-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--surface-light);
  border-radius: var(--radius-md);

  .status-indicator {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;

    &.online {
      background: var(--success-color);
      box-shadow: 0 0 8px var(--success-color);
      animation: pulse 2s infinite;
    }

    &.offline {
      background: var(--danger-color);
    }

    &.warning {
      background: var(--warning-color);
    }
  }

  .status-name {
    flex: 1;
    font-size: 0.85rem;
    color: var(--text-secondary);
  }

  .status-value {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--success-color);
  }
}

// Responsive
@media (max-width: 1200px) {
  .stat-card-hero .stat-value {
    font-size: 2.5rem !important;
  }

  .status-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .stat-card-hero {
    min-height: 140px;

    .stat-value {
      font-size: 2rem !important;
    }
  }
}
</style>
