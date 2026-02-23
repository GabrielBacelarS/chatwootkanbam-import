<template>
  <div class="produtos">
    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <va-progress-circle indeterminate size="large" />
      <p>Carregando produtos...</p>
    </div>

    <template v-else>
    <div class="toolbar">
      <div class="search-area">
        <va-input
          v-model="searchQuery"
          placeholder="Buscar produtos..."
          @keyup.enter="searchProducts"
        >
          <template #prependInner>
            <i class="mdi mdi-magnify"></i>
          </template>
        </va-input>
        <va-button @click="searchProducts">
          <i class="mdi mdi-magnify"></i>
        </va-button>
      </div>

      <div class="actions-area">
        <va-chip v-if="schema" size="small" color="secondary">
          <i :class="getIconClass(schema.icon)"></i>
          {{ schema.name }}
        </va-chip>
        <va-button preset="secondary" @click="generateAllEmbeddings" :loading="generatingEmbeddings">
          <i class="mdi mdi-flash"></i>
          Gerar Embeddings
        </va-button>
        <va-button @click="openProductDialog()">
          <i class="mdi mdi-plus"></i>
          Novo Produto
        </va-button>
      </div>
    </div>

    <!-- Grid de Produtos -->
    <div class="products-grid">
      <div v-for="product in products" :key="product.id" class="product-card">
        <div class="product-image">
          <img v-if="product.main_image_url" :src="product.main_image_url" :alt="product.name" />
          <div v-else class="no-image">
            <i :class="getIconClass(schema?.icon)"></i>
          </div>
          <va-chip v-if="!product.is_available" color="danger" size="small" class="sold-badge">
            Vendido
          </va-chip>
          <va-chip v-if="product.is_featured" color="warning" size="small" class="featured-badge">
            Destaque
          </va-chip>
        </div>

        <div class="product-info">
          <h3>{{ getProductTitle(product) }}</h3>
          <p class="product-details">{{ getProductSubtitle(product) }}</p>
          <p class="product-price" v-if="product.price">
            R$ {{ formatNumber(product.price) }}
          </p>
          <div class="product-actions">
            <va-button preset="plain" size="small" @click="openProductDialog(product)">
              <i class="mdi mdi-pencil"></i>
            </va-button>
            <va-button preset="plain" size="small" @click="openImagesDialog(product)">
              <i class="mdi mdi-image-multiple"></i>
            </va-button>
            <va-button preset="plain" size="small" color="danger" @click="confirmDelete(product)">
              <i class="mdi mdi-delete"></i>
            </va-button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="products.length === 0" class="empty-state">
      <i :class="getIconClass(schema?.icon)"></i>
      <h3>Nenhum produto cadastrado</h3>
      <p>Adicione produtos para a IA usar como base de conhecimento</p>
      <va-button @click="openProductDialog()">
        <i class="mdi mdi-plus"></i>
        Adicionar Produto
      </va-button>
    </div>
    </template>

    <!-- Dialog Produto -->
    <va-modal
      v-model="showProductDialog"
      :title="editingProduct ? 'Editar Produto' : 'Novo Produto'"
      size="large"
      hide-default-actions
    >
      <div class="product-form">
        <!-- Imagem do Produto -->
        <div class="image-upload-section">
          <label>Imagem Principal</label>
          <div class="image-upload-area">
            <div v-if="pendingImagePreview" class="image-preview">
              <img :src="pendingImagePreview" alt="Preview" />
              <va-button
                v-if="pendingImage"
                preset="plain"
                color="danger"
                size="small"
                class="remove-image-btn"
                @click="removePendingImage"
              >
                <i class="mdi mdi-close"></i>
              </va-button>
            </div>
            <div v-else class="image-placeholder" @click="$refs.productImageInput.click()">
              <i class="mdi mdi-image-plus"></i>
              <span>Clique para adicionar imagem</span>
            </div>
            <input
              type="file"
              accept="image/*"
              @change="selectProductImage"
              ref="productImageInput"
              style="display: none"
            />
            <va-button v-if="!pendingImagePreview" size="small" @click="$refs.productImageInput.click()">
              <i class="mdi mdi-upload"></i>
              Selecionar Imagem
            </va-button>
            <va-button v-else size="small" @click="$refs.productImageInput.click()">
              <i class="mdi mdi-swap-horizontal"></i>
              Trocar Imagem
            </va-button>
          </div>
        </div>

        <!-- Campos fixos obrigatorios -->
        <div class="form-row">
          <div class="form-group col-6">
            <label>Nome *</label>
            <va-input v-model="productForm.name" placeholder="Nome do produto" />
          </div>
          <div class="form-group col-6">
            <label>Preco (R$)</label>
            <va-input v-model="productForm.price" type="number" placeholder="0,00" />
          </div>
        </div>

        <!-- Campos dinamicos do schema -->
        <template v-if="schema && schema.fields && schema.fields.length > 0">
          <div class="schema-fields-section">
            <div class="section-title">
              <i :class="getIconClass(schema.icon)"></i>
              Campos do {{ schema.name }}
            </div>
            <div class="form-row dynamic-fields">
              <div
                v-for="field in schema.fields"
                :key="field.key"
                class="form-group"
                :class="getFieldSizeClass(field)"
              >
                <DynamicField
                  :field="field"
                  v-model="productForm.dynamic_fields[field.key]"
                />
              </div>
            </div>
          </div>
        </template>

        <!-- Descricoes -->
        <div class="form-group">
          <label>Descricao Curta</label>
          <va-input v-model="productForm.short_description" placeholder="Breve descricao do produto..." />
        </div>

        <div class="form-group">
          <label>Descricao Completa</label>
          <va-textarea v-model="productForm.description" :min-rows="3" autosize />
        </div>

        <!-- Opcoes -->
        <div class="form-row">
          <div class="form-group col-6">
            <va-checkbox v-model="productForm.is_available" label="Disponivel" />
          </div>
          <div class="form-group col-6">
            <va-checkbox v-model="productForm.is_featured" label="Destaque" />
          </div>
        </div>
      </div>

      <template #footer>
        <div class="modal-actions">
          <va-button preset="secondary" @click="showProductDialog = false">Cancelar</va-button>
          <va-button @click="saveProduct" :loading="savingProduct">
            <i class="mdi mdi-check"></i>
            {{ editingProduct ? 'Salvar' : 'Criar' }}
          </va-button>
        </div>
      </template>
    </va-modal>

    <!-- Dialog Imagens -->
    <va-modal v-model="showImagesDialog" title="Gerenciar Imagens" size="medium" hide-default-actions>
      <div class="images-manager" v-if="selectedProduct">
        <div class="main-image-section">
          <label>Imagem Principal</label>
          <div class="main-image-area">
            <img v-if="selectedProduct.main_image_url" :src="selectedProduct.main_image_url" />
            <div v-else class="no-image">
              <i class="mdi mdi-image"></i>
              <span>Sem imagem</span>
            </div>
          </div>
          <input type="file" accept="image/*" @change="(e) => uploadImage(e, true)" ref="mainImageInput" style="display: none" />
          <va-button size="small" @click="$refs.mainImageInput.click()">
            <i class="mdi mdi-upload"></i>
            Upload Principal
          </va-button>
        </div>

        <div class="gallery-section">
          <label>Galeria</label>
          <div class="gallery-grid">
            <div v-for="(img, index) in selectedProduct.images_urls" :key="index" class="gallery-item">
              <img :src="img" />
              <va-button
                preset="plain"
                color="danger"
                size="small"
                class="delete-btn"
                @click="deleteImage(index)"
              >
                <i class="mdi mdi-close"></i>
              </va-button>
            </div>
            <div class="gallery-add">
              <input type="file" accept="image/*" @change="(e) => uploadImage(e, false)" ref="galleryImageInput" style="display: none" />
              <va-button preset="plain" @click="$refs.galleryImageInput.click()">
                <i class="mdi mdi-plus"></i>
              </va-button>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <va-button @click="showImagesDialog = false">Fechar</va-button>
      </template>
    </va-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { productsApi } from '@/api/client'
import DynamicField from '@/components/DynamicField.vue'

const props = defineProps(['slug', 'client'])
const toast = useToast()
const { confirm } = useConfirm()

const products = ref([])
const loading = ref(true)
const searchQuery = ref('')
const showProductDialog = ref(false)
const showImagesDialog = ref(false)
const editingProduct = ref(null)
const selectedProduct = ref(null)
const savingProduct = ref(false)
const generatingEmbeddings = ref(false)
const uploadingImage = ref(false)
const schema = ref(null)
const pendingImage = ref(null)
const pendingImagePreview = ref(null)

// Form para criar/editar produto
const productForm = ref({
  name: '',
  price: null,
  short_description: '',
  description: '',
  is_available: true,
  is_featured: false,
  dynamic_fields: {}
})

// Carrega o schema do cliente
const loadSchema = async () => {
  try {
    const { data } = await productsApi.getSchema(props.slug)
    schema.value = data
  } catch (error) {
    console.warn('Schema nao encontrado, usando modo basico')
    schema.value = null
  }
}

// Determina a classe de tamanho para o campo no grid
const getFieldSizeClass = (field) => {
  const type = field.type
  if (type === 'textarea') return 'col-12'
  if (type === 'select' || type === 'date') return 'col-4'
  if (type === 'number') return 'col-3'
  return 'col-4'
}

// Retorna o titulo do produto baseado no schema
const getProductTitle = (product) => {
  if (schema.value?.card_title_field && schema.value.card_title_field !== 'name') {
    const titleField = schema.value.card_title_field
    const dynamicValue = product.dynamic_fields?.[titleField]
    if (dynamicValue) return dynamicValue
  }
  return product.name
}

// Retorna o subtitulo do produto baseado no template do schema
const getProductSubtitle = (product) => {
  if (schema.value?.card_subtitle_template) {
    let subtitle = schema.value.card_subtitle_template
    // Substitui placeholders {field} pelos valores
    const matches = subtitle.match(/\{(\w+)\}/g)
    if (matches) {
      matches.forEach(match => {
        const fieldKey = match.replace(/[{}]/g, '')
        let value = product.dynamic_fields?.[fieldKey] || product[fieldKey] || ''
        // Formata valores especificos
        if (fieldKey === 'mileage' && value) value = `${formatNumber(value)} km`
        if (fieldKey === 'price' && value) value = `R$ ${formatNumber(value)}`
        subtitle = subtitle.replace(match, value)
      })
    }
    // Remove separadores duplos e limpa
    return subtitle.replace(/\s*[-•|]\s*[-•|]\s*/g, ' • ').replace(/^\s*[-•|]\s*|\s*[-•|]\s*$/g, '').trim()
  }
  // Fallback: monta subtitulo dos campos show_in_card
  const parts = []
  if (schema.value?.fields) {
    schema.value.fields.filter(f => f.show_in_card).slice(0, 3).forEach(field => {
      const value = product.dynamic_fields?.[field.key]
      if (value) {
        if (field.rag_format === 'km') parts.push(`${formatNumber(value)} km`)
        else if (field.rag_format === 'currency') parts.push(`R$ ${formatNumber(value)}`)
        else parts.push(value)
      }
    })
  }
  // Fallback legado para veiculos
  if (parts.length === 0) {
    if (product.year) parts.push(`${product.year_fab || product.year}/${product.year}`)
    if (product.mileage) parts.push(`${formatNumber(product.mileage)} km`)
    if (product.color) parts.push(product.color)
  }
  return parts.join(' • ')
}

const loadProducts = async () => {
  try {
    const { data } = await productsApi.list(props.slug, { available_only: false })
    products.value = data
  } catch (error) {
    console.error('Erro ao carregar produtos:', error)
  }
}

const searchProducts = async () => {
  if (!searchQuery.value.trim()) {
    loadProducts()
    return
  }
  try {
    const { data } = await productsApi.search(props.slug, searchQuery.value)
    products.value = data.products
  } catch (error) {
    toast.error('Erro', 'Falha na busca')
  }
}

const openProductDialog = (product = null) => {
  editingProduct.value = product
  // Limpar imagem pendente
  removePendingImage()

  if (product) {
    // Editar produto existente - carregar imagem atual como preview
    productForm.value = {
      name: product.name || '',
      price: product.price,
      short_description: product.short_description || '',
      description: product.description || '',
      is_available: product.is_available !== false,
      is_featured: product.is_featured || false,
      dynamic_fields: { ...(product.dynamic_fields || {}) }
    }
    // Preview da imagem existente
    if (product.main_image_url) {
      pendingImagePreview.value = product.main_image_url
    }
    // Migra campos legados para dynamic_fields se existirem
    if (schema.value?.fields) {
      schema.value.fields.forEach(field => {
        if (productForm.value.dynamic_fields[field.key] === undefined && product[field.key] !== undefined) {
          productForm.value.dynamic_fields[field.key] = product[field.key]
        }
      })
    }
  } else {
    // Novo produto - inicializa dynamic_fields vazios
    const emptyDynamicFields = {}
    if (schema.value?.fields) {
      schema.value.fields.forEach(field => {
        emptyDynamicFields[field.key] = field.type === 'boolean' ? false : (field.type === 'number' ? null : '')
      })
    }
    productForm.value = {
      name: '',
      price: null,
      short_description: '',
      description: '',
      is_available: true,
      is_featured: false,
      dynamic_fields: emptyDynamicFields
    }
  }
  showProductDialog.value = true
}

const saveProduct = async () => {
  if (!productForm.value.name) {
    toast.warn('Atencao', 'Nome e obrigatorio')
    return
  }

  savingProduct.value = true
  try {
    let productId

    if (editingProduct.value) {
      await productsApi.update(props.slug, editingProduct.value.id, productForm.value)
      productId = editingProduct.value.id
      toast.success('Sucesso', 'Produto atualizado!')
    } else {
      const { data } = await productsApi.create(props.slug, productForm.value)
      productId = data.id
      toast.success('Sucesso', 'Produto criado!')
    }

    // Upload da imagem se houver uma nova selecionada
    if (pendingImage.value && productId) {
      try {
        uploadingImage.value = true
        await productsApi.uploadImage(props.slug, productId, pendingImage.value, true)
        toast.success('Imagem', 'Imagem enviada com sucesso!')
      } catch (imgError) {
        toast.warn('Aviso', 'Produto salvo mas falha no upload da imagem')
      } finally {
        uploadingImage.value = false
      }
    }

    showProductDialog.value = false
    removePendingImage()
    loadProducts()
  } catch (error) {
    toast.error('Erro', 'Falha ao salvar')
  } finally {
    savingProduct.value = false
  }
}

const confirmDelete = (product) => {
  confirm({
    message: `Excluir "${product.name}"?`,
    header: 'Confirmar Exclusao',
    icon: 'mdi-delete',
    accept: async () => {
      try {
        await productsApi.delete(props.slug, product.id)
        toast.success('Sucesso', 'Produto excluido!')
        loadProducts()
      } catch (error) {
        toast.error('Erro', 'Falha ao excluir')
      }
    }
  })
}

const openImagesDialog = (product) => {
  selectedProduct.value = product
  showImagesDialog.value = true
}

const uploadImage = async (event, isMain) => {
  const file = event.target.files[0]
  if (!file) return

  try {
    await productsApi.uploadImage(props.slug, selectedProduct.value.id, file, isMain)
    toast.success('Sucesso', 'Imagem enviada!')
    loadProducts()
    const { data } = await productsApi.get(props.slug, selectedProduct.value.id)
    selectedProduct.value = data
  } catch (error) {
    toast.error('Erro', 'Falha no upload')
  }

  event.target.value = ''
}

const deleteImage = async (index) => {
  try {
    await productsApi.deleteImage(props.slug, selectedProduct.value.id, index)
    toast.success('Sucesso', 'Imagem removida!')
    const { data } = await productsApi.get(props.slug, selectedProduct.value.id)
    selectedProduct.value = data
    loadProducts()
  } catch (error) {
    toast.error('Erro', 'Falha ao remover')
  }
}

const generateAllEmbeddings = async () => {
  generatingEmbeddings.value = true
  try {
    const { data } = await productsApi.generateAllEmbeddings(props.slug)
    toast.success('Sucesso', `${data.generated} embeddings gerados!`)
  } catch (error) {
    toast.error('Erro', 'Falha ao gerar embeddings')
  } finally {
    generatingEmbeddings.value = false
  }
}

const formatNumber = (num) => {
  return new Intl.NumberFormat('pt-BR').format(num)
}

// Formata classe do icone corretamente
const getIconClass = (icon) => {
  if (!icon) return 'mdi mdi-package'
  if (icon.startsWith('mdi ')) return icon
  if (icon.startsWith('mdi-')) return 'mdi ' + icon
  return 'mdi mdi-' + icon
}

const loadData = async () => {
  loading.value = true
  try {
    await loadSchema()
    await loadProducts()
  } finally {
    loading.value = false
  }
}

// Seleciona imagem para upload (antes de salvar o produto)
const selectProductImage = (event) => {
  const file = event.target.files[0]
  if (!file) return

  pendingImage.value = file
  pendingImagePreview.value = URL.createObjectURL(file)
  event.target.value = ''
}

// Remove imagem selecionada
const removePendingImage = () => {
  if (pendingImagePreview.value) {
    URL.revokeObjectURL(pendingImagePreview.value)
  }
  pendingImage.value = null
  pendingImagePreview.value = null
}

watch(() => props.slug, loadData)

onMounted(loadData)
</script>

<style lang="scss" scoped>
// Loading State
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  gap: 1.5rem;

  p {
    color: var(--text-secondary);
    font-size: 1rem;
  }
}

// Image Upload Section
.image-upload-section {
  margin-bottom: 1.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--border-color);

  > label {
    display: block;
    font-weight: 500;
    color: var(--text-dark);
    font-size: 0.875rem;
    margin-bottom: 0.75rem;
  }
}

.image-upload-area {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
}

.image-preview {
  position: relative;
  width: 150px;
  height: 150px;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--border-color);

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .remove-image-btn {
    position: absolute;
    top: 0.25rem;
    right: 0.25rem;
    background: rgba(0, 0, 0, 0.5);
    border-radius: 50%;
  }
}

.image-placeholder {
  width: 150px;
  height: 150px;
  border: 2px dashed var(--border-color);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  cursor: pointer;
  transition: all 0.2s ease;

  i {
    font-size: 2rem;
    color: var(--text-muted);
  }

  span {
    font-size: 0.75rem;
    color: var(--text-muted);
    text-align: center;
  }

  &:hover {
    border-color: var(--primary-color);
    background: var(--surface-light);

    i, span {
      color: var(--primary-color);
    }
  }
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.search-area {
  display: flex;
  gap: 0.5rem;
}

.actions-area {
  display: flex;
  gap: 0.5rem;
}

.products-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
}

.product-card {
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--border-color);
  transition: transform 0.2s, box-shadow 0.2s;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  }

  .product-image {
    position: relative;
    height: 180px;
    background: var(--surface-light);

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .no-image {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--text-muted);

      i {
        font-size: 3rem;
      }
    }

    .sold-badge {
      position: absolute;
      top: 0.5rem;
      right: 0.5rem;
    }

    .featured-badge {
      position: absolute;
      top: 0.5rem;
      left: 0.5rem;
    }
  }

  .product-info {
    padding: 1rem;

    h3 {
      font-size: 1.1rem;
      margin-bottom: 0.5rem;
      color: var(--text-dark);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .product-details {
      font-size: 0.9rem;
      color: var(--text-secondary);
      margin-bottom: 0.5rem;

      span:not(:last-child)::after {
        content: ' • ';
      }
    }

    .product-price {
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--primary-color);
      margin-bottom: 0.5rem;
    }

    .product-actions {
      display: flex;
      gap: 0.25rem;
    }
  }
}

// Product Form
.product-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-row {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 1;

  label {
    font-weight: 500;
    color: var(--text-dark);
    font-size: 0.875rem;
  }

  &.col-3 { flex: 0 0 calc(25% - 0.75rem); }
  &.col-4 { flex: 0 0 calc(33.33% - 0.67rem); }
  &.col-6 { flex: 0 0 calc(50% - 0.5rem); }
  &.col-12 { flex: 0 0 100%; }
}

// Schema Fields Section
.schema-fields-section {
  background: var(--surface-light);
  border-radius: var(--radius-md);
  padding: 1rem;
  margin: 0.5rem 0;

  .section-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 600;
    color: var(--text-dark);
    margin-bottom: 1rem;
    font-size: 0.9rem;

    i {
      color: var(--primary-color);
    }
  }

  .dynamic-fields {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
  }
}

// Images Manager
.images-manager {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.main-image-section {
  label {
    display: block;
    font-weight: 500;
    margin-bottom: 0.75rem;
    color: var(--text-dark);
  }
}

.main-image-area {
  height: 200px;
  background: var(--surface-light);
  border-radius: var(--radius-md);
  overflow: hidden;
  margin-bottom: 0.75rem;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .no-image {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    color: var(--text-muted);

    i {
      font-size: 2rem;
    }
  }
}

.gallery-section {
  label {
    display: block;
    font-weight: 500;
    margin-bottom: 0.75rem;
    color: var(--text-dark);
  }
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.75rem;

  .gallery-item {
    position: relative;
    aspect-ratio: 1;
    border-radius: var(--radius-md);
    overflow: hidden;

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .delete-btn {
      position: absolute;
      top: 0.25rem;
      right: 0.25rem;
    }
  }

  .gallery-add {
    aspect-ratio: 1;
    border: 2px dashed var(--border-color);
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
  }
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
}
</style>
