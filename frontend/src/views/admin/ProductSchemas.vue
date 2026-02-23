<template>
  <div class="schemas-view">
    <!-- Header -->
    <div class="view-header">
      <div class="header-left">
        <h1><i class="mdi mdi-shape"></i> Esquemas de Produto</h1>
        <p class="subtitle">Configure tipos de produto para diferentes negocios</p>
      </div>
      <div class="header-actions">
        <va-button preset="secondary" @click="seedSchemas" :loading="seeding">
          <i class="mdi mdi-database-plus"></i>
          Seed Padrao
        </va-button>
        <va-button @click="openSchemaDialog()">
          <i class="mdi mdi-plus"></i>
          Novo Schema
        </va-button>
      </div>
    </div>

    <!-- Schemas Grid -->
    <div class="schemas-grid">
      <div
        v-for="schema in schemas"
        :key="schema.id"
        class="schema-card"
        :class="{ default: schema.is_default, inactive: !schema.is_active }"
      >
        <div class="schema-header">
          <div class="schema-icon">
            <i :class="getIconClass(schema.icon)"></i>
          </div>
          <div class="schema-info">
            <h3>{{ schema.name }}</h3>
            <span class="schema-slug">{{ schema.slug }}</span>
          </div>
          <div class="schema-badges">
            <va-chip v-if="schema.is_default" color="success" size="small">Padrao</va-chip>
            <va-chip v-if="!schema.is_active" color="danger" size="small">Inativo</va-chip>
          </div>
        </div>

        <p class="schema-description">{{ schema.description || 'Sem descricao' }}</p>

        <div class="schema-fields">
          <span class="fields-count">
            <i class="mdi mdi-form-textbox"></i>
            {{ schema.fields?.length || 0 }} campos
          </span>
          <div class="fields-preview">
            <span v-for="field in (schema.fields || []).slice(0, 4)" :key="field.key" class="field-tag">
              {{ field.label }}
            </span>
            <span v-if="(schema.fields?.length || 0) > 4" class="field-tag more">
              +{{ schema.fields.length - 4 }}
            </span>
          </div>
        </div>

        <div class="schema-actions">
          <va-button preset="plain" size="small" @click="openSchemaDialog(schema)">
            <i class="mdi mdi-pencil"></i>
          </va-button>
          <va-button v-if="!schema.is_default" preset="plain" size="small" @click="setDefault(schema)">
            <i class="mdi mdi-star-outline"></i>
          </va-button>
          <va-button v-if="!schema.is_default" preset="plain" size="small" color="danger" @click="confirmDelete(schema)">
            <i class="mdi mdi-delete"></i>
          </va-button>
        </div>
      </div>
    </div>

    <div v-if="schemas.length === 0 && !loading" class="empty-state">
      <i class="mdi mdi-shape-outline"></i>
      <h3>Nenhum schema configurado</h3>
      <p>Clique em "Seed Padrao" para criar os schemas iniciais</p>
    </div>

    <!-- Dialog Criar/Editar Schema -->
    <va-modal
      v-model="showSchemaDialog"
      :title="editingSchema ? 'Editar Schema' : 'Novo Schema'"
      size="large"
      hide-default-actions
    >
      <div class="schema-form">
        <div class="form-row">
          <div class="form-group col-4">
            <label>Slug *</label>
            <va-input
              v-model="schemaForm.slug"
              placeholder="ex: vehicles"
              :disabled="!!editingSchema"
            />
          </div>
          <div class="form-group col-4">
            <label>Nome *</label>
            <va-input v-model="schemaForm.name" placeholder="ex: Veiculos" />
          </div>
          <div class="form-group col-4">
            <label>Icone</label>
            <div class="icon-selector">
              <div class="selected-icon" @click="showIconPicker = !showIconPicker">
                <i :class="getIconClass(schemaForm.icon)"></i>
                <span>{{ schemaForm.icon || 'Selecionar' }}</span>
                <i class="mdi mdi-chevron-down"></i>
              </div>
              <div v-if="showIconPicker" class="icon-picker">
                <div class="icon-search">
                  <va-input v-model="iconSearch" placeholder="Buscar icone..." size="small" />
                </div>
                <div class="icon-grid">
                  <div
                    v-for="icon in filteredIcons"
                    :key="icon.name"
                    class="icon-option"
                    :class="{ selected: schemaForm.icon === icon.name }"
                    @click="selectIcon(icon.name)"
                    :title="icon.label"
                  >
                    <i :class="'mdi ' + icon.name"></i>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="form-group">
          <label>Descricao</label>
          <va-input v-model="schemaForm.description" placeholder="Descricao do tipo de produto" />
        </div>

        <div class="form-row">
          <div class="form-group col-6">
            <va-checkbox v-model="schemaForm.is_active" label="Ativo" />
          </div>
        </div>

        <div class="form-section">
          <div class="section-header">
            <h3>Campos Dinamicos</h3>
            <va-button size="small" @click="addField">
              <i class="mdi mdi-plus"></i> Adicionar Campo
            </va-button>
          </div>

          <div class="fields-list">
            <div v-for="(field, index) in schemaForm.fields" :key="index" class="field-item">
              <div class="field-drag">
                <i class="mdi mdi-drag"></i>
              </div>

              <div class="field-row">
                <va-input v-model="field.key" placeholder="key" class="field-key" />
                <va-input v-model="field.label" placeholder="Label" class="field-label" />
                <va-select
                  v-model="field.type"
                  :options="fieldTypes"
                  text-by="label"
                  value-by="value"
                  class="field-type"
                />
                <va-input
                  v-if="field.type === 'select'"
                  v-model="field.optionsText"
                  placeholder="opcao1, opcao2, opcao3"
                  class="field-options"
                  @update:modelValue="field.options = $event?.split(',').map(o => o.trim()).filter(o => o)"
                />
              </div>

              <div class="field-row-secondary">
                <va-checkbox v-model="field.show_in_card" label="Card" size="small" />
                <va-checkbox v-model="field.show_in_rag" label="RAG" size="small" />
                <va-select
                  v-model="field.rag_format"
                  :options="ragFormats"
                  text-by="label"
                  value-by="value"
                  placeholder="Formato RAG"
                  clearable
                  class="field-rag-format"
                />
                <va-input v-model="field.placeholder" placeholder="Placeholder" class="field-placeholder" />
              </div>

              <va-button preset="plain" color="danger" size="small" @click="removeField(index)">
                <i class="mdi mdi-close"></i>
              </va-button>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="modal-actions">
          <va-button preset="secondary" @click="showSchemaDialog = false">Cancelar</va-button>
          <va-button @click="saveSchema" :loading="saving">
            <i class="mdi mdi-check"></i>
            {{ editingSchema ? 'Salvar' : 'Criar' }}
          </va-button>
        </div>
      </template>
    </va-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { schemasApi } from '@/api/client'

const toast = useToast()
const { confirm } = useConfirm()

const schemas = ref([])
const loading = ref(false)
const saving = ref(false)
const seeding = ref(false)
const showSchemaDialog = ref(false)
const editingSchema = ref(null)
const showIconPicker = ref(false)
const iconSearch = ref('')

// Lista de icones comuns para produtos/negocios
const availableIcons = [
  // Veiculos
  { name: 'mdi-car', label: 'Carro' },
  { name: 'mdi-car-sports', label: 'Carro Esportivo' },
  { name: 'mdi-car-pickup', label: 'Pickup' },
  { name: 'mdi-truck', label: 'Caminhao' },
  { name: 'mdi-motorbike', label: 'Moto' },
  { name: 'mdi-bicycle', label: 'Bicicleta' },
  { name: 'mdi-bus', label: 'Onibus' },
  { name: 'mdi-tractor', label: 'Trator' },
  // Imoveis
  { name: 'mdi-home', label: 'Casa' },
  { name: 'mdi-home-city', label: 'Cidade' },
  { name: 'mdi-office-building', label: 'Predio' },
  { name: 'mdi-warehouse', label: 'Galpao' },
  { name: 'mdi-store', label: 'Loja' },
  { name: 'mdi-domain', label: 'Dominio' },
  // Moda/Vestuario
  { name: 'mdi-tshirt-crew', label: 'Camiseta' },
  { name: 'mdi-shoe-formal', label: 'Sapato' },
  { name: 'mdi-glasses', label: 'Oculos' },
  { name: 'mdi-watch', label: 'Relogio' },
  { name: 'mdi-bag-personal', label: 'Bolsa' },
  { name: 'mdi-hanger', label: 'Cabide' },
  // Financeiro
  { name: 'mdi-bank', label: 'Banco' },
  { name: 'mdi-cash', label: 'Dinheiro' },
  { name: 'mdi-credit-card', label: 'Cartao' },
  { name: 'mdi-chart-line', label: 'Grafico' },
  { name: 'mdi-calculator', label: 'Calculadora' },
  { name: 'mdi-file-document', label: 'Documento' },
  // Tecnologia
  { name: 'mdi-laptop', label: 'Laptop' },
  { name: 'mdi-cellphone', label: 'Celular' },
  { name: 'mdi-television', label: 'TV' },
  { name: 'mdi-headphones', label: 'Fone' },
  { name: 'mdi-camera', label: 'Camera' },
  { name: 'mdi-gamepad-variant', label: 'Game' },
  // Alimentacao
  { name: 'mdi-food', label: 'Comida' },
  { name: 'mdi-pizza', label: 'Pizza' },
  { name: 'mdi-coffee', label: 'Cafe' },
  { name: 'mdi-glass-cocktail', label: 'Drink' },
  { name: 'mdi-cart', label: 'Carrinho' },
  { name: 'mdi-basket', label: 'Cesta' },
  // Servicos
  { name: 'mdi-wrench', label: 'Ferramenta' },
  { name: 'mdi-hammer', label: 'Martelo' },
  { name: 'mdi-broom', label: 'Limpeza' },
  { name: 'mdi-scissors-cutting', label: 'Corte' },
  { name: 'mdi-medical-bag', label: 'Saude' },
  { name: 'mdi-school', label: 'Educacao' },
  // Outros
  { name: 'mdi-package', label: 'Pacote' },
  { name: 'mdi-package-variant', label: 'Caixa' },
  { name: 'mdi-gift', label: 'Presente' },
  { name: 'mdi-tag', label: 'Tag' },
  { name: 'mdi-star', label: 'Estrela' },
  { name: 'mdi-heart', label: 'Coracao' },
  { name: 'mdi-paw', label: 'Pet' },
  { name: 'mdi-flower', label: 'Flor' },
  { name: 'mdi-airplane', label: 'Aviao' },
  { name: 'mdi-beach', label: 'Praia' }
]

const filteredIcons = computed(() => {
  if (!iconSearch.value) return availableIcons
  const search = iconSearch.value.toLowerCase()
  return availableIcons.filter(i =>
    i.name.toLowerCase().includes(search) ||
    i.label.toLowerCase().includes(search)
  )
})

const getIconClass = (icon) => {
  if (!icon) return 'mdi mdi-package'
  // Se ja tem 'mdi ' no inicio, retorna como esta
  if (icon.startsWith('mdi ')) return icon
  // Se comeca com 'mdi-', adiciona 'mdi ' na frente
  if (icon.startsWith('mdi-')) return 'mdi ' + icon
  // Caso contrario, adiciona prefixo completo
  return 'mdi mdi-' + icon
}

const selectIcon = (iconName) => {
  schemaForm.value.icon = iconName
  showIconPicker.value = false
  iconSearch.value = ''
}

// Fechar icon picker ao clicar fora
const handleClickOutside = (e) => {
  if (showIconPicker.value && !e.target.closest('.icon-selector')) {
    showIconPicker.value = false
  }
}

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

const fieldTypes = [
  { label: 'Texto', value: 'text' },
  { label: 'Numero', value: 'number' },
  { label: 'Select', value: 'select' },
  { label: 'Textarea', value: 'textarea' },
  { label: 'Checkbox', value: 'boolean' },
  { label: 'Data', value: 'date' }
]

const ragFormats = [
  { label: 'Nenhum', value: null },
  { label: 'Moeda (R$)', value: 'currency' },
  { label: 'Numero', value: 'number' },
  { label: 'Km', value: 'km' }
]

const schemaForm = ref({
  slug: '',
  name: '',
  icon: 'mdi-package',
  description: '',
  is_active: true,
  fields: []
})

const loadSchemas = async () => {
  loading.value = true
  try {
    const { data } = await schemasApi.list()
    schemas.value = data
  } catch (error) {
    toast.error('Erro', 'Falha ao carregar schemas')
  } finally {
    loading.value = false
  }
}

const openSchemaDialog = (schema = null) => {
  editingSchema.value = schema
  if (schema) {
    schemaForm.value = {
      ...schema,
      fields: (schema.fields || []).map(f => ({
        ...f,
        optionsText: f.options?.join(', ') || ''
      }))
    }
  } else {
    schemaForm.value = {
      slug: '',
      name: '',
      icon: 'mdi-package',
      description: '',
      is_active: true,
      fields: []
    }
  }
  showSchemaDialog.value = true
}

const addField = () => {
  schemaForm.value.fields.push({
    key: '',
    label: '',
    type: 'text',
    required: false,
    placeholder: '',
    group: '',
    order: schemaForm.value.fields.length + 1,
    options: [],
    optionsText: '',
    show_in_card: true,
    show_in_rag: true,
    rag_label: '',
    rag_format: null
  })
}

const removeField = (index) => {
  schemaForm.value.fields.splice(index, 1)
}

const saveSchema = async () => {
  if (!schemaForm.value.slug || !schemaForm.value.name) {
    toast.warn('Atencao', 'Slug e nome sao obrigatorios')
    return
  }

  saving.value = true
  try {
    // Limpar campos temporarios e preparar dados
    const data = {
      ...schemaForm.value,
      fields: schemaForm.value.fields.map(f => {
        const { optionsText, ...field } = f
        if (!field.rag_label) field.rag_label = field.label
        return field
      })
    }

    if (editingSchema.value) {
      await schemasApi.update(editingSchema.value.id, data)
      toast.success('Sucesso', 'Schema atualizado!')
    } else {
      await schemasApi.create(data)
      toast.success('Sucesso', 'Schema criado!')
    }
    showSchemaDialog.value = false
    loadSchemas()
  } catch (error) {
    toast.error('Erro', error.response?.data?.detail || 'Falha ao salvar')
  } finally {
    saving.value = false
  }
}

const setDefault = async (schema) => {
  try {
    await schemasApi.setDefault(schema.id)
    toast.success('Sucesso', `${schema.name} definido como padrao`)
    loadSchemas()
  } catch (error) {
    toast.error('Erro', 'Falha ao definir padrao')
  }
}

const confirmDelete = (schema) => {
  confirm({
    message: `Excluir o schema "${schema.name}"?`,
    header: 'Confirmar Exclusao',
    icon: 'mdi-delete',
    accept: async () => {
      try {
        await schemasApi.delete(schema.id)
        toast.success('Sucesso', 'Schema removido')
        loadSchemas()
      } catch (error) {
        toast.error('Erro', error.response?.data?.detail || 'Falha ao remover')
      }
    }
  })
}

const seedSchemas = async () => {
  seeding.value = true
  try {
    const { data } = await schemasApi.seed()
    toast.success('Sucesso', data.message)
    loadSchemas()
  } catch (error) {
    toast.error('Erro', error.response?.data?.detail || 'Falha ao criar schemas')
  } finally {
    seeding.value = false
  }
}

onMounted(() => {
  loadSchemas()
  document.addEventListener('click', handleClickOutside)
})
</script>

<style lang="scss" scoped>
.view-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;

  .header-left {
    h1 {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      font-size: 1.75rem;
      color: var(--text-dark);

      i { color: var(--primary-color); }
    }

    .subtitle {
      color: var(--text-secondary);
      margin-top: 0.25rem;
    }
  }

  .header-actions {
    display: flex;
    gap: 0.75rem;
  }
}

.schemas-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.schema-card {
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  padding: 1.5rem;
  transition: all 0.2s ease;

  &:hover {
    border-color: var(--primary-color);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  }

  &.default {
    border-color: var(--success-color);
    background: linear-gradient(135deg, var(--surface-card), rgba(16, 185, 129, 0.05));
  }

  &.inactive {
    opacity: 0.6;
  }

  .schema-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1rem;

    .schema-icon {
      width: 48px;
      height: 48px;
      border-radius: var(--radius-md);
      background: var(--primary-gradient);
      display: flex;
      align-items: center;
      justify-content: center;

      i {
        font-size: 1.5rem;
        color: white;
      }
    }

    .schema-info {
      flex: 1;

      h3 {
        font-size: 1.1rem;
        color: var(--text-dark);
        margin: 0;
      }

      .schema-slug {
        font-size: 0.8rem;
        color: var(--text-muted);
        font-family: monospace;
      }
    }

    .schema-badges {
      display: flex;
      gap: 0.5rem;
    }
  }

  .schema-description {
    color: var(--text-secondary);
    font-size: 0.9rem;
    margin-bottom: 1rem;
    line-height: 1.4;
  }

  .schema-fields {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-bottom: 1rem;

    .fields-count {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.85rem;
      color: var(--text-secondary);

      i { color: var(--primary-color); }
    }

    .fields-preview {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;

      .field-tag {
        font-size: 0.75rem;
        padding: 0.25rem 0.5rem;
        background: var(--surface-light);
        border-radius: var(--radius-sm);
        color: var(--text-secondary);

        &.more {
          background: var(--primary-50);
          color: var(--primary-color);
        }
      }
    }
  }

  .schema-actions {
    display: flex;
    gap: 0.25rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border-color);
  }
}

// Form styles
.schema-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-row {
  display: flex;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 1;

  &.col-4 { flex: 0 0 calc(33.33% - 0.67rem); }
  &.col-6 { flex: 0 0 calc(50% - 0.5rem); }

  label {
    font-weight: 500;
    color: var(--text-dark);
    font-size: 0.875rem;
  }
}

.form-section {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color);

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;

    h3 {
      font-size: 1rem;
      color: var(--text-dark);
      margin: 0;
    }
  }
}

.fields-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.field-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--surface-light);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);

  .field-drag {
    color: var(--text-muted);
    cursor: grab;
    padding-top: 0.5rem;
  }

  .field-row {
    display: flex;
    gap: 0.5rem;
    flex: 1;
    flex-wrap: wrap;

    .field-key { flex: 0 0 100px; }
    .field-label { flex: 1; min-width: 120px; }
    .field-type { flex: 0 0 120px; }
    .field-options { flex: 1; min-width: 150px; }
  }

  .field-row-secondary {
    display: flex;
    gap: 0.75rem;
    align-items: center;
    flex-wrap: wrap;
    margin-top: 0.5rem;
    width: 100%;

    .field-rag-format { width: 120px; }
    .field-placeholder { flex: 1; min-width: 150px; }
  }
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: var(--text-muted);

  i {
    font-size: 4rem;
    opacity: 0.3;
  }

  h3 {
    margin-top: 1rem;
    color: var(--text-dark);
  }

  p {
    margin-top: 0.5rem;
  }
}

// Icon Picker
.icon-selector {
  position: relative;
}

.selected-icon {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  background: var(--surface-light);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    border-color: var(--primary-color);
  }

  i:first-child {
    font-size: 1.25rem;
    color: var(--primary-color);
  }

  span {
    flex: 1;
    font-size: 0.9rem;
    color: var(--text-secondary);
  }

  i:last-child {
    color: var(--text-muted);
    font-size: 1rem;
  }
}

.icon-picker {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 100;
  background: var(--surface-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  margin-top: 0.25rem;
  max-height: 300px;
  overflow: hidden;
  display: flex;
  flex-direction: column;

  .icon-search {
    padding: 0.75rem;
    border-bottom: 1px solid var(--border-color);
  }

  .icon-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 0.25rem;
    padding: 0.75rem;
    overflow-y: auto;
    max-height: 220px;
  }

  .icon-option {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0.75rem;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: all 0.15s ease;

    i {
      font-size: 1.25rem;
      color: var(--text-secondary);
    }

    &:hover {
      background: var(--surface-hover);

      i { color: var(--primary-color); }
    }

    &.selected {
      background: var(--primary-color);

      i { color: white; }
    }
  }
}
</style>
