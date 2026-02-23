<template>
  <va-modal
    v-model="confirmState.visible"
    :title="confirmState.header"
    size="small"
    hide-default-actions
    @cancel="reject"
  >
    <div class="confirm-content">
      <div class="confirm-icon" :class="iconClass">
        <i :class="confirmState.icon"></i>
      </div>
      <p class="confirm-message">{{ confirmState.message }}</p>
    </div>

    <template #footer>
      <div class="confirm-actions">
        <va-button
          preset="secondary"
          @click="reject"
        >
          {{ confirmState.rejectLabel }}
        </va-button>
        <va-button
          color="danger"
          @click="accept"
        >
          {{ confirmState.acceptLabel }}
        </va-button>
      </div>
    </template>
  </va-modal>
</template>

<script setup>
import { computed } from 'vue'
import { useConfirm } from '@/composables/useConfirm'

const { state: confirmState, accept, reject } = useConfirm()

const iconClass = computed(() => {
  if (confirmState.icon.includes('alert') || confirmState.icon.includes('warning')) {
    return 'icon-warning'
  }
  if (confirmState.icon.includes('delete') || confirmState.icon.includes('trash')) {
    return 'icon-danger'
  }
  return 'icon-info'
})
</script>

<style lang="scss" scoped>
.confirm-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 1rem 0;
}

.confirm-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1rem;

  i {
    font-size: 2rem;
  }

  &.icon-warning {
    background: rgba(245, 158, 11, 0.1);
    color: #f59e0b;
  }

  &.icon-danger {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
  }

  &.icon-info {
    background: rgba(99, 102, 241, 0.1);
    color: #6366f1;
  }
}

.confirm-message {
  font-size: 1rem;
  color: var(--text-color);
  margin: 0;
  line-height: 1.5;
}

.confirm-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  width: 100%;
}
</style>
