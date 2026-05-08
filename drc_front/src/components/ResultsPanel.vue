<script setup lang="ts">
import { computed, ref } from 'vue'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { useReportStore } from '../stores/reportStore'
import { useMetaStore } from '../stores/metaStore'
import { useJointView, isClickable } from '../composables/useJointView'
import JointViewChart from './JointViewChart.vue'
import type { VariantResult } from '../types/api'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

// Custom plugin: extends bar hover hit zone so bars with very small values
// are still hoverable. The hit area spans from the bar top down to 20% of
// the chart height (i.e. y-value = 20 on a 0–100 scale).
const expandedHitPlugin = {
  id: 'expandedHitZone',
  afterDraw(chart: any) {
    // nothing to draw — this plugin only affects hit detection
  },
  beforeEvent(chart: any, args: any) {
    const event = args.event
    if (event.type !== 'mousemove' && event.type !== 'mouseout') return
    if (event.type === 'mouseout') return

    const { x, y } = event
    for (const meta of Object.values(chart._metasets) as any[]) {
      for (const element of meta.data as any[]) {
        const { x: ex, width } = element.getProps(['x', 'width'], true)
        const halfW = (width ?? 8) / 2
        // left/right bounds of the bar column
        if (x < ex - halfW || x > ex + halfW) continue
        // bottom of chart area (y=0 on scale)
        const yBottom = chart.scales.y.getPixelForValue(0)
        // 20% of chart height above the bottom
        const yMin = chart.scales.y.getPixelForValue(20)
        // if cursor is within the extended zone, fake the element as active
        if (y >= yMin && y <= yBottom) {
          // nudge the event y to sit on the bar top so Chart.js picks it up
          args.event = { ...event, y: element.y }
          return
        }
      }
    }
  },
}
ChartJS.register(expandedHitPlugin)

const report = useReportStore()
const meta = useMetaStore()

// Diagonal red stripe pattern for =0 bars
function createStripePattern(baseColor: string, stripeColor: string = '#e53e3e'): CanvasPattern | string {
  if (typeof document === 'undefined') return baseColor
  const canvas = document.createElement('canvas')
  canvas.width = 16
  canvas.height = 16
  const ctx = canvas.getContext('2d')
  if (!ctx) return baseColor
  ctx.fillStyle = baseColor
  ctx.fillRect(0, 0, 16, 16)
  ctx.strokeStyle = stripeColor
  ctx.lineWidth = 5
  ctx.beginPath()
  ctx.moveTo(0, 16)
  ctx.lineTo(16, 0)
  ctx.stroke()
  ctx.beginPath()
  ctx.moveTo(-5, 5)
  ctx.lineTo(5, -5)
  ctx.stroke()
  ctx.beginPath()
  ctx.moveTo(11, 21)
  ctx.lineTo(21, 11)
  ctx.stroke()
  return ctx.createPattern(canvas, 'repeat') ?? baseColor
}

const STRATEGY_LABELS: Record<string, string> = {
  max_damage:        'Max Damage',
  balanced:          'Balanced',
  black_doubles:     'Black Doubles',
  max_accuracy_blue: 'Max Accuracy (blue)',
}

function describeResults(results: string[], poolType: string): string {
  return meta.describeResults(results, poolType)
}

const OP_LABELS: Record<string, string> = { reroll: 'Reroll', cancel: 'Cancel', add_dice: 'Add Dice', change_die: 'Change Die' }

function humanReadableResult(f: string): string {
  const colorMap: Record<string, string> = { R: 'Red', U: 'Blue', B: 'Black' }
  const match = f.match(/^([A-Z])_(.+)$/)
  if (match) return `${colorMap[match[1]] ?? match[1]} ${match[2]}`
  return f.charAt(0).toUpperCase() + f.slice(1)
}

function buildTitle(req: import('../types/api').ReportRequest): string {
  const { dice_pool: p, pipeline } = req
  const type = req.pool_label ?? (p.type.charAt(0).toUpperCase() + p.type.slice(1))
  const poolParts: string[] = []
  if (p.red)   poolParts.push(`${p.red} Red`)
  if (p.blue)  poolParts.push(`${p.blue} Blue`)
  if (p.black) poolParts.push(`${p.black} Black`)
  const poolStr = `${type} : ${poolParts.join(' ')}`

  // Collapse consecutive color_in_pool effects with the same priority into a
  // single counted entry. The API receives them expanded (N separate effects),
  // but the title should show "Add 2 From Pool" not "Add From Pool, Add From Pool".
  type CollapsedOp = import('../types/api').AttackEffect & { _collapsedCount?: number }
  const collapsedPipeline: CollapsedOp[] = []
  for (const op of pipeline) {
    const prev = collapsedPipeline[collapsedPipeline.length - 1]
    if (
      op.type === 'add_dice' &&
      op.color_in_pool &&
      prev?.type === 'add_dice' &&
      prev?.color_in_pool &&
      JSON.stringify(op.color_priority) === JSON.stringify(prev.color_priority) &&
      op.face_condition === prev.face_condition
    ) {
      prev._collapsedCount = (prev._collapsedCount ?? 1) + 1
    } else {
      collapsedPipeline.push({ ...op })
    }
  }

  const opParts = collapsedPipeline.map(op => {
    if (op.type === 'add_dice') {
      if (op.color_in_pool) {
        // Use _collapsedCount (from expansion collapse) or the stored count field
        const count = (op as CollapsedOp)._collapsedCount ?? (op.count && op.count !== 'any' ? (op.count as number) : 1)
        return `Add ${count} From Pool`
      }
      const d = op.dice_to_add ?? {}
      const added: string[] = []
      if (d.red)   added.push(`${d.red} Red`)
      if (d.blue)  added.push(`${d.blue} Blue`)
      if (d.black) added.push(`${d.black} Black`)
      return `Add Dice: ${added.join(' ')}`
    }
    if (op.type === 'change_die') {
      const sourcesDesc = (op.applicable_results ?? []).length > 0
        ? describeResults(op.applicable_results!, p.type)
        : 'any'
      const targetDesc = op.target_result ? humanReadableResult(op.target_result) : '?'
      return `Change Die [${sourcesDesc} > ${targetDesc}]`
    }
    if (op.type === 'reroll_all') {
      const c = op.condition
      if (!c) return 'Reroll All'
      const opSymbols: Record<string, string> = { lte: '≤', lt: '<', gte: '≥', gt: '>', eq: '=', neq: '≠' }
      const attrNames: Record<string, string> = { damage: 'Damage', crit: 'Crit', acc: 'Acc', blank: 'Blank' }
      return `Reroll All if ${attrNames[c.attribute] ?? c.attribute} ${opSymbols[c.operator] ?? c.operator} ${c.threshold}`
    }
    const countStr = (op.count === 'any' || op.count == null) ? 'any' : `${op.count}`
    const resultsDesc = describeResults(op.applicable_results ?? [], p.type)
    return `${OP_LABELS[op.type] ?? op.type} ${countStr} ${resultsDesc}`
  })
  // Defense pipeline summary
  const defParts = (req.defense_pipeline ?? []).map(op => {
    switch (op.type) {
      case 'defense_reroll': return `Def Reroll ${op.count ?? 1}× [${op.mode ?? 'safe'}]`
      case 'defense_cancel': return `Def Cancel ${op.count ?? 1}×`
      case 'reduce_damage': return `Reduce ${op.amount ?? 0}`
      case 'divide_damage': return 'Halve'
      default: return String(op.type)
    }
  })

  let title = poolStr
  if (opParts.length > 0) title += ` — Attack: ${opParts.join(', ')}`
  if (defParts.length > 0) title += ` — Defense: ${defParts.join(', ')}`
  return title
}

// Keep computed reportTitle for any remaining references
const reportTitle = buildTitle

// Flat list of cards for TransitionGroup — stable key per variant
const allCards = computed(() =>
  report.groups.flatMap(group =>
    group.variants.map(variant => ({ key: `${group.id}-${variant.label}`, group, variant }))
  )
)

function damageChartData(variant: VariantResult) {
  const src = variant.pre_defense ?? variant
  const entries: [string, number][] = src.damage.map(([t, p], i) =>
    i === 0
      ? ['=0', src.damage_zero * 100]
      : [`≥${t}`, p * 100]
  )

  // When post_defense exists, show both datasets overlaid on the same chart
  if (variant.post_defense) {
    const postEntries: [string, number][] = variant.post_defense.damage.map(([t, p], i) =>
      i === 0
        ? ['=0', variant.post_defense!.damage_zero * 100]
        : [`≥${t}`, p * 100]
    )
    // Use the longer label set (pre may have more thresholds than post or vice versa)
    const maxLen = Math.max(entries.length, postEntries.length)
    const labels = Array.from({ length: maxLen }, (_, i) => {
      if (i === 0) return '=0'
      return `≥${i}`
    })
    // Pad shorter arrays with 0
    const preData = labels.map((_, i) => entries[i]?.[1] ?? 0)
    const postData = labels.map((_, i) => postEntries[i]?.[1] ?? 0)

    return {
      labels,
      datasets: [
        {
          label: 'Pre-Defense',
          data: preData,
          backgroundColor: preData.map((_, i) => i === 0 ? createStripePattern('#d69e2e') : '#d69e2e'),
          borderColor: preData.map((_, i) => i === 0 ? '#d69e2e' : '#b7791f'),
          borderWidth: preData.map((_, i) => i === 0 ? 3 : 1),
        },
        {
          label: 'Post-Defense',
          data: postData,
          backgroundColor: postData.map(() => '#48bb78'),
          borderColor: postData.map(() => '#276749'),
          borderWidth: 1,
        },
      ],
    }
  }

  // No defense — single dataset
  const colors = entries.map((_, i) => i === 0 ? createStripePattern('#d69e2e') : '#d69e2e')
  const borders = entries.map((_, i) => i === 0 ? '#d69e2e' : '#b7791f')
  return {
    labels: entries.map(([l]) => l),
    datasets: [{
      label: 'P(damage)',
      data: entries.map(([, v]) => v),
      backgroundColor: colors,
      borderColor: borders,
      borderWidth: entries.map((_, i) => i === 0 ? 3 : 1),
    }],
  }
}

function accuracyChartData(variant: VariantResult) {
  const src = variant.pre_defense ?? variant
  const entries: [string, number][] = src.accuracy.map(([t, p], i) =>
    i === 0
      ? ['=0', src.acc_zero * 100]
      : [`≥${t}`, p * 100]
  )
  const colors = entries.map((_, i) => i === 0 ? createStripePattern('#4299e1') : '#4299e1')
  const borders = entries.map((_, i) => i === 0 ? '#4299e1' : '#2b6cb0')
  return {
    labels: entries.map(([l]) => l),
    datasets: [{
      label: 'P(acc)',
      data: entries.map(([, v]) => v),
      backgroundColor: colors,
      borderColor: borders,
      borderWidth: entries.map((_, i) => i === 0 ? 3 : 1),
    }],
  }
}

function formatPct(v: number): string {
  if (v === 0) return '0%'
  const absV = Math.abs(v)
  if (absV < 0.01) {
    // tiny value — use toFixed with enough decimals to avoid scientific notation
    const decimals = Math.ceil(-Math.log10(absV)) + 4
    return `${v.toFixed(decimals).replace(/\.?0+$/, '')}%`
  }
  // normal value — full JS float precision, no toFixed rounding
  return `${v}%`
}

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index' as const,
    axis: 'x' as const,
    intersect: false,
  },
  plugins: {
    legend: {
      display: true,
      labels: {
        color: '#f0f0f0',
        font: { size: 10 },
        boxWidth: 12,
        generateLabels(chart: any) {
          const datasets = chart.data.datasets
          return datasets.map((ds: any, i: number) => {
            // Use the last backgroundColor (always a solid color, not the =0 pattern)
            const bg = Array.isArray(ds.backgroundColor)
              ? ds.backgroundColor[ds.backgroundColor.length - 1]
              : ds.backgroundColor
            const bc = Array.isArray(ds.borderColor)
              ? ds.borderColor[ds.borderColor.length - 1]
              : ds.borderColor
            return {
              text: ds.label,
              fillStyle: bg,
              strokeStyle: bc,
              lineWidth: 1,
              fontColor: '#f0f0f0',
              datasetIndex: i,
              hidden: !chart.isDatasetVisible(i),
            }
          })
        },
      },
    },
    tooltip: {
      callbacks: {
        label: (ctx: any) => formatPct(ctx.parsed.y),
      },
    },
  },
  scales: {
    x: { ticks: { color: '#8892a4', font: { size: 10 } }, grid: { color: '#252840' } },
    y: {
      min: 0, max: 100,
      ticks: { color: '#8892a4', font: { size: 10 }, callback: (v: any) => `${v}%` },
      grid: { color: '#252840' },
    },
  },
}

// --- Joint View State Management ---

// Store joint view state per card-chart pair
const jointViews = new Map<string, ReturnType<typeof useJointView>>()

function getJointView(cardKey: string, chartType: 'damage' | 'accuracy', variant: VariantResult) {
  const key = `${cardKey}-${chartType}`
  if (!jointViews.has(key)) {
    const variantRef = ref(variant)
    jointViews.set(key, useJointView(variantRef))
  }
  return jointViews.get(key)!
}

function makeDamageChartOptions(cardKey: string, variant: VariantResult) {
  const clickable = isClickable(variant)
  return {
    ...chartOptions,
    ...(clickable ? {
      onClick(_event: any, elements: any[]) {
        if (elements.length === 0) return
        const barIndex = elements[0].index
        const jv = getJointView(cardKey, 'damage', variant)
        jv.enterJointView('damage', barIndex)
        // Skip animation overlay, transition directly to joint view
        if (jv.state.value.mode === 'animating-in') {
          jv.state.value = { ...jv.state.value, mode: 'joint' }
        }
      },
      onHover(event: any, elements: any[], chart: any) {
        const canvas = chart.canvas as HTMLCanvasElement
        canvas.style.cursor = elements.length > 0 ? 'pointer' : 'default'
      },
      hover: {
        mode: 'index' as const,
        intersect: false,
      },
    } : {}),
  }
}

function makeAccuracyChartOptions(cardKey: string, variant: VariantResult) {
  const clickable = isClickable(variant)
  return {
    ...chartOptions,
    ...(clickable ? {
      onClick(_event: any, elements: any[]) {
        if (elements.length === 0) return
        const barIndex = elements[0].index
        const jv = getJointView(cardKey, 'accuracy', variant)
        jv.enterJointView('accuracy', barIndex)
        // Skip animation overlay, transition directly to joint view
        if (jv.state.value.mode === 'animating-in') {
          jv.state.value = { ...jv.state.value, mode: 'joint' }
        }
      },
      onHover(event: any, elements: any[], chart: any) {
        const canvas = chart.canvas as HTMLCanvasElement
        canvas.style.cursor = elements.length > 0 ? 'pointer' : 'default'
      },
      hover: {
        mode: 'index' as const,
        intersect: false,
      },
    } : {}),
  }
}

/**
 * Check if any chart on a card is in joint view mode.
 */
function isAnyChartInJointView(cardKey: string, variant: VariantResult): boolean {
  const dmgKey = `${cardKey}-damage`
  const accKey = `${cardKey}-accuracy`
  const dmgJv = jointViews.get(dmgKey)
  const accJv = jointViews.get(accKey)
  return (dmgJv?.state.value.mode === 'joint') || (accJv?.state.value.mode === 'joint')
}

/**
 * Exit the active joint view on a card (whichever chart is in joint mode).
 */
function exitActiveJointView(cardKey: string, variant: VariantResult) {
  const dmgKey = `${cardKey}-damage`
  const accKey = `${cardKey}-accuracy`
  const dmgJv = jointViews.get(dmgKey)
  const accJv = jointViews.get(accKey)
  if (dmgJv?.state.value.mode === 'joint') {
    exitJointViewDirect(cardKey, 'damage', variant)
  } else if (accJv?.state.value.mode === 'joint') {
    exitJointViewDirect(cardKey, 'accuracy', variant)
  }
}

/**
 * Exit joint view directly (skip animation), resetting state to normal.
 */
function exitJointViewDirect(cardKey: string, chartType: 'damage' | 'accuracy', variant: VariantResult) {
  const jv = getJointView(cardKey, chartType, variant)
  jv.state.value = {
    mode: 'normal',
    chartType: null,
    anchorIndex: 0,
    anchorThreshold: 0,
    anchorIsZeroBar: false,
    anchorValue: 0,
    jointData: [],
    jointLabels: [],
    anchorLabel: '',
    anchorValuePost: null,
    jointDataPost: null,
  }
}
</script>

<template>
  <div class="bg-[#1a1d2e] rounded-lg p-4 h-full flex flex-col">
    <h2 class="text-[#d69e2e] font-semibold text-sm uppercase tracking-wider mb-4">Results</h2>

    <!-- Empty state -->
    <div v-if="!report.isLoading && !report.error && report.groups.length === 0"
         class="flex-1 flex items-center justify-center text-[#8892a4] text-sm italic">
      Configure your pool and hit Calculate.
    </div>

    <!-- Results — newest group first, with loading overlay -->
    <div v-else class="flex-1 overflow-y-auto relative">
      <!-- Loading spinner overlay — keeps old cards visible -->
      <div v-if="report.isLoading"
           class="absolute inset-0 z-10 flex items-center justify-center bg-[#1a1d2e]/60 backdrop-blur-sm rounded">
        <div class="w-8 h-8 border-2 border-[#d69e2e] border-t-transparent rounded-full animate-spin"></div>
      </div>

      <!-- Error banner -->
      <div v-if="report.error" class="mb-4">
        <p class="text-[#e53e3e] text-sm text-center">{{ report.error }}</p>
      </div>

      <TransitionGroup name="card" tag="div" class="space-y-6">
        <div v-for="card in allCards" :key="card.key"
             class="bg-[#252840] rounded-lg p-4 space-y-4">

          <!-- Title (pool + pipeline) + back arrow + dismiss -->
          <div class="flex items-start gap-2">
            <p class="flex-1 text-[#f0f0f0] text-sm font-semibold">{{ buildTitle(card.group.request) }}</p>
            <button
              v-if="isAnyChartInJointView(card.key, card.variant)"
              @click="exitActiveJointView(card.key, card.variant)"
              class="w-6 h-6 rounded bg-[#1a1d2e] text-[#8892a4] hover:text-[#d69e2e] text-xs flex-shrink-0 flex items-center justify-center"
              title="Back to normal view"
            >←</button>
            <button
              @click="report.removeGroup(card.group.id)"
              class="w-6 h-6 rounded bg-[#1a1d2e] text-[#8892a4] hover:text-[#e53e3e] text-xs flex-shrink-0 flex items-center justify-center"
              title="Dismiss"
            >✕</button>
          </div>

          <!-- Pre-Defense label (shown when defense pipeline was applied) -->
          <p v-if="card.variant.pre_defense" class="text-[#d69e2e] text-xs font-semibold uppercase tracking-wider mb-1">Pre-Defense</p>

          <!-- Key stats -->
          <div class="flex gap-6 text-sm">
            <div>
              <span class="text-[#8892a4] text-xs">Strategy</span>
              <p class="text-[#f0f0f0] font-mono font-semibold">{{ STRATEGY_LABELS[card.variant.label] ?? card.variant.label }}</p>
            </div>
            <div>
              <span class="text-[#8892a4] text-xs">Avg Damage</span>
              <p class="text-[#f0f0f0] font-mono font-semibold">{{ (card.variant.pre_defense?.avg_damage ?? card.variant.avg_damage).toFixed(3) }}</p>
            </div>
            <div>
              <span class="text-[#8892a4] text-xs">Crit %</span>
              <p class="text-[#f0f0f0] font-mono font-semibold">{{ ((card.variant.pre_defense?.crit ?? card.variant.crit) * 100).toFixed(3) }}%</p>
            </div>
          </div>

          <!-- Charts -->
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <p class="text-[#8892a4] text-xs mb-1">Cumulative Damage</p>
              <div class="h-36">
                <Bar
                  v-if="getJointView(card.key, 'damage', card.variant).state.value.mode === 'normal'"
                  :data="damageChartData(card.variant)"
                  :options="makeDamageChartOptions(card.key, card.variant)"
                />
                <JointViewChart
                  v-else-if="getJointView(card.key, 'damage', card.variant).state.value.mode === 'joint'"
                  :anchor-label="getJointView(card.key, 'damage', card.variant).state.value.anchorLabel"
                  :anchor-value="getJointView(card.key, 'damage', card.variant).state.value.anchorValue"
                  :anchor-color="'#d69e2e'"
                  :anchor-is-zero-bar="getJointView(card.key, 'damage', card.variant).state.value.anchorIsZeroBar"
                  :joint-data="getJointView(card.key, 'damage', card.variant).state.value.jointData"
                  :joint-labels="getJointView(card.key, 'damage', card.variant).state.value.jointLabels"
                  :cross-dimension-label="'accuracy'"
                  :anchor-value-post="getJointView(card.key, 'damage', card.variant).state.value.anchorValuePost"
                  :joint-data-post="getJointView(card.key, 'damage', card.variant).state.value.jointDataPost"
                  @exit="exitJointViewDirect(card.key, 'damage', card.variant)"
                />
              </div>
            </div>
            <div v-if="(card.variant.pre_defense?.accuracy ?? card.variant.accuracy)?.length > 1">
              <p class="text-[#8892a4] text-xs mb-1">Cumulative Accuracy</p>
              <div class="h-36">
                <Bar
                  v-if="getJointView(card.key, 'accuracy', card.variant).state.value.mode === 'normal'"
                  :data="accuracyChartData(card.variant)"
                  :options="makeAccuracyChartOptions(card.key, card.variant)"
                />
                <JointViewChart
                  v-else-if="getJointView(card.key, 'accuracy', card.variant).state.value.mode === 'joint'"
                  :anchor-label="getJointView(card.key, 'accuracy', card.variant).state.value.anchorLabel"
                  :anchor-value="getJointView(card.key, 'accuracy', card.variant).state.value.anchorValue"
                  :anchor-color="'#4299e1'"
                  :anchor-is-zero-bar="getJointView(card.key, 'accuracy', card.variant).state.value.anchorIsZeroBar"
                  :joint-data="getJointView(card.key, 'accuracy', card.variant).state.value.jointData"
                  :joint-labels="getJointView(card.key, 'accuracy', card.variant).state.value.jointLabels"
                  :cross-dimension-label="'damage'"
                  :anchor-value-post="getJointView(card.key, 'accuracy', card.variant).state.value.anchorValuePost"
                  :joint-data-post="getJointView(card.key, 'accuracy', card.variant).state.value.jointDataPost"
                  @exit="exitJointViewDirect(card.key, 'accuracy', card.variant)"
                />
              </div>
            </div>
          </div>

          <!-- Engine type -->
          <p v-if="card.variant.engine_type" class="text-[#8892a4] text-[10px] italic text-right mt-1">
            Engine: {{ card.variant.engine_type }}
          </p>

          <!-- Post-Defense Stats (shown when defense pipeline was applied) -->
          <template v-if="card.variant.post_defense">
            <div class="border-t border-[#276749]/30 pt-3 mt-2">
              <p class="text-[#48bb78] text-xs font-semibold uppercase tracking-wider mb-2">Post-Defense</p>

              <!-- Post-defense key stats -->
              <div class="flex gap-6 text-sm">
                <div>
                  <span class="text-[#8892a4] text-xs">Avg Damage</span>
                  <p class="text-[#48bb78] font-mono font-semibold">{{ card.variant.post_defense.avg_damage.toFixed(3) }}</p>
                </div>
                <div>
                  <span class="text-[#8892a4] text-xs">Crit %</span>
                  <p class="text-[#48bb78] font-mono font-semibold">{{ (card.variant.post_defense.crit * 100).toFixed(3) }}%</p>
                </div>
              </div>
            </div>
          </template>
        </div>
      </TransitionGroup>
    </div>
  </div>
</template>

<style scoped>
/* New card slides in from top */
.card-enter-active {
  transition: all 0.35s ease;
}
.card-enter-from {
  opacity: 0;
  transform: translateY(-16px);
}
.card-enter-to {
  opacity: 1;
  transform: translateY(0);
}

/* Existing cards shift down smoothly */
.card-move {
  transition: transform 0.35s ease;
}
</style>
