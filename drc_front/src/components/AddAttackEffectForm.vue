<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useConfigStore } from '../stores/configStore'
import { useMetaStore } from '../stores/metaStore'
import type { AttackEffect } from '../types/api'

const emit = defineEmits<{ close: [] }>()

const config = useConfigStore()
const meta = useMetaStore()

const opType = ref<'reroll' | 'cancel' | 'add_dice' | 'change_die'>('reroll')
const countMode = ref<'any' | 'count'>('any')
const count = ref(1)
const selectedResults = ref<string[]>([])
const targetResult = ref<string | null>(null)
const addRed = ref(0)
const addBlue = ref(0)
const addBlack = ref(0)

// Sort order: blank < acc < hit < crit < doubles (hit+hit, hit+crit)
const FACE_ORDER = ['blank', 'acc', 'hit+crit', 'hit+hit', 'crit', 'hit']
function resultRank(face: string): number {
  const suffix = face.replace(/^[^_]+_/, '') // strip color prefix
  // doubles first among multi-face values
  if (suffix === 'hit+hit') return 4
  if (suffix === 'hit+crit') return 3
  if (suffix === 'crit') return 2
  if (suffix === 'hit') return 1
  if (suffix === 'acc') return -1
  // blank
  return -2
}

// Results grouped by color, sorted blank → acc → hit → crit → doubles
const resultsByColor = computed(() => {
  const fv = meta.resultValuesForType(config.pool.type)
  const sort = (faces: string[]) => [...faces].sort((a, b) => resultRank(a) - resultRank(b))
  return [
    { color: 'red',   label: 'Red',   faces: sort(fv['red']   ?? []), accent: '#e53e3e' },
    { color: 'blue',  label: 'Blue',  faces: sort(fv['blue']  ?? []), accent: '#4299e1' },
    { color: 'black', label: 'Black', faces: sort(fv['black'] ?? []), accent: '#718096' },
  ].filter(g => g.faces.length > 0)
})

const hasResults = computed(() => resultsByColor.value.some(g => g.faces.length > 0))

// Color-agnostic face options for change_die target picker
const COLOR_AGNOSTIC_FACES = ['hit', 'crit', 'acc']

// Faces for the change_die target picker — same as resultsByColor but with blank faces removed
const setDieTargetFaces = computed(() =>
  resultsByColor.value.map(g => ({
    ...g,
    faces: g.faces.filter(f => !f.endsWith('_blank')),
  })).filter(g => g.faces.length > 0)
)

// Human-readable label for a result value string
function humanReadableResultLabel(face: string): string {
  const colorMap: Record<string, string> = { R: 'Red', U: 'Blue', B: 'Black' }
  const match = face.match(/^([A-Z])_(.+)$/)
  if (match) return `${colorMap[match[1]] ?? match[1]} ${match[2]}`
  // color-agnostic: capitalise first letter
  return face.charAt(0).toUpperCase() + face.slice(1)
}

// Dice color shortcuts — toggling a color selects/deselects all its faces
const COLOR_META = [
  { color: 'red',   label: 'Red',   accent: '#e53e3e' },
  { color: 'blue',  label: 'Blue',  accent: '#4299e1' },
  { color: 'black', label: 'Black', accent: '#718096' },
]

function isColorChecked(color: string): boolean {
  const group = resultsByColor.value.find(g => g.color === color)
  if (!group || group.faces.length === 0) return false
  return group.faces.every(f => selectedResults.value.includes(f))
}

function isColorIndeterminate(color: string): boolean {
  const group = resultsByColor.value.find(g => g.color === color)
  if (!group || group.faces.length === 0) return false
  const count = group.faces.filter(f => selectedResults.value.includes(f)).length
  return count > 0 && count < group.faces.length
}

function toggleColor(color: string) {
  const group = resultsByColor.value.find(g => g.color === color)
  if (!group) return
  if (isColorChecked(color)) {
    // deselect all results of this color
    selectedResults.value = selectedResults.value.filter(f => !group.faces.includes(f))
  } else {
    // select all results of this color (add missing ones)
    const toAdd = group.faces.filter(f => !selectedResults.value.includes(f))
    selectedResults.value = [...selectedResults.value, ...toAdd]
  }
}

const showCustomResults = ref(false)

// Reset results and collapse panel when op type or pool type changes
watch([opType, () => config.pool.type], () => {
  selectedResults.value = []
  targetResult.value = null
  showCustomResults.value = false
})

function submit() {
  let op: AttackEffect
  if (opType.value === 'add_dice') {
    if (addRed.value + addBlue.value + addBlack.value === 0) return
    op = { type: 'add_dice', dice_to_add: { red: addRed.value, blue: addBlue.value, black: addBlack.value } }
  } else if (opType.value === 'change_die') {
    if (selectedResults.value.length === 0 || targetResult.value === null) return
    op = { type: 'change_die', applicable_results: [...selectedResults.value], target_result: targetResult.value }
  } else {
    if (selectedResults.value.length === 0) return
    // count='any' is passed as-is to the API; the backend resolves it to pool size
    const resolvedCount = countMode.value === 'any' ? 'any' : count.value
    op = { type: opType.value, count: resolvedCount, applicable_results: [...selectedResults.value] }
  }
  config.addAttackEffect(op)
  emit('close')
}

const canSubmit = computed(() => {
  if (opType.value === 'add_dice') {
    const adding = addRed.value + addBlue.value + addBlack.value
    return adding > 0 && config.totalDiceCount + adding <= 20
  }
  if (opType.value === 'change_die') return selectedResults.value.length > 0 && targetResult.value !== null
  return selectedResults.value.length > 0 && (countMode.value === 'any' || count.value >= 1)
})
</script>

<template>
  <div class="bg-[#252840] rounded-lg p-4 space-y-3 border border-[#d69e2e]/30">
    <h3 class="text-[#d69e2e] text-xs font-semibold uppercase tracking-wider">Add Attack Effect</h3>

    <!-- Op type selector -->
    <div class="flex gap-2">
      <button
        v-for="[t, tLabel] in [['reroll', 'Reroll'], ['cancel', 'Cancel'], ['add_dice', 'Add Dice'], ['change_die', 'Change Die']]"
        :key="t"
        @click="opType = t as any"
        :class="[
          'flex-1 py-1 rounded text-xs font-medium transition-colors',
          opType === t ? 'bg-[#d69e2e] text-[#0f1117]' : 'bg-[#1a1d2e] text-[#8892a4] hover:text-[#f0f0f0]'
        ]"
      >{{ tLabel }}</button>
    </div>

    <!-- reroll / cancel fields -->
    <template v-if="opType !== 'add_dice' && opType !== 'change_die'">
      <div class="flex items-center gap-4">
        <label class="flex items-center gap-1 cursor-pointer">
          <input type="radio" v-model="countMode" value="any" class="accent-[#d69e2e]" />
          <span class="text-[#f0f0f0] text-xs">Any</span>
        </label>
        <label class="flex items-center gap-1 cursor-pointer">
          <input type="radio" v-model="countMode" value="count" class="accent-[#d69e2e]" />
          <span class="text-[#f0f0f0] text-xs">Count</span>
        </label>
        <input
          v-model.number="count"
          type="number" min="1"
          :disabled="countMode !== 'count'"
          :class="[
            'w-16 bg-[#1a1d2e] text-[#f0f0f0] rounded px-2 py-1 text-xs border outline-none transition-opacity',
            countMode === 'count'
              ? 'border-[#8892a4]/30 focus:border-[#d69e2e] opacity-100'
              : 'border-[#8892a4]/15 opacity-30 cursor-not-allowed'
          ]"
        />
      </div>
      <div>
        <!-- Dice colors — always visible -->
        <div v-if="hasResults">
          <p class="text-[#8892a4] text-xs font-semibold mb-1">Dice colors</p>
          <div class="flex gap-3 mb-2">
            <label
              v-for="cm in COLOR_META.filter(c => resultsByColor.find(g => g.color === c.color))"
              :key="cm.color"
              class="flex items-center gap-1 cursor-pointer"
            >
              <input
                type="checkbox"
                :checked="isColorChecked(cm.color)"
                :indeterminate="isColorIndeterminate(cm.color)"
                @change="toggleColor(cm.color)"
                class="accent-[#d69e2e]"
              />
              <span class="text-xs font-semibold" :style="{ color: cm.accent }">{{ cm.label }}</span>
            </label>
          </div>
        </div>

        <!-- Expandable "Customize applicable results" panel -->
        <button
          @click="showCustomResults = !showCustomResults"
          class="flex items-center gap-1 text-[#8892a4] text-xs hover:text-[#f0f0f0] transition-colors mb-1"
        >
          <span>{{ showCustomResults ? '▾' : '▸' }}</span>
          <span>Customize applicable results</span>
          <span v-if="selectedResults.length" class="ml-1 text-[#d69e2e]">({{ selectedResults.length }})</span>
        </button>

        <div v-if="showCustomResults">
          <div v-if="hasResults">
            <p class="text-[#8892a4] text-xs mb-1">Applicable results</p>
            <div class="grid grid-cols-3 gap-x-3">
              <div v-for="group in resultsByColor" :key="group.color" class="flex flex-col gap-1">
                <span class="text-xs font-semibold mb-0.5" :style="{ color: group.accent }">{{ group.label }}</span>
                <label
                  v-for="result in group.faces"
                  :key="result"
                  class="flex items-center gap-1 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    :value="result"
                    v-model="selectedResults"
                    class="accent-[#d69e2e]"
                  />
                  <span class="text-[#f0f0f0] text-xs font-mono">{{ result.replace(/^[^_]+_/, '') }}</span>
                </label>
              </div>
            </div>
          </div>
          <p v-else class="text-[#8892a4] text-xs italic">Waiting for metadata…</p>
        </div>
      </div>
    </template>

    <!-- change_die fields -->
    <template v-else-if="opType === 'change_die'">
      <div>
        <!-- Applicable faces (source faces to change) -->
        <div v-if="hasResults">
          <p class="text-[#8892a4] text-xs font-semibold mb-1">Dice colors</p>
          <div class="flex gap-3 mb-2">
            <label
              v-for="cm in COLOR_META.filter(c => resultsByColor.find(g => g.color === c.color))"
              :key="cm.color"
              class="flex items-center gap-1 cursor-pointer"
            >
              <input
                type="checkbox"
                :checked="isColorChecked(cm.color)"
                :indeterminate="isColorIndeterminate(cm.color)"
                @change="toggleColor(cm.color)"
                class="accent-[#d69e2e]"
              />
              <span class="text-xs font-semibold" :style="{ color: cm.accent }">{{ cm.label }}</span>
            </label>
          </div>
        </div>

        <!-- Expandable applicable results panel -->
        <button
          @click="showCustomResults = !showCustomResults"
          class="flex items-center gap-1 text-[#8892a4] text-xs hover:text-[#f0f0f0] transition-colors mb-2"
        >
          <span>{{ showCustomResults ? '▾' : '▸' }}</span>
          <span>Customize applicable results</span>
          <span v-if="selectedResults.length" class="ml-1 text-[#d69e2e]">({{ selectedResults.length }})</span>
        </button>

        <div v-if="showCustomResults" class="mb-2">
          <div v-if="hasResults">
            <p class="text-[#8892a4] text-xs mb-1">Applicable results</p>
            <div class="grid grid-cols-3 gap-x-3">
              <div v-for="group in resultsByColor" :key="group.color" class="flex flex-col gap-1">
                <span class="text-xs font-semibold mb-0.5" :style="{ color: group.accent }">{{ group.label }}</span>
                <label
                  v-for="result in group.faces"
                  :key="result"
                  class="flex items-center gap-1 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    :value="result"
                    v-model="selectedResults"
                    class="accent-[#d69e2e]"
                  />
                  <span class="text-[#f0f0f0] text-xs font-mono">{{ humanReadableResultLabel(result) }}</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        <!-- Result to set picker -->
        <p class="text-[#8892a4] text-xs font-semibold mb-1">Result to set</p>
        <div class="space-y-1">
          <!-- Color-agnostic options -->
          <p class="text-[#8892a4] text-xs italic">Any color</p>
          <div class="flex flex-wrap gap-x-3 gap-y-1 mb-3">
            <label
              v-for="face in COLOR_AGNOSTIC_FACES"
              :key="face"
              class="flex items-center gap-1 cursor-pointer"
            >
              <input
                type="radio"
                :value="face"
                v-model="targetResult"
                class="accent-[#d69e2e]"
              />
              <span class="text-[#f0f0f0] text-xs font-mono">{{ humanReadableResultLabel(face) }}</span>
            </label>
          </div>
          <!-- Color-specific options grouped by color -->
          <div class="grid grid-cols-3 gap-x-3">
          <div v-for="group in setDieTargetFaces" :key="group.color">
            <p class="text-xs font-semibold mb-0.5" :style="{ color: group.accent }">{{ group.label }}</p>
            <div class="flex flex-col gap-1 mb-1">
              <label
                v-for="face in group.faces"
                :key="face"
                class="flex items-center gap-1 cursor-pointer"
              >
                <input
                  type="radio"
                  :value="face"
                  v-model="targetResult"
                  class="accent-[#d69e2e]"
                />
                <span class="text-[#f0f0f0] text-xs font-mono">{{ humanReadableResultLabel(face) }}</span>
              </label>
            </div>
          </div>
          </div>
        </div>
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
      <p v-if="config.totalDiceCount + addRed + addBlue + addBlack > 20" class="text-[#e53e3e] text-xs">
        Exceeds 20-dice limit (currently {{ config.totalDiceCount }}).
      </p>
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
