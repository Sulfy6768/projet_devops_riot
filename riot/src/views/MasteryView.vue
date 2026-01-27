<template>
  <div class="mastery-page">
    <div v-if="!userStore.isLoggedIn" class="not-logged">
      <h2>🔒 Connexion requise</h2>
      <p>Connectez-vous pour voir vos masteries</p>
      <RouterLink to="/login" class="login-btn">Se connecter</RouterLink>
    </div>

    <div v-else class="mastery-content">
      <div class="mastery-header">
        <h1>🏆 Mes Masteries</h1>
        <div class="user-info">
          <span class="riot-id">{{ userStore.user?.riot_id }}</span>
          <button @click="refreshMasteries" class="refresh-btn" :disabled="loading">
            🔄 {{ loading ? 'Chargement...' : 'Actualiser' }}
          </button>
        </div>
      </div>

      <div v-if="error" class="error-message">
        {{ error }}
      </div>

      <div class="mastery-stats">
        <div class="stat-card">
          <span class="stat-value">{{ totalPoints.toLocaleString() }}</span>
          <span class="stat-label">Points totaux</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ mastery7Count }}</span>
          <span class="stat-label">Mastery 7</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ mastery6Count }}</span>
          <span class="stat-label">Mastery 6</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ masteries.length }}</span>
          <span class="stat-label">Champions joués</span>
        </div>
      </div>

      <div class="masteries-grid">
        <div 
          v-for="mastery in masteries" 
          :key="mastery.champion_id" 
          class="mastery-card"
          :class="getMasteryClass(mastery.champion_level)"
        >
          <img 
            :src="getChampionImage(mastery.champion_name)" 
            :alt="mastery.champion_name"
            class="champion-img"
            @error="onImageError"
          />
          <div class="mastery-info">
            <span class="champion-name">{{ mastery.champion_name }}</span>
            <div class="mastery-details">
              <span class="mastery-level">M{{ mastery.champion_level }}</span>
              <span class="mastery-points">{{ formatPoints(mastery.champion_points) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useUserStore } from '../stores/user'

interface Mastery {
  champion_id: number
  champion_name: string
  champion_level: number
  champion_points: number
  last_play_time?: number
}

const userStore = useUserStore()
const masteries = ref<Mastery[]>([])
const loading = ref(false)
const error = ref('')

const totalPoints = computed(() => 
  masteries.value.reduce((sum, m) => sum + m.champion_points, 0)
)

const mastery7Count = computed(() => 
  masteries.value.filter(m => m.champion_level >= 7).length
)

const mastery6Count = computed(() => 
  masteries.value.filter(m => m.champion_level === 6).length
)

onMounted(() => {
  if (userStore.isLoggedIn) {
    fetchMasteries()
  }
})

async function fetchMasteries() {
  if (!userStore.user?.riot_id) return
  
  loading.value = true
  error.value = ''

  try {
    const response = await fetch(
      `http://localhost:8000/masteries/${encodeURIComponent(userStore.user.riot_id)}`
    )

    if (!response.ok) {
      throw new Error('Impossible de charger les masteries')
    }

    const data = await response.json()
    masteries.value = data.masteries || []
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function refreshMasteries() {
  if (!userStore.user?.riot_id) return
  
  loading.value = true
  error.value = ''

  try {
    const response = await fetch(
      `http://localhost:8000/masteries/${encodeURIComponent(userStore.user.riot_id)}/refresh`,
      { method: 'POST' }
    )

    if (!response.ok) {
      throw new Error('Impossible de rafraîchir les masteries')
    }

    // Recharger les masteries
    await fetchMasteries()
  } catch (e: any) {
    error.value = e.message
    loading.value = false
  }
}

function getChampionImage(name: string): string {
  const fileName = name.toLowerCase().replace(/\s+/g, '_').replace(/'/g, '').replace(/\./g, '')
  return `/champ_img/${fileName}.png`
}

function onImageError(event: Event) {
  const img = event.target as HTMLImageElement
  img.src = '/champ_img/ahri.png'
}

function formatPoints(points: number): string {
  if (points >= 1000000) {
    return (points / 1000000).toFixed(1) + 'M'
  }
  if (points >= 1000) {
    return (points / 1000).toFixed(0) + 'K'
  }
  return points.toString()
}

function getMasteryClass(level: number): string {
  if (level >= 7) return 'mastery-7'
  if (level >= 6) return 'mastery-6'
  if (level >= 5) return 'mastery-5'
  return ''
}
</script>

<style scoped>
.mastery-page {
  padding: 1rem;
  width: 100%;
  max-width: 1200px;
}

.not-logged {
  text-align: center;
  padding: 4rem 2rem;
  background: #1a1a2e;
  border-radius: 16px;
}

.not-logged h2 {
  color: #42b883;
  margin-bottom: 1rem;
}

.not-logged p {
  color: #a0aec0;
  margin-bottom: 1.5rem;
}

.login-btn {
  display: inline-block;
  padding: 0.75rem 2rem;
  background: #42b883;
  color: #1a1a2e;
  text-decoration: none;
  border-radius: 8px;
  font-weight: 600;
}

.mastery-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.mastery-header h1 {
  color: #42b883;
  font-size: 1.5rem;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.riot-id {
  color: #a0aec0;
  font-size: 0.9rem;
}

.refresh-btn {
  padding: 0.5rem 1rem;
  background: #2d3748;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: background 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  background: #42b883;
  color: #1a1a2e;
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.mastery-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: #1a1a2e;
  padding: 1.5rem;
  border-radius: 12px;
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 1.75rem;
  font-weight: 700;
  color: #42b883;
}

.stat-label {
  display: block;
  font-size: 0.85rem;
  color: #a0aec0;
  margin-top: 0.25rem;
}

.masteries-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.mastery-card {
  background: #1a1a2e;
  border-radius: 12px;
  padding: 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  border: 2px solid transparent;
  transition: transform 0.2s, border-color 0.2s;
}

.mastery-card:hover {
  transform: translateY(-2px);
}

.mastery-card.mastery-7 {
  border-color: #c0a060;
  background: linear-gradient(135deg, #1a1a2e 0%, #2a2040 100%);
}

.mastery-card.mastery-6 {
  border-color: #9966cc;
}

.mastery-card.mastery-5 {
  border-color: #e04040;
}

.champion-img {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  object-fit: cover;
}

.mastery-info {
  flex: 1;
}

.champion-name {
  display: block;
  font-weight: 600;
  color: white;
  font-size: 0.95rem;
}

.mastery-details {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.25rem;
}

.mastery-level {
  font-size: 0.8rem;
  font-weight: 700;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  background: #42b883;
  color: #1a1a2e;
}

.mastery-7 .mastery-level {
  background: linear-gradient(135deg, #c0a060, #e8d48c);
}

.mastery-6 .mastery-level {
  background: #9966cc;
  color: white;
}

.mastery-5 .mastery-level {
  background: #e04040;
  color: white;
}

.mastery-points {
  font-size: 0.85rem;
  color: #a0aec0;
}
</style>
