<template>
  <div class="login-page">
    <div class="login-card">
      <h1>{{ isRegister ? '📝 Créer un compte' : '🔐 Connexion' }}</h1>
      
      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label for="riotId">Riot ID</label>
          <input 
            id="riotId"
            v-model="riotId" 
            type="text" 
            placeholder="GameName#TagLine (ex: KKC Sulfy#SuS)"
            required
          />
        </div>

        <div class="form-group">
          <label for="password">Mot de passe</label>
          <input 
            id="password"
            v-model="password" 
            type="password" 
            placeholder="Votre mot de passe"
            required
          />
        </div>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <button type="submit" class="submit-btn" :disabled="loading">
          {{ loading ? 'Chargement...' : (isRegister ? 'Créer le compte' : 'Se connecter') }}
        </button>
      </form>

      <div class="toggle-mode">
        <span v-if="isRegister">
          Déjà un compte ? 
          <a href="#" @click.prevent="isRegister = false">Se connecter</a>
        </span>
        <span v-else>
          Pas encore de compte ? 
          <a href="#" @click.prevent="isRegister = true">Créer un compte</a>
        </span>
      </div>

      <div class="info-box">
        <p>💡 En vous connectant, vos <strong>masteries</strong> seront automatiquement synchronisées depuis votre compte Riot.</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const isRegister = ref(false)
const riotId = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleSubmit() {
  error.value = ''
  loading.value = true

  try {
    const endpoint = isRegister.value ? '/auth/register' : '/auth/login'
    const response = await fetch(`http://localhost:8000${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        riot_id: riotId.value,
        password: password.value
      })
    })

    if (!response.ok) {
      const data = await response.json()
      throw new Error(data.detail || 'Erreur de connexion')
    }

    const userData = await response.json()
    
    // Sauvegarder l'utilisateur dans le store
    userStore.login(userData)
    
    // Rediriger vers la page mastery
    router.push('/mastery')
  } catch (e: any) {
    error.value = e.message || 'Une erreur est survenue'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 80vh;
  padding: 1rem;
}

.login-card {
  background: #1a1a2e;
  border-radius: 16px;
  padding: 2rem;
  width: 100%;
  max-width: 400px;
}

.login-card h1 {
  text-align: center;
  color: #42b883;
  margin-bottom: 1.5rem;
  font-size: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #a0aec0;
  font-size: 0.9rem;
}

.form-group input {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 2px solid #2d3748;
  border-radius: 8px;
  background: #16213e;
  color: white;
  font-size: 1rem;
  transition: border-color 0.2s;
}

.form-group input:focus {
  outline: none;
  border-color: #42b883;
}

.error-message {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
  padding: 0.75rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.submit-btn {
  width: 100%;
  padding: 0.875rem;
  background: #42b883;
  color: #1a1a2e;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.submit-btn:hover:not(:disabled) {
  background: #3aa876;
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.toggle-mode {
  text-align: center;
  margin-top: 1.5rem;
  color: #a0aec0;
  font-size: 0.9rem;
}

.toggle-mode a {
  color: #42b883;
  text-decoration: none;
  font-weight: 500;
}

.toggle-mode a:hover {
  text-decoration: underline;
}

.info-box {
  margin-top: 1.5rem;
  padding: 1rem;
  background: rgba(66, 184, 131, 0.1);
  border-radius: 8px;
  border: 1px solid rgba(66, 184, 131, 0.3);
}

.info-box p {
  color: #a0aec0;
  font-size: 0.85rem;
  margin: 0;
  line-height: 1.5;
}
</style>
