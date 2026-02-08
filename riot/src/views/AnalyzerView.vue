<template>
  <div class="analyzer-container">
    <!-- Draft Phase Indicator -->
    <div class="draft-phase">
      <h2>{{ currentPhaseLabel }}</h2>
      <div class="phase-progress">
        <div 
          v-for="(step, idx) in draftOrder" 
          :key="idx" 
          class="phase-step"
          :class="{ 
            active: idx === currentStep,
            done: idx < currentStep,
            ban: step.type === 'ban',
            pick: step.type === 'pick',
            blue: step.team === 'blue',
            red: step.team === 'red'
          }"
        >
          {{ step.type === 'ban' ? 'B' : 'P' }}
        </div>
      </div>
    </div>

    <!-- Bans Section -->
    <div class="bans-section">
      <div class="bans-row blue-bans">
        <span class="bans-label">🔵 Bans</span>
        <div class="bans-list">
          <div 
            v-for="(ban, idx) in blueBans" 
            :key="'blue-ban-' + idx"
            class="ban-slot"
            :class="{ filled: ban, active: isCurrentBanSlot('blue', idx) }"
            @click="selectBanSlot('blue', idx)"
          >
            <img v-if="ban" :src="ban.image" :alt="ban.name" />
            <span v-else class="ban-number">{{ idx + 1 }}</span>
          </div>
        </div>
      </div>
      <div class="bans-row red-bans">
        <span class="bans-label">🔴 Bans</span>
        <div class="bans-list">
          <div 
            v-for="(ban, idx) in redBans" 
            :key="'red-ban-' + idx"
            class="ban-slot"
            :class="{ filled: ban, active: isCurrentBanSlot('red', idx) }"
            @click="selectBanSlot('red', idx)"
          >
            <img v-if="ban" :src="ban.image" :alt="ban.name" />
            <span v-else class="ban-number">{{ idx + 1 }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="teams-wrapper">
      <!-- Blue Team Section -->
      <div class="team blue-team">
        <div class="team-header">
          <h2>🔵 Blue Team</h2>
          <div class="win-rate" :class="{ loading: mlPrediction.loading, 'ml-active': mlPrediction.model_loaded }">
            <span v-if="mlPrediction.loading">⏳</span>
            <span v-else>{{ blueWinRate }}%</span>
            <span v-if="mlPrediction.model_loaded && !mlPrediction.loading" class="ml-badge" title="Prédiction ML">🤖</span>
          </div>
        </div>
        <div class="champions-slots">
          <div
            v-for="(slot, index) in blueSlots"
            :key="'blue-' + index"
            class="champion-slot"
            :class="{ filled: slot.champion, selected: isSlotSelected('blue', index) }"
          >
            <!-- Riot ID Input -->
            <div class="player-input-row">
              <span class="role-badge" :class="getRoleClass(index)">{{ getRoleName(index) }}</span>
              <input 
                v-model="slot.riotId" 
                type="text" 
                placeholder="Riot ID"
                @blur="loadPlayerMasteries('blue', index)"
                @click.stop
              />
              <span v-if="slot.loading" class="status-icon">⏳</span>
              <span v-else-if="slot.masteries.length > 0" class="status-icon success">✓</span>
            </div>
            
            <!-- Champion Display or Recommendations -->
            <div v-if="slot.champion" class="champion-card" @click="selectSlot('blue', index)">
              <img :src="slot.champion.image" :alt="slot.champion.name" />
              <div class="champion-info">
                <p class="champion-name">{{ slot.champion.name }}</p>
              </div>
              <button class="remove-btn" @click.stop="removeChampion('blue', index)">×</button>
            </div>
            <div v-else class="empty-slot" @click="selectSlot('blue', index)">
              <!-- Recommendations based on meta + masteries -->
              <div v-if="slot.recommendations.length > 0" class="recommendations-mini">
                <div 
                  v-for="(rec, recIndex) in slot.recommendations" 
                  :key="`blue-${index}-${recIndex}-${rec.champion_name}`"
                  class="rec-mini"
                  :class="[getMasteryClass(rec.champion_level), getTierClass(rec.tier)]"
                  @click.stop="quickPick('blue', index, rec.champion_name)"
                  :title="getRecTooltip(rec)"
                >
                  <img :src="rec.image" :alt="rec.champion_name" />
                  <span v-if="rec.tier" class="tier-badge" :class="'tier-' + rec.tier">{{ rec.tier }}</span>
                </div>
              </div>
              <span v-else class="slot-placeholder">Cliquez pour pick</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Champion Pool (Center) -->
      <div class="champion-pool-section">
        <div class="pool-header">
          <h3>Champions</h3>
          <input v-model="searchQuery" type="text" placeholder="Rechercher..." class="search-input" />
        </div>
        <div class="champions-grid">
          <div
            v-for="champion in filteredChampions"
            :key="champion.id"
            class="pool-champion"
            :class="{ 
              disabled: isChampionUnavailable(champion.id),
              'has-mastery': currentSlotHasMastery(champion.name)
            }"
            @click="selectChampion(champion)"
          >
            <img :src="champion.image" :alt="champion.name" />
            <span v-if="currentSlotHasMastery(champion.name)" class="mastery-badge" :class="getMasteryClassForChamp(champion.name)">
              M{{ getMasteryLevelForChamp(champion.name) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Red Team Section -->
      <div class="team red-team">
        <div class="team-header">
          <h2>🔴 Red Team</h2>
          <div class="win-rate" :class="{ loading: mlPrediction.loading, 'ml-active': mlPrediction.model_loaded }">
            <span v-if="mlPrediction.loading">⏳</span>
            <span v-else>{{ redWinRate }}%</span>
            <span v-if="mlPrediction.model_loaded && !mlPrediction.loading" class="ml-badge" title="Prédiction ML">🤖</span>
          </div>
        </div>
        <div class="champions-slots">
          <div
            v-for="(slot, index) in redSlots"
            :key="'red-' + index"
            class="champion-slot"
            :class="{ filled: slot.champion, selected: isSlotSelected('red', index) }"
          >
            <!-- Riot ID Input -->
            <div class="player-input-row">
              <span class="role-badge" :class="getRoleClass(index)">{{ getRoleName(index) }}</span>
              <input 
                v-model="slot.riotId" 
                type="text" 
                placeholder="Riot ID"
                @blur="loadPlayerMasteries('red', index)"
                @click.stop
              />
              <span v-if="slot.loading" class="status-icon">⏳</span>
              <span v-else-if="slot.masteries.length > 0" class="status-icon success">✓</span>
            </div>
            
            <!-- Champion Display -->
            <div v-if="slot.champion" class="champion-card" @click="selectSlot('red', index)">
              <img :src="slot.champion.image" :alt="slot.champion.name" />
              <div class="champion-info">
                <p class="champion-name">{{ slot.champion.name }}</p>
              </div>
              <button class="remove-btn" @click.stop="removeChampion('red', index)">×</button>
            </div>
            <div v-else class="empty-slot" @click="selectSlot('red', index)">
              <div v-if="slot.recommendations.length > 0" class="recommendations-mini">
                <div 
                  v-for="(rec, recIndex) in slot.recommendations" 
                  :key="`red-${index}-${recIndex}-${rec.champion_name}`"
                  class="rec-mini"
                  :class="[getMasteryClass(rec.champion_level), getTierClass(rec.tier)]"
                  @click.stop="quickPick('red', index, rec.champion_name)"
                  :title="getRecTooltip(rec)"
                >
                  <img :src="rec.image" :alt="rec.champion_name" />
                  <span v-if="rec.tier" class="tier-badge" :class="'tier-' + rec.tier">{{ rec.tier }}</span>
                </div>
              </div>
              <span v-else class="slot-placeholder">Cliquez pour pick</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="actions">
      <button class="action-btn reset" @click="resetDraft">🔄 Reset Draft</button>
      <button class="action-btn next" @click="nextStep" :disabled="currentStep >= draftOrder.length">
        Étape suivante →
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { loadChampionsSync, normalizeChampionName, getChampionImagePath } from '../utils/championLoader'

interface Champion {
  id: string
  name: string
  role: string
  image: string
  tier: number
  winRate: number
}

interface PlayerMastery {
  champion_id: number
  champion_name: string
  champion_level: number
  champion_points: number
}

interface RecommendationItem {
  champion_name: string
  champion_level: number
  image: string
  winrate?: number
  tier?: string
  score?: number
  reason?: string
  counter_score?: number
}

interface ApiRecommendation {
  champion: string
  mastery_level?: number
  winrate?: number
  tier?: string
  score?: number
  reason?: string
  counter_score?: number
}

interface PlayerSlot {
  riotId: string
  champion: Champion | null
  loading: boolean
  masteries: PlayerMastery[]
  recommendations: RecommendationItem[]
}

interface DraftStep {
  type: 'ban' | 'pick'
  team: 'blue' | 'red'
  index: number
}

const API_URL = 'http://localhost:8000'

// Pro draft order (simplified)
// Ban Phase 1: B-R-B-R-B-R (6 bans)
// Pick Phase 1: B-R-R-B-B-R (6 picks)
// Ban Phase 2: R-B-R-B (4 bans)
// Pick Phase 2: R-B-B-R (4 picks)
const draftOrder = ref<DraftStep[]>([
  // Ban Phase 1
  { type: 'ban', team: 'blue', index: 0 },
  { type: 'ban', team: 'red', index: 0 },
  { type: 'ban', team: 'blue', index: 1 },
  { type: 'ban', team: 'red', index: 1 },
  { type: 'ban', team: 'blue', index: 2 },
  { type: 'ban', team: 'red', index: 2 },
  // Pick Phase 1
  { type: 'pick', team: 'blue', index: 0 },
  { type: 'pick', team: 'red', index: 0 },
  { type: 'pick', team: 'red', index: 1 },
  { type: 'pick', team: 'blue', index: 1 },
  { type: 'pick', team: 'blue', index: 2 },
  { type: 'pick', team: 'red', index: 2 },
  // Ban Phase 2
  { type: 'ban', team: 'red', index: 3 },
  { type: 'ban', team: 'blue', index: 3 },
  { type: 'ban', team: 'red', index: 4 },
  { type: 'ban', team: 'blue', index: 4 },
  // Pick Phase 2
  { type: 'pick', team: 'red', index: 3 },
  { type: 'pick', team: 'blue', index: 3 },
  { type: 'pick', team: 'blue', index: 4 },
  { type: 'pick', team: 'red', index: 4 },
])

const currentStep = ref(0)
const champions = ref<Champion[]>([])
const searchQuery = ref('')

const blueSlots = ref<PlayerSlot[]>([
  { riotId: '', champion: null, loading: false, masteries: [], recommendations: [] },
  { riotId: '', champion: null, loading: false, masteries: [], recommendations: [] },
  { riotId: '', champion: null, loading: false, masteries: [], recommendations: [] },
  { riotId: '', champion: null, loading: false, masteries: [], recommendations: [] },
  { riotId: '', champion: null, loading: false, masteries: [], recommendations: [] },
])

const redSlots = ref<PlayerSlot[]>([
  { riotId: '', champion: null, loading: false, masteries: [], recommendations: [] },
  { riotId: '', champion: null, loading: false, masteries: [], recommendations: [] },
  { riotId: '', champion: null, loading: false, masteries: [], recommendations: [] },
  { riotId: '', champion: null, loading: false, masteries: [], recommendations: [] },
  { riotId: '', champion: null, loading: false, masteries: [], recommendations: [] },
])

const blueBans = ref<(Champion | null)[]>([null, null, null, null, null])
const redBans = ref<(Champion | null)[]>([null, null, null, null, null])

const selectedSlot = ref<{ team: 'blue' | 'red' | null; index: number | null; type: 'pick' | 'ban' }>({ 
  team: null, 
  index: null,
  type: 'pick'
})

// ML Prediction state
const mlPrediction = ref({
  blue_winrate: 50.0,
  red_winrate: 50.0,
  model_loaded: false,
  loading: false,
  confidence: 'low' as 'low' | 'high'
})

// Position mapping for picks
const POSITION_MAP = ['top', 'jng', 'mid', 'bot', 'sup']

onMounted(() => {
  champions.value = loadChampionsSync()
  updateCurrentSelection()
})

const currentPhaseLabel = computed(() => {
  if (currentStep.value >= draftOrder.value.length) return '✅ Draft Terminé'
  const step = draftOrder.value[currentStep.value]
  if (!step) return '✅ Draft Terminé'
  const teamName = step.team === 'blue' ? 'Bleue' : 'Rouge'
  const action = step.type === 'ban' ? 'Ban' : 'Pick'
  return `${action} - Équipe ${teamName}`
})

// Use ML prediction for winrates
const blueWinRate = computed(() => {
  return mlPrediction.value.blue_winrate.toFixed(1)
})

const redWinRate = computed(() => {
  return mlPrediction.value.red_winrate.toFixed(1)
})

const currentSlotMasteries = computed(() => {
  if (selectedSlot.value.team && selectedSlot.value.index !== null && selectedSlot.value.type === 'pick') {
    const slots = selectedSlot.value.team === 'blue' ? blueSlots.value : redSlots.value
    return slots[selectedSlot.value.index]?.masteries || []
  }
  return []
})

const filteredChampions = computed(() => {
  let filtered = champions.value.filter(c => 
    c.name.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
  
  // Sort by mastery if slot selected
  if (currentSlotMasteries.value.length > 0) {
    const masteryMap = new Map(currentSlotMasteries.value.map(m => [m.champion_name.toLowerCase(), m]))
    filtered = [...filtered].sort((a, b) => {
      const mA = masteryMap.get(a.name.toLowerCase())
      const mB = masteryMap.get(b.name.toLowerCase())
      if (mA && mB) return mB.champion_points - mA.champion_points
      if (mA) return -1
      if (mB) return 1
      return 0
    })
  }
  
  return filtered
})

function updateCurrentSelection() {
  if (currentStep.value < draftOrder.value.length) {
    const step = draftOrder.value[currentStep.value]
    if (step) {
      selectedSlot.value = { team: step.team, index: step.index, type: step.type }
    }
  }
}

// ============================================
// ML Prediction Functions
// ============================================

async function fetchMLPrediction() {
  // Build draft data for the API
  const blueBanNames = blueBans.value
    .filter(b => b !== null)
    .map(b => b!.name)
  
  const redBanNames = redBans.value
    .filter(b => b !== null)
    .map(b => b!.name)
  
  // Format picks as "Champion.position"
  const bluePicks = blueSlots.value
    .map((slot, idx) => {
      if (!slot.champion) return ''
      const position = POSITION_MAP[idx] || 'unknown'
      return `${slot.champion.name}.${position}`
    })
    .filter(p => p !== '')
  
  const redPicks = redSlots.value
    .map((slot, idx) => {
      if (!slot.champion) return ''
      const position = POSITION_MAP[idx] || 'unknown'
      return `${slot.champion.name}.${position}`
    })
    .filter(p => p !== '')
  
  // Only call API if we have at least some data
  if (blueBanNames.length === 0 && redBanNames.length === 0 && 
      bluePicks.length === 0 && redPicks.length === 0) {
    mlPrediction.value = {
      blue_winrate: 50.0,
      red_winrate: 50.0,
      model_loaded: false,
      loading: false,
      confidence: 'low'
    }
    return
  }
  
  mlPrediction.value.loading = true
  
  try {
    const response = await fetch(`${API_URL}/draft/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        blue_bans: blueBanNames,
        red_bans: redBanNames,
        blue_picks: bluePicks,
        red_picks: redPicks
      })
    })
    
    if (response.ok) {
      const data = await response.json()
      mlPrediction.value = {
        blue_winrate: data.blue_winrate || 50.0,
        red_winrate: data.red_winrate || 50.0,
        model_loaded: data.model_loaded || false,
        loading: false,
        confidence: data.confidence || 'low'
      }
    }
  } catch (error) {
    console.error('Error fetching ML prediction:', error)
    mlPrediction.value.loading = false
  }
}

// Watch for draft changes and update prediction
watch(
  () => [
    blueBans.value.filter(b => b).length,
    redBans.value.filter(b => b).length,
    blueSlots.value.filter(s => s.champion).length,
    redSlots.value.filter(s => s.champion).length
  ],
  () => {
    // Debounce: wait 300ms after last change
    fetchMLPrediction()
  },
  { deep: true }
)

// ============================================
// Draft Selection Functions
// ============================================

function isCurrentBanSlot(team: 'blue' | 'red', index: number): boolean {
  return selectedSlot.value.type === 'ban' && 
         selectedSlot.value.team === team && 
         selectedSlot.value.index === index
}

function selectBanSlot(team: 'blue' | 'red', index: number) {
  selectedSlot.value = { team, index, type: 'ban' }
}

function isSlotSelected(team: 'blue' | 'red', index: number): boolean {
  return selectedSlot.value.type === 'pick' &&
         selectedSlot.value.team === team && 
         selectedSlot.value.index === index
}

function selectSlot(team: 'blue' | 'red', index: number) {
  selectedSlot.value = { team, index, type: 'pick' }
}

function isChampionUnavailable(championId: string): boolean {
  const allPicked = [...blueSlots.value, ...redSlots.value]
    .filter(s => s.champion)
    .map(s => s.champion!.id)
  const allBanned = [...blueBans.value, ...redBans.value]
    .filter(b => b)
    .map(b => b!.id)
  return allPicked.includes(championId) || allBanned.includes(championId)
}

function selectChampion(champion: Champion) {
  if (isChampionUnavailable(champion.id)) return
  
  const { team, index, type } = selectedSlot.value
  if (!team || index === null) return
  
  if (type === 'ban') {
    if (team === 'blue') {
      blueBans.value[index] = champion
    } else {
      redBans.value[index] = champion
    }
  } else {
    const slots = team === 'blue' ? blueSlots.value : redSlots.value
    const slot = slots[index]
    if (slot) {
      slot.champion = champion
    }
  }
  
  // Update recommendations to exclude newly picked/banned champion
  updateAllRecommendations()
  
  // Auto advance to next step
  if (currentStep.value < draftOrder.value.length) {
    currentStep.value++
    updateCurrentSelection()
  }
}

function quickPick(team: 'blue' | 'red', index: number, championName: string) {
  const champion = champions.value.find(c => c.name.toLowerCase() === championName.toLowerCase())
  if (champion && !isChampionUnavailable(champion.id)) {
    const slots = team === 'blue' ? blueSlots.value : redSlots.value
    const slot = slots[index]
    if (slot) {
      slot.champion = champion
      // Update recommendations to exclude newly picked champion
      updateAllRecommendations()
      
      // Auto advance to next step
      if (currentStep.value < draftOrder.value.length) {
        currentStep.value++
        updateCurrentSelection()
      }
    }
  }
}

function removeChampion(team: 'blue' | 'red', index: number) {
  const slots = team === 'blue' ? blueSlots.value : redSlots.value
  const slot = slots[index]
  if (slot) {
    slot.champion = null
    // Update recommendations since champion is now available
    updateAllRecommendations()
  }
}

function nextStep() {
  if (currentStep.value < draftOrder.value.length) {
    currentStep.value++
    updateCurrentSelection()
  }
}

function resetDraft() {
  currentStep.value = 0
  blueSlots.value.forEach(s => s.champion = null)
  redSlots.value.forEach(s => s.champion = null)
  blueBans.value = [null, null, null, null, null]
  redBans.value = [null, null, null, null, null]
  updateCurrentSelection()
}

async function loadPlayerMasteries(team: 'blue' | 'red', index: number) {
  const slots = team === 'blue' ? blueSlots.value : redSlots.value
  const slot = slots[index]
  if (!slot || !slot.riotId || !slot.riotId.includes('#')) return
  
  slot.loading = true
  slot.masteries = []
  slot.recommendations = []
  
  const role = getRoleKey(index) // top, jng, mid, bot, sup
  
  try {
    // D'abord charger les masteries pour le champion pool via lookup (pas besoin d'être enregistré)
    const parts = slot.riotId.split('#')
    const gameName = parts[0] || ''
    const tagLine = parts[1] || ''
    if (!gameName || !tagLine) return
    
    const masteryResponse = await fetch(`${API_URL}/masteries/lookup/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}?limit=50`)
    
    if (masteryResponse.ok) {
      const masteryData = await masteryResponse.json()
      slot.masteries = masteryData.masteries || []
      
      // Auto-ajouter le joueur à la BDD pour les futures recommandations
      fetch(`${API_URL}/players/add/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}`, { method: 'POST' })
        .catch(() => {}) // Ignorer les erreurs silencieusement
    }
    
    // Construire les paramètres pour les recommandations
    const enemyTeamSlots = team === 'blue' ? redSlots.value : blueSlots.value
    const allyTeamSlots = team === 'blue' ? blueSlots.value : redSlots.value
    
    // Champions ennemis déjà pickés
    const enemyChampions = enemyTeamSlots
      .filter(s => s.champion)
      .map(s => s.champion!.name)
    
    // Champions alliés déjà pickés (exclure le slot actuel)
    const allyChampions = allyTeamSlots
      .filter((s, i) => s.champion && i !== index)
      .map(s => s.champion!.name)
    
    // Champions bannis
    const bannedChampions = [...blueBans.value, ...redBans.value]
      .filter(b => b)
      .map(b => b!.name)
    
    // Déterminer le mode: counter si ennemis, sinon blind
    const mode = enemyChampions.length > 0 ? 'counter' : 'balanced'
    
    // Construire l'URL avec les paramètres
    let recUrl = `${API_URL}/recommend/${encodeURIComponent(slot.riotId)}?role=${role}&top_n=4&min_pickrate=0.5&mode=${mode}`
    
    if (enemyChampions.length > 0) {
      recUrl += `&enemy_champions=${encodeURIComponent(enemyChampions.join(','))}`
    }
    if (allyChampions.length > 0) {
      recUrl += `&ally_champions=${encodeURIComponent(allyChampions.join(','))}`
    }
    if (bannedChampions.length > 0) {
      recUrl += `&banned_champions=${encodeURIComponent(bannedChampions.join(','))}`
    }
    
    const recResponse = await fetch(recUrl)
    
    if (recResponse.ok) {
      const recData = await recResponse.json()
      const roleRecs = recData.recommendations?.[role] || []
      
      // Mapper les recommandations avec les images
      slot.recommendations = roleRecs
        .filter((rec: ApiRecommendation) => {
          const normalizedName = normalizeChampionName(rec.champion)
          const champ = champions.value.find(c => c.name.toLowerCase() === normalizedName.toLowerCase())
          return champ && !isChampionUnavailable(champ.id)
        })
        .slice(0, 4)
        .map((rec: ApiRecommendation) => {
          const displayName = normalizeChampionName(rec.champion)
          return {
            champion_name: displayName,
            champion_level: rec.mastery_level || 0,
            image: getChampionImagePath(rec.champion),
            winrate: rec.winrate,
            tier: rec.tier,
            score: rec.score,
            reason: rec.reason,
            counter_score: rec.counter_score
          }
        })
    } else {
      // Pas de recommandations disponibles - ne pas faire de fallback sur les masteries
      slot.recommendations = []
    }
  } catch (error) {
    console.error('Error loading recommendations:', error)
    // En cas d'erreur, ne pas faire de fallback sur les masteries
    slot.recommendations = []
  } finally {
    slot.loading = false
  }
}

function getRoleKey(index: number): string {
  const roles = ['top', 'jng', 'mid', 'bot', 'sup']
  return roles[index] || 'top'
}

async function updateAllRecommendations() {
  // Recharger les recommandations pour tous les slots qui ont un riotId
  // Cela prend en compte le nouveau contexte du draft
  const slotsToUpdate: Array<{ team: 'blue' | 'red', index: number }> = []
  
  blueSlots.value.forEach((slot, index) => {
    if (slot.riotId && slot.riotId.includes('#') && !slot.champion) {
      slotsToUpdate.push({ team: 'blue', index })
    }
  })
  
  redSlots.value.forEach((slot, index) => {
    if (slot.riotId && slot.riotId.includes('#') && !slot.champion) {
      slotsToUpdate.push({ team: 'red', index })
    }
  })
  
  // Mettre à jour en parallèle
  await Promise.all(
    slotsToUpdate.map(({ team, index }) => loadPlayerMasteries(team, index))
  )
}

function currentSlotHasMastery(championName: string): boolean {
  return currentSlotMasteries.value.some(m => m.champion_name.toLowerCase() === championName.toLowerCase())
}

function getMasteryLevelForChamp(championName: string): number {
  const m = currentSlotMasteries.value.find(m => m.champion_name.toLowerCase() === championName.toLowerCase())
  return m?.champion_level || 0
}

function getMasteryClassForChamp(championName: string): string {
  const level = getMasteryLevelForChamp(championName)
  return getMasteryClass(level)
}

function getMasteryClass(level: number): string {
  if (level >= 7) return 'm7'
  if (level >= 6) return 'm6'
  if (level >= 5) return 'm5'
  return 'mlow'
}

function getTierClass(tier?: string): string {
  if (!tier) return ''
  return 'tier-' + tier.toLowerCase()
}

function getRecTooltip(rec: RecommendationItem): string {
  let tooltip = rec.champion_name
  if (rec.tier) tooltip += ` | Tier ${rec.tier}`
  if (rec.winrate) tooltip += ` | ${rec.winrate}% WR`
  if (rec.champion_level > 0) tooltip += ` | M${rec.champion_level}`
  if (rec.reason) tooltip += `\n${rec.reason}`
  return tooltip
}

function getRoleName(index: number): string {
  const roles = ['TOP', 'JGL', 'MID', 'BOT', 'SUP']
  return roles[index] || ''
}

function getRoleClass(index: number): string {
  const classes = ['top', 'jungle', 'middle', 'bottom', 'utility']
  return classes[index] || ''
}
</script>

<style scoped>
.analyzer-container {
  width: 100%;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  color: #fff;
  padding: 15px;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* Draft Phase */
.draft-phase {
  text-align: center;
  margin-bottom: 15px;
}

.draft-phase h2 {
  color: #42b883;
  margin: 0 0 10px 0;
  font-size: 1.2rem;
}

.phase-progress {
  display: flex;
  justify-content: center;
  gap: 4px;
  flex-wrap: wrap;
}

.phase-step {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: bold;
  opacity: 0.3;
}

.phase-step.done { opacity: 0.6; }
.phase-step.active { opacity: 1; transform: scale(1.2); }
.phase-step.ban.blue { background: #3498db; }
.phase-step.ban.red { background: #e74c3c; }
.phase-step.pick.blue { background: #2980b9; }
.phase-step.pick.red { background: #c0392b; }

/* Bans Section */
.bans-section {
  display: flex;
  justify-content: space-between;
  margin-bottom: 15px;
  gap: 20px;
}

.bans-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bans-label {
  font-weight: bold;
  font-size: 0.9rem;
}

.bans-list {
  display: flex;
  gap: 5px;
}

.ban-slot {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s;
}

.ban-slot.active {
  border-color: #f39c12;
  box-shadow: 0 0 10px rgba(243, 156, 18, 0.5);
}

.ban-slot.filled {
  border-color: #e74c3c;
}

.ban-slot img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  filter: grayscale(100%);
}

.ban-number {
  color: #666;
  font-size: 0.8rem;
}

/* Teams Wrapper */
.teams-wrapper {
  display: grid;
  grid-template-columns: 300px 1fr 300px;
  gap: 15px;
}

/* Team Sections */
.team {
  background: rgba(0,0,0,0.3);
  border-radius: 10px;
  padding: 15px;
}

.team-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.team-header h2 {
  margin: 0;
  font-size: 1rem;
}

.win-rate {
  background: #42b883;
  padding: 4px 10px;
  border-radius: 15px;
  font-weight: bold;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: all 0.3s ease;
}

.win-rate.loading {
  opacity: 0.7;
}

.win-rate.ml-active {
  background: linear-gradient(45deg, #42b883, #2c7a56);
  box-shadow: 0 0 10px rgba(66, 184, 131, 0.4);
}

.ml-badge {
  font-size: 0.75rem;
}

.champions-slots {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.champion-slot {
  background: rgba(255,255,255,0.05);
  border-radius: 8px;
  padding: 8px;
  border: 2px solid transparent;
  transition: all 0.2s;
}

.champion-slot.selected {
  border-color: #f39c12;
  box-shadow: 0 0 10px rgba(243, 156, 18, 0.3);
}

.champion-slot.filled {
  border-color: #42b883;
}

/* Player Input Row */
.player-input-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.role-badge {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.65rem;
  font-weight: bold;
}

.role-badge.top { background: #e74c3c; }
.role-badge.jungle { background: #27ae60; }
.role-badge.middle { background: #3498db; }
.role-badge.bottom { background: #f39c12; }
.role-badge.utility { background: #9b59b6; }

.player-input-row input {
  flex: 1;
  padding: 4px 8px;
  border: 1px solid #333;
  border-radius: 4px;
  background: rgba(0,0,0,0.3);
  color: white;
  font-size: 0.75rem;
}

.player-input-row input:focus {
  border-color: #42b883;
  outline: none;
}

.status-icon {
  font-size: 0.8rem;
}

.status-icon.success {
  color: #42b883;
}

/* Champion Card */
.champion-card {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  position: relative;
}

.champion-card img {
  width: 45px;
  height: 45px;
  border-radius: 8px;
}

.champion-info {
  flex: 1;
}

.champion-name {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 500;
}

.remove-btn {
  position: absolute;
  top: -5px;
  right: -5px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: none;
  background: #e74c3c;
  color: white;
  cursor: pointer;
  font-size: 0.8rem;
}

/* Empty Slot */
.empty-slot {
  min-height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.slot-placeholder {
  color: #666;
  font-size: 0.8rem;
}

/* Mini Recommendations */
.recommendations-mini {
  display: flex;
  gap: 5px;
}

.rec-mini {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s;
}

.rec-mini:hover {
  transform: scale(1.1);
}

.rec-mini.m7 { border-color: #9b59b6; }
.rec-mini.m6 { border-color: #e74c3c; }
.rec-mini.m5 { border-color: #f39c12; }
.rec-mini.mlow { border-color: #555; }

/* Tier styling */
.rec-mini.tier-s { box-shadow: 0 0 8px rgba(255, 215, 0, 0.7); }
.rec-mini.tier-a { box-shadow: 0 0 6px rgba(0, 191, 255, 0.6); }
.rec-mini.tier-b { box-shadow: 0 0 4px rgba(50, 205, 50, 0.5); }

.rec-mini {
  position: relative;
}

.tier-badge {
  position: absolute;
  bottom: 0;
  right: 0;
  font-size: 9px;
  font-weight: bold;
  padding: 1px 3px;
  border-radius: 3px 0 0 0;
  background: rgba(0,0,0,0.8);
}

.tier-badge.tier-S { color: #ffd700; }
.tier-badge.tier-A { color: #00bfff; }
.tier-badge.tier-B { color: #32cd32; }
.tier-badge.tier-C { color: #888; }
.tier-badge.tier-D { color: #666; }

.rec-mini img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* Champion Pool */
.champion-pool-section {
  background: rgba(0,0,0,0.3);
  border-radius: 10px;
  padding: 10px;
  max-height: 600px;
  overflow-y: auto;
}

.pool-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.pool-header h3 {
  margin: 0;
  font-size: 1rem;
  color: #42b883;
}

.search-input {
  padding: 5px 10px;
  border: 1px solid #333;
  border-radius: 5px;
  background: rgba(0,0,0,0.3);
  color: white;
  font-size: 0.85rem;
  width: 150px;
}

.champions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(50px, 1fr));
  gap: 5px;
}

.pool-champion {
  width: 50px;
  height: 50px;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  position: relative;
  border: 2px solid transparent;
  transition: all 0.2s;
}

.pool-champion:hover:not(.disabled) {
  transform: scale(1.1);
  z-index: 10;
}

.pool-champion.disabled {
  opacity: 0.3;
  cursor: not-allowed;
  filter: grayscale(100%);
}

.pool-champion.has-mastery {
  border-color: #42b883;
  box-shadow: 0 0 8px rgba(66, 184, 131, 0.4);
}

.pool-champion img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.mastery-badge {
  position: absolute;
  bottom: 2px;
  right: 2px;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 0.55rem;
  font-weight: bold;
}

.mastery-badge.m7 { background: #9b59b6; }
.mastery-badge.m6 { background: #e74c3c; }
.mastery-badge.m5 { background: #f39c12; }
.mastery-badge.mlow { background: #555; }

/* Actions */
.actions {
  display: flex;
  justify-content: center;
  gap: 15px;
  margin-top: 15px;
}

.action-btn {
  padding: 10px 25px;
  border: none;
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn.reset {
  background: linear-gradient(45deg, #e74c3c, #c0392b);
  color: white;
}

.action-btn.next {
  background: linear-gradient(45deg, #42b883, #2c7a56);
  color: white;
}

.action-btn:hover:not(:disabled) {
  transform: translateY(-2px);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Responsive */
@media (max-width: 1200px) {
  .teams-wrapper {
    grid-template-columns: 1fr;
  }
  
  .bans-section {
    flex-direction: column;
    align-items: center;
  }
}
</style>