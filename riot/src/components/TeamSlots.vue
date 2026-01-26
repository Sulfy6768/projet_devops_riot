<template>
  <div class="team" :class="teamClass">
    <div class="team-header">
      <h2>{{ teamTitle }}</h2>
      <div class="win-rate">
        <span class="percentage">{{ winRate }}%</span>
      </div>
    </div>

    <div class="champions-slots">
      <div
        v-for="(champion, index) in champions"
        :key="`${team}-${index}`"
        class="champion-slot"
        :class="{ filled: champion, selected: isSlotSelected(index) }"
        @click="$emit('select-slot', team, index)"
      >
        <div v-if="champion" class="champion-card">
          <img :src="champion.image" :alt="champion.name" />
          <div class="champion-info">
            <p class="champion-name">{{ champion.name }}</p>
            <p class="champion-role">{{ champion.role }}</p>
          </div>
          <button class="remove-btn" @click.stop="$emit('remove-champion', team, index)">×</button>
        </div>
        <div v-else class="empty-slot">
          <span class="slot-number">{{ index + 1 }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Champion {
  id: string
  name: string
  role: string
  image: string
  tier: number
  winRate: number
}

interface Props {
  team: 'blue' | 'red'
  champions: (Champion | null)[]
  winRate: number
  selectedSlot: { team: 'blue' | 'red' | null; index: number | null }
}

const props = defineProps<Props>()

defineEmits<{
  'select-slot': [team: 'blue' | 'red', index: number]
  'remove-champion': [team: 'blue' | 'red', index: number]
}>()

const teamClass = computed(() => props.team === 'blue' ? 'blue-team' : 'red-team')
const teamTitle = computed(() => props.team === 'blue' ? 'Blue Team' : 'Red Team')

const isSlotSelected = (index: number) => {
  return props.selectedSlot.team === props.team && props.selectedSlot.index === index
}
</script>

<style scoped src="../assets/TeamSlots.css"></style>