<template>
  <div class="joueur-page">
    <h1>🔍 Recherche de Joueur</h1>
    
    <div class="search-box">
      <input 
        v-model="searchQuery" 
        type="text" 
        placeholder="Entrez un pseudo Riot (ex: KKC Sulfy#SuS)"
        @keyup.enter="searchPlayer"
        :disabled="isLoading"
      />
      <button @click="searchPlayer" :disabled="isLoading">
        {{ isLoading ? 'Chargement...' : 'Rechercher' }}
      </button>
    </div>

    <div v-if="isLoading" class="loading">
      <p>⏳ Récupération des parties depuis l'API Riot...</p>
    </div>

    <div v-else-if="errorMessage" class="error-message">
      <p>❌ {{ errorMessage }}</p>
    </div>

    <div v-else-if="playerGames.length > 0" class="player-results">
      <div class="player-header">
        <h2>{{ searchedPlayer }}</h2>
        <div class="stats-summary">
          <span class="wins">{{ getWins() }}V</span>
          <span class="losses">{{ getLosses() }}D</span>
          <span class="winrate">{{ getWinrate() }}% WR</span>
        </div>
      </div>
      
      <div class="match-history">
        <div 
          v-for="game in playerGames" 
          :key="game.match_id" 
          class="match-container"
          :class="{ 'expanded': expandedGames.includes(game.match_id) }"
        >
          <!-- Carte de la game avec fond coloré -->
          <div 
            class="match-card"
            :class="game.playerWin ? 'win' : 'loss'"
            @click="toggleExpand(game.match_id)"
          >
            <img 
              :src="getChampionImage(game.playerData?.championName || '')" 
              :alt="game.playerData?.championName"
              class="champion-icon"
              @error="onImageError"
            />
            
            <div class="match-main-info">
              <div class="result-line">
                <span class="result-text">{{ game.playerWin ? 'Victoire' : 'Défaite' }}</span>
                <span class="duration">{{ formatDuration(game.game_duration) }}</span>
              </div>
              <div class="stats-row">
                <span class="kda">{{ game.playerData?.kills }}/{{ game.playerData?.deaths }}/{{ game.playerData?.assists }}</span>
                <span class="kda-ratio">{{ getKDAString(game.playerData) }}</span>
                <span class="sep">|</span>
                <span class="cs">{{ game.playerData?.cs }} CS</span>
                <span class="sep">|</span>
                <span class="damage">{{ formatNumber(game.playerData?.totalDamageDealt) }} DMG</span>
              </div>
            </div>
            
            <div class="match-meta">
              <span class="date">{{ formatDate(game.game_creation) }}</span>
              <span class="expand-icon">{{ expandedGames.includes(game.match_id) ? '▲' : '▼' }}</span>
            </div>
          </div>
          
          <!-- Détails dépliés -->
          <div v-if="expandedGames.includes(game.match_id)" class="match-details">
            <div class="team-column blue-side">
              <div class="team-header" :class="{ 'winner': game.team_100_win }">
                Équipe Bleue {{ game.team_100_win ? '✓' : '' }}
              </div>
              <div class="column-headers">
                <span class="h-champ"></span>
                <span class="h-name">Joueur</span>
                <span class="h-kda">KDA</span>
                <span class="h-cs">CS</span>
                <span class="h-dmg">Dégâts</span>
                <span class="h-taken">Reçus</span>
                <span class="h-role">Rôle</span>
              </div>
              <div 
                v-for="player in game.team_100_champions" 
                :key="player.championId" 
                class="player-row"
                :class="{ 'highlighted': isSearchedPlayer(player) }"
              >
                <img :src="getChampionImage(player.championName)" class="champ-icon" @error="onImageError" />
                <span class="p-name">{{ getPlayerName(player) }}</span>
                <span class="p-kda">{{ player.kills }}/{{ player.deaths }}/{{ player.assists }}</span>
                <span class="p-cs">{{ player.cs }}</span>
                <div class="damage-bar-container">
                  <div class="damage-bar dmg-dealt" :style="{ width: getDamagePercent(player.totalDamageDealt, getMaxDamageDealt(game)) + '%' }">
                    <span class="damage-value">{{ formatNumber(player.totalDamageDealt) }}</span>
                  </div>
                </div>
                <div class="damage-bar-container">
                  <div class="damage-bar dmg-taken" :style="{ width: getDamagePercent(player.totalDamageTaken, getMaxDamageTaken(game)) + '%' }">
                    <span class="damage-value">{{ formatNumber(player.totalDamageTaken) }}</span>
                  </div>
                </div>
                <span class="p-role">{{ player.teamPosition }}</span>
              </div>
            </div>
            
            <div class="team-column red-side">
              <div class="team-header" :class="{ 'winner': !game.team_100_win }">
                Équipe Rouge {{ !game.team_100_win ? '✓' : '' }}
              </div>
              <div class="column-headers">
                <span class="h-champ"></span>
                <span class="h-name">Joueur</span>
                <span class="h-kda">KDA</span>
                <span class="h-cs">CS</span>
                <span class="h-dmg">Dégâts</span>
                <span class="h-taken">Reçus</span>
                <span class="h-role">Rôle</span>
              </div>
              <div 
                v-for="player in game.team_200_champions" 
                :key="player.championId" 
                class="player-row"
                :class="{ 'highlighted': isSearchedPlayer(player) }"
              >
                <img :src="getChampionImage(player.championName)" class="champ-icon" @error="onImageError" />
                <span class="p-name">{{ getPlayerName(player) }}</span>
                <span class="p-kda">{{ player.kills }}/{{ player.deaths }}/{{ player.assists }}</span>
                <span class="p-cs">{{ player.cs }}</span>
                <div class="damage-bar-container">
                  <div class="damage-bar dmg-dealt" :style="{ width: getDamagePercent(player.totalDamageDealt, getMaxDamageDealt(game)) + '%' }">
                    <span class="damage-value">{{ formatNumber(player.totalDamageDealt) }}</span>
                  </div>
                </div>
                <div class="damage-bar-container">
                  <div class="damage-bar dmg-taken" :style="{ width: getDamagePercent(player.totalDamageTaken, getMaxDamageTaken(game)) + '%' }">
                    <span class="damage-value">{{ formatNumber(player.totalDamageTaken) }}</span>
                  </div>
                </div>
                <span class="p-role">{{ player.teamPosition }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="searchedPlayer && !isLoading" class="no-results">
      <p>Aucune partie ranked trouvée pour "{{ searchedPlayer }}"</p>
    </div>

    <div v-else class="help-text">
      <p>Recherchez un joueur par son pseudo Riot (ex: KKC Sulfy#SuS)</p>
      <p class="hint">Les parties ranked Solo/Duo seront récupérées depuis l'API Riot</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { getChampionImagePath } from '../utils/championLoader'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface Champion {
  championId: number
  championName: string
  teamPosition: string
  kills?: number
  deaths?: number
  assists?: number
  cs?: number
  goldEarned?: number
  totalDamageDealt?: number
  totalDamageTaken?: number
  win: boolean
  summonerName?: string
  riotIdGameName?: string
  riotIdTagline?: string
}

interface Match {
  match_id: string
  game_version: string
  queue_id: number
  game_duration: number
  game_creation: number
  game_mode: string
  team_100_win: boolean
  team_100_champions: Champion[]
  team_200_champions: Champion[]
  playerWin: boolean
  playerData?: Champion
}

const searchQuery = ref('')
const searchedPlayer = ref('')
const playerGames = ref<Match[]>([])
const isLoading = ref(false)
const errorMessage = ref('')
const expandedGames = ref<string[]>([])

function toggleExpand(matchId: string) {
  const index = expandedGames.value.indexOf(matchId)
  if (index === -1) {
    expandedGames.value.push(matchId)
  } else {
    expandedGames.value.splice(index, 1)
  }
}

function getWins(): number {
  return playerGames.value.filter(g => g.playerWin).length
}

function getLosses(): number {
  return playerGames.value.filter(g => !g.playerWin).length
}

function getWinrate(): number {
  const total = playerGames.value.length
  if (total === 0) return 0
  return Math.round((getWins() / total) * 100)
}

function getKDAString(player: Champion | undefined): string {
  if (!player) return '0.00'
  const kills = player.kills || 0
  const deaths = player.deaths || 0
  const assists = player.assists || 0
  if (deaths === 0) return 'Perfect'
  return ((kills + assists) / deaths).toFixed(2) + ' KDA'
}

function formatNumber(num: number | undefined): string {
  if (!num) return '0'
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num.toString()
}

async function searchPlayer() {
  const query = searchQuery.value.trim()
  if (!query) return
  
  // Parser le Riot ID (GameName#TagLine)
  let gameName = query
  let tagLine = 'EUW'  // Tag par défaut
  
  if (query.includes('#')) {
    const parts = query.split('#')
    gameName = parts[0]?.trim() || query
    tagLine = parts[1]?.trim() || 'EUW'
  }
  
  searchedPlayer.value = `${gameName}#${tagLine}`
  isLoading.value = true
  errorMessage.value = ''
  playerGames.value = []
  
  try {
    const response = await fetch(
      `${API_URL}/matches/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}?count=20`
    )
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Erreur lors de la recherche')
    }
    
    const data = await response.json()
    playerGames.value = data.matches
  } catch (error) {
    console.error('Erreur:', error)
    errorMessage.value = error instanceof Error ? error.message : 'Erreur inconnue'
  } finally {
    isLoading.value = false
  }
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
  return getChampionImagePath(name)
}

function onImageError(event: Event) {
  const img = event.target as HTMLImageElement
  img.src = '/champ_img/ahri.png'
}

function getMaxDamageDealt(game: Match): number {
  const allPlayers = [...(game.team_100_champions || []), ...(game.team_200_champions || [])]
  return Math.max(...allPlayers.map(p => p.totalDamageDealt || 0), 1)
}

function getMaxDamageTaken(game: Match): number {
  const allPlayers = [...(game.team_100_champions || []), ...(game.team_200_champions || [])]
  return Math.max(...allPlayers.map(p => p.totalDamageTaken || 0), 1)
}

function getDamagePercent(damage: number | undefined, maxDamage: number): number {
  if (!damage || !maxDamage) return 0
  return Math.round((damage / maxDamage) * 100)
}

function formatDuration(seconds: number): string {
  const min = Math.floor(seconds / 60)
  const sec = seconds % 60
  return `${min}:${sec.toString().padStart(2, '0')}`
}

function formatDate(timestamp: number): string {
  const date = new Date(timestamp)
  return date.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}
</script>

<style scoped>
.joueur-page h1 {
  margin-bottom: 2rem;
  color: #42b883;
}

/* Search Box */
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

.search-box button:disabled {
  background: #555;
  cursor: not-allowed;
}

.search-box input:disabled {
  background: #2d3748;
  cursor: not-allowed;
}

/* Player Header */
.player-header {
  display: flex;
  align-items: center;
  gap: 2rem;
  margin-bottom: 1.5rem;
}

.player-header h2 {
  color: #42b883;
  margin: 0;
}

.stats-summary {
  display: flex;
  gap: 1rem;
  font-size: 1.1rem;
}

.stats-summary .wins {
  color: #5383e8;
  font-weight: 600;
}

.stats-summary .losses {
  color: #e84057;
  font-weight: 600;
}

.stats-summary .winrate {
  color: #888;
}

/* Match History */
.match-history {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: 100%;
}

/* Match Container - Layout vertical */
.match-container {
  display: flex;
  flex-direction: column;
  border-radius: 8px;
  overflow: hidden;
  width: 100%;
}

/* Match Card - Fond coloré complet, pleine largeur */
.match-card {
  display: flex;
  align-items: center;
  padding: 1rem 1.5rem;
  gap: 1.5rem;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s;
  width: 100%;
  box-sizing: border-box;
}

.match-card.win {
  background: linear-gradient(135deg, rgba(83, 131, 232, 0.4) 0%, rgba(83, 131, 232, 0.2) 100%);
  border: 2px solid #5383e8;
}

.match-card.loss {
  background: linear-gradient(135deg, rgba(232, 64, 87, 0.4) 0%, rgba(232, 64, 87, 0.2) 100%);
  border: 2px solid #e84057;
}

.match-card:hover {
  filter: brightness(1.1);
}

.match-container.expanded .match-card {
  border-radius: 8px 8px 0 0;
}

/* Champion Icon */
.champion-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  object-fit: cover;
  border: 3px solid rgba(255, 255, 255, 0.3);
  flex-shrink: 0;
}

.match-card.win .champion-icon {
  border-color: #5383e8;
}

.match-card.loss .champion-icon {
  border-color: #e84057;
}

/* Match Main Info */
.match-main-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.result-line {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.result-text {
  font-weight: 700;
  font-size: 1.2rem;
}

.match-card.win .result-text {
  color: #5383e8;
}

.match-card.loss .result-text {
  color: #e84057;
}

.duration {
  color: #888;
  font-size: 1rem;
}

.stats-row {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex-wrap: wrap;
}

.kda {
  font-weight: 700;
  font-size: 1.3rem;
  color: #fff;
}

.kda-ratio {
  font-size: 0.9rem;
  color: #aaa;
  background: rgba(0,0,0,0.2);
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.sep {
  color: #444;
  font-size: 0.9rem;
}

.cs, .damage {
  font-size: 0.95rem;
  color: #888;
}

.damage {
  color: #e74c3c;
}

/* Match Meta */
.match-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.5rem;
  min-width: 100px;
}

.date {
  font-size: 0.9rem;
  color: #888;
}

.expand-icon {
  font-size: 1.2rem;
  color: #aaa;
  background: rgba(0,0,0,0.2);
  padding: 0.3rem 0.6rem;
  border-radius: 4px;
}

/* Match Details - En dessous */
.match-details {
  display: flex;
  gap: 1rem;
  background: #1a1a2e;
  border-radius: 0 0 8px 8px;
  padding: 1rem;
  border: 2px solid #2d3748;
  border-top: none;
}

/* Team Columns */
.team-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-radius: 6px;
  overflow: hidden;
}

.team-column.blue-side {
  background: rgba(83, 131, 232, 0.1);
  border: 1px solid rgba(83, 131, 232, 0.3);
}

.team-column.red-side {
  background: rgba(232, 64, 87, 0.1);
  border: 1px solid rgba(232, 64, 87, 0.3);
}

.team-header {
  padding: 0.6rem 1rem;
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
}

.team-column.blue-side .team-header {
  color: #5383e8;
  background: rgba(83, 131, 232, 0.25);
}

.team-column.red-side .team-header {
  color: #e84057;
  background: rgba(232, 64, 87, 0.25);
}

.team-header.winner {
  color: #42b883 !important;
}

/* Column Headers */
.column-headers {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.4rem 1rem;
  font-size: 0.7rem;
  color: #666;
  text-transform: uppercase;
  border-bottom: 1px solid rgba(45, 55, 72, 0.8);
  background: rgba(0, 0, 0, 0.2);
}

.h-champ { width: 32px; }
.h-name { flex: 1; min-width: 120px; }
.h-kda { min-width: 60px; text-align: center; }
.h-cs { min-width: 40px; text-align: center; }
.h-dmg { min-width: 100px; text-align: center; }
.h-taken { min-width: 100px; text-align: center; }
.h-role { min-width: 60px; text-align: right; }

/* Player Rows */
.player-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
  border-bottom: 1px solid rgba(45, 55, 72, 0.5);
}

.player-row:last-child {
  border-bottom: none;
}

.player-row.highlighted {
  background: rgba(66, 184, 131, 0.25);
}

.champ-icon {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  object-fit: cover;
  flex-shrink: 0;
}

.p-name {
  flex: 1;
  color: #a0aec0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 120px;
  font-size: 0.85rem;
}

.player-row.highlighted .p-name {
  color: #42b883;
  font-weight: 600;
}

.p-kda {
  color: #fff;
  font-weight: 600;
  min-width: 60px;
  text-align: center;
  font-size: 0.9rem;
}

.p-cs {
  color: #888;
  min-width: 40px;
  text-align: center;
  font-size: 0.8rem;
}

/* Damage Bars */
.damage-bar-container {
  width: 100px;
  height: 20px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 3px;
  overflow: hidden;
  position: relative;
}

.damage-bar {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 4px;
  transition: width 0.3s ease;
  min-width: fit-content;
}

.damage-bar.dmg-dealt {
  background: linear-gradient(90deg, rgba(231, 76, 60, 0.4) 0%, rgba(231, 76, 60, 0.8) 100%);
}

.damage-bar.dmg-taken {
  background: linear-gradient(90deg, rgba(52, 152, 219, 0.4) 0%, rgba(52, 152, 219, 0.8) 100%);
}

.damage-value {
  font-size: 0.7rem;
  color: #fff;
  font-weight: 600;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
  white-space: nowrap;
}

.p-role {
  color: #666;
  font-size: 0.75rem;
  min-width: 60px;
  text-align: right;
  text-transform: uppercase;
}

/* States */
.no-results, .help-text {
  text-align: center;
  color: #888;
  padding: 2rem;
}

.help-text .hint {
  font-size: 0.85rem;
  margin-top: 0.5rem;
  color: #666;
}

.loading {
  text-align: center;
  padding: 2rem;
  color: #42b883;
  font-size: 1.1rem;
}

.error-message {
  text-align: center;
  padding: 2rem;
  color: #e74c3c;
  background: rgba(231, 76, 60, 0.1);
  border-radius: 8px;
}

/* Responsive */
@media (max-width: 900px) {
  .match-details {
    flex-direction: column;
  }
  
  .player-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
  
  .match-card {
    flex-wrap: wrap;
  }
}
</style>
