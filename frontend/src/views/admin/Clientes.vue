<template>
  <div class="page-container">
    <div class="page-header">
      <h1>Clientes</h1>
      <div class="actions">
        <va-button @click="showDialog = true">
          <i class="mdi mdi-plus"></i>
          Novo Cliente
        </va-button>
      </div>
    </div>

    <div class="card">
      <!-- Search -->
      <div class="table-toolbar">
        <va-input
          v-model="searchQuery"
          placeholder="Buscar..."
          clearable
        >
          <template #prependInner>
            <i class="mdi mdi-magnify"></i>
          </template>
        </va-input>
      </div>

      <!-- Table -->
      <va-data-table
        :items="filteredClients"
        :columns="columns"
        :loading="loading"
        striped
        hoverable
        :per-page="10"
        :current-page="currentPage"
      >
        <template #cell(ai_enabled)="{ value }">
          <va-chip :color="value ? 'success' : 'secondary'" size="small">
            {{ value ? 'Ativa' : 'Inativa' }}
          </va-chip>
        </template>

        <template #cell(actions)="{ rowData }">
          <div class="table-actions">
            <router-link :to="`/admin/cliente/${rowData.slug}`">
              <va-button preset="plain" size="small" title="Configurar">
                <i class="mdi mdi-cog"></i>
              </va-button>
            </router-link>
            <va-button
              preset="plain"
              size="small"
              color="danger"
              title="Excluir"
              @click="confirmDelete(rowData)"
            >
              <i class="mdi mdi-delete"></i>
            </va-button>
          </div>
        </template>
      </va-data-table>

      <!-- Pagination -->
      <div class="table-pagination" v-if="filteredClients.length > 10">
        <va-pagination
          v-model="currentPage"
          :pages="Math.ceil(filteredClients.length / 10)"
          :visible-pages="5"
          buttons-preset="secondary"
        />
      </div>
    </div>

    <!-- Dialog Novo Cliente -->
    <va-modal
      v-model="showDialog"
      title="Novo Cliente"
      size="medium"
      hide-default-actions
    >
      <div class="form-grid">
        <div class="form-group">
          <label>Nome</label>
          <va-input v-model="newClient.name" placeholder="Ex: Minha Empresa" />
        </div>

        <div class="form-group">
          <label>Slug (identificador unico)</label>
          <va-input v-model="newClient.slug" placeholder="Ex: minha-empresa" />
          <small class="hint">Use apenas letras minusculas, numeros e hifen</small>
        </div>

        <div class="form-group">
          <label>URL do Chatwoot</label>
          <va-input v-model="newClient.chatwoot_url" placeholder="https://chat.exemplo.com" />
        </div>

        <div class="form-group">
          <label>Account ID</label>
          <va-input v-model="newClient.account_id" placeholder="1" />
        </div>

        <div class="form-group">
          <label>API Token</label>
          <va-input
            v-model="newClient.api_token"
            :type="showPassword ? 'text' : 'password'"
            placeholder="Token de acesso a API do Chatwoot"
          >
            <template #appendInner>
              <va-button preset="plain" size="small" @click="showPassword = !showPassword">
                <i :class="showPassword ? 'mdi mdi-eye-off' : 'mdi mdi-eye'"></i>
              </va-button>
            </template>
          </va-input>
        </div>
      </div>

      <template #footer>
        <div class="modal-actions">
          <va-button preset="secondary" @click="showDialog = false">
            Cancelar
          </va-button>
          <va-button @click="createClient" :loading="saving">
            <i class="mdi mdi-check"></i>
            Criar
          </va-button>
        </div>
      </template>
    </va-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { clientsApi } from '@/api/client'

const toast = useToast()
const { confirm } = useConfirm()

const clients = ref([])
const loading = ref(false)
const showDialog = ref(false)
const saving = ref(false)
const searchQuery = ref('')
const currentPage = ref(1)
const showPassword = ref(false)

const columns = [
  { key: 'name', label: 'Nome', sortable: true },
  { key: 'slug', label: 'Slug', sortable: true },
  { key: 'chatwoot_url', label: 'Chatwoot URL' },
  { key: 'ai_enabled', label: 'IA' },
  { key: 'actions', label: 'Acoes', width: '120px' }
]

const newClient = ref({
  name: '',
  slug: '',
  chatwoot_url: '',
  account_id: '',
  api_token: ''
})

const filteredClients = computed(() => {
  if (!searchQuery.value) return clients.value
  const query = searchQuery.value.toLowerCase()
  return clients.value.filter(c =>
    c.name?.toLowerCase().includes(query) ||
    c.slug?.toLowerCase().includes(query)
  )
})

const loadClients = async () => {
  loading.value = true
  try {
    const { data } = await clientsApi.list()
    clients.value = Object.values(data)
  } catch (error) {
    toast.error('Erro', 'Falha ao carregar clientes')
  } finally {
    loading.value = false
  }
}

const createClient = async () => {
  saving.value = true
  try {
    await clientsApi.create(newClient.value)
    toast.success('Sucesso', 'Cliente criado!')
    showDialog.value = false
    newClient.value = { name: '', slug: '', chatwoot_url: '', account_id: '', api_token: '' }
    loadClients()
  } catch (error) {
    toast.error('Erro', error.response?.data?.detail || 'Falha ao criar cliente')
  } finally {
    saving.value = false
  }
}

const confirmDelete = (client) => {
  confirm({
    message: `Tem certeza que deseja excluir "${client.name}"?`,
    header: 'Confirmar Exclusao',
    icon: 'mdi-alert-circle-outline',
    accept: async () => {
      try {
        await clientsApi.delete(client.slug)
        toast.success('Sucesso', 'Cliente excluido!')
        loadClients()
      } catch (error) {
        toast.error('Erro', 'Falha ao excluir cliente')
      }
    }
  })
}

onMounted(loadClients)
</script>

<style lang="scss" scoped>
.table-toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 1rem;

  .va-input {
    max-width: 300px;
  }
}

.table-actions {
  display: flex;
  gap: 0.5rem;
}

.table-pagination {
  display: flex;
  justify-content: center;
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color);
}

.form-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;

  label {
    font-weight: 500;
    color: var(--text-dark);
    font-size: 0.875rem;
  }

  .hint {
    font-size: 0.75rem;
    color: var(--text-muted);
  }
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
}
</style>
