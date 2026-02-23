import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  // ===== ÁREA ADMIN =====
  {
    path: '/',
    redirect: '/admin/dashboard'
  },
  {
    path: '/admin',
    component: () => import('./layouts/AdminLayout.vue'),
    children: [
      {
        path: '',
        redirect: '/admin/dashboard'
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('./views/admin/Dashboard.vue')
      },
      {
        path: 'analytics',
        name: 'Analytics',
        component: () => import('./views/admin/Analytics.vue')
      },
      {
        path: 'clientes',
        name: 'Clientes',
        component: () => import('./views/admin/Clientes.vue')
      },
      {
        path: 'cliente/:slug',
        name: 'ClienteConfig',
        component: () => import('./views/admin/ClienteConfig.vue')
      },
      {
        path: 'ab-testing',
        name: 'ABTesting',
        component: () => import('./views/admin/ABTesting.vue')
      },
      {
        path: 'lead-scoring',
        name: 'LeadScoring',
        component: () => import('./views/admin/LeadScoring.vue')
      },
      {
        path: 'integrations',
        name: 'Integrations',
        component: () => import('./views/admin/Integrations.vue')
      },
      {
        path: 'schemas',
        name: 'ProductSchemas',
        component: () => import('./views/admin/ProductSchemas.vue')
      },
      {
        path: 'compliance',
        name: 'Compliance',
        component: () => import('./views/admin/Compliance.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
