<script setup lang="ts">
import { ref, computed } from 'vue'
import { useConfigStore } from '../stores/configStore'
import { useMetaStore } from '../stores/metaStore'
import AttackEffectCard from './AttackEffectCard.vue'
import AddAttackEffectForm from './AddAttackEffectForm.vue'

const config = useConfigStore()
const meta = useMetaStore()
const showForm = ref(false)

// --- Strategy logic (merged from StrategySelector) ---
const strategies = computed(() => meta.strategiesForType(config.effectiveType))
const priorityLists = computed(() => meta.priorityListsForType(config.effectiveType))

const STRATEGY_META: Record<string, { label: string; desc: string }> = {
  max_damage:        { label: 'Max Damage',         desc: 'Reroll blanks and accuracies to maximize total damage output.' },
  balanced:          { label: 'Balanced',           desc: 'Reroll blanks only — keeps accuracies and damage results.' },
  black_doubles:     { label: 'Black Doubles',      desc: 'Reroll blanks and black hits to maximize double-damage results.' },
  max_accuracy_blue: { label: 'Max Accuracy (blue)', desc: 'Reroll blue hits and crits to fish for accuracy results.' },
}

function label(key: string) { return STRATEGY_META[key]?.label ?? key }
function desc(key: string) { return STRATEGY_META[key]?.desc ?? '' }

const COLOR_MAP: Record<string, string> = { R: 'red', U: 'blue', B: 'black' }
function humanReadableResult(f: string): string {
  const match = f.match(/^([A-Z])_(.+)$/)
  if (match) return `${COLOR_MAP[match[1]] ?? match[1]} ${match[2]}`
  return f
}

const OP_LABELS: Record<string, string> = { reroll: 'Reroll', cancel: 'Cancel' }
const openInfo = ref<string | null>(null)

function toggleInfo(key: string, e: MouseEvent) {
  e.stopPropagation()
  openInfo.value = openInfo.value === key ? null : key
}
function closeInfo() { openInfo.value = null }

function infoLines(key: string): { op: string; results: string }[] {
  const entry = priorityLists.value[key]
  if (!entry) return []
  const lines: { op: string; results: string }[] = []
  for (const op of ['reroll', 'cancel'] as const) {
    const list: string[] = (entry as any)[op] ?? []
    if (list.length) lines.push({ op: OP_LABELS[op], results: list.map(humanReadableResult).join(' › ') })
  }
  const changeDie = entry.change_die ?? {}
  for (const subKey of ['acc', 'hit', 'double']) {
    const results = changeDie[subKey] as string[] | undefined
    if (results?.length) lines.push({ op: `Change die → ${subKey}`, results: results.map(humanReadableResult).join(' › ') })
  }
  return lines
}
</script>

<template>
  <div class="bg-[#1a1d2e] rounded-lg p-4 space-y-4 border border-[#b7791f]" @click="closeInfo">
    <!-- Attack Effects section -->
    <div class="space-y-3">
      <h2 class="text-[#d69e2e] font-semibold text-sm uppercase tracking-wider">Attack Effects</h2>

      <div v-if="config.pipeline.length === 0" class="text-[#8892a4] text-xs italic">
        No attack effects — raw roll.
      </div>

      <div class="space-y-1.5">
        <AttackEffectCard
          v-for="(op, i) in config.pipeline"
          :key="i"
          :op="op"
          :index="i"
          :total="config.pipeline.length"
          @remove="config.removeAttackEffect"
          @moveUp="(idx) => config.moveAttackEffect(idx, idx - 1)"
          @moveDown="(idx) => config.moveAttackEffect(idx, idx + 1)"
        />
      </div>

      <AddAttackEffectForm v-if="showForm" @close="showForm = false" />

      <button
        v-if="!showForm"
        @click="showForm = true"
        class="w-full py-1.5 rounded border border-dashed border-[#d69e2e]/40 text-[#d69e2e] text-xs hover:border-[#d69e2e] hover:bg-[#d69e2e]/10 transition-colors"
      >+ Add Attack Effect</button>
    </div>

    <!-- Divider -->
    <div class="border-t border-[#d69e2e]/20"></div>

    <!-- Strategy section -->
    <div class="space-y-2">
      <h2 class="text-[#d69e2e] font-semibold text-sm uppercase tracking-wider">Reroll/Cancel/Set Strategy</h2>

      <p v-if="strategies.length === 0" class="text-[#8892a4] text-xs italic">Waiting for metadata…</p>

      <div class="flex flex-col gap-2">
        <div v-for="s in strategies" :key="s" class="flex flex-col gap-1">
          <div class="flex items-center gap-2">
            <button
              :class="[
                'w-1/2 px-3 py-1.5 rounded text-xs font-medium transition-colors border text-left',
                config.strategies.includes(s)
                  ? 'bg-[#d69e2e] text-[#0f1117] border-[#d69e2e]'
                  : 'bg-[#252840] text-[#8892a4] border-[#8892a4]/30 hover:border-[#d69e2e] hover:text-[#f0f0f0]'
              ]"
              @click.stop="config.toggleStrategy(s)"
            >{{ label(s) }}</button>
            <button
              class="text-[#8892a4] hover:text-[#d69e2e] transition-colors text-xs leading-none w-4 h-4 flex items-center justify-center rounded-full border border-[#8892a4]/40 hover:border-[#d69e2e] flex-shrink-0"
              @click="toggleInfo(s, $event)"
              :aria-label="`Info for ${label(s)}`"
            >i</button>
          </div>
          <span class="text-[#8892a4] text-xs leading-tight">{{ desc(s) }}</span>
          <div
            v-if="openInfo === s"
            class="bg-[#0f1117] border border-[#d69e2e]/30 rounded p-3 text-xs space-y-1.5"
            @click.stop
          >
            <p class="text-[#d69e2e] font-semibold mb-1">{{ label(s) }}</p>
            <template v-if="infoLines(s).length">
              <div v-for="line in infoLines(s)" :key="line.op" class="flex flex-col gap-0.5">
                <span class="text-[#f0f0f0] font-medium">{{ line.op }}</span>
                <span class="text-[#8892a4] leading-snug">{{ line.results }}</span>
              </div>
            </template>
            <p v-else class="text-[#8892a4] italic">No priority data available.</p>
          </div>
        </div>
      </div>

      <p v-if="config.strategies.length === 0" class="text-[#e53e3e] text-xs">
        Select at least one strategy to calculate.
      </p>
    </div>
  </div>
</template>
