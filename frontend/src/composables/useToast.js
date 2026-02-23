import { ref, reactive } from 'vue'

const toasts = ref([])
let toastId = 0

export function useToast() {
  const add = (options) => {
    const id = toastId++
    const toast = {
      id,
      severity: options.severity || 'info',
      summary: options.summary || '',
      detail: options.detail || '',
      life: options.life || 3000
    }

    toasts.value.push(toast)

    if (toast.life > 0) {
      setTimeout(() => {
        remove(id)
      }, toast.life)
    }

    return id
  }

  const remove = (id) => {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index > -1) {
      toasts.value.splice(index, 1)
    }
  }

  const clear = () => {
    toasts.value = []
  }

  // Helper methods
  const success = (summary, detail = '') => add({ severity: 'success', summary, detail })
  const info = (summary, detail = '') => add({ severity: 'info', summary, detail })
  const warn = (summary, detail = '') => add({ severity: 'warning', summary, detail })
  const error = (summary, detail = '') => add({ severity: 'danger', summary, detail })

  return {
    toasts,
    add,
    remove,
    clear,
    success,
    info,
    warn,
    error
  }
}
