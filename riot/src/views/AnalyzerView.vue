<template>
  <div class="analyzer-container">
    <div class="teams-wrapper">
      <!-- Blue Team Section -->
      <TeamSlots
        team="blue"
        :champions="blueTeam"
        :win-rate="blueWinRate"
        :selected-slot="selectedSlot"
        @select-slot="selectSlot"
        @remove-champion="removeChampion"
      />

      <!-- Champion Pool (Center) -->
      <ChampionPool
        :champions="champions"
        :blue-team="blueTeam"
        :red-team="redTeam"
        @select-champion="selectChampionForSlot"
      />

      <!-- Red Team Section -->
      <TeamSlots
        team="red"
        :champions="redTeam"
        :win-rate="redWinRate"
        :selected-slot="selectedSlot"
        @select-slot="selectSlot"
        @remove-champion="removeChampion"
      />
    </div>

    <!-- Reset Button -->
    <div class="actions">
      <button class="reset-btn" @click="resetSelection">Reset Selection</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import TeamSlots from '../components/TeamSlots.vue'
import ChampionPool from '../components/ChampionPool.vue'
import { calculateWinRate } from '../components/useTeamWinRate'
import { loadChampionsSync } from '../utils/championLoader'

interface Champion {
  id: string
  name: string
  role: string
  image: string
  tier: number
  winRate: number
}

const champions = ref<Champion[]>([])

// Load champions on component mount
onMounted(() => {
  champions.value = loadChampionsSync()
})

const blueTeam = ref<(Champion | null)[]>([null, null, null, null, null])
const redTeam = ref<(Champion | null)[]>([null, null, null, null, null])
const selectedSlot = ref<{ team: 'blue' | 'red' | null; index: number | null }>({ team: null, index: null })

const blueWinRate = computed(() => calculateWinRate(blueTeam.value, redTeam.value))
const redWinRate = computed(() => calculateWinRate(redTeam.value, blueTeam.value))

const selectSlot = (team: 'blue' | 'red', index: number) => {
  selectedSlot.value = { team, index }
}

const selectChampionForSlot = (champion: Champion) => {
  console.log(
    `[Champion Selected] ${champion.name} — Win Rate: ${champion.winRate}%`
  )
  const isSelected = [...blueTeam.value, ...redTeam.value].some(c => c?.id === champion.id)
  if (isSelected) return
  
  let team = selectedSlot.value.team
  let index = selectedSlot.value.index

  if (!team || index === null) {
    const blueEmptyIndex = blueTeam.value.findIndex(c => c === null)
    if (blueEmptyIndex !== -1) {
      team = 'blue'
      index = blueEmptyIndex
    } else {
      const redEmptyIndex = redTeam.value.findIndex(c => c === null)
      if (redEmptyIndex !== -1) {
        team = 'red'
        index = redEmptyIndex
      } else {
        return
      }
    }
  }

  if (team === 'blue') {
    blueTeam.value[index!] = champion
  } else {
    redTeam.value[index!] = champion
  }
  selectedSlot.value = { team: null, index: null }
}

const removeChampion = (team: 'blue' | 'red', index: number) => {
  if (team === 'blue') {
    blueTeam.value[index] = null
  } else {
    redTeam.value[index] = null
  }
}

const resetSelection = () => {
  blueTeam.value = [null, null, null, null, null]
  redTeam.value = [null, null, null, null, null]
  selectedSlot.value = { team: null, index: null }
}
</script>

<style scoped>
.analyzer-container {
  width: 100%;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  color: #fff;
  padding: 15px;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  display: flex;
  flex-direction: column;
}

h1 {
  text-align: center;
  margin: 0 0 15px 0;
  font-size: 1.6em;
  color: #42b883;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
}

.teams-wrapper {
  display: grid;
  grid-template-columns: 280px 1fr 280px;
  gap: 15px;
  max-width: 1600px;
  margin: 0 auto;
  width: 100%;
}

.actions {
  display: flex;
  justify-content: center;
  margin-top: 10px;
}

.reset-btn {
  padding: 7px 20px;
  font-size: 0.9em;
  font-weight: 600;
  border: none;
  border-radius: 5px;
  background: linear-gradient(45deg, #ff6b9d, #0a9eff);
  color: #fff;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.3);
}

.reset-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
}

@media (max-width: 1200px) {
  .teams-wrapper {
    grid-template-columns: 1fr;
    gap: 15px;
  }
}
</style>