<template>
  <div class="joueur-page">
    <h1>🔍 Recherche de Joueur</h1>
    
    <div class="search-box">
      <input 
        v-model="searchQuery" 
        type="text" 
        placeholder="Entrez un pseudo Riot (ex: KKC Sulfy#SuS)"
        @keyup.enter="searchPlayer"
      />
      <button @click="searchPlayer">Rechercher</button>
    </div>

    <div v-if="playerGames.length > 0" class="player-results">
      <h2>Parties de {{ searchedPlayer }}</h2>
      <p class="games-count">{{ playerGames.length }} parties trouvées</p>
      
      <div class="games-list">
        <div v-for="game in playerGames" :key="game.match_id" class="game-card">
          <div class="game-header">
            <span class="match-id">{{ game.match_id }}</span>
            <span class="duration">{{ formatDuration(game.game_duration) }}</span>
            <span :class="['result', game.playerWin ? 'win' : 'loss']">
              {{ game.playerWin ? 'Victoire' : 'Défaite' }}
            </span>
          </div>

          <div class="teams">
            <div class="team" :class="{ winner: game.team_100_win }">
              <h4>🔵 Équipe Bleue</h4>
              <div class="players">
                <div v-for="player in game.team_100_champions" :key="player.championId" class="player-row">
                  <img 
                    :src="getChampionImage(player.championName)" 
                    :alt="player.championName"
                    class="champ-img"
                    @error="onImageError"
                  />
                  <span class="player-name" :class="{ 'searched-player': isSearchedPlayer(player) }">
                    {{ getPlayerName(player) }}
                  </span>
                  <span class="position">{{ player.teamPosition }}</span>
                </div>
              </div>
            </div>

            <div class="team" :class="{ winner: !game.team_100_win }">
              <h4>🔴 Équipe Rouge</h4>
              <div class="players">
                <div v-for="player in game.team_200_champions" :key="player.championId" class="player-row">
                  <img 
                    :src="getChampionImage(player.championName)" 
                    :alt="player.championName"
                    class="champ-img"
                    @error="onImageError"
                  />
                  <span class="player-name" :class="{ 'searched-player': isSearchedPlayer(player) }">
                    {{ getPlayerName(player) }}
                  </span>
                  <span class="position">{{ player.teamPosition }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="searchedPlayer" class="no-results">
      <p>Aucune partie trouvée pour "{{ searchedPlayer }}"</p>
    </div>

    <div v-else class="help-text">
      <p>Recherchez un joueur par son pseudo Riot (ex: KKC Sulfy#SuS ou juste KKC Sulfy)</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import draftsData from '../../drafts_data.json'

interface Champion {
  championId: number
  championName: string
  teamPosition: string
  win: boolean
  summonerName?: string
  riotIdGameName?: string
  riotIdTagline?: string
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

interface GameWithPlayerInfo extends Draft {
  playerWin: boolean
}

const searchQuery = ref('')
const searchedPlayer = ref('')
const playerGames = ref<GameWithPlayerInfo[]>([])

function searchPlayer() {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return
  
  searchedPlayer.value = searchQuery.value.trim()
  
  // Chercher toutes les parties où ce joueur apparaît
  const games: GameWithPlayerInfo[] = []
  
  draftsData.forEach((draft: Draft) => {
    const allPlayers = [...draft.team_100_champions, ...draft.team_200_champions]
    
    const foundPlayer = allPlayers.find((p: Champion) => {
      const summonerName = (p.summonerName || '').toLowerCase()
      const riotIdGameName = (p.riotIdGameName || '').toLowerCase()
      const fullRiotId = p.riotIdGameName && p.riotIdTagline 
        ? `${p.riotIdGameName}#${p.riotIdTagline}`.toLowerCase() 
        : ''
      
      return summonerName.includes(query) || 
             riotIdGameName.includes(query) ||
             fullRiotId.includes(query)
    })
    
    if (foundPlayer) {
      games.push({
        ...draft,
        playerWin: foundPlayer.win
      })
    }
  })
  
  playerGames.value = games
}

function getPlayerName(player: Champion): string {
  if (player.riotIdGameName) {
    return player.riotIdTagline 
      ? `${player.riotIdGameName}#${player.riotIdTagline}`
      : player.riotIdGameName
  }
  return player.summonerName || player.championName
}

function isSearchedPlayer(player: Champion): boolean {
  const query = searchedPlayer.value.toLowerCase()
  const summonerName = (player.summonerName || '').toLowerCase()
  const riotIdGameName = (player.riotIdGameName || '').toLowerCase()
  const fullRiotId = player.riotIdGameName && player.riotIdTagline 
    ? `${player.riotIdGameName}#${player.riotIdTagline}`.toLowerCase() 
    : ''
  
  return summonerName.includes(query) || 
         riotIdGameName.includes(query) ||
         fullRiotId.includes(query)
}

function getChampionImage(name: string): string {
  const fileName = name.toLowerCase().replace(/\s+/g, '_').replace(/'/g, '').replace(/\./g, '')
  return `/champ_img/${fileName}.png`
}

function onImageError(event: Event) {
  const img = event.target as HTMLImageElement
  img.src = '/champ_img/ahri.png'
}

function formatDuration(seconds: number): string {
  const min = Math.floor(seconds / 60)
  const sec = seconds % 60
  return `${min}:${sec.toString().padStart(2, '0')}`
}
</script>

<style scoped>
.joueur-page h1 {
  margin-bottom: 2rem;
  color: #42b883;
}

.search-box {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  max-width: 600px;
}

.search-box input {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 2px solid #2d3748;
  border-radius: 8px;
  background: #1a1a2e;
  color: white;
  font-size: 1rem;
}

.search-box input:focus {
  outline: none;
  border-color: #42b883;
}

.search-box button {
  padding: 0.75rem 1.5rem;
  background: #42b883;
  color: #1a1a2e;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.search-box button:hover {
  background: #3aa876;
}

.player-results h2 {
  color: #42b883;
  margin-bottom: 0.5rem;
}

.games-count {
  color: #888;
  margin-bottom: 1.5rem;
}

.games-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.game-card {
  background: #1a1a2e;
  border-radius: 12px;
  padding: 1.5rem;
}

.game-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.match-id {
  color: #888;
  font-size: 0.85rem;
}

.duration {
  color: white;
}

.result {
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-weight: 600;
  font-size: 0.85rem;
}

.result.win {
  background: rgba(66, 184, 131, 0.2);
  color: #42b883;
}

.result.loss {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
}

.teams {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
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
  font-size: 0.95rem;
}

.players {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.player-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.champ-img {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid #42b883;
}

.player-name {
  flex: 1;
  font-size: 0.9rem;
  color: #a0aec0;
}

.player-name.searched-player {
  color: #42b883;
  font-weight: 600;
}

.position {
  font-size: 0.75rem;
  color: #888;
  background: #1a1a2e;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.no-results, .help-text {
  text-align: center;
  color: #888;
  padding: 2rem;
}

@media (max-width: 768px) {
  .teams {
    grid-template-columns: 1fr;
  }
}
</style>
