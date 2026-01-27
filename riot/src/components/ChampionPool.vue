<template>
  <div class="champion-pool">
    <div class="pool-header">
      <h3>Champion Pool</h3>
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search champions..."
        class="search-input"
      />
    </div>

    <div v-if="currentSlotMasteries.length > 0" class="mastery-hint">
      💡 Champions triés par maîtrise du joueur
    </div>

    <div class="champions-grid">
      <div
        v-for="champion in filteredChampions"
        :key="champion.id"
        class="pool-champion"
        :class="{ 
          disabled: isChampionSelected(champion.id),
          'has-mastery': hasMastery(champion.name)
        }"
        @click="selectChampion(champion)"
        :title="`${champion.name} - ${champion.role}${getMasteryTooltip(champion.name)}`"
      >
        <img :src="champion.image" :alt="champion.name" />
        <div class="pool-info">
          <p class="name">{{ champion.name }}</p>
          <span v-if="hasMastery(champion.name)" class="mastery-indicator" :class="getMasteryClass(champion.name)">
            M{{ getMasteryLevel(champion.name) }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

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

interface Props {
  champions: Champion[]
  blueTeam: (Champion | null)[]
  redTeam: (Champion | null)[]
  currentSlotMasteries?: PlayerMastery[]
}

const props = withDefaults(defineProps<Props>(), {
  currentSlotMasteries: () => []
})

const emit = defineEmits<{
  'select-champion': [champion: Champion]
}>()

const searchQuery = ref('')

// Create mastery map for quick lookup
const masteryMap = computed(() => {
  const map = new Map<string, PlayerMastery>()
  for (const m of props.currentSlotMasteries) {
    map.set(m.champion_name.toLowerCase(), m)
  }
  return map
})

const filteredChampions = computed(() => {
  const selectedIds = new Set([...props.blueTeam, ...props.redTeam].filter(c => c).map(c => c!.id))
  
  let filtered = props.champions.filter(champ => {
    const matchesSearch = champ.name.toLowerCase().includes(searchQuery.value.toLowerCase())
    const notSelected = !selectedIds.has(champ.id)
    return matchesSearch && notSelected
  })
  
  // Sort by mastery if masteries are available
  if (props.currentSlotMasteries.length > 0) {
    filtered = filtered.sort((a, b) => {
      const masteryA = masteryMap.value.get(a.name.toLowerCase())
      const masteryB = masteryMap.value.get(b.name.toLowerCase())
      
      if (masteryA && masteryB) {
        return masteryB.champion_points - masteryA.champion_points
      }
      if (masteryA) return -1
      if (masteryB) return 1
      return 0
    })
  }
  
  return filtered
})

const isChampionSelected = (championId: string): boolean => {
  return [...props.blueTeam, ...props.redTeam].some(c => c?.id === championId)
}

const hasMastery = (championName: string): boolean => {
  return masteryMap.value.has(championName.toLowerCase())
}

const getMasteryLevel = (championName: string): number => {
  return masteryMap.value.get(championName.toLowerCase())?.champion_level || 0
}

const getMasteryClass = (championName: string): string => {
  const level = getMasteryLevel(championName)
  if (level >= 7) return 'm7'
  if (level >= 6) return 'm6'
  if (level >= 5) return 'm5'
  return 'mlow'
}

const getMasteryTooltip = (championName: string): string => {
  const mastery = masteryMap.value.get(championName.toLowerCase())
  if (mastery) {
    const points = mastery.champion_points >= 1000 
      ? (mastery.champion_points / 1000).toFixed(0) + 'K' 
      : mastery.champion_points
    return ` - M${mastery.champion_level} (${points} pts)`
  }
  return ''
}

const selectChampion = (champion: Champion) => {
  if (!isChampionSelected(champion.id)) {
    emit('select-champion', champion)
  }
}
</script>

<style scoped>
@import '../assets/ChampionPool.css';

.mastery-hint {
  background: rgba(66, 184, 131, 0.2);
  border: 1px solid #42b883;
  border-radius: 6px;
  padding: 6px 10px;
  margin-bottom: 10px;
  font-size: 0.8rem;
  color: #42b883;
}

.pool-champion.has-mastery {
  border: 2px solid #42b883;
  box-shadow: 0 0 8px rgba(66, 184, 131, 0.4);
}

.mastery-indicator {
  position: absolute;
  bottom: 2px;
  right: 2px;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 0.6rem;
  font-weight: bold;
}

.mastery-indicator.m7 { background: #9b59b6; color: white; }
.mastery-indicator.m6 { background: #e74c3c; color: white; }
.mastery-indicator.m5 { background: #f39c12; color: white; }
.mastery-indicator.mlow { background: #555; color: #ccc; }

.pool-info {
  position: relative;
}
</style>