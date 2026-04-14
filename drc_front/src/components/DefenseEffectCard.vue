<script setup lang="ts">
import type { DefenseEffect } from '../types/api'

const props = defineProps<{ op: DefenseEffect; index: number; total: number }>()
const emit = defineEmits<{
  remove: [index: number]
  moveUp: [index: number]
  moveDown: [index: number]
}>()

function opSummary(op: DefenseEffect): string {
  switch (op.type) {
    case 'defense_reroll': {
      const countStr = `${op.count ?? 1}×`
      const modeStr = op.mode ?? 'safe'
      const results = op.applicable_results ?? []
      const base = `Reroll ${countStr} [${modeStr}]`
      return results.length > 0 ? `${base} {${results.join(', ')}}` : base
    }
    case 'defense_cancel': {
      const countStr = `${op.count ?? 1}×`
      const results = op.applicable_results ?? []
      const base = `Cancel ${countStr}`
      return results.length > 0 ? `${base} {${results.join(', ')}}` : base
    }
    case 'reduce_damage':
      return `Reduce Damage by ${op.amount ?? 0}`
    case 'divide_damage':
      return 'Halve Damage'
    default:
      return String(op.type)
  }
}
</script>

<template>
  <div class="flex items-center gap-2 bg-[#252840] rounded px-3 py-2 text-sm">
    <span class="flex-1 text-[#f0f0f0] font-mono text-xs">{{ opSummary(op) }}</span>
    <div class="flex gap-1">
      <button
        @click="emit('moveUp', index)"
        :disabled="index === 0"
        class="w-6 h-6 rounded bg-[#1a1d2e] text-[#8892a4] hover:text-[#68d391] disabled:opacity-30 text-xs"
        title="Move up"
      >↑</button>
      <button
        @click="emit('moveDown', index)"
        :disabled="index === total - 1"
        class="w-6 h-6 rounded bg-[#1a1d2e] text-[#8892a4] hover:text-[#68d391] disabled:opacity-30 text-xs"
        title="Move down"
      >↓</button>
      <button
        @click="emit('remove', index)"
        class="w-6 h-6 rounded bg-[#1a1d2e] text-[#8892a4] hover:text-[#e53e3e] text-xs"
        title="Remove"
      >✕</button>
    </div>
  </div>
</template>
