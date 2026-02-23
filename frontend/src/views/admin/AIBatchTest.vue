<template>
  <div class="batch-test-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h2>Testes em Lote do Agente</h2>
        <p class="subtitle">Execute e avalie multiplos cenarios de teste</p>
      </div>
    </div>

    <!-- Controles -->
    <div class="card controls-card">
      <div class="controls-row">
        <div class="control-group">
          <label>Testes Simultaneos</label>
          <div class="button-group">
            <button
              v-for="opt in [10, 15, 20]"
              :key="opt"
              :class="['btn-option', { active: concurrentTests === opt }]"
              @click="concurrentTests = opt"
            >
              {{ opt }}
            </button>
          </div>
        </div>

        <div class="control-group">
          <label>Categoria</label>
          <va-select
            v-model="categoryFilter"
            :options="categoryOptions"
            placeholder="Todas"
            clearable
          />
        </div>

        <div class="control-group">
          <label>&nbsp;</label>
          <va-button
            @click="runTests"
            :loading="running"
            :disabled="selectedTests.length === 0 || running"
            color="success"
          >
            <i class="mdi mdi-play"></i>
            Executar {{ selectedTests.length }} Testes
          </va-button>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tabs-container">
      <div class="tabs">
        <button
          :class="['tab', { active: activeTab === 'conversation' }]"
          @click="activeTab = 'conversation'"
        >
          <i class="mdi mdi-chat-processing"></i>
          Simular Conversa
        </button>
        <button
          :class="['tab', { active: activeTab === 'cases' }]"
          @click="activeTab = 'cases'"
        >
          <i class="mdi mdi-test-tube"></i>
          Testes Unitarios ({{ testCases.length }})
        </button>
        <button
          :class="['tab', { active: activeTab === 'results' }]"
          @click="activeTab = 'results'"
        >
          <i class="mdi mdi-chart-box"></i>
          Resultados
        </button>
        <button
          :class="['tab', { active: activeTab === 'history' }]"
          @click="activeTab = 'history'"
        >
          <i class="mdi mdi-history"></i>
          Historico
        </button>
      </div>
    </div>

    <!-- Tab: Simular Conversa -->
    <div v-if="activeTab === 'conversation'" class="card">
      <div class="conversation-header">
        <div class="conv-info">
          <i class="mdi mdi-chat-processing"></i>
          <div>
            <h3>Simular Conversas Reais</h3>
            <p>A IA simula um cliente real conversando com seu agente em multiplos turnos</p>
          </div>
        </div>
      </div>

      <div class="conv-config">
        <div class="config-row">
          <div class="config-item">
            <label>Quantidade de Conversas</label>
            <div class="button-group">
              <button
                v-for="opt in [1, 3, 5, 10]"
                :key="opt"
                :class="['btn-option', { active: numConversations === opt }]"
                @click="numConversations = opt"
              >
                {{ opt }}
              </button>
            </div>
          </div>

          <div class="config-item">
            <label>Turnos por Conversa</label>
            <div class="button-group">
              <button
                v-for="opt in [3, 5, 7, 10]"
                :key="opt"
                :class="['btn-option', { active: turnsPerConv === opt }]"
                @click="turnsPerConv = opt"
              >
                {{ opt }}
              </button>
            </div>
          </div>

          <div class="config-item">
            <label>Perfil do Cliente</label>
            <va-select
              v-model="selectedProfile"
              :options="clientProfiles"
              placeholder="Aleatorio"
              clearable
              text-by="name"
              value-by="name"
            />
          </div>
        </div>

        <div class="config-actions">
          <va-button
            color="success"
            size="large"
            @click="runConversationSimulation"
            :loading="simulatingConv"
            :disabled="simulatingConv"
          >
            <i class="mdi mdi-play"></i>
            Iniciar {{ numConversations }} Conversa(s)
          </va-button>
        </div>
      </div>

      <!-- Resultados da Conversa -->
      <div v-if="conversationResults.length > 0" class="conv-results">
        <!-- Metricas Resumo -->
        <div v-if="convMetrics" class="conv-metrics-summary">
          <div class="metrics-grid">
            <div class="metric-card success">
              <i class="mdi mdi-check-circle"></i>
              <span class="metric-value">{{ convMetrics.passed }}</span>
              <span class="metric-label">Aprovadas</span>
            </div>
            <div class="metric-card warning">
              <i class="mdi mdi-alert-circle"></i>
              <span class="metric-value">{{ convMetrics.warning }}</span>
              <span class="metric-label">Parciais</span>
            </div>
            <div class="metric-card error">
              <i class="mdi mdi-close-circle"></i>
              <span class="metric-value">{{ convMetrics.failed + convMetrics.errors }}</span>
              <span class="metric-label">Falhas</span>
            </div>
            <div class="metric-card neutral">
              <i class="mdi mdi-chart-line"></i>
              <span class="metric-value">{{ convMetrics.average_score }}</span>
              <span class="metric-label">Média</span>
            </div>
            <div class="metric-card neutral">
              <i class="mdi mdi-percent"></i>
              <span class="metric-value">{{ convMetrics.pass_rate }}%</span>
              <span class="metric-label">Aprovação</span>
            </div>
          </div>

          <!-- Breakdown por categoria -->
          <div v-if="convMetrics.breakdown" class="metrics-breakdown">
            <span class="breakdown-item" v-for="(value, key) in convMetrics.breakdown" :key="key">
              <span class="breakdown-label">{{ formatBreakdownKey(key) }}</span>
              <span :class="['breakdown-value', getScoreClass(value)]">{{ value }}</span>
            </span>
          </div>

          <!-- Problemas mais comuns -->
          <div v-if="convMetrics.top_issues?.length" class="metrics-issues">
            <span class="issues-label">Problemas frequentes:</span>
            <va-chip
              v-for="item in convMetrics.top_issues"
              :key="item.issue"
              size="small"
              color="warning"
            >
              {{ item.issue }} ({{ item.count }})
            </va-chip>
          </div>
        </div>

        <h4>Conversas Simuladas</h4>

        <div
          v-for="conv in conversationResults"
          :key="conv.conversation_id"
          class="conversation-card"
        >
          <div class="conv-card-header" @click="toggleConversation(conv.conversation_id)">
            <div class="conv-meta">
              <span class="conv-number">Conversa #{{ conv.conversation_id }}</span>
              <!-- Score badge -->
              <span
                v-if="conv.evaluation"
                :class="['score-badge', conv.evaluation.status]"
              >
                {{ conv.evaluation.score }}
              </span>
              <va-chip v-if="conv.error" size="small" color="danger">Erro</va-chip>
              <va-chip v-else size="small" color="info">{{ conv.client_profile }}</va-chip>
              <span v-if="!conv.error" class="conv-turns">{{ conv.num_turns }} turnos</span>
            </div>
            <div class="conv-tools" v-if="conv.tools_used?.length">
              <va-chip
                v-for="tool in conv.tools_used"
                :key="tool"
                size="small"
                color="secondary"
              >
                {{ tool }}
              </va-chip>
            </div>
            <i :class="['mdi', expandedConvs.includes(conv.conversation_id) ? 'mdi-chevron-up' : 'mdi-chevron-down']"></i>
          </div>

          <div v-if="expandedConvs.includes(conv.conversation_id)" class="conv-messages">
            <!-- Evaluation details -->
            <div v-if="conv.evaluation" class="conv-evaluation">
              <div class="eval-scores">
                <span v-for="(value, key) in conv.evaluation.breakdown" :key="key" class="eval-item">
                  <span class="eval-label">{{ formatBreakdownKey(key) }}</span>
                  <span :class="['eval-value', getScoreClass(value)]">{{ value }}</span>
                </span>
              </div>
              <div v-if="conv.evaluation.issues?.length" class="eval-issues">
                <va-chip
                  v-for="issue in conv.evaluation.issues"
                  :key="issue"
                  size="small"
                  color="warning"
                >
                  {{ issue }}
                </va-chip>
              </div>
            </div>
            <!-- Error state -->
            <div v-if="conv.error" class="conv-error">
              <i class="mdi mdi-alert-circle"></i>
              <span>Erro: {{ conv.error }}</span>
            </div>

            <!-- Conversation turns -->
            <div
              v-else
              v-for="(turn, idx) in conv.turn_details"
              :key="idx"
              class="turn-block"
            >
              <div class="message client-message">
                <div class="msg-header">
                  <i class="mdi mdi-account"></i>
                  <span>Cliente</span>
                </div>
                <div class="msg-content">{{ turn.client_message }}</div>
              </div>
              <div class="message agent-message">
                <div class="msg-header">
                  <i class="mdi mdi-robot"></i>
                  <span>Agente</span>
                  <div class="tool-chips" v-if="turn.tools_used?.length">
                    <va-chip
                      v-for="tool in turn.tools_used"
                      :key="tool"
                      size="small"
                      color="info"
                    >
                      {{ tool }}
                    </va-chip>
                  </div>
                </div>
                <div class="msg-content">{{ turn.agent_response }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="!simulatingConv" class="empty-state">
        <i class="mdi mdi-message-text-outline"></i>
        <p>Nenhuma simulacao executada ainda</p>
        <p class="empty-desc">Configure e inicie uma simulacao para testar seu agente com conversas reais</p>
      </div>

      <div v-if="simulatingConv" class="loading-state">
        <va-progress-circle indeterminate size="large" />
        <h3>Simulando conversas...</h3>
        <p>Isso pode levar alguns minutos dependendo da quantidade de conversas</p>
      </div>
    </div>

    <!-- Tab: Casos de Teste -->
    <div v-if="activeTab === 'cases'" class="card">
      <div class="card-header">
        <div class="header-actions">
          <va-button color="warning" size="small" @click="showGenerateModal = true" :loading="generating">
            <i class="mdi mdi-robot"></i>
            Gerar Testes com IA
          </va-button>
          <va-button preset="secondary" size="small" @click="seedTemplates" :loading="seeding">
            <i class="mdi mdi-auto-fix"></i>
            Templates Padrao
          </va-button>
          <va-button color="primary" size="small" @click="openEditor(null)">
            <i class="mdi mdi-plus"></i>
            Novo Manual
          </va-button>
        </div>
      </div>

      <div v-if="loading" class="loading-state">
        <va-progress-circle indeterminate />
        <p>Carregando casos de teste...</p>
      </div>

      <div v-else-if="testCases.length === 0" class="empty-state">
        <i class="mdi mdi-robot"></i>
        <p>Nenhum caso de teste cadastrado</p>
        <p class="empty-desc">Gere testes automaticamente baseados nos seus produtos e prompt</p>
        <div class="empty-actions">
          <va-button color="warning" @click="showGenerateModal = true" :loading="generating">
            <i class="mdi mdi-robot"></i>
            Gerar com IA
          </va-button>
          <va-button preset="secondary" @click="seedTemplates" :loading="seeding">
            Templates Padrao
          </va-button>
        </div>
      </div>

      <div v-else class="test-cases-list">
        <div
          v-for="tc in filteredTestCases"
          :key="tc.id"
          :class="['test-case-card', { selected: selectedTestIds.includes(tc.id) }]"
          @click="toggleSelection(tc.id)"
        >
          <div class="tc-checkbox">
            <va-checkbox :model-value="selectedTestIds.includes(tc.id)" />
          </div>
          <div class="tc-content">
            <div class="tc-header">
              <span class="tc-name">{{ tc.name }}</span>
              <va-chip size="small" :color="getCategoryColor(tc.category)">
                {{ getCategoryLabel(tc.category) }}
              </va-chip>
            </div>
            <p class="tc-message">"{{ tc.input_message }}"</p>
            <div class="tc-expectations">
              <span v-if="tc.expected_tools?.length">
                <i class="mdi mdi-tools"></i>
                {{ tc.expected_tools.join(', ') }}
              </span>
              <span v-if="tc.expected_keywords?.length">
                <i class="mdi mdi-tag-text"></i>
                {{ tc.expected_keywords.slice(0, 3).join(', ') }}
                <template v-if="tc.expected_keywords.length > 3">...</template>
              </span>
            </div>
          </div>
          <div class="tc-actions">
            <va-button preset="plain" size="small" @click.stop="openEditor(tc)">
              <i class="mdi mdi-pencil"></i>
            </va-button>
            <va-button preset="plain" size="small" color="danger" @click.stop="deleteTestCase(tc)">
              <i class="mdi mdi-delete"></i>
            </va-button>
          </div>
        </div>
      </div>

      <div class="selection-bar" v-if="testCases.length > 0">
        <va-checkbox
          :model-value="allSelected"
          :indeterminate="someSelected && !allSelected"
          @update:model-value="toggleSelectAll"
          label="Selecionar todos"
        />
        <span class="selection-count">{{ selectedTests.length }} selecionados</span>
      </div>
    </div>

    <!-- Tab: Resultados -->
    <div v-if="activeTab === 'results'" class="card">
      <div v-if="running" class="running-state">
        <va-progress-circle indeterminate size="large" />
        <h3>Executando testes...</h3>
        <p>{{ runProgress }} de {{ selectedTests.length }} concluidos</p>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
        </div>
      </div>

      <div v-else-if="currentResults.length > 0">
        <!-- Summary -->
        <div class="results-summary">
          <div class="summary-item success">
            <i class="mdi mdi-check-circle"></i>
            <span class="value">{{ summaryStats.passed }}</span>
            <span class="label">Aprovados</span>
          </div>
          <div class="summary-item warning">
            <i class="mdi mdi-alert-circle"></i>
            <span class="value">{{ summaryStats.warning }}</span>
            <span class="label">Parciais</span>
          </div>
          <div class="summary-item error">
            <i class="mdi mdi-close-circle"></i>
            <span class="value">{{ summaryStats.failed }}</span>
            <span class="label">Reprovados</span>
          </div>
          <div class="summary-item neutral">
            <i class="mdi mdi-chart-line"></i>
            <span class="value">{{ summaryStats.average.toFixed(1) }}</span>
            <span class="label">Media</span>
          </div>
        </div>

        <!-- Results Table -->
        <div class="results-table">
          <table>
            <thead>
              <tr>
                <th>Teste</th>
                <th>Nota</th>
                <th>Tools Usadas</th>
                <th>Problemas</th>
                <th>Tempo</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="result in currentResults" :key="result.id">
                <td>
                  <strong>{{ result.test_case_name }}</strong>
                  <p class="input-preview">"{{ truncate(result.input_message, 40) }}"</p>
                </td>
                <td>
                  <span :class="['score-badge', result.status]">
                    {{ result.score?.toFixed(1) || '-' }}
                  </span>
                </td>
                <td>
                  <div class="tools-badges">
                    <va-chip
                      v-for="tool in result.tools_used"
                      :key="tool"
                      size="small"
                      color="info"
                    >
                      {{ tool }}
                    </va-chip>
                    <span v-if="!result.tools_used?.length" class="no-tools">-</span>
                  </div>
                </td>
                <td>
                  <div v-if="result.issues?.length" class="issues-cell">
                    <va-chip size="small" color="warning">
                      {{ result.issues.length }} problema(s)
                    </va-chip>
                  </div>
                  <span v-else class="no-issues">
                    <i class="mdi mdi-check"></i>
                  </span>
                </td>
                <td>{{ result.execution_time_ms }}ms</td>
                <td>
                  <va-button preset="plain" size="small" @click="viewResultDetail(result)">
                    <i class="mdi mdi-eye"></i>
                  </va-button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-else class="empty-state">
        <i class="mdi mdi-flask-empty"></i>
        <p>Execute os testes para ver os resultados</p>
      </div>
    </div>

    <!-- Tab: Historico -->
    <div v-if="activeTab === 'history'" class="card">
      <div v-if="runHistory.length === 0" class="empty-state">
        <i class="mdi mdi-history"></i>
        <p>Nenhuma execucao anterior</p>
      </div>

      <div v-else class="history-list">
        <div
          v-for="run in runHistory"
          :key="run.id"
          class="history-item"
          @click="loadRunResults(run)"
        >
          <div class="history-main">
            <span class="history-date">{{ formatDate(run.started_at) }}</span>
            <va-chip size="small" :color="run.status === 'completed' ? 'success' : 'warning'">
              {{ run.status }}
            </va-chip>
          </div>
          <div class="history-stats">
            <span class="stat success">{{ run.passed_count }} aprovados</span>
            <span class="stat warning">{{ run.warning_count }} parciais</span>
            <span class="stat error">{{ run.failed_count }} reprovados</span>
            <span class="stat">Media: {{ run.average_score?.toFixed(1) || '-' }}</span>
          </div>
          <div class="history-meta">
            {{ run.total_tests }} testes | {{ run.total_execution_time_ms }}ms |
            ~${{ run.estimated_cost?.toFixed(4) || '0' }}
          </div>
        </div>
      </div>
    </div>

    <!-- Modal: Editor de Caso de Teste -->
    <va-modal
      v-model="showEditor"
      :title="editingCase ? 'Editar Caso de Teste' : 'Novo Caso de Teste'"
      size="large"
      hide-default-actions
    >
      <div class="editor-form">
        <div class="form-group">
          <label>Nome do Teste *</label>
          <va-input v-model="editorForm.name" placeholder="Ex: Busca de produtos por cor" />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>Categoria</label>
            <va-select v-model="editorForm.category" :options="categoryOptions" />
          </div>
          <div class="form-group">
            <label>Descricao</label>
            <va-input v-model="editorForm.description" placeholder="Opcional" />
          </div>
        </div>

        <div class="form-group">
          <label>Mensagem de Entrada *</label>
          <va-textarea
            v-model="editorForm.input_message"
            placeholder="Mensagem que sera enviada ao agente"
            :min-rows="2"
          />
        </div>

        <div class="form-section">
          <h4>Criterios de Avaliacao</h4>

          <div class="form-group">
            <label>Tools Esperadas</label>
            <VaChipsInput
              v-model="editorForm.expected_tools"
              placeholder="Digite e pressione Enter"
            />
            <small>Ferramentas que o agente deve usar (buscar_produtos, calcular_financiamento, etc)</small>
          </div>

          <div class="form-group">
            <label>Palavras-chave Esperadas</label>
            <VaChipsInput
              v-model="editorForm.expected_keywords"
              placeholder="Digite e pressione Enter"
            />
            <small>Palavras que devem aparecer na resposta</small>
          </div>

          <div class="form-group">
            <label>Conteudo Proibido</label>
            <VaChipsInput
              v-model="editorForm.should_not_contain"
              placeholder="Digite e pressione Enter"
            />
            <small>Palavras que NAO devem aparecer na resposta</small>
          </div>
        </div>

        <div class="form-section">
          <h4>Pesos de Pontuacao</h4>
          <div class="weights-grid">
            <div class="weight-item">
              <label>Tools</label>
              <va-input v-model.number="editorForm.weight_tools" type="number" :min="0" :max="10" />
            </div>
            <div class="weight-item">
              <label>Keywords</label>
              <va-input v-model.number="editorForm.weight_keywords" type="number" :min="0" :max="10" />
            </div>
            <div class="weight-item">
              <label>Sem Erros</label>
              <va-input v-model.number="editorForm.weight_no_errors" type="number" :min="0" :max="10" />
            </div>
            <div class="weight-item">
              <label>Qualidade</label>
              <va-input v-model.number="editorForm.weight_quality" type="number" :min="0" :max="10" />
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <va-button preset="secondary" @click="showEditor = false">Cancelar</va-button>
        <va-button @click="saveTestCase" :loading="saving">Salvar</va-button>
      </template>
    </va-modal>

    <!-- Modal: Detalhe do Resultado -->
    <va-modal
      v-model="showResultDetail"
      title="Detalhe do Resultado"
      size="large"
      hide-default-actions
    >
      <div v-if="selectedResult" class="result-detail">
        <div class="detail-header">
          <h3>{{ selectedResult.test_case_name }}</h3>
          <span :class="['score-badge large', selectedResult.status]">
            {{ selectedResult.score?.toFixed(1) }}
          </span>
        </div>

        <div class="detail-section">
          <h4>Entrada</h4>
          <div class="message-box input">"{{ selectedResult.input_message }}"</div>
        </div>

        <div class="detail-section">
          <h4>Resposta do Agente</h4>
          <div class="message-box output">{{ selectedResult.ai_response }}</div>
        </div>

        <div class="detail-section" v-if="selectedResult.tools_used?.length">
          <h4>Tools Utilizadas</h4>
          <div class="tools-list">
            <va-chip v-for="tool in selectedResult.tools_used" :key="tool" color="info">
              {{ tool }}
            </va-chip>
          </div>
        </div>

        <div class="detail-section" v-if="selectedResult.issues?.length">
          <h4>Problemas Encontrados</h4>
          <ul class="issues-list">
            <li v-for="issue in selectedResult.issues" :key="issue">
              <i class="mdi mdi-alert-circle"></i>
              {{ issue }}
            </li>
          </ul>
        </div>

        <div class="detail-section" v-if="selectedResult.score_breakdown">
          <h4>Detalhamento da Pontuacao</h4>
          <div class="breakdown-grid">
            <div v-for="(data, key) in selectedResult.score_breakdown" :key="key" class="breakdown-item">
              <span class="breakdown-label">{{ formatBreakdownKey(key) }}</span>
              <span class="breakdown-score">{{ data.score?.toFixed(1) || '-' }}/10</span>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <va-button @click="showResultDetail = false">Fechar</va-button>
      </template>
    </va-modal>

    <!-- Modal: Gerar Testes com IA -->
    <va-modal
      v-model="showGenerateModal"
      title="Gerar Testes Automaticamente"
      size="small"
      hide-default-actions
    >
      <div class="generate-form">
        <div class="generate-info">
          <i class="mdi mdi-robot"></i>
          <p>
            A IA vai analisar seus <strong>produtos</strong> e <strong>prompt</strong>
            para gerar perguntas realistas que um cliente faria.
          </p>
        </div>

        <div class="form-group">
          <label>Quantidade de Testes</label>
          <div class="button-group">
            <button
              v-for="opt in [5, 10, 15, 20]"
              :key="opt"
              :class="['btn-option', { active: generateCount === opt }]"
              @click="generateCount = opt"
            >
              {{ opt }}
            </button>
          </div>
        </div>

        <div class="generate-note">
          <i class="mdi mdi-information"></i>
          Os testes serao baseados nos produtos do seu estoque e no comportamento
          esperado do agente conforme configurado no prompt.
        </div>
      </div>

      <template #footer>
        <va-button preset="secondary" @click="showGenerateModal = false">Cancelar</va-button>
        <va-button color="warning" @click="generateTests" :loading="generating">
          <i class="mdi mdi-robot"></i>
          Gerar {{ generateCount }} Testes
        </va-button>
      </template>
    </va-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useToast } from '@/composables/useToast'
import { batchTestingApi } from '@/api/client'
import VaChipsInput from '@/components/VaChipsInput.vue'

const props = defineProps({
  slug: { type: String, required: true }
})

const toast = useToast()

// State
const loading = ref(false)
const saving = ref(false)
const running = ref(false)
const seeding = ref(false)
const generating = ref(false)
const activeTab = ref('conversation')
const concurrentTests = ref(10)
const generateCount = ref(10)
const showGenerateModal = ref(false)
const categoryFilter = ref(null)

// Conversation Simulation State
const numConversations = ref(3)
const turnsPerConv = ref(5)
const selectedProfile = ref(null)
const conversationResults = ref([])
const expandedConvs = ref([])
const simulatingConv = ref(false)
const convMetrics = ref(null)
const clientProfiles = ref([
  { name: 'Cliente Direto', description: 'Sabe o que quer, vai direto ao ponto' },
  { name: 'Cliente Indeciso', description: 'Precisa de ajuda para decidir' },
  { name: 'Cliente Detalhista', description: 'Quer saber todos os detalhes antes de comprar' },
  { name: 'Cliente Apressado', description: 'Tem pouco tempo, quer resolver rapido' },
  { name: 'Cliente Negociador', description: 'Quer o melhor preco possivel' }
])

const testCases = ref([])
const selectedTestIds = ref([])
const currentResults = ref([])
const runHistory = ref([])
const runProgress = ref(0)
const currentRunId = ref(null)

// Editor
const showEditor = ref(false)
const editingCase = ref(null)
const editorForm = ref(getEmptyForm())

// Result Detail
const showResultDetail = ref(false)
const selectedResult = ref(null)

// Options
const categoryOptions = [
  { text: 'Busca de Produtos', value: 'product_search' },
  { text: 'Financiamento', value: 'financing' },
  { text: 'Agendamento', value: 'scheduling' },
  { text: 'Fotos e Midias', value: 'media' },
  { text: 'Saudacoes', value: 'greeting' },
  { text: 'Fora do Escopo', value: 'out_of_scope' },
  { text: 'Outros', value: 'other' }
]

// Computed
const filteredTestCases = computed(() => {
  if (!categoryFilter.value) return testCases.value
  return testCases.value.filter(tc => tc.category === categoryFilter.value)
})

const selectedTests = computed(() => {
  return testCases.value.filter(tc => selectedTestIds.value.includes(tc.id))
})

const allSelected = computed(() => {
  return filteredTestCases.value.length > 0 &&
    filteredTestCases.value.every(tc => selectedTestIds.value.includes(tc.id))
})

const someSelected = computed(() => {
  return selectedTestIds.value.length > 0
})

const progressPercent = computed(() => {
  if (selectedTests.value.length === 0) return 0
  return (runProgress.value / selectedTests.value.length) * 100
})

const summaryStats = computed(() => {
  const results = currentResults.value
  return {
    passed: results.filter(r => r.score >= 9).length,
    warning: results.filter(r => r.score >= 5 && r.score < 9).length,
    failed: results.filter(r => r.score < 5).length,
    average: results.length > 0
      ? results.reduce((sum, r) => sum + (r.score || 0), 0) / results.length
      : 0
  }
})

// Methods
function getEmptyForm() {
  return {
    name: '',
    description: '',
    category: 'product_search',
    input_message: '',
    expected_tools: [],
    expected_keywords: [],
    should_not_contain: [],
    weight_tools: 10,
    weight_keywords: 10,
    weight_no_errors: 10,
    weight_quality: 5
  }
}

async function loadTestCases() {
  loading.value = true
  try {
    const { data } = await batchTestingApi.listTestCases(props.slug)
    testCases.value = data
  } catch (error) {
    toast.error('Erro ao carregar casos de teste')
  } finally {
    loading.value = false
  }
}

async function loadRunHistory() {
  try {
    const { data } = await batchTestingApi.listRuns(props.slug)
    runHistory.value = data
  } catch (error) {
    console.error('Erro ao carregar historico:', error)
  }
}

function toggleSelection(id) {
  const idx = selectedTestIds.value.indexOf(id)
  if (idx >= 0) {
    selectedTestIds.value.splice(idx, 1)
  } else {
    selectedTestIds.value.push(id)
  }
}

function toggleSelectAll(value) {
  if (value) {
    selectedTestIds.value = filteredTestCases.value.map(tc => tc.id)
  } else {
    selectedTestIds.value = []
  }
}

function openEditor(testCase) {
  editingCase.value = testCase
  if (testCase) {
    editorForm.value = { ...testCase }
  } else {
    editorForm.value = getEmptyForm()
  }
  showEditor.value = true
}

async function saveTestCase() {
  if (!editorForm.value.name || !editorForm.value.input_message) {
    toast.warn('Preencha os campos obrigatorios')
    return
  }

  saving.value = true
  try {
    if (editingCase.value) {
      await batchTestingApi.updateTestCase(props.slug, editingCase.value.id, editorForm.value)
      toast.success('Caso de teste atualizado')
    } else {
      await batchTestingApi.createTestCase(props.slug, editorForm.value)
      toast.success('Caso de teste criado')
    }
    showEditor.value = false
    await loadTestCases()
  } catch (error) {
    toast.error('Erro ao salvar')
  } finally {
    saving.value = false
  }
}

async function deleteTestCase(testCase) {
  if (!confirm(`Excluir "${testCase.name}"?`)) return

  try {
    await batchTestingApi.deleteTestCase(props.slug, testCase.id)
    toast.success('Caso de teste removido')
    await loadTestCases()
  } catch (error) {
    toast.error('Erro ao remover')
  }
}

async function seedTemplates() {
  seeding.value = true
  try {
    const { data } = await batchTestingApi.seedTemplates(props.slug)
    toast.success(data.message || 'Templates criados')
    await loadTestCases()
  } catch (error) {
    toast.error('Erro ao criar templates')
  } finally {
    seeding.value = false
  }
}

async function generateTests() {
  generating.value = true
  showGenerateModal.value = false

  try {
    toast.info('Gerando testes com IA... Isso pode levar alguns segundos.')

    const { data } = await batchTestingApi.generateTests(props.slug, generateCount.value, true)
    toast.success(data.message || `${data.generated} testes gerados!`)
    await loadTestCases()

    // Selecionar todos os novos testes
    if (testCases.value.length > 0) {
      selectedTestIds.value = testCases.value.map(tc => tc.id)
    }
  } catch (error) {
    const msg = error.response?.data?.detail || 'Erro ao gerar testes'
    toast.error(msg)
  } finally {
    generating.value = false
  }
}

// Conversation Simulation Functions
async function runConversationSimulation() {
  simulatingConv.value = true
  conversationResults.value = []
  expandedConvs.value = []
  convMetrics.value = null

  try {
    toast.info(`Iniciando ${numConversations.value} conversa(s) com ${turnsPerConv.value} turnos cada...`)

    const { data } = await batchTestingApi.runConversation(
      props.slug,
      numConversations.value,
      turnsPerConv.value,
      selectedProfile.value
    )

    // Conversas já vêm com conversation_id do backend
    conversationResults.value = data.conversations || []

    // Métricas agregadas
    convMetrics.value = data.metrics || null

    // Expandir a primeira conversa automaticamente
    if (conversationResults.value.length > 0) {
      expandedConvs.value = [1]
    }

    const avgScore = data.metrics?.average_score || 0
    toast.success(`${conversationResults.value.length} conversa(s) simulada(s) - Média: ${avgScore}`)
  } catch (error) {
    const msg = error.response?.data?.detail || 'Erro ao simular conversas'
    toast.error(msg)
  } finally {
    simulatingConv.value = false
  }
}

function toggleConversation(convId) {
  const idx = expandedConvs.value.indexOf(convId)
  if (idx >= 0) {
    expandedConvs.value.splice(idx, 1)
  } else {
    expandedConvs.value.push(convId)
  }
}

async function runTests() {
  if (selectedTests.value.length === 0) {
    toast.warn('Selecione pelo menos um caso de teste')
    return
  }

  running.value = true
  runProgress.value = 0
  currentResults.value = []
  activeTab.value = 'results'

  try {
    const { data } = await batchTestingApi.runBatch(
      props.slug,
      selectedTestIds.value,
      concurrentTests.value
    )
    currentRunId.value = data.run_id

    // Poll for results
    await pollResults(data.run_id)

  } catch (error) {
    toast.error('Erro ao executar testes')
    running.value = false
  }
}

async function pollResults(runId) {
  const maxAttempts = 120 // 2 minutos
  let attempts = 0

  while (attempts < maxAttempts) {
    try {
      const { data: run } = await batchTestingApi.getRunStatus(props.slug, runId)

      if (run.results) {
        currentResults.value = run.results.map(r => ({
          ...r,
          status: r.score >= 9 ? 'success' : (r.score >= 5 ? 'warning' : 'error')
        }))
        runProgress.value = run.results.length
      }

      if (run.status === 'completed' || run.status === 'failed') {
        running.value = false
        await loadRunHistory()

        if (run.status === 'completed') {
          toast.success(`Testes concluidos! Media: ${run.average_score?.toFixed(1)}`)
        } else {
          toast.error('Execucao falhou')
        }
        return
      }

      await new Promise(r => setTimeout(r, 1000))
      attempts++

    } catch (error) {
      console.error('Erro ao verificar status:', error)
      attempts++
    }
  }

  running.value = false
  toast.warn('Timeout ao aguardar resultados')
}

async function loadRunResults(run) {
  try {
    const { data: fullRun } = await batchTestingApi.getRunStatus(props.slug, run.id)
    currentResults.value = (fullRun.results || []).map(r => ({
      ...r,
      status: r.score >= 9 ? 'success' : (r.score >= 5 ? 'warning' : 'error')
    }))
    activeTab.value = 'results'
  } catch (error) {
    toast.error('Erro ao carregar resultados')
  }
}

function viewResultDetail(result) {
  selectedResult.value = result
  showResultDetail.value = true
}

// Helpers
function getCategoryLabel(category) {
  const opt = categoryOptions.find(o => o.value === category)
  return opt?.text || category || 'Outros'
}

function getCategoryColor(category) {
  const colors = {
    product_search: 'primary',
    financing: 'success',
    scheduling: 'warning',
    media: 'info',
    greeting: 'secondary',
    out_of_scope: 'danger'
  }
  return colors[category] || 'secondary'
}

function truncate(text, maxLen) {
  if (!text) return ''
  return text.length > maxLen ? text.substring(0, maxLen) + '...' : text
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('pt-BR')
}

function formatBreakdownKey(key) {
  const labels = {
    tools: 'Tools',
    keywords: 'Palavras-chave',
    no_errors: 'Sem Erros',
    quality: 'Qualidade',
    flow: 'Fluxo',
    goal: 'Objetivo'
  }
  return labels[key] || key
}

function getScoreClass(score) {
  if (score >= 8) return 'success'
  if (score >= 5) return 'warning'
  return 'error'
}

// Lifecycle
onMounted(async () => {
  await loadTestCases()
  await loadRunHistory()
})
</script>

<style lang="scss" scoped>
.batch-test-page {
  padding: 1.5rem;
}

.page-header {
  margin-bottom: 1.5rem;

  h2 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--va-text-primary);
  }

  .subtitle {
    margin: 0.25rem 0 0;
    color: var(--va-text-secondary);
    font-size: 0.9rem;
  }
}

.card {
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  border: 1px solid var(--border-color);
  margin-bottom: 1rem;
}

// Button Group (used in controls-card and conv-config)
.button-group {
  display: flex;
  gap: 0.25rem;

  .btn-option {
    padding: 0.5rem 1rem;
    border: 1px solid var(--border-color);
    background: var(--va-background-secondary);
    color: var(--va-text-primary);
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: all 0.15s;

    &.active {
      background: var(--va-primary);
      color: white;
      border-color: var(--va-primary);
    }

    &:hover:not(.active) {
      border-color: var(--va-primary);
      background: var(--va-background-element);
    }
  }
}

.controls-card {
  .controls-row {
    display: flex;
    gap: 2rem;
    align-items: flex-end;
    flex-wrap: wrap;
  }

  .control-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;

    label {
      font-size: 0.85rem;
      font-weight: 500;
      color: var(--va-text-secondary);
    }
  }
}

.tabs-container {
  margin-bottom: 1rem;

  .tabs {
    display: flex;
    gap: 0.5rem;

    .tab {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.75rem 1.25rem;
      background: var(--va-background-secondary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      cursor: pointer;
      transition: all 0.15s;
      font-size: 0.9rem;
      color: var(--va-text-primary);

      &.active {
        background: var(--va-primary);
        color: white;
        border-color: var(--va-primary);
      }

      &:hover:not(.active) {
        border-color: var(--va-primary);
        background: var(--va-background-element);
      }
    }
  }
}

.card-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-color);

  .header-actions {
    display: flex;
    gap: 0.5rem;
  }
}

.loading-state,
.empty-state,
.running-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  text-align: center;
  color: var(--text-secondary);

  i {
    font-size: 3rem;
    margin-bottom: 1rem;
    opacity: 0.5;
  }

  p {
    margin: 0.5rem 0;
  }
}

.running-state {
  h3 {
    margin: 1rem 0 0.5rem;
  }

  .progress-bar {
    width: 100%;
    max-width: 300px;
    height: 8px;
    background: var(--border-color);
    border-radius: 4px;
    margin-top: 1rem;
    overflow: hidden;

    .progress-fill {
      height: 100%;
      background: var(--primary);
      transition: width 0.3s;
    }
  }
}

.test-cases-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.test-case-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: var(--va-background-secondary);
  border-radius: var(--radius-md);
  border: 2px solid var(--border-color);
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    border-color: var(--va-primary);
  }

  &.selected {
    border-color: var(--va-primary);
    background: rgba(99, 102, 241, 0.15);
  }

  .tc-checkbox {
    flex-shrink: 0;
  }

  .tc-content {
    flex: 1;
    min-width: 0;

    .tc-header {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 0.25rem;

      .tc-name {
        font-weight: 600;
        color: var(--va-text-primary);
      }
    }

    .tc-message {
      font-size: 0.85rem;
      color: var(--va-text-secondary);
      margin: 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .tc-expectations {
      display: flex;
      gap: 1rem;
      margin-top: 0.5rem;
      font-size: 0.8rem;
      color: var(--va-text-secondary);

      span {
        display: flex;
        align-items: center;
        gap: 0.25rem;
      }
    }
  }

  .tc-actions {
    display: flex;
    gap: 0.25rem;
  }
}

.selection-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color);

  .selection-count {
    color: var(--va-text-secondary);
    font-size: 0.9rem;
  }
}

.results-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;

  .summary-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 1rem;
    border-radius: var(--radius-md);
    background: var(--va-background-secondary);
    border: 1px solid var(--border-color);

    i {
      font-size: 1.5rem;
      margin-bottom: 0.5rem;
    }

    .value {
      font-size: 1.5rem;
      font-weight: 700;
    }

    .label {
      font-size: 0.8rem;
      color: var(--va-text-secondary);
    }

    &.success {
      color: #34d399;
      background: rgba(16, 185, 129, 0.2);
      border-color: #34d399;
    }

    &.warning {
      color: #fbbf24;
      background: rgba(245, 158, 11, 0.2);
      border-color: #fbbf24;
    }

    &.error {
      color: #f87171;
      background: rgba(239, 68, 68, 0.2);
      border-color: #f87171;
    }

    &.neutral {
      color: var(--va-text-primary);
    }
  }
}

.results-table {
  overflow-x: auto;

  table {
    width: 100%;
    border-collapse: collapse;

    th,
    td {
      padding: 0.75rem;
      text-align: left;
      border-bottom: 1px solid var(--border-color);
    }

    th {
      font-weight: 600;
      font-size: 0.85rem;
      color: var(--text-secondary);
    }

    .input-preview {
      font-size: 0.8rem;
      color: var(--text-tertiary);
      margin: 0.25rem 0 0;
    }
  }
}

.score-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 48px;
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-md);
  font-weight: 700;
  font-size: 0.9rem;
  border: 1px solid;

  &.success {
    background: rgba(16, 185, 129, 0.25);
    color: #34d399;
    border-color: #34d399;
  }

  &.warning {
    background: rgba(245, 158, 11, 0.25);
    color: #fbbf24;
    border-color: #fbbf24;
  }

  &.error {
    background: rgba(239, 68, 68, 0.25);
    color: #f87171;
    border-color: #f87171;
  }

  &.large {
    font-size: 1.5rem;
    padding: 0.5rem 1rem;
  }
}

.tools-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.no-tools,
.no-issues {
  color: var(--va-text-secondary);
}

.no-issues i {
  color: #34d399;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.history-item {
  padding: 1rem;
  background: var(--va-background-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    background: var(--va-background-element);
    border-color: var(--va-primary);
  }

  .history-main {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;

    .history-date {
      font-weight: 600;
      color: var(--va-text-primary);
    }
  }

  .history-stats {
    display: flex;
    gap: 1rem;
    font-size: 0.85rem;

    .stat {
      &.success { color: #34d399; }
      &.warning { color: #fbbf24; }
      &.error { color: #f87171; }
    }
  }

  .history-meta {
    margin-top: 0.5rem;
    font-size: 0.8rem;
    color: var(--va-text-secondary);
  }
}

// Editor Modal
.editor-form {
  .form-group {
    margin-bottom: 1rem;

    label {
      display: block;
      margin-bottom: 0.5rem;
      font-weight: 500;
      color: var(--va-text-primary);
    }

    small {
      display: block;
      margin-top: 0.25rem;
      color: var(--va-text-secondary);
      font-size: 0.8rem;
    }
  }

  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }

  .form-section {
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border-color);

    h4 {
      margin: 0 0 1rem;
      font-size: 0.95rem;
      color: var(--va-text-primary);
    }
  }

  .weights-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;

    .weight-item {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;

      label {
        font-size: 0.8rem;
        color: var(--va-text-secondary);
      }
    }
  }
}

// Result Detail Modal
.result-detail {
  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;

    h3 {
      margin: 0;
      color: var(--va-text-primary);
    }
  }

  .detail-section {
    margin-bottom: 1.5rem;

    h4 {
      margin: 0 0 0.75rem;
      font-size: 0.9rem;
      color: var(--va-text-secondary);
    }
  }

  .message-box {
    padding: 1rem;
    border-radius: var(--radius-md);
    font-size: 0.9rem;
    white-space: pre-wrap;
    color: var(--va-text-primary);

    &.input {
      background: rgba(99, 102, 241, 0.15);
      border-left: 3px solid var(--va-primary);
    }

    &.output {
      background: var(--va-background-secondary);
      border: 1px solid var(--border-color);
      max-height: 300px;
      overflow-y: auto;
    }
  }

  .tools-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .issues-list {
    list-style: none;
    padding: 0;
    margin: 0;

    li {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 0.75rem;
      background: rgba(239, 68, 68, 0.2);
      border: 1px solid #f87171;
      border-radius: var(--radius-sm);
      margin-bottom: 0.5rem;
      color: #f87171;

      i {
        flex-shrink: 0;
      }
    }
  }

  .breakdown-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;

    .breakdown-item {
      display: flex;
      justify-content: space-between;
      padding: 0.5rem 0.75rem;
      background: var(--va-background-secondary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);

      .breakdown-label {
        color: var(--va-text-secondary);
      }

      .breakdown-score {
        font-weight: 600;
        color: var(--va-text-primary);
      }
    }
  }
}

// Generate Modal
.generate-form {
  .generate-info {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    padding: 1rem;
    background: rgba(245, 158, 11, 0.15);
    border: 1px solid #fbbf24;
    border-radius: var(--radius-md);
    margin-bottom: 1.5rem;

    i {
      font-size: 2rem;
      color: #fbbf24;
      flex-shrink: 0;
    }

    p {
      margin: 0;
      font-size: 0.9rem;
      line-height: 1.5;
      color: var(--va-text-primary);

      strong {
        color: #fbbf24;
      }
    }
  }

  .form-group {
    margin-bottom: 1rem;

    label {
      display: block;
      margin-bottom: 0.5rem;
      font-weight: 500;
      color: var(--va-text-primary);
    }
  }

  .generate-note {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.75rem;
    background: var(--va-background-secondary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-sm);
    font-size: 0.8rem;
    color: var(--va-text-secondary);

    i {
      flex-shrink: 0;
      color: var(--va-text-secondary);
    }
  }
}

// Empty State
.empty-state {
  .empty-desc {
    color: var(--va-text-secondary);
    font-size: 0.85rem;
    margin-top: 0;
  }

  .empty-actions {
    display: flex;
    gap: 0.75rem;
    margin-top: 1rem;
  }
}

// Card fix for dark mode
.card {
  background: var(--va-background-secondary);
  color: var(--va-text-primary);
}

// Table fixes for dark mode
.results-table {
  table {
    th {
      color: var(--va-text-secondary);
    }

    td {
      color: var(--va-text-primary);
    }

    .input-preview {
      color: var(--va-text-secondary);
    }
  }
}

// Conversation Simulation Styles
.conversation-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 1.5rem;

  .conv-info {
    display: flex;
    align-items: center;
    gap: 1rem;

    i {
      font-size: 2.5rem;
      color: var(--va-primary);
    }

    h3 {
      margin: 0;
      font-size: 1.25rem;
      color: var(--va-text-primary);
    }

    p {
      margin: 0.25rem 0 0;
      color: var(--va-text-secondary);
      font-size: 0.9rem;
    }
  }
}

.conv-config {
  background: var(--va-background-element);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 1.5rem;
  margin-bottom: 1.5rem;

  .config-row {
    display: flex;
    gap: 2rem;
    flex-wrap: wrap;
    align-items: flex-end;
    margin-bottom: 1rem;
  }

  .config-item {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;

    label {
      font-size: 0.85rem;
      font-weight: 500;
      color: var(--va-text-secondary);
    }
  }

  .config-actions {
    display: flex;
    justify-content: center;
    padding-top: 1rem;
  }
}

.conv-results {
  h4 {
    margin: 0 0 1rem;
    color: var(--va-text-primary);
    font-size: 1.1rem;
  }
}

.conversation-card {
  background: var(--va-background-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  margin-bottom: 1rem;
  overflow: hidden;

  .conv-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem;
    cursor: pointer;
    transition: background 0.15s;

    &:hover {
      background: var(--va-background-element);
    }

    .conv-meta {
      display: flex;
      align-items: center;
      gap: 0.75rem;

      .conv-number {
        font-weight: 600;
        color: var(--va-text-primary);
      }

      .conv-turns {
        font-size: 0.85rem;
        color: var(--va-text-secondary);
      }
    }

    .conv-tools {
      display: flex;
      gap: 0.25rem;
      flex-wrap: wrap;
    }

    > i {
      font-size: 1.25rem;
      color: var(--va-text-secondary);
    }
  }

  .conv-messages {
    border-top: 1px solid var(--border-color);
    padding: 1rem;
    background: var(--va-background-element);
  }
}

.turn-block {
  margin-bottom: 1.5rem;

  &:last-child {
    margin-bottom: 0;
  }
}

.conv-error {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid #f87171;
  border-radius: var(--radius-md);
  color: #f87171;

  i {
    font-size: 1.25rem;
  }
}

.message {
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  margin-bottom: 0.5rem;

  .msg-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
    font-size: 0.8rem;
    font-weight: 600;

    i {
      font-size: 1rem;
    }

    .tool-chips {
      margin-left: auto;
      display: flex;
      gap: 0.25rem;
    }
  }

  .msg-content {
    font-size: 0.9rem;
    line-height: 1.5;
    white-space: pre-wrap;
  }

  &.client-message {
    background: rgba(99, 102, 241, 0.2);
    border: 1px solid rgba(99, 102, 241, 0.4);
    color: var(--va-text-primary);

    .msg-header {
      color: #a5b4fc;
    }
  }

  &.agent-message {
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.3);
    color: var(--va-text-primary);

    .msg-header {
      color: #34d399;
    }
  }
}

.loading-state {
  color: var(--va-text-primary);

  h3 {
    color: var(--va-text-primary);
  }

  p {
    color: var(--va-text-secondary);
  }
}

// Conversation Metrics
.conv-metrics-summary {
  background: var(--va-background-element);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 1.5rem;
  margin-bottom: 1.5rem;

  .metrics-grid {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    margin-bottom: 1rem;
  }

  .metric-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 1rem 1.5rem;
    border-radius: var(--radius-md);
    background: var(--va-background-secondary);
    border: 1px solid var(--border-color);
    min-width: 100px;

    i {
      font-size: 1.5rem;
      margin-bottom: 0.5rem;
    }

    .metric-value {
      font-size: 1.5rem;
      font-weight: 700;
    }

    .metric-label {
      font-size: 0.8rem;
      color: var(--va-text-secondary);
    }

    &.success {
      color: #34d399;
      background: rgba(16, 185, 129, 0.2);
      border-color: #34d399;
    }

    &.warning {
      color: #fbbf24;
      background: rgba(245, 158, 11, 0.2);
      border-color: #fbbf24;
    }

    &.error {
      color: #f87171;
      background: rgba(239, 68, 68, 0.2);
      border-color: #f87171;
    }

    &.neutral {
      color: var(--va-text-primary);
    }
  }

  .metrics-breakdown {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    padding: 1rem 0;
    border-top: 1px solid var(--border-color);

    .breakdown-item {
      display: flex;
      align-items: center;
      gap: 0.5rem;

      .breakdown-label {
        color: var(--va-text-secondary);
        font-size: 0.85rem;
      }

      .breakdown-value {
        font-weight: 600;
        padding: 0.25rem 0.5rem;
        border-radius: var(--radius-sm);

        &.success { color: #34d399; }
        &.warning { color: #fbbf24; }
        &.error { color: #f87171; }
      }
    }
  }

  .metrics-issues {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    padding-top: 1rem;
    border-top: 1px solid var(--border-color);

    .issues-label {
      font-size: 0.85rem;
      color: var(--va-text-secondary);
    }
  }
}

// Conversation Evaluation
.conv-evaluation {
  background: var(--va-background-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 1rem;
  margin-bottom: 1rem;

  .eval-scores {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    margin-bottom: 0.75rem;

    .eval-item {
      display: flex;
      align-items: center;
      gap: 0.5rem;

      .eval-label {
        font-size: 0.8rem;
        color: var(--va-text-secondary);
      }

      .eval-value {
        font-weight: 600;
        font-size: 0.9rem;

        &.success { color: #34d399; }
        &.warning { color: #fbbf24; }
        &.error { color: #f87171; }
      }
    }
  }

  .eval-issues {
    display: flex;
    gap: 0.25rem;
    flex-wrap: wrap;
  }
}
</style>
