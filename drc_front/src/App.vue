<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useMetaStore } from './stores/metaStore'
import { useConfigStore } from './stores/configStore'
import { useReport } from './composables/useReport'
import DicePoolConfig from './components/DicePoolConfig.vue'
import AttackEffectPipeline from './components/AttackEffectPipeline.vue'
import ResultsPanel from './components/ResultsPanel.vue'
import DefenseEffectPipeline from './components/DefenseEffectPipeline.vue'
import AboutModal from './components/AboutModal.vue'
import ChangelogModal from './components/ChangelogModal.vue'

const showAbout = ref(false)
const showChangelog = ref(false)

const meta = useMetaStore()
const config = useConfigStore()
const { calculate } = useReport()

onMounted(() => meta.loadMeta())

const canCalculate = () => !config.isPoolEmpty && config.strategies.length > 0
</script>

<template>
  <div class="min-h-screen bg-[#0f1117] flex flex-col">

    <!-- Header -->
    <header class="bg-[#1a1d2e] border-b border-[#d69e2e]/20 px-6 py-3 flex items-center gap-3">
      <span class="text-[#d69e2e] text-lg font-bold tracking-wide">DRC</span>
      <span class="text-[#8892a4] text-sm">Dice Reroute Circuits</span>
      <button
        class="ml-auto text-[#d69e2e] text-sm hover:text-[#b7791f] transition-colors"
        @click="showChangelog = true"
      >Changelog</button>
      <button
        class="text-[#d69e2e] text-sm hover:text-[#b7791f] transition-colors"
        @click="showAbout = true"
      >About</button>
    </header>

    <!-- Connection error banner -->
    <div v-if="meta.error"
         class="bg-[#e53e3e]/20 border-b border-[#e53e3e]/40 px-6 py-2 text-[#e53e3e] text-sm">
      {{ meta.error }}
    </div>

    <!-- Main layout -->
    <main class="flex-1 flex flex-col md:flex-row gap-4 p-4 overflow-hidden">

      <!-- Left panel: config -->
      <aside class="w-full md:w-80 lg:w-96 flex-shrink-0 space-y-3 overflow-y-auto">
        <DicePoolConfig />
        <AttackEffectPipeline />
        <DefenseEffectPipeline />

        <button
          @click="calculate"
          :disabled="!canCalculate()"
          class="w-full py-2.5 rounded bg-[#d69e2e] text-[#0f1117] font-semibold text-sm hover:bg-[#b7791f] transition-colors"
        >
          Calculate
        </button>
      </aside>

      <!-- Right panel: results -->
      <section class="flex-1 min-h-64 md:min-h-0 overflow-y-auto">
        <ResultsPanel />
      </section>

    </main>

    <AboutModal v-model="showAbout" />
    <ChangelogModal v-model="showChangelog" />
  </div>
</template>
