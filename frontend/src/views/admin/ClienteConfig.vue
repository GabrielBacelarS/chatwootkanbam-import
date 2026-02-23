<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <router-link to="/admin/clientes" class="back-link">
          <i class="mdi mdi-arrow-left"></i>
          Voltar
        </router-link>
        <h1>{{ client?.name || 'Carregando...' }}</h1>
        <p class="subtitle">Configuracoes de IA do cliente</p>
      </div>
    </div>

    <div class="card" v-if="client">
      <va-tabs v-model="activeTab">
        <template #tabs>
          <va-tab name="ia">Configuracoes de IA</va-tab>
          <va-tab name="produtos">Produtos (RAG)</va-tab>
          <va-tab name="testes">Testes em Lote</va-tab>
          <va-tab name="info">Informacoes</va-tab>
        </template>
      </va-tabs>

      <div class="tab-content">
        <div v-if="activeTab === 'ia'">
          <IAConfig :slug="slug" :client="client" />
        </div>
        <div v-else-if="activeTab === 'produtos'">
          <Produtos :slug="slug" :client="client" />
        </div>
        <div v-else-if="activeTab === 'testes'">
          <AIBatchTest :slug="slug" />
        </div>
        <div v-else-if="activeTab === 'info'">
          <!-- Schema de Produto -->
          <div class="schema-section">
            <h3>
              <i class="mdi mdi-shape"></i>
              Tipo de Produto
            </h3>
            <p class="section-desc">Define quais campos o formulario de produtos tera e como a IA vai descrever os produtos.</p>
            <div class="schema-selector">
              <va-select
                v-model="selectedSchemaId"
                :options="schemaOptions"
                placeholder="Selecione o tipo de produto"
                text-by="text"
                value-by="value"
                @update:modelValue="updateClientSchema"
              />
              <div v-if="currentSchema" class="schema-preview">
                <i :class="currentSchema.icon || 'mdi mdi-package'"></i>
                <div>
                  <strong>{{ currentSchema.name }}</strong>
                  <span>{{ currentSchema.fields?.length || 0 }} campos configurados</span>
                </div>
              </div>
            </div>
          </div>

          <hr class="divider" />

          <div class="info-grid">
            <div class="info-item">
              <label>Slug</label>
              <span>{{ client.slug }}</span>
            </div>
            <div class="info-item">
              <label>URL do Chatwoot</label>
              <span>{{ client.chatwoot_url }}</span>
            </div>
            <div class="info-item">
              <label>Account ID</label>
              <span>{{ client.account_id }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="card">
      <div class="empty-state">
        <i class="mdi mdi-loading mdi-spin"></i>
        <p>Carregando...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { clientsApi, schemasApi } from '@/api/client'
import { useToast } from '@/composables/useToast'

import IAConfig from './IAConfig.vue'
import Produtos from './Produtos.vue'
import AIBatchTest from './AIBatchTest.vue'

const route = useRoute()
const toast = useToast()
const slug = computed(() => route.params.slug)
const client = ref(null)
const activeTab = ref('ia')

// Schemas
const schemas = ref([])
const selectedSchemaId = ref(null)
const currentSchema = computed(() => schemas.value.find(s => s.id === selectedSchemaId.value))
const schemaOptions = computed(() => [
  { text: 'Nenhum (somente nome e preco)', value: null },
  ...schemas.value.map(s => ({ text: s.name, value: s.id }))
])

const loadClient = async () => {
  try {
    const { data } = await clientsApi.get(slug.value)
    client.value = data
    selectedSchemaId.value = data.product_schema_id || null
  } catch (error) {
    console.error('Erro ao carregar cliente:', error)
  }
}

const loadSchemas = async () => {
  try {
    const { data } = await schemasApi.list(true) // apenas ativos
    schemas.value = data
  } catch (error) {
    console.warn('Erro ao carregar schemas:', error)
    schemas.value = []
  }
}

const updateClientSchema = async (schemaId) => {
  try {
    await schemasApi.assignToClient(slug.value, schemaId)
    toast.success('Sucesso', 'Tipo de produto atualizado!')
    // Atualiza o client local
    if (client.value) {
      client.value.product_schema_id = schemaId
    }
  } catch (error) {
    console.error('Erro ao atualizar schema:', error)
    toast.error('Erro', 'Falha ao atualizar tipo de produto')
    // Reverte a selecao
    selectedSchemaId.value = client.value?.product_schema_id || null
  }
}

onMounted(async () => {
  await Promise.all([loadClient(), loadSchemas()])
})
</script>

<style lang="scss" scoped>
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-muted);
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
  text-decoration: none;
  transition: color 0.2s;

  &:hover {
    color: var(--primary-color);
  }
}

.tab-content {
  padding-top: 1.5rem;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
}

.info-item {
  label {
    display: block;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    margin-bottom: 0.5rem;
  }

  span {
    font-size: 1rem;
    color: var(--text-dark);
  }
}

.schema-section {
  margin-bottom: 1.5rem;

  h3 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1.1rem;
    margin-bottom: 0.5rem;
    color: var(--text-dark);

    i {
      color: var(--primary-color);
    }
  }

  .section-desc {
    font-size: 0.875rem;
    color: var(--text-muted);
    margin-bottom: 1rem;
  }
}

.schema-selector {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-width: 400px;

  .schema-preview {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    background: var(--surface-light);
    border-radius: var(--radius-md);
    border: 1px solid var(--border-color);

    > i {
      font-size: 1.5rem;
      color: var(--primary-color);
    }

    > div {
      display: flex;
      flex-direction: column;

      strong {
        font-size: 0.9rem;
        color: var(--text-dark);
      }

      span {
        font-size: 0.75rem;
        color: var(--text-muted);
      }
    }
  }
}

.divider {
  border: none;
  border-top: 1px solid var(--border-color);
  margin: 1.5rem 0;
}
</style>
