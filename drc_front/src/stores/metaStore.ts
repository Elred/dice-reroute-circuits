import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchMeta } from '../api/client'
import type { MetaResponse } from '../types/api'

export const useMetaStore = defineStore('meta', () => {
  const meta = ref<MetaResponse | null>(null)
  const error = ref<string | null>(null)

  async function loadMeta() {
    try {
      meta.value = await fetchMeta()
    } catch {
      error.value = 'Could not connect to the stat engine API.'
    }
  }

  const strategiesForType = computed(() =>
    (type: string): string[] => meta.value?.strategies[type] ?? []
  )

  const resultValuesForType = computed(() =>
    (type: string): Record<string, string[]> => meta.value?.result_values[type] ?? {}
  )

  const priorityListsForType = computed(() =>
    (type: string): Record<string, { reroll: string[]; cancel: string[]; change_die: Record<string, string[]> }> =>
      meta.value?.strategy_priority_lists[type] ?? {}
  )

  // Given a list of applicable_results results and pool type, return a compact
  // human-readable description: full colors collapsed to "Red"/"Blue"/"Black",
  // multiple full colors joined with " or ", remaining partial results listed
  // with color prefix stripped (e.g. "R_blank" → "blank").
  function describeResults(results: string[], poolType: string): string {
    const fv = resultValuesForType.value(poolType)
    const colorLabels: Record<string, string> = { red: 'Red', blue: 'Blue', black: 'Black' }
    const resultSet = new Set(results)
    const fullColors: string[] = []
    const remaining = new Set(results)

    for (const color of ['red', 'blue', 'black']) {
      const colorResults = fv[color] ?? []
      if (colorResults.length > 0 && colorResults.every(f => resultSet.has(f))) {
        fullColors.push(colorLabels[color])
        colorResults.forEach(f => remaining.delete(f))
      }
    }

    // For individual results, prefix with color name: "R_blank" → "red blank"
    const humanReadableResult = (f: string) => {
      const colorMap: Record<string, string> = { R: 'red', U: 'blue', B: 'black' }
      const match = f.match(/^([A-Z])_(.+)$/)
      if (match) return `${colorMap[match[1]] ?? match[1]} ${match[2]}`
      return f
    }

    const parts: string[] = []
    if (fullColors.length > 0) parts.push(fullColors.join(' or '))
    if (remaining.size > 0)    parts.push([...remaining].map(humanReadableResult).join(', '))
    return parts.join(' + ') || results.map(humanReadableResult).join(', ')
  }

  return { meta, error, loadMeta, strategiesForType, resultValuesForType, priorityListsForType, describeResults }
})
