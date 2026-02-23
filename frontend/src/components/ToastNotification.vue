<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="toast-item"
          :class="`toast-${toast.severity}`"
        >
          <div class="toast-icon">
            <i :class="getIcon(toast.severity)"></i>
          </div>
          <div class="toast-content">
            <div class="toast-summary">{{ toast.summary }}</div>
            <div v-if="toast.detail" class="toast-detail">{{ toast.detail }}</div>
          </div>
          <button class="toast-close" @click="remove(toast.id)">
            <i class="mdi mdi-close"></i>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
import { useToast } from '@/composables/useToast'

const { toasts, remove } = useToast()

const getIcon = (severity) => {
  const icons = {
    success: 'mdi mdi-check-circle',
    info: 'mdi mdi-information',
    warning: 'mdi mdi-alert',
    danger: 'mdi mdi-alert-circle'
  }
  return icons[severity] || icons.info
}
</script>

<style lang="scss" scoped>
.toast-container {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  max-width: 400px;
}

.toast-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem;
  border-radius: var(--radius-md);
  background: var(--surface-card);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  border-left: 4px solid;

  &.toast-success {
    border-color: var(--success-color, #10b981);
    .toast-icon { color: var(--success-color, #10b981); }
  }

  &.toast-info {
    border-color: var(--info-color, #0ea5e9);
    .toast-icon { color: var(--info-color, #0ea5e9); }
  }

  &.toast-warning {
    border-color: var(--warning-color, #f59e0b);
    .toast-icon { color: var(--warning-color, #f59e0b); }
  }

  &.toast-danger {
    border-color: var(--danger-color, #ef4444);
    .toast-icon { color: var(--danger-color, #ef4444); }
  }
}

.toast-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.toast-content {
  flex: 1;
}

.toast-summary {
  font-weight: 600;
  color: var(--text-dark);
  margin-bottom: 0.25rem;
}

.toast-detail {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.toast-close {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0.25rem;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);

  &:hover {
    background: var(--surface-hover);
    color: var(--text-dark);
  }
}

// Animations
.toast-enter-active {
  animation: toast-in 0.3s ease-out;
}

.toast-leave-active {
  animation: toast-out 0.3s ease-in;
}

@keyframes toast-in {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes toast-out {
  from {
    opacity: 1;
    transform: translateX(0);
  }
  to {
    opacity: 0;
    transform: translateX(100%);
  }
}
</style>
