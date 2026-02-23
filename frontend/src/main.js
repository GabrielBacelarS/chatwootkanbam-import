import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createVuestic } from 'vuestic-ui'

import App from './App.vue'
import router from './router'

// Vuestic UI styles
import 'vuestic-ui/css'
import '@mdi/font/css/materialdesignicons.css'

// Custom styles
import './styles/main.scss'

const app = createApp(App)

app.use(createPinia())
app.use(router)

// Vuestic UI com configuracao de cores e icones
app.use(createVuestic({
  config: {
    icons: [
      {
        name: 'mdi-{icon}',
        resolve: ({ icon }) => ({
          class: `mdi mdi-${icon}`,
          tag: 'i'
        })
      },
      {
        name: 'mdi',
        resolve: ({ icon }) => ({
          class: `mdi ${icon}`,
          tag: 'i'
        })
      },
      // Aliases para icones padrao do Vuestic -> MDI
      { name: 'va-arrow-down', resolve: () => ({ class: 'mdi mdi-chevron-down', tag: 'i' }) },
      { name: 'va-arrow-up', resolve: () => ({ class: 'mdi mdi-chevron-up', tag: 'i' }) },
      { name: 'va-arrow-left', resolve: () => ({ class: 'mdi mdi-chevron-left', tag: 'i' }) },
      { name: 'va-arrow-right', resolve: () => ({ class: 'mdi mdi-chevron-right', tag: 'i' }) },
      { name: 'va-check', resolve: () => ({ class: 'mdi mdi-check', tag: 'i' }) },
      { name: 'va-close', resolve: () => ({ class: 'mdi mdi-close', tag: 'i' }) },
      { name: 'va-warning', resolve: () => ({ class: 'mdi mdi-alert', tag: 'i' }) },
      { name: 'va-info', resolve: () => ({ class: 'mdi mdi-information', tag: 'i' }) },
      { name: 'va-error', resolve: () => ({ class: 'mdi mdi-alert-circle', tag: 'i' }) },
      { name: 'va-success', resolve: () => ({ class: 'mdi mdi-check-circle', tag: 'i' }) },
      { name: 'va-calendar', resolve: () => ({ class: 'mdi mdi-calendar', tag: 'i' }) },
      { name: 'va-clear', resolve: () => ({ class: 'mdi mdi-close-circle', tag: 'i' }) },
      { name: 'va-loading', resolve: () => ({ class: 'mdi mdi-loading mdi-spin', tag: 'i' }) },
      { name: 'va-search', resolve: () => ({ class: 'mdi mdi-magnify', tag: 'i' }) },
      { name: 'va-eye', resolve: () => ({ class: 'mdi mdi-eye', tag: 'i' }) },
      { name: 'va-eye-off', resolve: () => ({ class: 'mdi mdi-eye-off', tag: 'i' }) },
      { name: 'va-delete', resolve: () => ({ class: 'mdi mdi-delete', tag: 'i' }) },
      // Icones de ordenacao (DataTable)
      { name: 'va-unsorted', resolve: () => ({ class: 'mdi mdi-swap-vertical', tag: 'i' }) },
      { name: 'va-sort-asc', resolve: () => ({ class: 'mdi mdi-arrow-up', tag: 'i' }) },
      { name: 'va-sort-desc', resolve: () => ({ class: 'mdi mdi-arrow-down', tag: 'i' }) },
      // Outros icones Vuestic
      { name: 'va-plus', resolve: () => ({ class: 'mdi mdi-plus', tag: 'i' }) },
      { name: 'va-minus', resolve: () => ({ class: 'mdi mdi-minus', tag: 'i' }) },
      { name: 'va-expand', resolve: () => ({ class: 'mdi mdi-chevron-down', tag: 'i' }) },
      { name: 'va-collapse', resolve: () => ({ class: 'mdi mdi-chevron-up', tag: 'i' }) },
      { name: 'va-first-page', resolve: () => ({ class: 'mdi mdi-page-first', tag: 'i' }) },
      { name: 'va-last-page', resolve: () => ({ class: 'mdi mdi-page-last', tag: 'i' }) },
      { name: 'va-prev-page', resolve: () => ({ class: 'mdi mdi-chevron-left', tag: 'i' }) },
      { name: 'va-next-page', resolve: () => ({ class: 'mdi mdi-chevron-right', tag: 'i' }) }
    ],
    colors: {
      presets: {
        light: {
          primary: '#6366f1',
          secondary: '#8b5cf6',
          success: '#10b981',
          warning: '#f59e0b',
          danger: '#ef4444',
          info: '#0ea5e9',
          backgroundPrimary: '#ffffff',
          backgroundSecondary: '#f8fafc',
          backgroundElement: '#ffffff',
          backgroundBorder: '#e2e8f0',
          textPrimary: '#1e293b',
          textInverted: '#ffffff'
        },
        dark: {
          primary: '#818cf8',
          secondary: '#a78bfa',
          success: '#34d399',
          warning: '#fbbf24',
          danger: '#f87171',
          info: '#38bdf8',
          backgroundPrimary: '#0f172a',
          backgroundSecondary: '#1e293b',
          backgroundElement: '#1e293b',
          backgroundBorder: '#334155',
          textPrimary: '#e2e8f0',
          textInverted: '#0f172a'
        }
      }
    },
    components: {
      VaButton: {
        round: true
      },
      VaInput: {
        outline: true
      },
      VaSelect: {
        outline: true
      },
      VaIcon: {
        font: 'mdi'
      }
    }
  }
}))

app.mount('#app')
