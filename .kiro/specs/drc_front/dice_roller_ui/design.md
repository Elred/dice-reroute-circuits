# Design — Dice Roller UI

## Overview

This document explains how the Vue.js front-end is structured, how data flows through it, and what each file does. It is written to be readable by someone new to Vue.js — each concept is explained as it appears.

---

## Vue.js 3 Primer (concepts used in this project)

Before diving into the design, here is a quick reference for the Vue 3 patterns used throughout.

### Single-File Components (SFCs)

Every UI piece is a `.vue` file with three sections:

```vue
<script setup lang="ts">
// Logic lives here — reactive state, computed values, functions
</script>

<template>
  <!-- HTML-like markup with Vue directives -->
</template>

<style scoped>
/* CSS scoped to this component only */
</style>
```

`<script setup>` is the modern shorthand for the Composition API. Everything declared inside it is automatically available in the template.

### Reactive State — `ref()` and `reactive()`

```ts
import { ref, reactive } from 'vue'

const count = ref(0)          // a single reactive value
count.value++                 // access/mutate via .value in script
// In the template: {{ count }} — no .value needed

const pool = reactive({ red: 0, blue: 0, black: 0 })  // reactive object
pool.red++                    // direct mutation, no .value
```

Use `ref` for primitives (numbers, strings, booleans). Use `reactive` for objects where you want to mutate properties directly.

### Computed Properties — `computed()`

```ts
import { computed } from 'vue'

const totalDice = computed(() => pool.red + pool.blue + pool.black)
// totalDice.value is recalculated automatically whenever pool changes
```

Computed values are cached — they only re-run when their dependencies change.

### Watchers — `watch()` and `watchEffect()`

```ts
import { watch } from 'vue'

watch(totalDice, (newVal) => {
  if (newVal === 0) console.log('pool is empty')
})
```

Use `watch` to react to state changes — e.g. triggering an API call when the pool changes.

### Pinia Store

Pinia is the official Vue 3 state management library. A store is a plain TypeScript file:

```ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useReportStore = defineStore('report', () => {
  const variants = ref([])
  const isLoading = ref(false)
  // ... actions, computed
  return { variants, isLoading }
})
```

Components import and use the store with `const store = useReportStore()`.

### Template Directives

| Directive | Purpose |
|---|---|
| `v-model` | Two-way binding between input and reactive state |
| `v-for` | Render a list |
| `v-if` / `v-else` | Conditional rendering |
| `v-bind:` or `:` | Bind a JS expression to an attribute |
| `v-on:` or `@` | Attach an event listener |

---

## Project Structure

```
drc_front/
├── public/
├── src/
│   ├── assets/
│   │   └── main.css          # Global dark theme base styles
│   ├── components/
│   │   ├── DicePoolConfig.vue
│   │   ├── OperationPipeline.vue
│   │   ├── OperationCard.vue
│   │   ├── AddOperationForm.vue
│   │   ├── StrategySelector.vue
│   │   └── ResultsPanel.vue
│   ├── composables/
│   │   └── useReport.ts      # Encapsulates the API call + debounce logic
│   ├── stores/
│   │   ├── configStore.ts    # Dice pool + pipeline + strategies (user inputs)
│   │   ├── metaStore.ts      # Metadata from /api/v1/meta
│   │   └── reportStore.ts    # API response + loading/error state
│   ├── types/
│   │   └── api.ts            # TypeScript interfaces for API request/response
│   ├── api/
│   │   └── client.ts         # Axios instance + typed API functions
│   ├── App.vue               # Root layout: left panel + right panel
│   └── main.ts               # App entry point
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

---

## TypeScript Types (`src/types/api.ts`)

These interfaces mirror the API contract exactly.

```ts
// --- Request types ---

export interface DicePool {
  red: number
  blue: number
  black: number
  type: 'ship' | 'squad'
}

export interface Operation {
  type: 'reroll' | 'cancel' | 'add_dice'
  count?: number
  applicable_results?: string[]
  dice_to_add?: { red: number; blue: number; black: number }
}

export interface ReportRequest {
  dice_pool: DicePool
  pipeline: Operation[]
  strategies: string[]
}

// --- Response types ---

export interface VariantResult {
  label: string
  avg_damage: number
  crit: number
  damage: [number, number][]    // [threshold, probability] pairs
  accuracy: [number, number][]
}

export interface ReportResponse {
  variants: VariantResult[]
}

// --- Metadata types ---

export interface MetaResponse {
  dice_types: string[]
  strategies: Record<string, string[]>
  operation_types: string[]
  face_values: Record<string, Record<string, string[]>>
}
```

---

## API Client (`src/api/client.ts`)

```ts
import axios from 'axios'
import type { ReportRequest, ReportResponse, MetaResponse } from '../types/api'

const http = axios.create({ baseURL: '/api/v1' })

export async function fetchMeta(): Promise<MetaResponse> {
  const res = await http.get<MetaResponse>('/meta')
  return res.data
}

export async function fetchReport(payload: ReportRequest): Promise<ReportResponse> {
  const res = await http.post<ReportResponse>('/report', payload)
  return res.data
}
```

The Vite dev proxy (configured in `vite.config.ts`) forwards `/api/*` to `http://localhost:5000`, so no CORS issues during development.

```ts
// vite.config.ts
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': 'http://localhost:5000'
    }
  }
})
```

---

## Stores

### `metaStore.ts` — metadata from the API

```ts
export const useMetaStore = defineStore('meta', () => {
  const meta = ref<MetaResponse | null>(null)
  const error = ref<string | null>(null)

  async function loadMeta() {
    try {
      meta.value = await fetchMeta()
    } catch (e) {
      error.value = 'Could not connect to the stat engine API.'
    }
  }

  const strategiesForType = computed(() =>
    (type: string) => meta.value?.strategies[type] ?? []
  )

  const faceValuesForType = computed(() =>
    (type: string) => meta.value?.face_values[type] ?? {}
  )

  return { meta, error, loadMeta, strategiesForType, faceValuesForType }
})
```

`loadMeta()` is called once in `App.vue` on mount.

---

### `configStore.ts` — user inputs

```ts
export const useConfigStore = defineStore('config', () => {
  const pool = reactive<DicePool>({ red: 0, blue: 0, black: 0, type: 'ship' })
  const pipeline = ref<Operation[]>([])
  const strategies = ref<string[]>(['max_damage'])

  const isPoolEmpty = computed(() => pool.red + pool.blue + pool.black === 0)

  function addOperation(op: Operation) { pipeline.value.push(op) }
  function removeOperation(index: number) { pipeline.value.splice(index, 1) }
  function moveOperation(from: number, to: number) {
    const [op] = pipeline.value.splice(from, 1)
    pipeline.value.splice(to, 0, op)
  }
  function toggleStrategy(name: string) {
    const idx = strategies.value.indexOf(name)
    if (idx === -1) strategies.value.push(name)
    else strategies.value.splice(idx, 1)
  }

  // When type changes, drop strategies not valid for the new type
  watch(() => pool.type, (newType) => {
    const meta = useMetaStore()
    const valid = meta.strategiesForType(newType)
    strategies.value = strategies.value.filter(s => valid.includes(s))
  })

  return { pool, pipeline, strategies, isPoolEmpty,
           addOperation, removeOperation, moveOperation, toggleStrategy }
})
```

---

### `reportStore.ts` — API response state

```ts
export const useReportStore = defineStore('report', () => {
  const variants = ref<VariantResult[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function runReport(payload: ReportRequest) {
    isLoading.value = true
    error.value = null
    variants.value = []
    try {
      const res = await fetchReport(payload)
      variants.value = res.variants
    } catch (e: any) {
      error.value = e.response?.data?.error ?? 'Unexpected error'
    } finally {
      isLoading.value = false
    }
  }

  return { variants, isLoading, error, runReport }
})
```

---

## Composable — `useReport.ts`

Encapsulates the "build request from config and call the API" logic so components stay thin.

```ts
export function useReport() {
  const config = useConfigStore()
  const report = useReportStore()

  function buildRequest(): ReportRequest {
    return {
      dice_pool: { ...config.pool },
      pipeline: config.pipeline,
      strategies: config.strategies,
    }
  }

  function calculate() {
    if (config.isPoolEmpty || config.strategies.length === 0) return
    report.runReport(buildRequest())
  }

  return { calculate }
}
```

---

## Components

### `App.vue` — Root Layout

Renders the two-panel layout and loads metadata on mount.

```
┌─────────────────────────────────────────────────────┐
│  DRC — Dice Probability Calculator          [title]  │
├──────────────────────────┬──────────────────────────┤
│  DicePoolConfig          │  ResultsPanel            │
│  OperationPipeline       │                          │
│  StrategySelector        │                          │
│  [Calculate]             │                          │
└──────────────────────────┴──────────────────────────┘
```

On narrow screens (< 768px), the panels stack vertically (config on top, results below).

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { useMetaStore } from './stores/metaStore'
const meta = useMetaStore()
onMounted(() => meta.loadMeta())
</script>
```

---

### `DicePoolConfig.vue`

Renders three dice color rows (Red, Blue, Black) each with +/- buttons and a count display, plus a Ship/Squad toggle.

Key Vue patterns:
- `v-model` on the toggle binds to `configStore.pool.type`
- `@click` on +/- buttons calls `pool.red++` / `pool.red--`
- `:disabled="pool.red === 0"` prevents going below 0
- Dice color classes applied conditionally with `:class`

```
┌─────────────────────────────┐
│  Dice Type:  [Ship] [Squad] │
│                             │
│  🔴 Red    [-] 3 [+]        │
│  🔵 Blue   [-] 2 [+]        │
│  ⚫ Black  [-] 0 [+]        │
│                             │
│  Pool: 3R 2U 0B — Ship      │
└─────────────────────────────┘
```

---

### `OperationPipeline.vue`

Renders the list of operations and an "Add Operation" button that opens `AddOperationForm`.

- `v-for="(op, i) in configStore.pipeline"` renders each `OperationCard`
- Each card has a remove button (`@click="configStore.removeOperation(i)"`)
- Up/Down buttons call `configStore.moveOperation(i, i-1)` / `moveOperation(i, i+1)`

### `OperationCard.vue`

Displays a single operation's type and parameters as a compact card. Read-only display — editing requires removing and re-adding.

### `AddOperationForm.vue`

A form (shown inline or in a modal) for configuring a new operation before adding it to the pipeline.

- Operation type selector: `<select v-model="opType">`
- For `reroll`/`cancel`: count input + face value checklist (populated from `metaStore.faceValuesForType(pool.type)`)
- For `add_dice`: three number inputs for red/blue/black counts
- "Add" button calls `configStore.addOperation(newOp)` and resets the form

---

### `StrategySelector.vue`

Renders strategy options as toggle buttons. Available strategies come from `metaStore.strategiesForType(pool.type)`.

```
┌──────────────────────────────────────────────┐
│  Strategies                                  │
│  [✓ Max Damage] [Max Accuracy] [Max Crits]   │
└──────────────────────────────────────────────┘
```

- `:class="{ active: strategies.includes(s) }"` highlights selected strategies
- `@click="configStore.toggleStrategy(s)"` toggles selection

Strategy display labels:
| Key | Label | Description |
|---|---|---|
| `max_damage` | Max Damage | Maximize total damage output |
| `max_accuracy` | Max Accuracy | Maximize accuracy tokens |
| `max_crits` | Max Crits | Maximize critical hits |
| `max_doubles` | Max Doubles | Maximize double-damage faces |

---

### `ResultsPanel.vue`

Renders the report output. Three states:

1. **Empty** — placeholder text ("Configure your pool and hit Calculate")
2. **Loading** — spinner overlay
3. **Results** — one `VariantResult` section per strategy

Each variant section contains:
- Strategy label as a heading
- Key stats row: avg damage + crit %
- Two `<Bar>` charts from `vue-chartjs`: damage distribution and accuracy distribution

Chart data is built from the `[threshold, probability]` pairs:
```ts
const damageChartData = computed(() => ({
  labels: variant.damage.map(([t]) => `≥${t}`),
  datasets: [{
    label: 'P(damage ≥ x)',
    data: variant.damage.map(([, p]) => p * 100),
    backgroundColor: '#d69e2e',  // amber
  }]
}))
```

---

## Layout & Styling

### Color Palette

| Token | Value | Usage |
|---|---|---|
| `bg-primary` | `#0f1117` | Page background |
| `bg-panel` | `#1a1d2e` | Panel backgrounds |
| `bg-card` | `#252840` | Card backgrounds |
| `accent-gold` | `#d69e2e` | Highlights, active states |
| `text-primary` | `#f0f0f0` | Main text |
| `text-muted` | `#8892a4` | Secondary text |
| `dice-red` | `#e53e3e` | Red dice |
| `dice-blue` | `#4299e1` | Blue dice |
| `dice-black` | `#718096` | Black dice |

### Tailwind Config Extension

```js
// tailwind.config.js
theme: {
  extend: {
    colors: {
      'bg-primary': '#0f1117',
      'bg-panel': '#1a1d2e',
      'bg-card': '#252840',
      'accent-gold': '#d69e2e',
      'dice-red': '#e53e3e',
      'dice-blue': '#4299e1',
      'dice-black': '#718096',
    }
  }
}
```

---

## Data Flow Summary

```
User interaction
    │
    ▼
configStore (pool, pipeline, strategies)
    │
    ▼  [Calculate clicked]
useReport.calculate()
    │  builds ReportRequest
    ▼
reportStore.runReport(request)
    │  calls fetchReport() via Axios
    ▼
POST /api/v1/report
    │  returns ReportResponse
    ▼
reportStore.variants updated
    │
    ▼
ResultsPanel re-renders (Vue reactivity)
```

Vue's reactivity system handles the last step automatically — when `reportStore.variants` changes, any component that reads it re-renders without any manual DOM manipulation.

---

## Vite Proxy Configuration

```ts
// vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      }
    }
  }
})
```

This means in development, a request to `/api/v1/report` from the browser is transparently forwarded to `http://localhost:5000/api/v1/report` by Vite — no CORS headers needed on the browser side.
