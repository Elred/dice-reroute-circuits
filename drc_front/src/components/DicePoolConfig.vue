<script setup lang="ts">
import { computed } from 'vue'
import { useConfigStore } from '../stores/configStore'

const config = useConfigStore()

const poolSummary = computed(() => {
  const { red, blue, black } = config.pool
  const parts = []
  if (red > 0) parts.push(`${red}R`)
  if (blue > 0) parts.push(`${blue}U`)
  if (black > 0) parts.push(`${black}B`)
  const label = parts.length ? parts.join(' ') : '0 dice'
  return `${label} — ${config.poolLabel}`
})

const diceRows = [
  { key: 'red' as const,   label: 'Red',   color: 'text-[#e53e3e]', dot: 'bg-[#e53e3e]' },
  { key: 'blue' as const,  label: 'Blue',  color: 'text-[#4299e1]', dot: 'bg-[#4299e1]' },
  { key: 'black' as const, label: 'Black', color: 'text-[#718096]', dot: 'bg-[#718096]' },
]

const TYPE_BUTTONS: [string, string][] = [['ship', 'Ship'], ['squad', 'Squadron']]
</script>

<template>
  <div class="bg-[#1a1d2e] rounded-lg p-4 space-y-4 border border-[#b7791f]">
    <h2 class="text-[#d69e2e] font-semibold text-sm uppercase tracking-wider">Dice Pool</h2>

    <!-- Ship / Squadron toggle -->
    <div class="flex gap-2">
      <button
        v-for="[t, tLabel] in TYPE_BUTTONS"
        :key="t"
        @click="config.pool.type = t as 'ship' | 'squad'"
        :class="[
          'flex-1 py-1.5 rounded text-sm font-medium transition-colors',
          config.pool.type === t
            ? 'bg-[#d69e2e] text-[#0f1117]'
            : 'bg-[#252840] text-[#8892a4] hover:text-[#f0f0f0]'
        ]"
      >{{ tLabel }}</button>
    </div>

    <!-- Bomber checkbox (only when Squadron selected) -->
    <label v-if="config.pool.type === 'squad'" class="flex items-center gap-2 cursor-pointer">
      <input type="checkbox" v-model="config.bomber" class="accent-[#d69e2e]" />
      <span class="text-[#f0f0f0] text-xs">Bomber</span>
      <span class="text-[#8892a4] text-[10px]">(uses ship dice)</span>
    </label>

    <!-- Dice count rows -->
    <div class="space-y-2">
      <div v-for="row in diceRows" :key="row.key" class="flex items-center gap-3">
        <span class="flex items-center gap-1.5 w-16 text-sm">
          <span :class="['w-2.5 h-2.5 rounded-full', row.dot]"></span>
          <span :class="row.color">{{ row.label }}</span>
        </span>
        <button
          @click="config.pool[row.key] = Math.max(0, config.pool[row.key] - 1)"
          :disabled="config.pool[row.key] === 0"
          class="w-7 h-7 rounded bg-[#252840] text-[#f0f0f0] hover:bg-[#d69e2e] hover:text-[#0f1117] transition-colors text-lg leading-none"
        >−</button>
        <span class="w-6 text-center text-[#f0f0f0] font-mono">{{ config.pool[row.key] }}</span>
        <button
          @click="config.pool[row.key]++"
          :disabled="config.totalDiceCount >= 20"
          class="w-7 h-7 rounded bg-[#252840] text-[#f0f0f0] hover:bg-[#d69e2e] hover:text-[#0f1117] transition-colors text-lg leading-none disabled:opacity-30 disabled:cursor-not-allowed"
        >+</button>
      </div>
    </div>

    <!-- Pool summary -->
    <p class="text-[#8892a4] text-xs font-mono">{{ poolSummary }}</p>
    <p v-if="config.isPoolEmpty" class="text-[#e53e3e] text-xs">Add at least one die to calculate.</p>
    <p v-else-if="config.totalDiceCount >= 20" class="text-[#e53e3e] text-xs">Maximum of 20 dice reached.</p>
  </div>
</template>
