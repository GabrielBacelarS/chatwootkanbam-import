<template>
  <div class="ia-config">
    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <va-progress-circle indeterminate size="large" />
      <p>Carregando configuracoes...</p>
    </div>

    <div v-else class="grid-2">
      <!-- Coluna Esquerda: Configurações -->
      <div class="card">
        <div class="card-header">
          <h2>Configuracoes da IA</h2>
          <div class="ia-toggle">
            <span class="toggle-label">{{ config.enabled ? 'Ativo' : 'Inativo' }}</span>
            <va-switch v-model="config.enabled" />
          </div>
        </div>

        <div class="form-section">
          <h3>Provedor</h3>
          <div class="form-row">
            <div class="form-group flex-1">
              <label>Provedor de IA</label>
              <va-select
                v-model="config.provider"
                :options="providers"
                text-by="label"
                value-by="value"
              />
            </div>
            <div class="form-group flex-1">
              <label>Modelo</label>
              <va-select
                v-model="config.model"
                :options="models"
                text-by="label"
                value-by="value"
              />
            </div>
          </div>

          <div class="form-group">
            <label>API Key</label>
            <va-input
              v-model="config.api_key"
              :type="showApiKey ? 'text' : 'password'"
            >
              <template #appendInner>
                <va-button preset="plain" size="small" @click="showApiKey = !showApiKey">
                  <i :class="showApiKey ? 'mdi mdi-eye-off' : 'mdi mdi-eye'"></i>
                </va-button>
              </template>
            </va-input>
          </div>
        </div>

        <div class="form-section">
          <h3>Comportamento</h3>

          <!-- System Prompt -->
          <div class="form-group mb-3">
            <div class="prompt-header">
              <label>System Prompt</label>
              <div class="prompt-actions">
                <va-button v-if="!editingPrompt" preset="plain" size="small" @click="editingPrompt = true">
                  <i class="mdi mdi-pencil"></i>
                  Editar
                </va-button>
                <va-button v-if="editingPrompt" preset="plain" size="small" @click="editingPrompt = false">
                  <i class="mdi mdi-eye"></i>
                  Preview
                </va-button>
                <va-button preset="plain" size="small" @click="openPromptEditor">
                  <i class="mdi mdi-arrow-expand"></i>
                </va-button>
              </div>
            </div>

            <!-- Modo Edição -->
            <div v-if="editingPrompt" class="prompt-edit-area">
              <va-textarea
                v-model="config.system_prompt"
                :min-rows="10"
                autosize
                placeholder="Voce e um assistente virtual da empresa X.&#10;Seja educado e prestativo.&#10;Responda apenas sobre nossos produtos."
                class="prompt-textarea"
              />
              <div class="prompt-stats">
                <span>{{ config.system_prompt?.length || 0 }} caracteres</span>
                <span>{{ promptLineCount }} linhas</span>
              </div>
            </div>

            <!-- Modo Preview -->
            <div v-else class="prompt-preview-wrapper">
              <div class="prompt-preview" :class="{ expanded: promptExpanded }" @click="editingPrompt = true">
                <pre class="prompt-content">{{ config.system_prompt || 'Clique para adicionar um prompt...' }}</pre>
                <div v-if="!promptExpanded && isPromptLong" class="prompt-fade"></div>
                <div class="edit-overlay">
                  <i class="mdi mdi-pencil"></i>
                  <span>Clique para editar</span>
                </div>
              </div>

              <button v-if="isPromptLong" class="expand-btn" @click.stop="promptExpanded = !promptExpanded">
                <i :class="promptExpanded ? 'mdi mdi-chevron-up' : 'mdi mdi-chevron-down'"></i>
                {{ promptExpanded ? 'Mostrar menos' : `Mostrar mais (${promptLineCount} linhas)` }}
              </button>
            </div>
          </div>

          <div class="form-group mb-3">
            <label>Mensagem de Boas-vindas</label>
            <va-input v-model="config.welcome_message" placeholder="Ola! Como posso ajudar?" />
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>Atribuir a Agente (nome)</label>
              <va-input v-model="config.required_assignee_name" placeholder="Ex: I.A" />
              <small class="hint-text">IA so responde quando atribuida a este agente</small>
            </div>

            <div class="form-group">
              <label>Equipe para Transferencia (ID)</label>
              <va-input v-model="config.transfer_team_id" type="number" placeholder="ID da equipe" />
              <small class="hint-text">Round-robin entre membros</small>
            </div>
          </div>
        </div>

        <div class="form-section">
          <h3>Palavras de Transferencia</h3>
          <VaChipsInput v-model="config.transfer_keywords" placeholder="Digite e pressione Enter" />
          <small class="hint-text">
            <strong>2 funcoes:</strong><br>
            1. Quando o <strong>cliente</strong> digitar essas palavras, transfere imediatamente<br>
            2. Quando a <strong>IA</strong> usar essas palavras na resposta, transfere para humano
          </small>
        </div>

        <div class="form-section">
          <h3>Quebra de Mensagens</h3>
          <p class="hint-text mb-3">
            Configure como a IA divide mensagens longas em partes menores para WhatsApp/Chat.
          </p>

          <div class="split-modes">
            <div
              v-for="mode in splitModes"
              :key="mode.value"
              class="split-mode-card"
              :class="{ active: config.split_mode === mode.value }"
              @click="config.split_mode = mode.value"
            >
              <div class="mode-header">
                <va-radio
                  :model-value="config.split_mode"
                  :option="mode.value"
                  @update:model-value="config.split_mode = mode.value"
                />
                <i :class="mode.icon"></i>
                <span class="mode-name">{{ mode.label }}</span>
              </div>
              <p class="mode-desc">{{ mode.description }}</p>
            </div>
          </div>

          <div v-if="config.split_mode !== 'none' && config.split_mode !== 'paragraph'" class="form-row mt-3">
            <div class="form-group">
              <label>Limite de caracteres por mensagem</label>
              <va-input v-model="config.split_message_at" type="number" :min="100" :max="4000" />
              <small class="hint-text">WhatsApp suporta até 4096 caracteres</small>
            </div>
          </div>
        </div>

        <div class="form-section">
          <h3>Ferramentas do Agente</h3>
          <p class="hint-text mb-3">Selecione quais ferramentas o agente pode usar durante as conversas</p>

          <div class="tools-grid">
            <div class="tool-card" :class="{ active: isToolEnabled('buscar_produtos') }">
              <div class="tool-header">
                <va-checkbox
                  :model-value="isToolEnabled('buscar_produtos')"
                  @update:model-value="toggleTool('buscar_produtos')"
                />
                <i class="mdi mdi-magnify"></i>
                <span class="tool-name">Buscar Produtos</span>
              </div>
              <p class="tool-desc">Busca produtos/veiculos no estoque quando o cliente perguntar</p>
            </div>

            <div class="tool-card" :class="{ active: isToolEnabled('calcular_financiamento') }">
              <div class="tool-header">
                <va-checkbox
                  :model-value="isToolEnabled('calcular_financiamento')"
                  @update:model-value="toggleTool('calcular_financiamento')"
                />
                <i class="mdi mdi-calculator"></i>
                <span class="tool-name">Calcular Financiamento</span>
              </div>
              <p class="tool-desc">Simula parcelas e financiamento de produtos</p>
            </div>

            <div class="tool-card" :class="{ active: isToolEnabled('enviar_imagem') }">
              <div class="tool-header">
                <va-checkbox
                  :model-value="isToolEnabled('enviar_imagem')"
                  @update:model-value="toggleTool('enviar_imagem')"
                />
                <i class="mdi mdi-image"></i>
                <span class="tool-name">Enviar Imagem</span>
              </div>
              <p class="tool-desc">Envia fotos dos produtos para o cliente</p>
            </div>

            <div class="tool-card" :class="{ active: isToolEnabled('agendar_visita') }">
              <div class="tool-header">
                <va-checkbox
                  :model-value="isToolEnabled('agendar_visita')"
                  @update:model-value="toggleTool('agendar_visita')"
                />
                <i class="mdi mdi-calendar-check"></i>
                <span class="tool-name">Agendar Visita</span>
              </div>
              <p class="tool-desc">Agenda visitas do cliente a loja</p>
            </div>

            <div class="tool-card" :class="{ active: isToolEnabled('transferir_atendimento') }">
              <div class="tool-header">
                <va-checkbox
                  :model-value="isToolEnabled('transferir_atendimento')"
                  @update:model-value="toggleTool('transferir_atendimento')"
                />
                <i class="mdi mdi-account-switch"></i>
                <span class="tool-name">Transferir Atendimento</span>
              </div>
              <p class="tool-desc">Transfere para atendente humano quando cliente quer fechar negocio</p>
            </div>
          </div>
        </div>

        <div class="form-section">
          <h3>Deteccao de Intencao de Busca</h3>
          <p class="hint-text mb-3">
            Como a IA identifica quando o cliente quer ver produtos/precos.
          </p>

          <div class="intent-modes">
            <div
              v-for="mode in intentModes"
              :key="mode.value"
              class="intent-mode-card"
              :class="{ active: config.intent_detection_mode === mode.value }"
              @click="config.intent_detection_mode = mode.value"
            >
              <div class="mode-header">
                <va-radio
                  :model-value="config.intent_detection_mode"
                  :option="mode.value"
                  @update:model-value="config.intent_detection_mode = mode.value"
                />
                <i :class="mode.icon"></i>
                <span class="mode-name">{{ mode.label }}</span>
                <va-badge v-if="mode.recommended" text="Novo" color="success" class="ml-2" />
              </div>
              <p class="mode-desc">{{ mode.description }}</p>
            </div>
          </div>

          <!-- Keywords - so mostra se modo for 'keywords' -->
          <div v-if="config.intent_detection_mode === 'keywords'" class="keywords-section mt-3">
            <label>Palavras-chave do Negocio</label>
            <VaChipsInput v-model="config.product_keywords" placeholder="Digite e pressione Enter" />
            <div class="keywords-examples">
              <small class="hint-text">
                <strong>Exemplos por ramo:</strong><br>
                Veiculos: carro, carros, veiculo, km, modelo<br>
                Ar Condicionado: ar, split, btu, instalacao, inverter<br>
                Roupas: roupa, camisa, tamanho, cor, vestido
              </small>
            </div>
          </div>
        </div>

        <div class="form-section">
          <h3>Tempo de Espera (Debounce)</h3>
          <p class="hint-text mb-3">
            Tempo em segundos que a IA aguarda para agrupar mensagens antes de responder.
            Util quando o cliente envia varias mensagens seguidas.
          </p>
          <div class="form-row">
            <div class="form-group">
              <label>Segundos</label>
              <va-input v-model="config.debounce_seconds" type="number" :min="1" :max="30" step="0.5" />
            </div>
            <div class="form-group debounce-info">
              <small class="hint-text">
                <strong>Recomendado:</strong> 5-10 segundos<br>
                Muito baixo: IA responde antes do cliente terminar<br>
                Muito alto: Cliente espera demais
              </small>
            </div>
          </div>
        </div>

        <div class="form-section">
          <h3>Follow-up Automatico</h3>
          <p class="hint-text mb-3">
            Envia mensagens automaticas quando o cliente nao responde apos um periodo.
            A IA analisa a conversa e gera um follow-up contextualizado.
          </p>

          <div class="followup-toggle mb-3">
            <va-switch v-model="config.followup_enabled" />
            <span class="toggle-label">{{ config.followup_enabled ? 'Ativado' : 'Desativado' }}</span>
          </div>

          <div v-if="config.followup_enabled" class="followup-settings">
            <div class="form-row">
              <div class="form-group">
                <label>Maximo de follow-ups</label>
                <va-input v-model="config.followup_max_count" type="number" :min="1" :max="10" />
                <small class="hint-text">Quantas mensagens de follow-up enviar por conversa</small>
              </div>
              <div class="form-group">
                <label>Tempo de espera</label>
                <div class="time-inputs">
                  <div class="time-input-group">
                    <va-input v-model="config.followup_delay_hours" type="number" :min="0" :max="168" />
                    <span class="time-label">horas</span>
                  </div>
                  <div class="time-input-group">
                    <va-input v-model="config.followup_delay_minutes" type="number" :min="0" :max="59" />
                    <span class="time-label">min</span>
                  </div>
                </div>
                <small class="hint-text">Tempo entre follow-ups</small>
              </div>
            </div>

            <div class="form-group mt-3">
              <label>Mensagem personalizada (opcional)</label>
              <va-textarea
                v-model="config.followup_message_template"
                :min-rows="2"
                placeholder="Deixe vazio para IA gerar automaticamente com base na conversa..."
              />
              <small class="hint-text">
                Se vazio, a IA analisa a conversa e gera uma mensagem contextualizada.
              </small>
            </div>
          </div>
        </div>

        <div class="form-actions mt-4">
          <va-button @click="saveConfig" :loading="saving">
            <i class="mdi mdi-content-save"></i>
            Salvar Configuracoes
          </va-button>
          <va-button preset="secondary" @click="openWebhookDialog">
            <i class="mdi mdi-webhook"></i>
            Configurar Webhook
          </va-button>
        </div>
      </div>

      <!-- Coluna Direita: Base de Conhecimento e Teste -->
      <div class="column-right">
        <!-- Base de Conhecimento -->
        <div class="card">
          <div class="card-header">
            <h2>Base de Conhecimento</h2>
            <va-file-upload
              type="single"
              file-types=".txt,.md,.json"
              @file-added="uploadKnowledge"
            >
              <va-button size="small">
                <i class="mdi mdi-upload"></i>
                Upload
              </va-button>
            </va-file-upload>
          </div>

          <!-- Adicionar URL externa -->
          <div class="url-import-section">
            <div class="url-input-row">
              <va-input
                v-model="knowledgeUrl"
                placeholder="https://exemplo.com/pagina"
                class="flex-1"
              >
                <template #prependInner>
                  <i class="mdi mdi-link-variant" style="color: var(--text-secondary);"></i>
                </template>
              </va-input>
              <va-button size="small" @click="addKnowledgeFromUrl" :loading="importingUrl" :disabled="!knowledgeUrl.trim()">
                <i class="mdi mdi-plus"></i>
                Importar
              </va-button>
            </div>
            <small class="hint-text">Importe conteudo de paginas web para a base de conhecimento</small>
          </div>

          <div v-if="knowledgeFiles.length === 0" class="empty-state" style="padding: 1.5rem;">
            <i class="mdi mdi-file-document-outline"></i>
            <p>Nenhum arquivo ou link carregado</p>
          </div>

          <div v-else class="knowledge-list">
            <div v-for="file in knowledgeFiles" :key="file.id" class="knowledge-item">
              <i :class="file.source_url ? 'mdi mdi-link-variant' : 'mdi mdi-file-document-edit'"></i>
              <div class="flex-1">
                <span class="font-medium">{{ file.filename }}</span>
                <small v-if="file.source_url" class="block hint-text url-truncate">{{ file.source_url }}</small>
                <small class="block hint-text">{{ formatSize(file.file_size) }}</small>
              </div>
              <va-button preset="plain" color="danger" size="small" @click="deleteKnowledge(file.id)">
                <i class="mdi mdi-delete"></i>
              </va-button>
            </div>
          </div>
        </div>

        <!-- Teste da IA -->
        <div class="card">
          <div class="card-header">
            <h2>Testar IA</h2>
            <va-button v-if="testMessages.length > 0" preset="plain" size="small" @click="testMessages = []">
              <i class="mdi mdi-delete"></i>
            </va-button>
          </div>

          <div class="test-area">
            <div class="test-messages" ref="messagesContainer">
              <div v-if="testMessages.length === 0" class="test-empty">
                <i class="mdi mdi-message-text-outline"></i>
                <p>Envie uma mensagem para testar a IA</p>
              </div>
              <div v-for="(msg, i) in testMessages" :key="i" :class="['message', msg.role]">
                <div class="message-content">{{ msg.content }}</div>
              </div>
            </div>

            <div class="test-input">
              <va-input
                v-model="testMessage"
                placeholder="Digite uma mensagem..."
                @keyup.enter="sendTestMessage"
              />
              <va-button @click="sendTestMessage" :loading="testing" :disabled="!testMessage.trim()">
                <i class="mdi mdi-send"></i>
              </va-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Dialog Webhook -->
    <va-modal v-model="showWebhookDialog" title="Configurar Webhook" size="medium" hide-default-actions>
      <div class="webhook-setup">
        <div class="webhook-info">
          <i class="mdi mdi-webhook"></i>
          <p>Configure o webhook no Chatwoot para que a IA receba as mensagens automaticamente.</p>
        </div>

        <div class="webhook-url-box">
          <label>URL do Webhook</label>
          <div class="url-input-group">
            <va-input v-model="webhookUrl" class="url-input" />
            <va-button preset="secondary" @click="copyWebhookUrl" title="Copiar URL">
              <i class="mdi mdi-content-copy"></i>
            </va-button>
          </div>
          <small class="hint-text">
            <i class="mdi mdi-information-outline"></i>
            Esta URL sera registrada automaticamente no Chatwoot
          </small>
        </div>

        <div class="webhook-manual">
          <details>
            <summary>Configuracao manual (se necessario)</summary>
            <div class="manual-content">
              <p>Se a configuracao automatica falhar, copie a URL acima e configure manualmente:</p>
              <ol>
                <li>Acesse seu Chatwoot</li>
                <li>Va em <strong>Configuracoes &gt; Integracoes &gt; Webhooks</strong></li>
                <li>Clique em "Adicionar novo webhook"</li>
                <li>Cole a URL e selecione o evento <code>message_created</code></li>
              </ol>
            </div>
          </details>
        </div>
      </div>

      <template #footer>
        <div class="modal-actions">
          <va-button preset="secondary" @click="showWebhookDialog = false">Cancelar</va-button>
          <va-button @click="setupWebhook" :loading="settingUpWebhook" color="success">
            <i class="mdi mdi-check"></i>
            Configurar Automaticamente
          </va-button>
        </div>
      </template>
    </va-modal>

    <!-- Dialog Editor de Prompt (Fullscreen) -->
    <va-modal v-model="showPromptEditor" title="Editar System Prompt" size="large" hide-default-actions>
      <div class="prompt-editor">
        <div class="editor-toolbar">
          <span class="char-count">{{ config.system_prompt?.length || 0 }} caracteres</span>
          <span class="line-count">{{ promptLineCount }} linhas</span>
        </div>
        <va-textarea
          v-model="config.system_prompt"
          class="fullscreen-textarea"
          :min-rows="20"
          placeholder="Digite o system prompt aqui..."
        />
      </div>

      <template #footer>
        <va-button @click="showPromptEditor = false">
          <i class="mdi mdi-close"></i>
          Fechar
        </va-button>
      </template>
    </va-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useToast } from '@/composables/useToast'
import { aiApi, getApiBaseUrl } from '@/api/client'
import VaChipsInput from '@/components/VaChipsInput.vue'

const props = defineProps(['slug', 'client'])
const emit = defineEmits(['refresh'])
const toast = useToast()

const messagesContainer = ref(null)
const showApiKey = ref(false)

const config = ref({
  enabled: false,
  provider: 'openai',
  api_key: '',
  model: 'gpt-4o-mini',
  system_prompt: '',
  welcome_message: '',
  transfer_keywords: ['consultor', 'especialista humano', 'transferindo', 'encaminhando para'],
  max_messages_before_transfer: 10,
  only_unassigned: true,
  split_message_at: 1000,
  split_by_paragraph: true,
  split_mode: 'smart',
  required_assignee_name: '',
  transfer_team_id: null,
  enabled_tools: ['buscar_produtos', 'calcular_financiamento', 'enviar_imagem', 'agendar_visita', 'transferir_atendimento'],
  product_keywords: ['produto', 'produtos', 'estoque', 'disponivel', 'preco', 'precos', 'quanto', 'valor', 'tem', 'quais'],
  debounce_seconds: 10,
  intent_detection_mode: 'keywords',
  // Follow-up settings
  followup_enabled: false,
  followup_max_count: 3,
  followup_delay_hours: 24,
  followup_delay_minutes: 0,
  followup_message_template: ''
})

const knowledgeFiles = ref([])
const knowledgeUrl = ref('')
const importingUrl = ref(false)
const loading = ref(true)
const saving = ref(false)
const testing = ref(false)
const testMessage = ref('')
const testMessages = ref([])
const showWebhookDialog = ref(false)
const webhookUrl = ref('')
const settingUpWebhook = ref(false)

// Prompt editor state
const promptExpanded = ref(false)
const showPromptEditor = ref(false)
const editingPrompt = ref(false)

const providers = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'Google Gemini', value: 'gemini' }
]

const models = [
  { label: 'GPT-4o Mini', value: 'gpt-4o-mini' },
  { label: 'GPT-4o', value: 'gpt-4o' },
  { label: 'GPT-4 Turbo', value: 'gpt-4-turbo' },
  { label: 'Gemini 1.5 Flash', value: 'gemini-1.5-flash' },
  { label: 'Gemini 1.5 Pro', value: 'gemini-1.5-pro' }
]

const splitModes = [
  {
    value: 'smart',
    label: 'Inteligente',
    icon: 'mdi mdi-auto-fix',
    description: 'Quebra por paragrafos, depois por sentencas, respeitando o limite de caracteres. Recomendado.'
  },
  {
    value: 'paragraph',
    label: 'Por Paragrafos',
    icon: 'mdi mdi-text-box-outline',
    description: 'Cada paragrafo vira uma mensagem separada. Ignora limite de caracteres.'
  },
  {
    value: 'sentence',
    label: 'Por Sentencas',
    icon: 'mdi mdi-format-text',
    description: 'Quebra em pontos finais (. ! ?) respeitando o limite de caracteres.'
  },
  {
    value: 'character',
    label: 'Por Caracteres',
    icon: 'mdi mdi-format-letter-spacing',
    description: 'Quebra apenas pelo limite de caracteres, cortando onde necessario.'
  },
  {
    value: 'none',
    label: 'Sem Quebra',
    icon: 'mdi mdi-message-text',
    description: 'Envia a mensagem completa sem dividir. Cuidado com mensagens muito longas.'
  }
]

const intentModes = [
  {
    value: 'auto',
    label: 'Inteligente (IA)',
    icon: 'mdi mdi-brain',
    description: 'A IA analisa a mensagem e decide automaticamente quando buscar produtos. Mais preciso, sem necessidade de configurar palavras-chave.',
    recommended: true
  },
  {
    value: 'keywords',
    label: 'Por Palavras-chave',
    icon: 'mdi mdi-tag-text',
    description: 'Busca produtos quando detecta palavras especificas na mensagem. Requer configurar a lista de palavras.',
    recommended: false
  },
  {
    value: 'always',
    label: 'Sempre Buscar',
    icon: 'mdi mdi-magnify',
    description: 'Sempre consulta os produtos em qualquer mensagem. Util para catalogos pequenos.',
    recommended: false
  }
]

// Computed
const promptLineCount = computed(() => {
  return (config.value.system_prompt || '').split('\n').length
})

const isPromptLong = computed(() => {
  return promptLineCount.value > 10 || (config.value.system_prompt?.length || 0) > 500
})

// Methods
const openPromptEditor = () => {
  showPromptEditor.value = true
}

const isToolEnabled = (toolName) => {
  return config.value.enabled_tools?.includes(toolName) ?? false
}

const toggleTool = (toolName) => {
  if (!config.value.enabled_tools) {
    config.value.enabled_tools = []
  }
  const index = config.value.enabled_tools.indexOf(toolName)
  if (index === -1) {
    config.value.enabled_tools.push(toolName)
  } else {
    config.value.enabled_tools.splice(index, 1)
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const loadConfig = async () => {
  try {
    const { data } = await aiApi.getConfig(props.slug)
    config.value = { ...config.value, ...data }
  } catch (error) {
    console.error('Erro ao carregar config:', error)
  }
}

const loadKnowledge = async () => {
  try {
    const { data } = await aiApi.listKnowledge(props.slug)
    knowledgeFiles.value = data
  } catch (error) {
    console.error('Erro ao carregar arquivos:', error)
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    await aiApi.saveConfig(props.slug, config.value)
    toast.success('Sucesso', 'Configuracoes salvas!')
    emit('refresh')
  } catch (error) {
    toast.error('Erro', 'Falha ao salvar')
  } finally {
    saving.value = false
  }
}

const uploadKnowledge = async (file) => {
  try {
    await aiApi.uploadKnowledge(props.slug, file)
    toast.success('Sucesso', 'Arquivo enviado!')
    loadKnowledge()
  } catch (error) {
    toast.error('Erro', 'Falha no upload')
  }
}

const deleteKnowledge = async (fileId) => {
  try {
    await aiApi.deleteKnowledge(props.slug, fileId)
    toast.success('Sucesso', 'Arquivo removido!')
    loadKnowledge()
  } catch (error) {
    toast.error('Erro', 'Falha ao remover')
  }
}

const addKnowledgeFromUrl = async () => {
  if (!knowledgeUrl.value.trim()) return
  importingUrl.value = true
  try {
    await aiApi.addKnowledgeUrl(props.slug, knowledgeUrl.value.trim())
    toast.success('Sucesso', 'Conteudo importado da URL!')
    knowledgeUrl.value = ''
    loadKnowledge()
  } catch (error) {
    const detail = error.response?.data?.detail || 'Falha ao importar URL'
    toast.error('Erro', detail)
  } finally {
    importingUrl.value = false
  }
}

const sendTestMessage = async () => {
  if (!testMessage.value.trim()) return

  const msg = testMessage.value
  testMessages.value.push({ role: 'user', content: msg })
  testMessage.value = ''
  testing.value = true
  scrollToBottom()

  try {
    const { data } = await aiApi.testAI(props.slug, msg)
    testMessages.value.push({ role: 'assistant', content: data.response })
  } catch (error) {
    testMessages.value.push({ role: 'assistant', content: 'Erro: ' + (error.response?.data?.detail || 'Falha ao testar') })
  } finally {
    testing.value = false
    scrollToBottom()
  }
}

const openWebhookDialog = () => {
  // Usar URL da API (ngrok) para o webhook
  const baseUrl = getApiBaseUrl()
  webhookUrl.value = `${baseUrl}/webhook/${props.slug}`
  showWebhookDialog.value = true
}

const copyWebhookUrl = async () => {
  try {
    await navigator.clipboard.writeText(webhookUrl.value)
    toast.success('Copiado', 'URL copiada para a area de transferencia')
  } catch (error) {
    toast.error('Erro', 'Falha ao copiar URL')
  }
}

const setupWebhook = async () => {
  settingUpWebhook.value = true
  try {
    const result = await aiApi.setupWebhook(props.slug, webhookUrl.value)
    if (result.data.action === 'created') {
      toast.success('Sucesso', 'Webhook criado no Chatwoot!')
    } else {
      toast.success('Sucesso', 'Webhook atualizado no Chatwoot!')
    }
    showWebhookDialog.value = false
  } catch (error) {
    toast.error('Erro', error.response?.data?.detail || 'Falha ao configurar webhook. Tente configurar manualmente.')
  } finally {
    settingUpWebhook.value = false
  }
}

const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const loadData = async () => {
  loading.value = true
  try {
    await Promise.all([loadConfig(), loadKnowledge()])
  } finally {
    loading.value = false
  }
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

.column-right {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

// IA Toggle
.ia-toggle {
  display: flex;
  align-items: center;
  gap: 0.75rem;

  .toggle-label {
    font-size: 0.85rem;
    font-weight: 600;
    padding: 0.25rem 0.75rem;
    border-radius: var(--radius-sm);
  }
}

// Form styles
.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;

  label {
    font-weight: 500;
    color: var(--text-dark);
    font-size: 0.875rem;
  }

  &.checkbox-group {
    justify-content: center;
  }
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.form-actions {
  display: flex;
  gap: 0.75rem;
}

// Hint text
.hint-text {
  color: var(--text-secondary);
  font-size: 0.8rem;
  line-height: 1.4;
}

.dialog-text {
  color: var(--text-secondary);
  line-height: 1.5;
}

// Prompt Header
.prompt-header {
  display: flex;
  align-items: center;
  justify-content: space-between;

  label {
    font-weight: 500;
    color: var(--text-dark);
  }

  .prompt-actions {
    display: flex;
    gap: 0.25rem;
  }
}

// Prompt Edit Area
.prompt-edit-area {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;

  .prompt-textarea {
    font-family: 'Fira Code', 'Monaco', 'Consolas', monospace;
    font-size: 0.85rem;
    line-height: 1.6;
    min-height: 200px;
  }

  .prompt-stats {
    display: flex;
    gap: 1rem;
    justify-content: flex-end;

    span {
      font-size: 0.75rem;
      color: var(--text-secondary);
      padding: 0.25rem 0.5rem;
      background: var(--surface-light);
      border-radius: var(--radius-sm);
    }
  }
}

// Prompt Preview Wrapper
.prompt-preview-wrapper {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

// Prompt Preview
.prompt-preview {
  position: relative;
  max-height: 200px;
  overflow: hidden;
  background: var(--surface-light);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  transition: all 0.3s ease;
  cursor: pointer;

  &:hover {
    border-color: var(--primary-color);

    .edit-overlay {
      opacity: 1;
    }
  }

  &.expanded {
    max-height: none;
  }

  .prompt-content {
    margin: 0;
    padding: 1rem;
    font-family: 'Fira Code', 'Monaco', 'Consolas', monospace;
    font-size: 0.85rem;
    line-height: 1.6;
    color: var(--text-dark);
    white-space: pre-wrap;
    word-break: break-word;
  }

  .prompt-fade {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 60px;
    background: linear-gradient(transparent, var(--surface-light));
    pointer-events: none;
  }

  .edit-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(99, 102, 241, 0.1);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    opacity: 0;
    transition: opacity 0.2s ease;

    i {
      font-size: 1.5rem;
      color: var(--primary-color);
    }

    span {
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--primary-color);
    }
  }
}

// Expand Button
.expand-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.625rem 1rem;
  background: transparent;
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    border-color: var(--primary-color);
    color: var(--primary-color);
    background: var(--primary-50);
  }
}

// Prompt Editor (Fullscreen Dialog)
.prompt-editor {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;

  .editor-toolbar {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--border-color);

    .char-count, .line-count {
      font-size: 0.8rem;
      color: var(--text-muted);
      padding: 0.25rem 0.75rem;
      background: var(--surface-light);
      border-radius: var(--radius-sm);
    }
  }

  .fullscreen-textarea {
    font-family: 'Fira Code', 'Monaco', 'Consolas', monospace;
    font-size: 0.9rem;
    line-height: 1.7;
  }
}

// URL Import Section
.url-import-section {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--border-color);

  .url-input-row {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    margin-bottom: 0.5rem;
  }
}

.url-truncate {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

// Knowledge List
.knowledge-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.knowledge-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.875rem 1rem;
  background: var(--surface-light);
  border-radius: var(--radius-md);
  transition: background var(--transition-fast);

  &:hover {
    background: var(--surface-hover);
  }

  > i {
    font-size: 1.5rem;
    color: var(--primary-color);
  }
}

// Test Area
.test-area {
  display: flex;
  flex-direction: column;
  height: 320px;

  .test-messages {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    padding: 1rem;
    background: var(--surface-light);
    border-radius: var(--radius-md);
    margin-bottom: 1rem;

    .test-empty {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      color: var(--text-muted);

      i {
        font-size: 2rem;
        opacity: 0.4;
      }

      p {
        font-size: 0.875rem;
      }
    }

    .message {
      max-width: 85%;
      animation: slideUp 0.2s ease;

      .message-content {
        padding: 0.75rem 1rem;
        border-radius: var(--radius-lg);
        line-height: 1.5;
        font-size: 0.9rem;
      }

      &.user {
        align-self: flex-end;

        .message-content {
          background: var(--primary-gradient);
          color: white;
          border-bottom-right-radius: 4px;
        }
      }

      &.assistant {
        align-self: flex-start;

        .message-content {
          background: var(--surface-card);
          border: 1px solid var(--border-color);
          color: var(--text-dark);
          border-bottom-left-radius: 4px;
        }
      }
    }
  }

  .test-input {
    display: flex;
    gap: 0.5rem;

    .va-input {
      flex: 1;
    }
  }
}

// Form section titles
.form-section h3 {
  color: var(--text-dark);
  font-size: 0.9rem;
  font-weight: 600;
  margin-bottom: 1rem;
}

// Modal actions
.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
}

// Webhook Setup Dialog
.webhook-setup {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.webhook-info {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem;
  background: var(--primary-50);
  border-radius: var(--radius-md);
  border: 1px solid var(--primary-200);

  > i {
    font-size: 2rem;
    color: var(--primary-color);
    flex-shrink: 0;
  }

  p {
    color: var(--text-dark);
    line-height: 1.5;
    margin: 0;
  }
}

.webhook-url-box {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;

  label {
    font-weight: 600;
    color: var(--text-dark);
    font-size: 0.9rem;
  }

  .url-input-group {
    display: flex;
    gap: 0.5rem;

    .url-input {
      flex: 1;
      font-family: 'Fira Code', monospace;
      font-size: 0.85rem;
    }
  }

  .hint-text {
    display: flex;
    align-items: center;
    gap: 0.5rem;

    i {
      color: var(--primary-color);
    }
  }
}

.webhook-manual {
  details {
    background: var(--surface-light);
    border-radius: var(--radius-md);
    border: 1px solid var(--border-color);

    summary {
      padding: 0.875rem 1rem;
      cursor: pointer;
      font-weight: 500;
      color: var(--text-secondary);
      transition: all 0.2s ease;

      &:hover {
        color: var(--primary-color);
      }
    }

    &[open] summary {
      border-bottom: 1px solid var(--border-color);
    }
  }

  .manual-content {
    padding: 1rem;

    p {
      margin: 0 0 1rem;
      color: var(--text-secondary);
    }

    ol {
      margin: 0;
      padding-left: 1.25rem;
      color: var(--text-dark);

      li {
        margin-bottom: 0.5rem;
        line-height: 1.5;

        code {
          background: var(--surface-card);
          padding: 0.125rem 0.375rem;
          border-radius: var(--radius-sm);
          font-size: 0.85rem;
          color: var(--primary-color);
        }
      }
    }
  }
}

// Tools Grid
.tools-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.tool-card {
  padding: 1rem;
  border-radius: var(--radius-md);
  border: 2px solid var(--border-color);
  background: var(--surface-light);
  transition: all 0.2s ease;
  cursor: pointer;

  &:hover {
    border-color: var(--primary-300);
    background: var(--surface-hover);
  }

  &.active {
    border-color: var(--primary-color);
    background: var(--primary-50);

    .tool-name {
      color: var(--primary-color);
    }

    i {
      color: var(--primary-color);
    }
  }

  .tool-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;

    i {
      font-size: 1.25rem;
      color: var(--text-secondary);
      transition: color 0.2s ease;
    }
  }

  .tool-name {
    font-weight: 600;
    font-size: 0.9rem;
    color: var(--text-dark);
    transition: color 0.2s ease;
  }

  .tool-desc {
    font-size: 0.8rem;
    color: var(--text-secondary);
    line-height: 1.4;
    margin: 0;
    padding-left: 2rem;
  }
}

@media (max-width: 768px) {
  .tools-grid {
    grid-template-columns: 1fr;
  }
}

// Split Modes
.split-modes {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.split-mode-card {
  padding: 1rem;
  border-radius: var(--radius-md);
  border: 2px solid var(--border-color);
  background: var(--surface-light);
  transition: all 0.2s ease;
  cursor: pointer;

  &:hover {
    border-color: var(--primary-300);
    background: var(--surface-hover);
  }

  &.active {
    border-color: var(--primary-color);
    background: var(--primary-50);

    .mode-name {
      color: var(--primary-color);
    }

    i {
      color: var(--primary-color);
    }
  }

  .mode-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;

    i {
      font-size: 1.25rem;
      color: var(--text-secondary);
      transition: color 0.2s ease;
    }
  }

  .mode-name {
    font-weight: 600;
    font-size: 0.95rem;
    color: var(--text-dark);
    transition: color 0.2s ease;
  }

  .mode-desc {
    font-size: 0.8rem;
    color: var(--text-secondary);
    line-height: 1.4;
    margin: 0;
    padding-left: 2.25rem;
  }
}

// Intent Modes (reutiliza estilos de split modes)
.intent-modes {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.intent-mode-card {
  padding: 1rem;
  border-radius: var(--radius-md);
  border: 2px solid var(--border-color);
  background: var(--surface-light);
  transition: all 0.2s ease;
  cursor: pointer;

  &:hover {
    border-color: var(--primary-300);
    background: var(--surface-hover);
  }

  &.active {
    border-color: var(--primary-color);
    background: var(--primary-50);

    .mode-name {
      color: var(--primary-color);
    }

    i {
      color: var(--primary-color);
    }
  }

  .mode-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;

    i {
      font-size: 1.25rem;
      color: var(--text-secondary);
      transition: color 0.2s ease;
    }
  }

  .mode-name {
    font-weight: 600;
    font-size: 0.95rem;
    color: var(--text-dark);
    transition: color 0.2s ease;
  }

  .mode-desc {
    font-size: 0.8rem;
    color: var(--text-secondary);
    line-height: 1.4;
    margin: 0;
    padding-left: 2.25rem;
  }
}

.keywords-section {
  padding: 1rem;
  background: var(--surface-light);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);

  label {
    font-weight: 500;
    margin-bottom: 0.5rem;
    display: block;
  }
}

// Follow-up Section
.followup-toggle {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: var(--surface-light);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);

  .toggle-label {
    font-weight: 500;
    color: var(--text-dark);
  }
}

.followup-settings {
  padding: 1rem;
  background: var(--surface-light);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  margin-top: 0.5rem;
}

.time-inputs {
  display: flex;
  gap: 0.75rem;
}

.time-input-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;

  .va-input {
    flex: 1;
    max-width: 80px;
  }

  .time-label {
    font-size: 0.85rem;
    color: var(--text-secondary);
  }
}
</style>
