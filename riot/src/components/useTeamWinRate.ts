interface Champion {
  id: string
  name: string
  role: string
  image: string
  tier: number
  winRate: number
}

/**
 * Calculate the win rate for a team based on champion stats, synergy, and counter matchups
 * @param team - The team to calculate win rate for
 * @param opposingTeam - The opposing team to check counters against
 * @returns The calculated win rate percentage (30-95)
 */
export function calculateWinRate(
  team: (Champion | null)[],
  opposingTeam: (Champion | null)[]
): number {
  const activeChampions = team.filter(c => c) as Champion[]
  
  // If no champions selected, return default 50%
  if (activeChampions.length === 0) return 50

  // Calculate base win rate from individual champion win rates
  let totalWinRate = 0
  activeChampions.forEach(champ => {
    totalWinRate += champ.winRate
  })
  const baseWinRate = totalWinRate / activeChampions.length

  // Calculate synergy bonus (more champions = better synergy)
  const synergyBonus = activeChampions.length > 1 ? (activeChampions.length - 1) * 1.5 : 0

  // Calculate counter bonus (lower tier champions counter higher tier)
  let counterBonus = 0
  activeChampions.forEach(teamChamp => {
    opposingTeam.forEach(enemyChamp => {
      if (enemyChamp && teamChamp.tier < enemyChamp.tier) {
        counterBonus += 1
      }
    })
  })

  // Calculate final win rate with min/max bounds
  const finalWinRate = baseWinRate + synergyBonus + counterBonus
  return Math.round(Math.min(Math.max(finalWinRate, 30), 95))
}

/**
 * Get team composition analysis
 * @param team - The team to analyze
 * @returns Analysis object with role distribution and tier breakdown
 */
export function analyzeTeamComposition(team: (Champion | null)[]) {
  const activeChampions = team.filter(c => c) as Champion[]
  
  const roleCount: Record<string, number> = {}
  const tierCount: Record<number, number> = {}
  
  activeChampions.forEach(champ => {
    roleCount[champ.role] = (roleCount[champ.role] || 0) + 1
    tierCount[champ.tier] = (tierCount[champ.tier] || 0) + 1
  })

  return {
    roleDistribution: roleCount,
    tierDistribution: tierCount,
    totalChampions: activeChampions.length
  }
}