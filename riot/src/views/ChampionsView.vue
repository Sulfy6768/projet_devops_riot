<template>
  <div class="champions-page">
    <h1>🏆 Statistiques des Champions</h1>

    <div class="position-tabs">
      <button 
        v-for="pos in positions" 
        :key="pos.key"
        :class="{ active: selectedPosition === pos.key }"
        @click="selectedPosition = pos.key"
      >
        {{ pos.icon }} {{ pos.label }}
      </button>
    </div>

    <div class="champions-table">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Champion</th>
            <th>Parties</th>
            <th>Victoires</th>
            <th>Win Rate</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(champ, index) in filteredChampions" :key="champ.name">
            <td>{{ index + 1 }}</td>
            <td class="champ-name">
              <img 
                :src="getChampionImage(champ.name)" 
                :alt="champ.name"
                class="champ-img"
                @error="onImageError"
              />
              {{ champ.name }}
            </td>
            <td>{{ champ.games }}</td>
            <td>{{ champ.wins }}</td>
            <td :class="getWinRateClass(champ.winRate)">
              {{ champ.winRate.toFixed(1) }}%
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import draftsData from '../../drafts_data.json'

interface Champion {
  championId: number
  championName: string
  teamPosition: string
  win: boolean
}

interface Draft {
  match_id: string
  team_100_champions: Champion[]
  team_200_champions: Champion[]
}

interface ChampionStats {
  name: string
  games: number
  wins: number
  winRate: number
}

const positions = [
  { key: 'ALL', label: 'Tous', icon: '📋' },
  { key: 'TOP', label: 'Top', icon: '🗡️' },
  { key: 'JUNGLE', label: 'Jungle', icon: '🌲' },
  { key: 'MIDDLE', label: 'Mid', icon: '⚡' },
  { key: 'BOTTOM', label: 'ADC', icon: '🏹' },
  { key: 'UTILITY', label: 'Support', icon: '🛡️' },
]

const selectedPosition = ref('ALL')
const championStats = ref<Map<string, Map<string, { wins: number; games: number }>>>(new Map())
const allChampionNames = ref<string[]>([])

// Liste complète des 172 champions LoL (noms API Riot)
const ALL_CHAMPIONS = [
  'Aatrox', 'Ahri', 'Akali', 'Akshan', 'Alistar', 'Ambessa', 'Amumu', 'Anivia', 'Annie', 'Aphelios',
  'Ashe', 'AurelionSol', 'Aurora', 'Azir', 'Bard', 'BelVeth', 'Blitzcrank', 'Brand', 'Braum', 'Briar',
  'Caitlyn', 'Camille', 'Cassiopeia', 'ChoGath', 'Corki', 'Darius', 'Diana', 'Draven', 'DrMundo',
  'Ekko', 'Elise', 'Evelynn', 'Ezreal', 'Fiddlesticks', 'Fiora', 'Fizz', 'Galio', 'Gangplank',
  'Garen', 'Gnar', 'Gragas', 'Graves', 'Gwen', 'Hecarim', 'Heimerdinger', 'Hwei', 'Illaoi', 'Irelia',
  'Ivern', 'Janna', 'JarvanIV', 'Jax', 'Jayce', 'Jhin', 'Jinx', 'KaiSa', 'Kalista', 'Karma',
  'Karthus', 'Kassadin', 'Katarina', 'Kayle', 'Kayn', 'Kennen', 'KhaZix', 'Kindred', 'Kled',
  'KogMaw', 'KSante', 'LeBlanc', 'LeeSin', 'Leona', 'Lillia', 'Lissandra', 'Lucian', 'Lulu', 'Lux',
  'Malphite', 'Malzahar', 'Maokai', 'MasterYi', 'Mel', 'Milio', 'MissFortune', 'MonkeyKing', 'Mordekaiser', 'Morgana',
  'Naafiri', 'Nami', 'Nasus', 'Nautilus', 'Neeko', 'Nidalee', 'Nilah', 'Nocturne', 'Nunu', 'Olaf',
  'Orianna', 'Ornn', 'Pantheon', 'Poppy', 'Pyke', 'Qiyana', 'Quinn', 'Rakan', 'Rammus', 'RekSai',
  'Rell', 'Renata', 'Renekton', 'Rengar', 'Riven', 'Rumble', 'Ryze', 'Samira', 'Sejuani', 'Senna',
  'Seraphine', 'Sett', 'Shaco', 'Shen', 'Shyvana', 'Singed', 'Sion', 'Sivir', 'Skarner', 'Smolder',
  'Sona', 'Soraka', 'Swain', 'Sylas', 'Syndra', 'TahmKench', 'Taliyah', 'Talon', 'Taric', 'Teemo',
  'Thresh', 'Tristana', 'Trundle', 'Tryndamere', 'TwistedFate', 'Twitch', 'Udyr', 'Urgot', 'Varus',
  'Vayne', 'Veigar', 'VelKoz', 'Vex', 'Vi', 'Viego', 'Viktor', 'Vladimir', 'Volibear', 'Warwick',
  'Wukong', 'Xayah', 'Xerath', 'XinZhao', 'Yasuo', 'Yone', 'Yorick', 'Yuumi', 'Zac','Zaahen', 'Zed',
  'Zeri', 'Ziggs', 'Zilean', 'Zoe', 'Zyra'
]

onMounted(() => {
  calculateStats()
  // Utiliser uniquement la liste statique des 172 champions
  allChampionNames.value = [...ALL_CHAMPIONS].sort()
})

function calculateStats() {
  const stats = new Map<string, Map<string, { wins: number; games: number }>>()
  
  // Initialiser les positions
  positions.forEach(pos => {
    stats.set(pos.key, new Map())
  })

  // Parcourir tous les matchs
  draftsData.forEach((draft: Draft) => {
    const allChampions = [...draft.team_100_champions, ...draft.team_200_champions]
    
    allChampions.forEach((champ: Champion) => {
      // Stats par position
      const positionMap = stats.get(champ.teamPosition)
      if (positionMap) {
        const current = positionMap.get(champ.championName) || { wins: 0, games: 0 }
        current.games++
        if (champ.win) current.wins++
        positionMap.set(champ.championName, current)
      }

      // Stats globales
      const allMap = stats.get('ALL')!
      const currentAll = allMap.get(champ.championName) || { wins: 0, games: 0 }
      currentAll.games++
      if (champ.win) currentAll.wins++
      allMap.set(champ.championName, currentAll)
    })
  })

  championStats.value = stats
}

const filteredChampions = computed<ChampionStats[]>(() => {
  const posStats = championStats.value.get(selectedPosition.value)
  if (!posStats) return []

  // Set des champions officiels pour filtrer
  const officialChampions = new Set(ALL_CHAMPIONS)

  const result: ChampionStats[] = []
  posStats.forEach((stats, name) => {
    // N'inclure que les champions de la liste officielle
    if (officialChampions.has(name)) {
      result.push({
        name,
        games: stats.games,
        wins: stats.wins,
        winRate: (stats.wins / stats.games) * 100
      })
    }
  })

  // Séparer les champions avec parties (>=1) et sans parties
  const withGames = result
    .filter(c => c.games >= 1)
    .sort((a, b) => {
      if (b.winRate !== a.winRate) return b.winRate - a.winRate
      return b.games - a.games
    })
  
  // Ajouter tous les champions connus sans parties à la fin
  const championsWithoutGames: ChampionStats[] = allChampionNames.value
    .filter(name => !posStats.has(name))
    .map(name => ({
      name,
      games: 0,
      wins: 0,
      winRate: 0
    }))
    .sort((a, b) => a.name.localeCompare(b.name))
  
  return [...withGames, ...championsWithoutGames]
})

function getWinRateClass(winRate: number): string {
  if (winRate >= 55) return 'high-wr'
  if (winRate >= 50) return 'mid-wr'
  return 'low-wr'
}

function getChampionImage(name: string): string {
  // Convertir le nom en format fichier (minuscules, espaces -> underscore)
  const fileName = name.toLowerCase().replace(/\s+/g, '_').replace(/'/g, '').replace(/\./g, '')
  return `/champ_img/${fileName}.png`
}

function onImageError(event: Event) {
  const img = event.target as HTMLImageElement
  img.src = '/champ_img/ahri.png'
}
</script>

<style scoped>
.champions-page h1 {
  margin-bottom: 2rem;
  color: #42b883;
}

.position-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.position-tabs button {
  padding: 0.75rem 1.25rem;
  background: #1a1a2e;
  color: white;
  border: 2px solid transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.95rem;
}

.position-tabs button:hover {
  background: #16213e;
}

.position-tabs button.active {
  border-color: #42b883;
  background: #16213e;
}

.champions-table {
  background: #1a1a2e;
  border-radius: 12px;
  overflow: hidden;
}

.champions-table table {
  width: 100%;
  border-collapse: collapse;
}

.champions-table th,
.champions-table td {
  padding: 1rem;
  text-align: left;
  border-bottom: 1px solid #2d3748;
}

.champions-table th {
  background: #16213e;
  color: #42b883;
  font-weight: 600;
}

.champions-table tbody tr:hover {
  background: #16213e;
}

.champ-name {
  font-weight: 500;
  color: white;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.champ-img {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid #42b883;
}

.high-wr {
  color: #42b883;
  font-weight: 600;
}

.mid-wr {
  color: #f0ad4e;
  font-weight: 600;
}

.low-wr {
  color: #e74c3c;
  font-weight: 600;
}
</style>
