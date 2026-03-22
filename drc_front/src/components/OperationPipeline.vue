<script setup lang="ts">
import { ref } from 'vue'
import { useConfigStore } from '../stores/configStore'
import OperationCard from './OperationCard.vue'
import AddOperationForm from './AddOperationForm.vue'

const config = useConfigStore()
const showForm = ref(false)
</script>

<template>
  <div class="bg-[#1a1d2e] rounded-lg p-4 space-y-3">
    <h2 class="text-[#d69e2e] font-semibold text-sm uppercase tracking-wider">Operation Pipeline</h2>

    <div v-if="config.pipeline.length === 0" class="text-[#8892a4] text-xs italic">
      No operations — raw roll.
    </div>

    <div class="space-y-1.5">
      <OperationCard
        v-for="(op, i) in config.pipeline"
        :key="i"
        :op="op"
        :index="i"
        :total="config.pipeline.length"
        @remove="config.removeOperation"
        @moveUp="(idx) => config.moveOperation(idx, idx - 1)"
        @moveDown="(idx) => config.moveOperation(idx, idx + 1)"
      />
    </div>

    <AddOperationForm v-if="showForm" @close="showForm = false" />

    <button
      v-if="!showForm"
      @click="showForm = true"
      class="w-full py-1.5 rounded border border-dashed border-[#d69e2e]/40 text-[#d69e2e] text-xs hover:border-[#d69e2e] hover:bg-[#d69e2e]/10 transition-colors"
    >+ Add Operation</button>
  </div>
</template>
