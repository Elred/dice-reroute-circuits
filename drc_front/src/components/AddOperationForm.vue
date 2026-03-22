<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useConfigStore } from '../stores/configStore'
import { useMetaStore } from '../stores/metaStore'
import type { Operation } from '../types/api'

const emit = defineEmits<{ close: [] }>()

const config = useConfigStore()
const meta = useMetaStore()

const opType = ref<'reroll' | 'cancel' | 'add_dice'>('reroll')
const count = ref(1)
const selectedFaces = ref<string[]>([])
const addRed = ref(0)
const addBlue = ref(0)
const addBlack = ref(0)

// All face values for current pool type (flat list)
const allFaces = computed(() => {
  const fv = meta.faceValuesForType(config.pool.type)
  return Object.values(fv).flat()
})

// Reset faces when op type or pool type changes
watch([opType, () => config.pool.type], () => { selectedFaces.value = [] })

function submit() {
  let op: Operation
  if (opType.value === 'add_dice') {
    if (addRed.value + addBlue.value + addBlack.value === 0) return
    op = { type: 'add_dice', dice_to_add: { red: addRed.value, blue: addBlue.value, black: addBlack.value } }
  } else {
    if (count.value < 1 || selectedFaces.value.length === 0) return
    op = { type: opType.value, count: count.value, applicable_results: [...selectedFaces.value] }
  }
  config.addOperation(op)
  emit('close')
}

const canSubmit = computed(() => {
  if (opType.value === 'add_dice') return addRed.value + addBlue.value + addBlack.value > 0
  return count.value >= 1 && selectedFaces.value.length > 0
})
</script>

<template>
  <div class="bg-[#252840] rounded-lg p-4 space-y-3 border border-[#d69e2e]/30">
    <h3 class="text-[#d69e2e] text-xs font-semibold uppercase tracking-wider">Add Operation</h3>

    <!-- Op type selector -->
    <div class="flex gap-2">
      <button
        v-for="t in ['reroll', 'cancel', 'add_dice']"
        :key="t"
        @click="opType = t as any"
        :class="[
          'flex-1 py-1 rounded text-xs font-medium transition-colors',
          opType === t ? 'bg-[#d69e2e] text-[#0f1117]' : 'bg-[#1a1d2e] text-[#8892a4] hover:text-[#f0f0f0]'
        ]"
      >{{ t }}</button>
    </div>

    <!-- reroll / cancel fields -->
    <template v-if="opType !== 'add_dice'">
      <div class="flex items-center gap-2">
        <label class="text-[#8892a4] text-xs w-12">Count</label>
        <input
          v-model.number="count"
          type="number" min="1"
          class="w-16 bg-[#1a1d2e] text-[#f0f0f0] rounded px-2 py-1 text-xs border border-[#8892a4]/30 focus:border-[#d69e2e] outline-none"
        />
      </div>
      <div>
        <p class="text-[#8892a4] text-xs mb-1">Applicable faces</p>
        <div class="flex flex-wrap gap-1.5">
          <label
            v-for="face in allFaces"
            :key="face"
            class="flex items-center gap-1 cursor-pointer"
          >
            <input
              type="checkbox"
              :value="face"
              v-model="selectedFaces"
              class="accent-[#d69e2e]"
            />
            <span class="text-[#f0f0f0] text-xs font-mono">{{ face }}</span>
          </label>
        </div>
        <p v-if="allFaces.length === 0" class="text-[#8892a4] text-xs italic">Waiting for metadata…</p>
      </div>
    </template>

    <!-- add_dice fields -->
    <template v-else>
      <div class="grid grid-cols-3 gap-2">
        <div>
          <label class="text-xs block mb-0.5 text-[#e53e3e]">Red</label>
          <input v-model.number="addRed" type="number" min="0"
            class="w-full bg-[#1a1d2e] text-[#f0f0f0] rounded px-2 py-1 text-xs border border-[#8892a4]/30 focus:border-[#d69e2e] outline-none" />
        </div>
        <div>
          <label class="text-xs block mb-0.5 text-[#4299e1]">Blue</label>
          <input v-model.number="addBlue" type="number" min="0"
            class="w-full bg-[#1a1d2e] text-[#f0f0f0] rounded px-2 py-1 text-xs border border-[#8892a4]/30 focus:border-[#d69e2e] outline-none" />
        </div>
        <div>
          <label class="text-xs block mb-0.5 text-[#718096]">Black</label>
          <input v-model.number="addBlack" type="number" min="0"
            class="w-full bg-[#1a1d2e] text-[#f0f0f0] rounded px-2 py-1 text-xs border border-[#8892a4]/30 focus:border-[#d69e2e] outline-none" />
        </div>
      </div>
    </template>

    <div class="flex gap-2 pt-1">
      <button
        @click="submit"
        :disabled="!canSubmit"
        class="flex-1 py-1.5 rounded bg-[#d69e2e] text-[#0f1117] text-xs font-semibold hover:bg-[#b7791f] transition-colors"
      >Add</button>
      <button
        @click="emit('close')"
        class="px-3 py-1.5 rounded bg-[#1a1d2e] text-[#8892a4] text-xs hover:text-[#f0f0f0] transition-colors"
      >Cancel</button>
    </div>
  </div>
</template>
