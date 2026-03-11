import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('auth_token') || null)
  const email = ref(localStorage.getItem('auth_email') || null)
  const loading = ref(false)
  const error = ref(null)

  const isAuthenticated = computed(() => !!token.value)

  async function login(emailInput, password) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.post('/auth/login', { email: emailInput, password })
      token.value = data.access_token
      email.value = data.email
      localStorage.setItem('auth_token', data.access_token)
      localStorage.setItem('auth_email', data.email)
      // Setar token no axios para proximas requisicoes
      api.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`
      return true
    } catch (err) {
      error.value = err.response?.data?.detail || 'Erro ao fazer login'
      return false
    } finally {
      loading.value = false
    }
  }

  function logout() {
    token.value = null
    email.value = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_email')
    delete api.defaults.headers.common['Authorization']
  }

  // Restaurar token no axios se ja existe
  function initAuth() {
    if (token.value) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
    }
  }

  return { token, email, loading, error, isAuthenticated, login, logout, initAuth }
})
