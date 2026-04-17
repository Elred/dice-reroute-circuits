<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useConfigStore } from '../stores/configStore'
import { useMetaStore } from '../stores/metaStore'
import type { DefenseEffect } from '../types/api'

const emit = defineEmits<{ close: [] }>()
const config = useConfigStore()
const meta = useMetaStore()

const opType = ref<'defense_reroll' | 'defense_cancel' | 'reduce_damage' | 'divide_damage'>('defense_reroll')
const mode = ref<'safe' | 'gamble'>('safe')
const count = ref(1)
const amount = ref(1)
const selectedResults = ref<string[]>([])
const showCustomResults = ref(false)
const showModeInfo = ref(false)

const MODE_INFO: Record<string, { label: string; desc: string; priority: string }> = {
  safe: {
    label: 'Safe',
    desc: 'Only rerolls dice whose faces cannot produce a blank. Guaranteed to not make things worse.',
    priority: 'R hit+hit › B hit+crit › U crit › U hit',
  },
  gamble: {
    label: 'Gamble',
    desc: 'Rerolls dice whose faces could become blank. Higher damage reduction potential but riskier.',
    priority: 'R hit+hit › B hit+crit › R crit › R hit › U crit › U hit › B hit',
  },
}

const resultsByColor = computed(() => {
  const fv = meta.resultValuesForType(config.pool.type)
  const isDefenseFace = (f: string) => !f.endsWith('_blank') && !f.endsWith('_acc')
  return [
    { color: 'red', label: 'Red', faces: (fv['red'] ?? []).filter(isDefenseFace), accent: '#e53e3e' },
    { color: 'blue', label: 'Blue', faces: (fv['blue'] ?? []).filter(isDefenseFace), accent: '#4299e1' },
    { color: 'black', label: 'Black', faces: (fv['black'] ?? []).filter(isDefenseFace), accent: '#718096' },
  ].filter(g => g.faces.length > 0)
})

watch(opType, () => {
  selectedResults.value = []
  showCustomResults.value = false
})

function submit() {
  let op: DefenseEffect
  if (opType.value === 'defense_reroll') {
    op = { type: 'defense_reroll', count: count.value, mode: mode.value }
    if (selectedResults.value.length > 0) op.applicable_results = [...selectedResults.value]
  } else if (opType.value === 'defense_cancel') {
    op = { type: 'defense_cancel', count: count.value }
    if (selectedResults.value.length > 0) op.applicable_results = [...selectedResults.value]
  } else if (opType.value === 'reduce_damage') {
    op = { type: 'reduce_damage', amount: amount.value }
  } else {
    op = { type: 'divide_damage' }
  }
  config.addDefenseEffect(op)
  emit('close')
}

const canSubmit = computed(() => {
  if (opType.value === 'defense_reroll') return count.value >= 1
  if (opType.value === 'defense_cancel') return count.value >= 1
  if (opType.value === 'reduce_damage') return amount.value >= 1
  return true
})
</script>

<template>
  <div class="bg-[#252840] rounded-lg p-4 space-y-3 border border-[#68d391]/30">
    <h3 class="text-[#68d391] text-xs font-semibold uppercase tracking-wider">Add Defense Effect</h3>

    <div class="flex flex-wrap gap-2">
      <button
        v-for="[t, tLabel] in [['defense_reroll', 'Reroll'], ['defense_cancel', 'Cancel'], ['reduce_damage', 'Reduce damage'], ['divide_damage', 'Halve damage']]"
        :key="t"
        @click="opType = t as any"
        :class="[
          'flex-1 py-1 rounded text-xs font-medium transition-colors',
          opType === t ? 'bg-[#68d391] text-[#0f1117]' : 'bg-[#1a1d2e] text-[#8892a4] hover:text-[#f0f0f0]'
        ]"
      >{{ tLabel }}</button>
    </div>

    <div v-if="opType === 'defense_reroll'" class="space-y-2">
      <div class="flex items-center gap-4">
        <label class="flex items-center gap-1 cursor-pointer">
          <input type="radio" v-model="mode" value="safe" class="accent-[#68d391]" />
          <span class="text-[#f0f0f0] text-xs">Safe</span>
        </label>
        <label class="flex items-center gap-1 cursor-pointer">
          <input type="radio" v-model="mode" value="gamble" class="accent-[#68d391]" />
          <span class="text-[#f0f0f0] text-xs">Gamble</span>
        </label>
        <button
          class="text-[#8892a4] hover:text-[#68d391] transition-colors text-xs leading-none w-4 h-4 flex items-center justify-center rounded-full border border-[#8892a4]/40 hover:border-[#68d391] flex-shrink-0"
          @click.stop="showModeInfo = !showModeInfo"
          aria-label="Reroll mode info"
        >i</button>
      </div>
      <div v-if="showModeInfo" class="bg-[#0f1117] border border-[#68d391]/30 rounded p-3 text-xs space-y-2">
        <div v-for="m in ['safe', 'gamble'] as const" :key="m" class="space-y-0.5">
          <p class="text-[#68d391] font-semibold">{{ MODE_INFO[m].label }}</p>
          <p class="text-[#8892a4] leading-snug">{{ MODE_INFO[m].desc }}</p>
          <p class="text-[#8892a4] leading-snug"><span class="text-[#f0f0f0] font-medium">Priority:</span> {{ MODE_INFO[m].priority }}</p>
        </div>
      </div>
    </div>

    <div v-if="opType === 'defense_reroll' || opType === 'defense_cancel'" class="flex items-center gap-2">
      <span class="text-[#8892a4] text-xs">Count</span>
      <input
        v-model.number="count"
        type="number" min="1"
        class="w-16 bg-[#1a1d2e] text-[#f0f0f0] rounded px-2 py-1 text-xs border border-[#8892a4]/30 focus:border-[#68d391] outline-none"
      />
    </div>

    <div v-if="opType === 'reduce_damage'" class="flex items-center gap-2">
      <span class="text-[#8892a4] text-xs">Amount</span>
      <input
        v-model.number="amount"
        type="number" min="1"
        class="w-16 bg-[#1a1d2e] text-[#f0f0f0] rounded px-2 py-1 text-xs border border-[#8892a4]/30 focus:border-[#68d391] outline-none"
      />
    </div>

    <div v-if="opType === 'defense_reroll' || opType === 'defense_cancel'">
      <button
        @click="showCustomResults = !showCustomResults"
        class="flex items-center gap-1 text-[#8892a4] text-xs hover:text-[#f0f0f0] transition-colors mb-1"
      >
        <span>{{ showCustomResults ? '▾' : '▸' }}</span>
        <span>Customize applicable results</span>
        <span v-if="selectedResults.length" class="ml-1 text-[#68d391]">({{ selectedResults.length }})</span>
      </button>

      <div v-if="showCustomResults">
        <div v-if="resultsByColor.length > 0">
          <p class="text-[#8892a4] text-xs mb-1">Applicable results</p>
          <div class="grid grid-cols-3 gap-x-3">
            <div v-for="group in resultsByColor" :key="group.color" class="flex flex-col gap-1">
              <span class="text-xs font-semibold mb-0.5" :style="{ color: group.accent }">{{ group.label }}</span>
              <label
                v-for="result in group.faces"
                :key="result"
                class="flex items-center gap-1 cursor-pointer"
              >
                <input type="checkbox" :value="result" v-model="selectedResults" class="accent-[#68d391]" />
                <span class="text-[#f0f0f0] text-xs font-mono">{{ result.replace(/^[^_]+_/, '') }}</span>
              </label>
            </div>
          </div>
        </div>
        <p v-else class="text-[#8892a4] text-xs italic">Waiting for metadata…</p>
      </div>
    </div>

    <div class="flex gap-2 pt-1">
      <button
        @click="submit"
        :disabled="!canSubmit"
        class="flex-1 py-1.5 rounded bg-[#68d391] text-[#0f1117] text-xs font-semibold hover:bg-[#48bb78] transition-colors disabled:opacity-50"
      >Add</button>
      <button
        @click="emit('close')"
        class="px-3 py-1.5 rounded bg-[#1a1d2e] text-[#8892a4] text-xs hover:text-[#f0f0f0] transition-colors"
      >Cancel</button>
    </div>
  </div>
</template>
