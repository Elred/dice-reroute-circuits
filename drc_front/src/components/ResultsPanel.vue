<script setup lang="ts">
import { computed } from 'vue'
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
  const type = p.type.charAt(0).toUpperCase() + p.type.slice(1)
  const poolParts: string[] = []
  if (p.red)   poolParts.push(`${p.red} Red`)
  if (p.blue)  poolParts.push(`${p.blue} Blue`)
  if (p.black) poolParts.push(`${p.black} Black`)
  const poolStr = `${type} : ${poolParts.join(' ')}`
  const opParts = pipeline.map(op => {
    if (op.type === 'add_dice') {
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
    const countStr = (op.count === 'any' || op.count == null) ? 'any' : `${op.count}`
    const resultsDesc = describeResults(op.applicable_results ?? [], p.type)
    return `${OP_LABELS[op.type] ?? op.type} ${countStr} ${resultsDesc}`
  })
  return opParts.length > 0 ? `${poolStr} — ${opParts.join(', ')}` : poolStr
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
  const entries: [string, number][] = variant.damage.map(([t, p], i) =>
    i === 0
      ? ['=0', +(variant.damage_zero * 100).toFixed(1)]
      : [`≥${t}`, +(p * 100).toFixed(1)]
  )
  const colors = entries.map((_, i) => i === 0 ? '#e53e3e' : '#d69e2e')
  const borders = entries.map((_, i) => i === 0 ? '#c53030' : '#b7791f')
  return {
    labels: entries.map(([l]) => l),
    datasets: [{
      label: 'P(damage)',
      data: entries.map(([, v]) => v),
      backgroundColor: colors,
      borderColor: borders,
      borderWidth: 1,
    }],
  }
}

function accuracyChartData(variant: VariantResult) {
  const entries: [string, number][] = variant.accuracy.map(([t, p], i) =>
    i === 0
      ? ['=0', +(variant.acc_zero * 100).toFixed(1)]
      : [`≥${t}`, +(p * 100).toFixed(1)]
  )
  const colors = entries.map((_, i) => i === 0 ? '#e53e3e' : '#4299e1')
  const borders = entries.map((_, i) => i === 0 ? '#c53030' : '#2b6cb0')
  return {
    labels: entries.map(([l]) => l),
    datasets: [{
      label: 'P(acc)',
      data: entries.map(([, v]) => v),
      backgroundColor: colors,
      borderColor: borders,
      borderWidth: 1,
    }],
  }
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
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx: any) => `${ctx.parsed.y.toFixed(1)}%`,
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

          <!-- Title (pool + pipeline) -->
          <p class="text-[#f0f0f0] text-sm font-semibold">{{ buildTitle(card.group.request) }}</p>

          <!-- Key stats -->
          <div class="flex gap-6 text-sm">
            <div>
              <span class="text-[#8892a4] text-xs">Strategy</span>
              <p class="text-[#f0f0f0] font-mono font-semibold">{{ STRATEGY_LABELS[card.variant.label] ?? card.variant.label }}</p>
            </div>
            <div>
              <span class="text-[#8892a4] text-xs">Avg Damage</span>
              <p class="text-[#f0f0f0] font-mono font-semibold">{{ card.variant.avg_damage.toFixed(2) }}</p>
            </div>
            <div>
              <span class="text-[#8892a4] text-xs">Crit %</span>
              <p class="text-[#f0f0f0] font-mono font-semibold">{{ (card.variant.crit * 100).toFixed(1) }}%</p>
            </div>
          </div>

          <!-- Charts -->
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <p class="text-[#8892a4] text-xs mb-1">Cumulative Damage</p>
              <div class="h-36">
                <Bar :data="damageChartData(card.variant)" :options="chartOptions" />
              </div>
            </div>
            <div v-if="card.variant.accuracy.length > 1">
              <p class="text-[#8892a4] text-xs mb-1">Cumulative Accuracy</p>
              <div class="h-36">
                <Bar :data="accuracyChartData(card.variant)" :options="chartOptions" />
              </div>
            </div>
          </div>
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
