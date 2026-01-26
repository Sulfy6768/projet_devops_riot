import draftsData from '../../drafts_data.json'

interface Champion {
  id: string
  name: string
  role: string
  image: string
  tier: number
  winRate: number
}

interface Draft {
  match_id: string
  team_100_champions: Array<{
    championId: number
    championName: string
    teamPosition: string
    win: boolean
  }>
  team_200_champions: Array<{
    championId: number
    championName: string
    teamPosition: string
    win: boolean
  }>
}

const ROLE_MAP: Record<string, string> = {
  'TOP': 'Top',
  'JUNGLE': 'Jungle',
  'MIDDLE': 'Mid',
  'BOTTOM': 'ADC',
  'UTILITY': 'Support'
}

/**
 * Convert file name to champion name
 * e.g., "ahri.png" -> "Ahri", "miss_fortune.png" -> "MissFortune"
 */
function fileNameToChampionName(fileName: string): string {
  // Remove extension
  let name = fileName.replace(/\.[^.]*$/, '')

  // Convert snake_case to camelCase (first letter capitalized)
  return name
    .split('_')
    .map(part => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join('')
}

/**
 * Calculate win rate and role for a champion from drafts data
 */
function getChampionStats(championName: string): { winRate: number; role: string } {
  let totalGames = 0
  let wins = 0
  const roles = new Map<string, number>()

  ;(draftsData as Draft[]).forEach(draft => {
    const allChampions = [...draft.team_100_champions, ...draft.team_200_champions]
    allChampions.forEach(champ => {
      if (champ.championName === championName) {
        totalGames++
        if (champ.win) wins++
        roles.set(champ.teamPosition, (roles.get(champ.teamPosition) || 0) + 1)
      }
    })
  })

  // Determine most played role
  let mostPlayedRole = 'Mid'
  let maxRoleCount = 0
  roles.forEach((count, role) => {
    if (count > maxRoleCount) {
      maxRoleCount = count
      mostPlayedRole = ROLE_MAP[role] || 'Mid'
    }
  })

  const winRate = totalGames > 0 ? (wins / totalGames) * 100 : 50
  return { winRate: Math.round(winRate), role: mostPlayedRole }
}

/**
 * Load all champions from champ_img folder and populate with stats from drafts_data
 */
export async function loadChampions(): Promise<Champion[]> {
  try {
    // Get list of champion images from public folder
    const champImages = import.meta.glob('/public/champ_img/*.png', { eager: false })
    const fileNames = Object.keys(champImages).map(path => path.split('/').pop() || '')

    const champions: Champion[] = []
    const processedNames = new Set<string>()

    // Process each image file
    fileNames.forEach(fileName => {
      if (!fileName.endsWith('.png')) return

      const champName = fileNameToChampionName(fileName)
      if (processedNames.has(champName)) return // Skip duplicates
      processedNames.add(champName)

      const stats = getChampionStats(champName)
      
      champions.push({
        id: champName.toLowerCase(),
        name: champName,
        role: stats.role,
        image: `/champ_img/${fileName}`,
        tier: 1, // Default tier, can be enhanced with more data
        winRate: stats.winRate
      })
    })

    // Sort by name for consistency
    champions.sort((a, b) => a.name.localeCompare(b.name))
    return champions
  } catch (error) {
    console.error('Error loading champions:', error)
    return []
  }
}

/**
 * Load champions synchronously using a hardcoded list
 * This is a fallback if async loading fails
 */
export function loadChampionsSync(): Champion[] {
  const championNames = [
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
    'Wukong', 'Xayah', 'Xerath', 'XinZhao', 'Yasuo', 'Yone', 'Yorick', 'Yuumi', 'Zac', 'Zaahen', 'Zed',
    'Zeri', 'Ziggs', 'Zilean', 'Zoe', 'Zyra'
  ]

  return championNames.map(champName => {
    const stats = getChampionStats(champName)
    const fileName = champName.toLowerCase()

    return {
      id: champName.toLowerCase(),
      name: champName,
      role: stats.role,
      image: `/champ_img/${fileName}.png`,
      tier: 1,
      winRate: stats.winRate
    }
  })
}
