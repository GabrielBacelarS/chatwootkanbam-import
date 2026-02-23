import { ref, reactive } from 'vue'

const state = reactive({
  visible: false,
  message: '',
  header: 'Confirmar',
  acceptLabel: 'Sim',
  rejectLabel: 'Cancelar',
  icon: 'mdi-alert-circle-outline',
  onAccept: null,
  onReject: null
})

export function useConfirm() {
  const confirm = (options) => {
    state.message = options.message || ''
    state.header = options.header || 'Confirmar'
    state.acceptLabel = options.acceptLabel || 'Sim'
    state.rejectLabel = options.rejectLabel || 'Cancelar'
    state.icon = options.icon || 'mdi-alert-circle-outline'
    state.onAccept = options.accept || null
    state.onReject = options.reject || null
    state.visible = true
  }

  const accept = () => {
    if (state.onAccept) {
      state.onAccept()
    }
    state.visible = false
  }

  const reject = () => {
    if (state.onReject) {
      state.onReject()
    }
    state.visible = false
  }

  return {
    state,
    confirm,
    accept,
    reject
  }
}
