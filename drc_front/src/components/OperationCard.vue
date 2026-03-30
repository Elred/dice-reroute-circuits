<script setup lang="ts">
import type { Operation } from '../types/api'

const props = defineProps<{ op: Operation; index: number; total: number }>()
const emit = defineEmits<{
  remove: [index: number]
  moveUp: [index: number]
  moveDown: [index: number]
}>()

function opSummary(op: Operation): string {
  if (op.type === 'add_dice') {
    const d = op.dice_to_add
    if (!d) return 'Add Dice'
    const parts = []
    if (d.red) parts.push(`${d.red}R`)
    if (d.blue) parts.push(`${d.blue}U`)
    if (d.black) parts.push(`${d.black}B`)
    return `Add Dice: ${parts.join(' ')}`
  }
  const label = op.type === 'reroll' ? 'Reroll' : 'Cancel'
  const faces = op.applicable_results?.join(', ') ?? 'any'
  return `${label} ${op.count ?? 1}× [${faces}]`
}
</script>

<template>
  <div class="flex items-center gap-2 bg-[#252840] rounded px-3 py-2 text-sm">
    <span class="flex-1 text-[#f0f0f0] font-mono text-xs">{{ opSummary(op) }}</span>
    <div class="flex gap-1">
      <button
        @click="emit('moveUp', index)"
        :disabled="index === 0"
        class="w-6 h-6 rounded bg-[#1a1d2e] text-[#8892a4] hover:text-[#d69e2e] disabled:opacity-30 text-xs"
        title="Move up"
      >↑</button>
      <button
        @click="emit('moveDown', index)"
        :disabled="index === total - 1"
        class="w-6 h-6 rounded bg-[#1a1d2e] text-[#8892a4] hover:text-[#d69e2e] disabled:opacity-30 text-xs"
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
