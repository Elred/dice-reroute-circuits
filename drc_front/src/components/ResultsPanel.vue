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
import type { VariantResult } from '../types/api'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const report = useReportStore()

function damageChartData(variant: VariantResult) {
  return {
    labels: variant.damage.map(([t]) => `≥${t}`),
    datasets: [{
      label: 'P(damage ≥ x)',
      data: variant.damage.map(([, p]) => +(p * 100).toFixed(1)),
      backgroundColor: '#d69e2e',
      borderColor: '#b7791f',
      borderWidth: 1,
    }],
  }
}

function accuracyChartData(variant: VariantResult) {
  return {
    labels: variant.accuracy.map(([t]) => `≥${t}`),
    datasets: [{
      label: 'P(acc ≥ x)',
      data: variant.accuracy.map(([, p]) => +(p * 100).toFixed(1)),
      backgroundColor: '#4299e1',
      borderColor: '#2b6cb0',
      borderWidth: 1,
    }],
  }
}

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
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
    <div v-if="!report.isLoading && !report.error && report.variants.length === 0"
         class="flex-1 flex items-center justify-center text-[#8892a4] text-sm italic">
      Configure your pool and hit Calculate.
    </div>

    <!-- Loading -->
    <div v-else-if="report.isLoading"
         class="flex-1 flex items-center justify-center">
      <div class="w-8 h-8 border-2 border-[#d69e2e] border-t-transparent rounded-full animate-spin"></div>
    </div>

    <!-- Error -->
    <div v-else-if="report.error"
         class="flex-1 flex items-center justify-center">
      <p class="text-[#e53e3e] text-sm text-center">{{ report.error }}</p>
    </div>

    <!-- Results -->
    <div v-else class="space-y-6 overflow-y-auto flex-1">
      <div v-for="variant in report.variants" :key="variant.label"
           class="bg-[#252840] rounded-lg p-4 space-y-4">

        <!-- Header -->
        <h3 class="text-[#d69e2e] font-semibold">{{ variant.label }}</h3>

        <!-- Key stats -->
        <div class="flex gap-6 text-sm">
          <div>
            <span class="text-[#8892a4] text-xs">Avg Damage</span>
            <p class="text-[#f0f0f0] font-mono font-semibold">{{ variant.avg_damage.toFixed(2) }}</p>
          </div>
          <div>
            <span class="text-[#8892a4] text-xs">Crit %</span>
            <p class="text-[#f0f0f0] font-mono font-semibold">{{ (variant.crit * 100).toFixed(1) }}%</p>
          </div>
        </div>

        <!-- Charts -->
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <p class="text-[#8892a4] text-xs mb-1">Cumulative Damage</p>
            <div class="h-36">
              <Bar :data="damageChartData(variant)" :options="chartOptions" />
            </div>
          </div>
          <div>
            <p class="text-[#8892a4] text-xs mb-1">Cumulative Accuracy</p>
            <div class="h-36">
              <Bar :data="accuracyChartData(variant)" :options="chartOptions" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
