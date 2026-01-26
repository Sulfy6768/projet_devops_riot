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

    <div class="champions-grid">
      <div
        v-for="champion in filteredChampions"
        :key="champion.id"
        class="pool-champion"
        :class="{ disabled: isChampionSelected(champion.id) }"
        @click="selectChampion(champion)"
        :title="`${champion.name} - ${champion.role}`"
      >
        <img :src="champion.image" :alt="champion.name" />
        <div class="pool-info">
          <p class="name">{{ champion.name }}</p>
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

interface Props {
  champions: Champion[]
  blueTeam: (Champion | null)[]
  redTeam: (Champion | null)[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'select-champion': [champion: Champion]
}>()

const searchQuery = ref('')

const filteredChampions = computed(() => {
  const selectedIds = new Set([...props.blueTeam, ...props.redTeam].filter(c => c).map(c => c!.id))
  return props.champions.filter(champ => {
    const matchesSearch = champ.name.toLowerCase().includes(searchQuery.value.toLowerCase())
    const notSelected = !selectedIds.has(champ.id)
    return matchesSearch && notSelected
  })
})

const isChampionSelected = (championId: string): boolean => {
  return [...props.blueTeam, ...props.redTeam].some(c => c?.id === championId)
}

const selectChampion = (champion: Champion) => {
  if (!isChampionSelected(champion.id)) {
    emit('select-champion', champion)
  }
}
</script>

<style scoped src="../assets/ChampionPool.css"></style>