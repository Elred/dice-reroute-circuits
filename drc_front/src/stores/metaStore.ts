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

  const faceValuesForType = computed(() =>
    (type: string): Record<string, string[]> => meta.value?.face_values[type] ?? {}
  )

  return { meta, error, loadMeta, strategiesForType, faceValuesForType }
})
