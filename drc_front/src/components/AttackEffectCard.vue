<script setup lang="ts">
import type { AttackEffect } from '../types/api'
import { useMetaStore } from '../stores/metaStore'
import { useConfigStore } from '../stores/configStore'

const props = defineProps<{ op: AttackEffect; index: number; total: number }>()
const emit = defineEmits<{
  remove: [index: number]
  moveUp: [index: number]
  moveDown: [index: number]
}>()

const meta = useMetaStore()
const config = useConfigStore()

function humanReadableResult(f: string): string {
  const colorMap: Record<string, string> = { R: 'Red', U: 'Blue', B: 'Black' }
  const match = f.match(/^([A-Z])_(.+)$/)
  if (match) return `${colorMap[match[1]] ?? match[1]} ${match[2]}`
  return f
}

function opSummary(op: AttackEffect): string {
  if (op.type === 'add_dice') {
    if (op.color_in_pool) {
      const prio = op.color_priority ? op.color_priority.join(' > ') : '?'
      const count = op.count && op.count !== 'any' ? (op.count as number) : 1
      let summary = `Add ${count} From Pool [${prio}]`
      if (op.face_condition) summary += ` if ${humanReadableResult(op.face_condition)} present`
      return summary
    }
    const d = op.dice_to_add
    if (!d) return 'Add Dice'
    const parts = []
    if (d.red) parts.push(`${d.red}R`)
    if (d.blue) parts.push(`${d.blue}U`)
    if (d.black) parts.push(`${d.black}B`)
    let summary = `Add Dice: ${parts.join(' ')}`
    if (op.face_condition) summary += ` if ${humanReadableResult(op.face_condition)} present`
    return summary
  }
  if (op.type === 'add_set_die') {
    const targetDesc = op.target_result ? humanReadableResult(op.target_result) : '?'
    let summary = `Add+Set Die [${targetDesc}]`
    if (op.face_condition) summary += ` if ${humanReadableResult(op.face_condition)} present`
    return summary
  }
  if (op.type === 'change_die') {
    const sourcesDesc = (op.applicable_results ?? []).length > 0
      ? meta.describeResults(op.applicable_results!, config.pool.type)
      : 'any'
    const targetDesc = op.target_result ? humanReadableResult(op.target_result) : '?'
    return `Change Die [${sourcesDesc} > ${targetDesc}]`
  }
  if (op.type === 'reroll_all') {
    const c = op.condition
    if (!c) return 'Reroll All'
    const opLabels: Record<string, string> = { lte: '≤', lt: '<', gte: '≥', gt: '>', eq: '=', neq: '≠' }
    const attrLabels: Record<string, string> = { damage: 'Damage', crit: 'Crit', acc: 'Accuracy', blank: 'Blank' }
    return `Reroll All if ${attrLabels[c.attribute] ?? c.attribute} ${opLabels[c.operator] ?? c.operator} ${c.threshold}`
  }
  const label = op.type === 'reroll' ? 'Reroll' : 'Cancel'
  const countStr = op.count === 'any' ? 'any' : `${op.count ?? 1}×`
  const results = op.applicable_results ?? []
  const resultsDesc = results.length > 0
    ? meta.describeResults(results, config.pool.type)
    : 'any'
  return `${label} ${countStr} [${resultsDesc}]`
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
