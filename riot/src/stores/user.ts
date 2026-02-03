import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

interface User {
  riot_id: string
  puuid?: string
  region?: string
}

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)

  // Charger l'utilisateur depuis localStorage au démarrage
  const savedUser = localStorage.getItem('riot_user')
  if (savedUser) {
    try {
      user.value = JSON.parse(savedUser)
    } catch {
      localStorage.removeItem('riot_user')
    }
  }

  const isLoggedIn = computed(() => user.value !== null)

  function login(userData: User) {
    user.value = userData
    localStorage.setItem('riot_user', JSON.stringify(userData))
  }

  function logout() {
    user.value = null
    localStorage.removeItem('riot_user')
  }

  return {
    user,
    isLoggedIn,
    login,
    logout
  }
})
