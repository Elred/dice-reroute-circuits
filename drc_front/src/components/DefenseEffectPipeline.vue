<script setup lang="ts">
import { ref } from 'vue'
import { useConfigStore } from '../stores/configStore'
import DefenseEffectCard from './DefenseEffectCard.vue'
import AddDefenseEffectForm from './AddDefenseEffectForm.vue'

const config = useConfigStore()
const showForm = ref(false)
</script>

<template>
  <div class="bg-[#1a1d2e] rounded-lg p-4 space-y-3 border border-[#276749]">
    <h2 class="text-[#68d391] font-semibold text-sm uppercase tracking-wider">Defense Effects</h2>

    <div v-if="config.defensePipeline.length === 0" class="text-[#8892a4] text-xs italic">
      No defense effects — full attack damage.
    </div>

    <div class="space-y-1.5">
      <DefenseEffectCard
        v-for="(op, i) in config.defensePipeline"
        :key="i"
        :op="op"
        :index="i"
        :total="config.defensePipeline.length"
        @remove="config.removeDefenseEffect"
        @moveUp="(idx) => config.moveDefenseEffect(idx, idx - 1)"
        @moveDown="(idx) => config.moveDefenseEffect(idx, idx + 1)"
      />
    </div>

    <AddDefenseEffectForm v-if="showForm" @close="showForm = false" />

    <button
      v-if="!showForm"
      @click="showForm = true"
      class="w-full py-1.5 rounded border border-dashed border-[#68d391]/40 text-[#68d391] text-xs hover:border-[#68d391] hover:bg-[#68d391]/10 transition-colors"
    >+ Add Defense Effect</button>
  </div>
</template>
