<template>
  <div class="admin-layout" :class="{ 'sidebar-collapsed': sidebarCollapsed, 'mobile-open': mobileMenuOpen }">
    <!-- Mobile Overlay -->
    <div v-if="mobileMenuOpen" class="mobile-overlay" @click="mobileMenuOpen = false"></div>

    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo">
          <div class="logo-icon">
            <i class="mdi mdi-message-text"></i>
          </div>
          <span class="logo-text" v-show="!sidebarCollapsed">Closefy</span>
        </div>
        <va-button
          class="collapse-btn hide-mobile"
          preset="plain"
          size="small"
          @click="toggleSidebar"
          :aria-label="sidebarCollapsed ? 'Expandir menu' : 'Recolher menu'"
        >
          <i :class="sidebarCollapsed ? 'mdi mdi-chevron-right' : 'mdi mdi-chevron-left'"></i>
        </va-button>
      </div>

      <nav class="sidebar-nav">
        <div class="nav-section">
          <span class="nav-label" v-show="!sidebarCollapsed">Menu</span>

          <router-link to="/admin/dashboard" class="nav-item" :title="sidebarCollapsed ? 'Dashboard' : undefined">
            <i class="mdi mdi-view-dashboard"></i>
            <span v-show="!sidebarCollapsed">Dashboard</span>
          </router-link>

          <router-link to="/admin/clientes" class="nav-item" :title="sidebarCollapsed ? 'Clientes' : undefined">
            <i class="mdi mdi-domain"></i>
            <span v-show="!sidebarCollapsed">Clientes</span>
          </router-link>
        </div>

        <div class="nav-section">
          <span class="nav-label" v-show="!sidebarCollapsed">Configuracoes</span>

          <router-link to="/admin/schemas" class="nav-item" :title="sidebarCollapsed ? 'Schemas' : undefined">
            <i class="mdi mdi-shape"></i>
            <span v-show="!sidebarCollapsed">Schemas</span>
          </router-link>
        </div>
      </nav>

      <div class="sidebar-footer">
        <!-- Theme Toggle -->
        <button class="theme-toggle" @click="toggleTheme" :title="sidebarCollapsed ? (isDark ? 'Modo claro' : 'Modo escuro') : undefined">
          <i :class="isDark ? 'mdi mdi-white-balance-sunny' : 'mdi mdi-weather-night'"></i>
          <span v-show="!sidebarCollapsed">{{ isDark ? 'Modo Claro' : 'Modo Escuro' }}</span>
        </button>

        <!-- User Card -->
        <div class="user-card" v-show="!sidebarCollapsed">
          <div class="user-avatar">
            <i class="mdi mdi-account"></i>
          </div>
          <div class="user-info">
            <span class="user-name">Admin</span>
            <span class="user-role">Administrador</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="main-content">
      <!-- Top Bar Mobile -->
      <header class="topbar hide-desktop">
        <va-button
          class="menu-toggle"
          preset="plain"
          @click="mobileMenuOpen = !mobileMenuOpen"
          aria-label="Menu"
        >
          <i :class="mobileMenuOpen ? 'mdi mdi-close' : 'mdi mdi-menu'"></i>
        </va-button>
        <div class="topbar-logo">
          <div class="logo-icon small">
            <i class="mdi mdi-message-text"></i>
          </div>
          <span>Closefy</span>
        </div>
        <va-button
          class="theme-toggle-mobile"
          preset="plain"
          @click="toggleTheme"
          aria-label="Alternar tema"
        >
          <i :class="isDark ? 'mdi mdi-white-balance-sunny' : 'mdi mdi-weather-night'"></i>
        </va-button>
      </header>

      <ToastNotification />
      <ConfirmDialog />
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useColors } from 'vuestic-ui'
import ToastNotification from '@/components/ToastNotification.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const route = useRoute()
const { applyPreset } = useColors()

const sidebarCollapsed = ref(false)
const mobileMenuOpen = ref(false)
const isDark = ref(false)

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
.admin-layout {
  display: flex;
  min-height: 100vh;
  background: var(--surface-ground);
  transition: background var(--transition-slow);
}

// ===== SIDEBAR =====
.sidebar {
  width: 260px;
  background: var(--surface-card);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  position: fixed;
  height: 100vh;
  z-index: 100;
  transition: width var(--transition-slow), transform var(--transition-slow), background var(--transition-slow), border-color var(--transition-slow);
  box-shadow: 2px 0 12px rgba(0, 0, 0, 0.04);
}

.sidebar-collapsed .sidebar {
  width: 72px;

  .nav-label,
  .user-card,
  .nav-external .external-icon {
    display: none;
  }

  .nav-item {
    justify-content: center;
    padding: 0.875rem;

    i:first-child {
      margin: 0;
    }
  }

  .theme-toggle {
    justify-content: center;
    padding: 0.75rem;
  }
}

.sidebar-header {
  padding: 1.25rem;
  border-bottom: 1px solid var(--border-color);
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
    background: var(--primary-gradient);
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
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
    font-weight: 800;
    color: var(--text-dark);
    letter-spacing: -0.03em;
  }
}

.collapse-btn {
  width: 32px;
  height: 32px;
  min-width: 32px !important;
  min-height: 32px !important;
  padding: 0 !important;
  background: var(--surface-light) !important;
  border-radius: var(--radius-sm) !important;
  color: var(--text-muted) !important;

  &:hover {
    background: var(--surface-hover) !important;
    color: var(--primary-color) !important;
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
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  padding: 0 0.75rem;
  margin-bottom: 0.75rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  text-decoration: none;
  transition: all var(--transition-fast);
  margin-bottom: 0.25rem;
  font-weight: 500;
  font-size: 0.9rem;
  position: relative;

  &:hover {
    background: var(--surface-hover);
    color: var(--text-dark);
  }

  &.router-link-active {
    background: var(--primary-gradient);
    color: white;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);

    i { color: white; }
  }

  i:first-child {
    font-size: 1.1rem;
    width: 20px;
    text-align: center;
    flex-shrink: 0;
  }

  .external-icon {
    font-size: 0.75rem;
    opacity: 0.6;
    margin-left: auto;
  }
}

.sidebar-footer {
  padding: 1rem;
  border-top: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.theme-toggle {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: var(--surface-light);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 0.875rem;
  font-weight: 500;
  transition: all var(--transition-fast);
  width: 100%;

  &:hover {
    background: var(--surface-hover);
    color: var(--primary-color);
  }

  i {
    font-size: 1.1rem;
    width: 20px;
    text-align: center;
  }
}

.user-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem;
  background: var(--surface-light);
  border-radius: var(--radius-md);

  .user-avatar {
    width: 36px;
    height: 36px;
    background: var(--primary-gradient);
    border-radius: var(--radius-sm);
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

    .user-name {
      font-weight: 600;
      font-size: 0.875rem;
      color: var(--text-dark);
    }

    .user-role {
      font-size: 0.7rem;
      color: var(--text-muted);
    }
  }
}

// ===== MAIN CONTENT =====
.main-content {
  flex: 1;
  margin-left: 260px;
  min-height: 100vh;
  transition: margin-left var(--transition-slow);
}

.sidebar-collapsed .main-content {
  margin-left: 72px;
}

// ===== TOPBAR MOBILE =====
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: var(--surface-card);
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 50;

  .menu-toggle,
  .theme-toggle-mobile {
    width: 40px;
    height: 40px;
    min-width: 40px !important;
    min-height: 40px !important;
    padding: 0 !important;
    background: var(--surface-light) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-secondary) !important;
    font-size: 1.25rem;

    &:hover {
      background: var(--surface-hover) !important;
      color: var(--primary-color) !important;
    }
  }

  .topbar-logo {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 700;
    color: var(--text-dark);
  }
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
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

// ===== RESPONSIVE =====
@media (max-width: 768px) {
  .sidebar {
    transform: translateX(-100%);
    width: 280px;
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.15);
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
}

@media (min-width: 769px) {
  .hide-desktop {
    display: none !important;
  }
}
</style>
