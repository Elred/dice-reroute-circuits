<script setup lang="ts">
import { computed } from 'vue'
import { useConfigStore } from '../stores/configStore'
import { useMetaStore } from '../stores/metaStore'

const config = useConfigStore()
const meta = useMetaStore()

const strategies = computed(() => meta.strategiesForType(config.pool.type))

const STRATEGY_META: Record<string, { label: string; description: string }> = {
  max_damage:   { label: 'Max Damage',   description: 'Maximize total damage output' },
  max_accuracy: { label: 'Max Accuracy', description: 'Maximize accuracy tokens' },
  max_crits:    { label: 'Max Crits',    description: 'Maximize critical hits' },
  max_doubles:  { label: 'Max Doubles',  description: 'Maximize double-damage faces' },
}

function info(key: string) {
  return STRATEGY_META[key] ?? { label: key, description: '' }
}
</script>

<template>
  <div class="bg-[#1a1d2e] rounded-lg p-4 space-y-3">
    <h2 class="text-[#d69e2e] font-semibold text-sm uppercase tracking-wider">Strategies</h2>

    <p v-if="strategies.length === 0" class="text-[#8892a4] text-xs italic">Waiting for metadata…</p>

    <div class="flex flex-wrap gap-2">
      <button
        v-for="s in strategies"
        :key="s"
        @click="config.toggleStrategy(s)"
        :title="info(s).description"
        :class="[
          'px-3 py-1.5 rounded text-xs font-medium transition-colors border',
          config.strategies.includes(s)
            ? 'bg-[#d69e2e] text-[#0f1117] border-[#d69e2e]'
            : 'bg-[#252840] text-[#8892a4] border-[#8892a4]/30 hover:border-[#d69e2e] hover:text-[#f0f0f0]'
        ]"
      >
        {{ info(s).label }}
      </button>
    </div>

    <p v-if="config.strategies.length === 0" class="text-[#e53e3e] text-xs">
      Select at least one strategy to calculate.
    </p>
  </div>
</template>
