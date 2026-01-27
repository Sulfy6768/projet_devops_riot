<template>
  <div class="draft-page">
    <h1>📊 Historique des Drafts</h1>
    
    <div class="drafts-list">
      <div v-for="draft in drafts" :key="draft.match_id" class="draft-card">
        <div class="draft-header">
          <span class="match-id">{{ draft.match_id }}</span>
          <span class="duration">{{ formatDuration(draft.game_duration) }}</span>
        </div>

        <div class="teams">
          <div class="team" :class="{ winner: draft.team_100_win }">
            <h4>🔵 Équipe Bleue {{ draft.team_100_win ? '✓' : '' }}</h4>
            <div class="champions">
              <div v-for="champ in draft.team_100_champions" :key="champ.championId" class="champion">
                <span class="champ-name">{{ champ.championName }}</span>
                <span class="position">{{ champ.teamPosition }}</span>
              </div>
            </div>
          </div>

          <div class="team" :class="{ winner: !draft.team_100_win }">
            <h4>🔴 Équipe Rouge {{ !draft.team_100_win ? '✓' : '' }}</h4>
            <div class="champions">
              <div v-for="champ in draft.team_200_champions" :key="champ.championId" class="champion">
                <span class="champ-name">{{ champ.championName }}</span>
                <span class="position">{{ champ.teamPosition }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import draftsData from '../../drafts_data.json'

interface Champion {
  championId: number
  championName: string
  teamPosition: string
  win: boolean
}

interface Draft {
  match_id: string
  game_version: string
  queue_id: number
  game_duration: number
  team_100_win: boolean
  team_100_champions: Champion[]
  team_200_champions: Champion[]
}

const drafts = ref<Draft[]>([])

onMounted(() => {
  drafts.value = draftsData.slice(0, 20)
})

function formatDuration(seconds: number): string {
  const min = Math.floor(seconds / 60)
  const sec = seconds % 60
  return `${min}:${sec.toString().padStart(2, '0')}`
}
</script>

<style scoped>
.draft-page h1 {
  margin-bottom: 2rem;
  color: #42b883;
}

.drafts-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.draft-card {
  background: #1a1a2e;
  border-radius: 12px;
  padding: 1.5rem;
}

.draft-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 1rem;
  color: #888;
  font-size: 0.9rem;
}

.teams {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.team {
  background: #16213e;
  border-radius: 8px;
  padding: 1rem;
  border: 2px solid transparent;
}

.team.winner {
  border-color: #42b883;
}

.team h4 {
  margin-bottom: 0.75rem;
  font-size: 1rem;
}

.champions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.champion {
  display: flex;
  justify-content: space-between;
  padding: 0.25rem 0.5rem;
  background: #1a1a2e;
  border-radius: 4px;
  font-size: 0.9rem;
}

.champ-name {
  color: white;
}

.position {
  color: #42b883;
  font-size: 0.8rem;
}
</style>
