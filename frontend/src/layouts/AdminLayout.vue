<template>
  <div class="admin-layout" :class="{ 'sidebar-collapsed': sidebarCollapsed, 'mobile-open': mobileMenuOpen }">
    <!-- Mobile Overlay -->
    <div v-if="mobileMenuOpen" class="mobile-overlay" @click="mobileMenuOpen = false"></div>

    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo">
          <div class="logo-icon">
            <i class="mdi mdi-robot"></i>
          </div>
          <span class="logo-text" v-show="!sidebarCollapsed">Closefy</span>
        </div>
        <button
          class="collapse-btn hide-mobile"
          @click="toggleSidebar"
          :aria-label="sidebarCollapsed ? 'Expandir menu' : 'Recolher menu'"
        >
          <i :class="sidebarCollapsed ? 'mdi mdi-chevron-right' : 'mdi mdi-chevron-left'"></i>
        </button>
      </div>

      <nav class="sidebar-nav">
        <!-- Principal -->
        <div class="nav-section">
          <span class="nav-label" v-show="!sidebarCollapsed">Principal</span>

          <router-link to="/admin/dashboard" class="nav-item" :title="sidebarCollapsed ? 'Dashboard' : undefined">
            <i class="mdi mdi-view-dashboard-outline"></i>
            <span v-show="!sidebarCollapsed">Dashboard</span>
          </router-link>

          <router-link to="/admin/analytics" class="nav-item" :title="sidebarCollapsed ? 'Analytics' : undefined">
            <i class="mdi mdi-chart-line"></i>
            <span v-show="!sidebarCollapsed">Analytics</span>
          </router-link>

          <router-link to="/admin/clientes" class="nav-item" :title="sidebarCollapsed ? 'Clientes' : undefined">
            <i class="mdi mdi-domain"></i>
            <span v-show="!sidebarCollapsed">Clientes</span>
          </router-link>
        </div>

        <!-- Inteligência -->
        <div class="nav-section">
          <span class="nav-label" v-show="!sidebarCollapsed">Inteligência</span>

          <router-link to="/admin/ab-testing" class="nav-item" :title="sidebarCollapsed ? 'A/B Testing' : undefined">
            <i class="mdi mdi-ab-testing"></i>
            <span v-show="!sidebarCollapsed">A/B Testing</span>
          </router-link>

          <router-link to="/admin/lead-scoring" class="nav-item" :title="sidebarCollapsed ? 'Lead Scoring' : undefined">
            <i class="mdi mdi-trophy-outline"></i>
            <span v-show="!sidebarCollapsed">Lead Scoring</span>
          </router-link>
        </div>

        <!-- Integracoes -->
        <div class="nav-section">
          <span class="nav-label" v-show="!sidebarCollapsed">Integracoes</span>

          <router-link to="/admin/integrations" class="nav-item" :title="sidebarCollapsed ? 'CRM' : undefined">
            <i class="mdi mdi-connection"></i>
            <span v-show="!sidebarCollapsed">CRM</span>
          </router-link>

          <router-link to="/admin/schemas" class="nav-item" :title="sidebarCollapsed ? 'Schemas' : undefined">
            <i class="mdi mdi-shape-outline"></i>
            <span v-show="!sidebarCollapsed">Schemas</span>
          </router-link>
        </div>

        <!-- Configuracoes -->
        <div class="nav-section">
          <span class="nav-label" v-show="!sidebarCollapsed">Configuracoes</span>

          <router-link to="/admin/compliance" class="nav-item" :title="sidebarCollapsed ? 'Compliance' : undefined">
            <i class="mdi mdi-shield-check-outline"></i>
            <span v-show="!sidebarCollapsed">LGPD</span>
          </router-link>
        </div>
      </nav>

      <div class="sidebar-footer">
        <!-- User Card -->
        <div class="user-card">
          <div class="user-avatar">
            <i class="mdi mdi-account"></i>
          </div>
          <div class="user-info" v-show="!sidebarCollapsed">
            <span class="user-name">{{ userEmail }}</span>
            <span class="user-role">Administrador</span>
          </div>
          <button
            v-show="!sidebarCollapsed"
            class="logout-btn"
            @click="handleLogout"
            title="Sair"
          >
            <i class="mdi mdi-logout"></i>
          </button>
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="main-content">
      <!-- Top Bar -->
      <header class="topbar">
        <div class="topbar-left">
          <button
            class="menu-toggle show-mobile"
            @click="mobileMenuOpen = !mobileMenuOpen"
            aria-label="Menu"
          >
            <i :class="mobileMenuOpen ? 'mdi mdi-close' : 'mdi mdi-menu'"></i>
          </button>
          <div class="topbar-logo show-mobile">
            <div class="logo-icon small">
              <i class="mdi mdi-robot"></i>
            </div>
            <span>Closefy</span>
          </div>
          <h1 class="page-title hide-mobile">{{ pageTitle }}</h1>
        </div>
        <div class="topbar-right">
          <button class="topbar-btn" title="Notificacoes">
            <i class="mdi mdi-bell-outline"></i>
            <span class="notification-badge">3</span>
          </button>
          <button class="topbar-btn" @click="toggleTheme" :title="isDark ? 'Modo claro' : 'Modo escuro'">
            <i :class="isDark ? 'mdi mdi-white-balance-sunny' : 'mdi mdi-weather-night'"></i>
          </button>
        </div>
      </header>

      <div class="content-wrapper">
        <ToastNotification />
        <ConfirmDialog />
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useColors } from 'vuestic-ui'
import { useAuthStore } from '@/stores/auth'
import ToastNotification from '@/components/ToastNotification.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { applyPreset } = useColors()

const userEmail = computed(() => auth.email || 'Admin')

function handleLogout() {
  auth.logout()
  router.push('/login')
}

const sidebarCollapsed = ref(false)
const mobileMenuOpen = ref(false)
const isDark = ref(false)

const pageTitles = {
  '/admin/dashboard': 'Dashboard',
  '/admin/analytics': 'Analytics',
  '/admin/clientes': 'Clientes',
  '/admin/ab-testing': 'A/B Testing',
  '/admin/lead-scoring': 'Lead Scoring',
  '/admin/integrations': 'Integracoes CRM',
  '/admin/schemas': 'Schemas',
  '/admin/compliance': 'Compliance LGPD'
}

const pageTitle = computed(() => {
  return pageTitles[route.path] || 'Closefy'
})

const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem('sidebar_collapsed', sidebarCollapsed.value)
}

const toggleTheme = () => {
  isDark.value = !isDark.value
  document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
  applyPreset(isDark.value ? 'dark' : 'light')
}

// Close mobile menu on route change
watch(() => route.path, () => {
  mobileMenuOpen.value = false
})

onMounted(async () => {
  // Load preferences
  const savedTheme = localStorage.getItem('theme')
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  isDark.value = savedTheme === 'dark' || (!savedTheme && prefersDark)
  document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
  applyPreset(isDark.value ? 'dark' : 'light')

  const savedCollapsed = localStorage.getItem('sidebar_collapsed')
  sidebarCollapsed.value = savedCollapsed === 'true'
})
</script>

<style lang="scss" scoped>
// ===== LAYOUT =====
.admin-layout {
  display: flex;
  min-height: 100vh;
  background: var(--bg-primary);
}

// ===== SIDEBAR (Dark) =====
.sidebar {
  width: 260px;
  background: var(--sidebar-bg);
  display: flex;
  flex-direction: column;
  position: fixed;
  height: 100vh;
  z-index: 100;
  transition: width 0.2s ease, transform 0.2s ease;
}

.sidebar-collapsed .sidebar {
  width: 72px;

  .nav-label,
  .user-info {
    display: none;
  }

  .nav-item {
    justify-content: center;
    padding: 0.875rem;

    i:first-child {
      margin: 0;
    }
  }

  .user-card {
    justify-content: center;
    padding: 0.75rem;
  }
}

.sidebar-header {
  padding: 1.25rem;
  border-bottom: 1px solid var(--sidebar-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 72px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;

  .logo-icon {
    width: 40px;
    height: 40px;
    background: var(--primary-color);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;

    i {
      font-size: 1.25rem;
      color: white;
    }

    &.small {
      width: 32px;
      height: 32px;

      i { font-size: 1rem; }
    }
  }

  .logo-text {
    font-size: 1.35rem;
    font-weight: 700;
    color: white;
    letter-spacing: -0.02em;
  }
}

.collapse-btn {
  width: 32px;
  height: 32px;
  background: var(--sidebar-hover);
  border: none;
  border-radius: 8px;
  color: var(--sidebar-text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;

  &:hover {
    background: var(--sidebar-active);
    color: white;
  }
}

.sidebar-nav {
  flex: 1;
  padding: 1rem;
  overflow-y: auto;
}

.nav-section {
  margin-bottom: 1.5rem;
}

.nav-label {
  display: block;
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--sidebar-text-muted);
  padding: 0 0.75rem;
  margin-bottom: 0.5rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  color: var(--sidebar-text);
  text-decoration: none;
  transition: all 0.15s ease;
  margin-bottom: 0.125rem;
  font-weight: 500;
  font-size: 0.875rem;

  &:hover {
    background: var(--sidebar-hover);
    color: white;
  }

  &.router-link-active {
    background: var(--primary-color);
    color: white;

    i { color: white; }
  }

  i:first-child {
    font-size: 1.125rem;
    width: 20px;
    text-align: center;
    flex-shrink: 0;
    opacity: 0.85;
  }

  &.router-link-active i:first-child {
    opacity: 1;
  }
}

.sidebar-footer {
  padding: 1rem;
  border-top: 1px solid var(--sidebar-border);
}

.user-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: var(--sidebar-hover);
  border-radius: 8px;

  .user-avatar {
    width: 36px;
    height: 36px;
    background: var(--primary-color);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;

    i {
      font-size: 1rem;
      color: white;
    }
  }

  .user-info {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-width: 0;

    .user-name {
      font-weight: 600;
      font-size: 0.75rem;
      color: white;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .user-role {
      font-size: 0.7rem;
      color: var(--sidebar-text-muted);
    }
  }
}

.logout-btn {
  width: 32px;
  height: 32px;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: var(--sidebar-text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.15s ease;

  &:hover {
    background: rgba(239, 68, 68, 0.2);
    color: #f87171;
  }

  i {
    font-size: 1.125rem;
  }
}

// ===== MAIN CONTENT =====
.main-content {
  flex: 1;
  margin-left: 260px;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  transition: margin-left 0.2s ease;
}

.sidebar-collapsed .main-content {
  margin-left: 72px;
}

// ===== TOPBAR =====
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
  height: 64px;
  background: var(--surface-primary);
  border-bottom: 1px solid var(--border-light);
  position: sticky;
  top: 0;
  z-index: 50;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.page-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.topbar-btn {
  width: 40px;
  height: 40px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  position: relative;
  transition: all 0.15s ease;

  &:hover {
    background: var(--surface-secondary);
    color: var(--primary-color);
  }

  .notification-badge {
    position: absolute;
    top: 6px;
    right: 6px;
    width: 18px;
    height: 18px;
    background: var(--error-color);
    border-radius: 50%;
    font-size: 0.65rem;
    font-weight: 600;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}

.menu-toggle {
  width: 40px;
  height: 40px;
  background: var(--surface-secondary);
  border: none;
  border-radius: 8px;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;

  &:hover {
    background: var(--surface-tertiary);
    color: var(--primary-color);
  }
}

.topbar-logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 700;
  color: var(--text-primary);
}

// ===== CONTENT =====
.content-wrapper {
  flex: 1;
  padding: 1.5rem;
}

// ===== MOBILE OVERLAY =====
.mobile-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 99;
  backdrop-filter: blur(4px);
}

// ===== PAGE TRANSITIONS =====
.page-enter-active,
.page-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

// ===== RESPONSIVE =====
.show-mobile {
  display: none !important;
}

@media (max-width: 768px) {
  .sidebar {
    transform: translateX(-100%);
    width: 280px;
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.2);
  }

  .mobile-open {
    .sidebar {
      transform: translateX(0);
    }

    .mobile-overlay {
      display: block;
    }
  }

  .main-content {
    margin-left: 0;
  }

  .sidebar-collapsed .main-content {
    margin-left: 0;
  }

  .sidebar-collapsed .sidebar {
    width: 280px;
  }

  .hide-mobile {
    display: none !important;
  }

  .show-mobile {
    display: flex !important;
  }

  .topbar {
    padding: 0 1rem;
  }

  .content-wrapper {
    padding: 1rem;
  }
}
</style>
