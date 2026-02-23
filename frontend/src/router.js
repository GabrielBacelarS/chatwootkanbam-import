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
        path: 'schemas',
        name: 'ProductSchemas',
        component: () => import('./views/admin/ProductSchemas.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
