<template>
  <div class="analyzer-container">

    <div class="teams-wrapper">
      <!-- Blue Team Section -->
      <div class="team blue-team">
        <div class="team-header">
          <h2>Blue Team</h2>
          <div class="win-rate">
            <span class="percentage">{{ blueWinRate }}%</span>
          </div>
        </div>

        <div class="champions-slots">
          <div
            v-for="(champion, index) in blueTeam"
            :key="`blue-${index}`"
            class="champion-slot"
            :class="{ filled: champion, selected: selectedSlot.team === 'blue' && selectedSlot.index === index }"
            @click="selectSlot('blue', index)"
          >
            <div v-if="champion" class="champion-card">
              <img :src="champion.image" :alt="champion.name" />
              <div class="champion-info">
                <p class="champion-name">{{ champion.name }}</p>
                <p class="champion-role">{{ champion.role }}</p>
              </div>
              <button class="remove-btn" @click.stop="removeChampion('blue', index)">×</button>
            </div>
            <div v-else class="empty-slot">
              <span class="slot-number">{{ index + 1 }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Champion Pool (Center) -->
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

        <div class="champions-grid">
          <div
            v-for="champion in filteredChampions"
            :key="champion.id"
            class="pool-champion"
            :class="{ disabled: isChampionSelected(champion.id) }"
            @click="selectChampionForSlot(champion)"
            :title="`${champion.name} - ${champion.role}`"
          >
            <img :src="champion.image" :alt="champion.name" />
            <div class="pool-info">
              <p class="name">{{ champion.name }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Red Team Section -->
      <div class="team red-team">
        <div class="team-header">
          <h2>Red Team</h2>
          <div class="win-rate">
            <span class="percentage">{{ redWinRate }}%</span>
          </div>
        </div>

        <div class="champions-slots">
          <div
            v-for="(champion, index) in redTeam"
            :key="`red-${index}`"
            class="champion-slot"
            :class="{ filled: champion, selected: selectedSlot.team === 'red' && selectedSlot.index === index }"
            @click="selectSlot('red', index)"
          >
            <div v-if="champion" class="champion-card">
              <img :src="champion.image" :alt="champion.name" />
              <div class="champion-info">
                <p class="champion-name">{{ champion.name }}</p>
                <p class="champion-role">{{ champion.role }}</p>
              </div>
              <button class="remove-btn" @click.stop="removeChampion('red', index)">×</button>
            </div>
            <div v-else class="empty-slot">
              <span class="slot-number">{{ index + 1 }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Reset Button -->
    <div class="actions">
      <button class="reset-btn" @click="resetSelection">Reset Selection</button>
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

const champions = ref<Champion[]>([
  { id: 'ahri', name: 'Ahri', role: 'Mid', image: 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Ahri.png', tier: 1, winRate: 52 },
  { id: 'akali', name: 'Akali', role: 'Mid', image: 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Akali.png', tier: 2, winRate: 50 },
  { id: 'annie', name: 'Annie', role: 'Mid', image: 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Annie.png', tier: 1, winRate: 51 },
  { id: 'ashe', name: 'Ashe', role: 'ADC', image: 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Ashe.png', tier: 1, winRate: 53 },
  { id: 'blitzcrank', name: 'Blitzcrank', role: 'Support', image: 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Blitzcrank.png', tier: 2, winRate: 49 },
  { id: 'braum', name: 'Braum', role: 'Support', image: 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Braum.png', tier: 1, winRate: 54 },
  { id: 'caitlyn', name: 'Caitlyn', role: 'ADC', image: 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Caitlyn.png', tier: 1, winRate: 51 },
  { id: 'chogath', name: "Cho'Gath", role: 'Top', image: 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Chogath.png', tier: 2, winRate: 48 },
  { id: 'darius', name: 'Darius', role: 'Top', image: 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Darius.png', tier: 1, winRate: 52 },
  { id: 'diana', name: 'Diana', role: 'Mid', image: 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Diana.png', tier: 1, winRate: 50 },
  { id: 'draven', name: 'Draven', role: 'ADC', image: 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Draven.png', tier: 2, winRate: 49 },
  { id: 'elise', name: 'Elise', role: 'Jungle', image: 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Elise.png', tier: 1, winRate: 51 },
  { id: 'evelynn', name: 'Evelynn', role: 'Jungle', image: 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Evelynn.png', tier: 1, winRate: 53 },
  { id: 'ezreal', name: 'Ezreal', role: 'ADC', image: 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Ezreal.png', tier: 1, winRate: 50 },
  { id: 'fiddlesticks', name: 'Fiddlesticks', role: 'Jungle', image: 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Fiddlesticks.png', tier: 2, winRate: 48 },
  { id: 'fiora', name: 'Fiora', role: 'Top', image: 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Fiora.png', tier: 1, winRate: 52 },
  { id: 'gragas', name: 'Gragas', role: 'Mid', image: 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Gragas.png', tier: 2, winRate: 49 },
  { id: 'garen', name: 'Garen', role: 'Top', image: 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Garen.png', tier: 1, winRate: 51 },
  { id: 'gnar', name: 'Gnar', role: 'Top', image: 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Gnar.png', tier: 2, winRate: 47 },
  { id: 'hecarim', name: 'Hecarim', role: 'Jungle', image: 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Hecarim.png', tier: 1, winRate: 54 }
])

const blueTeam = ref<(Champion | null)[]>([null, null, null, null, null])
const redTeam = ref<(Champion | null)[]>([null, null, null, null, null])
const searchQuery = ref('')
const selectedSlot = ref<{ team: 'blue' | 'red' | null; index: number | null }>({ team: null, index: null })

const filteredChampions = computed(() => {
  const selectedIds = new Set([...blueTeam.value, ...redTeam.value].filter(c => c).map(c => c!.id))
  return champions.value.filter(champ => {
    const matchesSearch = champ.name.toLowerCase().includes(searchQuery.value.toLowerCase())
    const notSelected = !selectedIds.has(champ.id)
    return matchesSearch && notSelected
  })
})

const blueWinRate = computed(() => {
  if (blueTeam.value.filter(c => c).length === 0) return 50
  let totalWinRate = 0
  let count = 0
  blueTeam.value.forEach(champ => {
    if (champ) {
      totalWinRate += champ.winRate
      count++
    }
  })
  const synergyBonus = count > 1 ? (count - 1) * 1.5 : 0
  const baseWinRate = count > 0 ? totalWinRate / count : 50
  let counterBonus = 0
  blueTeam.value.forEach(blueChamp => {
    if (blueChamp) {
      redTeam.value.forEach(redChamp => {
        if (redChamp && blueChamp.tier < redChamp.tier) counterBonus += 1
      })
    }
  })
  return Math.round(Math.min(Math.max(baseWinRate + synergyBonus + counterBonus, 30), 95))
})

const redWinRate = computed(() => {
  if (redTeam.value.filter(c => c).length === 0) return 50
  let totalWinRate = 0
  let count = 0
  redTeam.value.forEach(champ => {
    if (champ) {
      totalWinRate += champ.winRate
      count++
    }
  })
  const synergyBonus = count > 1 ? (count - 1) * 1.5 : 0
  const baseWinRate = count > 0 ? totalWinRate / count : 50
  let counterBonus = 0
  redTeam.value.forEach(redChamp => {
    if (redChamp) {
      blueTeam.value.forEach(blueChamp => {
        if (blueChamp && redChamp.tier < blueChamp.tier) counterBonus += 1
      })
    }
  })
  return Math.round(Math.min(Math.max(baseWinRate + synergyBonus + counterBonus, 30), 95))
})

const isChampionSelected = (championId: string): boolean => {
  return [...blueTeam.value, ...redTeam.value].some(c => c?.id === championId)
}

const selectSlot = (team: 'blue' | 'red', index: number) => {
  selectedSlot.value = { team, index }
}

const selectChampionForSlot = (champion: Champion) => {
  if (isChampionSelected(champion.id)) return
  
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
  searchQuery.value = ''
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
  overflow: hidden;
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
  overflow: hidden;
  max-width: 1600px;
  margin: 0 auto;
  width: 100%;
  max-height: calc(100vh - 120px);
}

.team {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  padding: 12px;
  border: 2px solid;
  backdrop-filter: blur(10px);
  display: flex;
  flex-direction: column;
  max-height: 100%;
  overflow: hidden;
}

.blue-team {
  border-color: #0a9eff;
  box-shadow: 0 0 20px rgba(10, 158, 255, 0.3);
}

.red-team {
  border-color: #ff6b9d;
  box-shadow: 0 0 20px rgba(255, 107, 157, 0.3);
}

.team-header {
  margin-bottom: 12px;
  text-align: center;
}

.team-header h2 {
  font-size: 1.2em;
  margin: 0 0 6px 0;
}

.blue-team h2 {
  color: #0a9eff;
}

.red-team h2 {
  color: #ff6b9d;
}

.win-rate {
  font-size: 0.85em;
  font-weight: 600;
}

.percentage {
  font-size: 1.2em;
  font-weight: bold;
  padding: 3px 10px;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.1);
}

.blue-team .percentage {
  color: #0a9eff;
  border: 1px solid #0a9eff;
}

.red-team .percentage {
  color: #ff6b9d;
  border: 1px solid #ff6b9d;
}

.champions-slots {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.champion-slot {
  height: 70px;
  border: 2px dashed rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.02);
  position: relative;
}

.champion-slot:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.5);
}

.champion-slot.filled {
  border-style: solid;
  border-color: rgba(255, 255, 255, 0.3);
}

.champion-slot.selected {
  border-style: solid;
  border-width: 2px;
}

.blue-team .champion-slot.selected {
  border-color: #0a9eff;
  box-shadow: 0 0 15px rgba(10, 158, 255, 0.5);
  background: rgba(10, 158, 255, 0.15);
}

.red-team .champion-slot.selected {
  border-color: #ff6b9d;
  box-shadow: 0 0 15px rgba(255, 107, 157, 0.5);
  background: rgba(255, 107, 157, 0.15);
}

.empty-slot {
  font-size: 1em;
  color: rgba(255, 255, 255, 0.4);
  font-weight: 600;
}

.champion-card {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  height: 100%;
  padding: 0 10px;
  position: relative;
}

.champion-card img {
  width: 50px;
  height: 50px;
  border-radius: 6px;
  object-fit: cover;
  border: 2px solid rgba(255, 255, 255, 0.3);
}

.champion-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 2px;
}

.champion-name {
  margin: 0;
  font-weight: 600;
  font-size: 0.95em;
  color: #fff;
}

.champion-role {
  margin: 0;
  font-size: 0.8em;
  color: rgba(255, 255, 255, 0.7);
}

.remove-btn {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: none;
  background: #ff6b9d;
  color: #fff;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  line-height: 1;
  padding: 0;
  margin-left: auto;
}

.remove-btn:hover {
  background: #ff4081;
  transform: scale(1.1);
}

.champion-pool {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  padding: 12px;
  border: 2px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  max-height: 100%;
}

.pool-header {
  margin-bottom: 10px;
}

.pool-header h3 {
  margin: 0 0 8px 0;
  font-size: 1.1em;
  background: linear-gradient(45deg, #0a9eff, #ff6b9d);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.search-input {
  width: 100%;
  padding: 7px 10px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  font-size: 0.85em;
  transition: all 0.3s ease;
}

.search-input::placeholder {
  color: rgba(255, 255, 255, 0.5);
}

.search-input:focus {
  outline: none;
  border-color: #0a9eff;
  background: rgba(255, 255, 255, 0.12);
  box-shadow: 0 0 10px rgba(10, 158, 255, 0.3);
}

.champions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(60px, 1fr));
  gap: 8px;
  overflow-y: auto;
  padding-right: 5px;
}

.champions-grid::-webkit-scrollbar {
  width: 5px;
}

.champions-grid::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
}

.champions-grid::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 10px;
}

.pool-champion {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.2s ease;
  padding: 5px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.pool-champion:hover:not(.disabled) {
  background: rgba(255, 255, 255, 0.15);
  border-color: #0a9eff;
  transform: translateY(-2px);
}

.pool-champion.disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.pool-champion img {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: 4px;
  margin-bottom: 4px;
}

.pool-info {
  width: 100%;
  text-align: center;
}

.pool-info .name {
  margin: 0;
  font-weight: 600;
  font-size: 0.7em;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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