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
  type ChartEvent,
  type ActiveElement,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const props = defineProps<{
  anchorLabel: string
  anchorValue: number
  anchorColor: string
  anchorIsZeroBar: boolean
  jointData: number[]
  jointLabels: string[]
  crossDimensionLabel: string
  anchorValuePost?: number | null
  jointDataPost?: number[] | null
}>()

const emit = defineEmits<{
  (e: 'exit'): void
}>()

// Diagonal red stripe pattern for =0 bars (same as ResultsPanel)
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

// Joint bar color matches the cross-dimension's main chart color:
// - When showing accuracy bars (crossDimensionLabel='accuracy'), use blue (#4299e1)
// - When showing damage bars (crossDimensionLabel='damage'), use gold (#d69e2e)
const jointColor = computed(() =>
  props.crossDimensionLabel === 'accuracy' ? '#4299e1' : '#d69e2e'
)
const jointBorderColor = computed(() =>
  props.crossDimensionLabel === 'accuracy' ? '#2b6cb0' : '#b7791f'
)

// Color for the condition text in the subtitle (exposed for parent use)
const conditionColor = computed(() => props.anchorColor)

const isDefenseVariant = computed(() =>
  props.anchorValuePost != null && props.jointDataPost != null
)

const chartData = computed(() => {
  // Format joint labels with dimension prefix: P(acc=0), P(acc≥1), P(acc≥2)...
  const dimPrefix = props.crossDimensionLabel === 'accuracy' ? 'acc' : 'dmg'
  const displayLabels = props.jointLabels.map((l, i) => {
    if (i === 0) return `P(${dimPrefix}=0)`
    // l is "≥N" — extract the number
    return `P(${dimPrefix}${l})`
  })
  // Anchor label for the first bar (the clicked bar from the other dimension)
  const anchorDimPrefix = props.crossDimensionLabel === 'accuracy' ? 'dmg' : 'acc'
  const anchorDisplayLabel = props.anchorIsZeroBar
    ? `P(${anchorDimPrefix}=0)`
    : `P(${anchorDimPrefix}≥${props.anchorLabel.match(/\d+/)?.[0] ?? '?'})`
  const labels = [anchorDisplayLabel, ...displayLabels]

  if (isDefenseVariant.value) {
    const preAnchorBg = props.anchorIsZeroBar
      ? createStripePattern('#d69e2e')
      : '#d69e2e'
    const postAnchorBg = '#48bb78'

    const preData = [props.anchorValue, ...props.jointData]
    const postData = [props.anchorValuePost!, ...props.jointDataPost!]

    return {
      labels,
      datasets: [
        {
          label: 'Pre-Defense',
          data: preData,
          backgroundColor: preData.map((_, i) => {
            if (i === 0) return preAnchorBg
            if (i === 1) return createStripePattern(jointColor.value) // =0 bar gets stripe
            return jointColor.value
          }),
          borderColor: preData.map((_, i) => {
            if (i === 0) return '#b7791f'
            if (i === 1) return jointColor.value // =0 bar border
            return jointBorderColor.value
          }),
          borderWidth: preData.map((_, i) => (i === 0 && props.anchorIsZeroBar) || i === 1 ? 3 : 1),
        },
        {
          label: 'Post-Defense',
          data: postData,
          backgroundColor: postData.map((_, i) => {
            if (i === 0) return postAnchorBg
            return '#48bb78'
          }),
          borderColor: postData.map((_, i) => i === 0 ? '#276749' : '#276749'),
          borderWidth: 1,
        },
      ],
    }
  }

  // Non-defense: single dataset
  const anchorBg = props.anchorIsZeroBar
    ? createStripePattern(props.anchorColor)
    : props.anchorColor
  const data = [props.anchorValue, ...props.jointData]

  return {
    labels,
    datasets: [
      {
        label: `P(${props.crossDimensionLabel})`,
        data,
        backgroundColor: data.map((_, i) => {
          if (i === 0) return anchorBg
          if (i === 1) return createStripePattern(jointColor.value) // =0 bar gets stripe
          return jointColor.value
        }),
        borderColor: data.map((_, i) => {
          if (i === 0) return props.anchorColor
          if (i === 1) return jointColor.value // =0 bar border
          return jointBorderColor.value
        }),
        borderWidth: data.map((_, i) => (i === 0 && props.anchorIsZeroBar) || i === 1 ? 3 : 1),
      },
    ],
  }
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index' as const,
    axis: 'x' as const,
    intersect: false,
  },
  onClick(_event: ChartEvent, elements: ActiveElement[]) {
    if (elements.length === 0) return
    const barIndex = elements[0].index
    if (barIndex === 0) {
      emit('exit')
    }
  },
  onHover(event: ChartEvent, elements: ActiveElement[], chart: any) {
    const canvas = chart.canvas as HTMLCanvasElement
    if (elements.length > 0 && elements[0].index === 0) {
      canvas.style.cursor = 'pointer'
    } else {
      canvas.style.cursor = 'default'
    }
  },
  plugins: {
    legend: {
      display: isDefenseVariant.value,
      labels: {
        color: '#f0f0f0',
        font: { size: 10 },
        boxWidth: 12,
        generateLabels(chart: any) {
          const datasets = chart.data.datasets
          return datasets.map((ds: any, i: number) => {
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
        label: (ctx: any) => {
          const v = ctx.parsed.y
          if (v === 0) return '0%'
          const absV = Math.abs(v)
          if (absV < 0.01) {
            const decimals = Math.ceil(-Math.log10(absV)) + 4
            return `${v.toFixed(decimals).replace(/\.?0+$/, '')}%`
          }
          return `${v}%`
        },
      },
    },
  },
  scales: {
    x: { ticks: { color: '#8892a4', font: { size: 10 } }, grid: { color: '#252840' } },
    y: {
      min: 0,
      max: 100,
      ticks: { color: '#8892a4', font: { size: 10 }, callback: (v: any) => `${v}%` },
      grid: { color: '#252840' },
    },
  },
}))
</script>

<template>
  <div class="h-full">
    <Bar :data="chartData" :options="chartOptions" />
  </div>
</template>
