import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchReport } from '../api/client'
import type { ReportRequest, VariantResult } from '../types/api'

export interface ReportGroup {
  id: number
  request: ReportRequest
  variants: VariantResult[]
}

let nextId = 1

export const useReportStore = defineStore('report', () => {
  const groups = ref<ReportGroup[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Keep lastRequest for backward compat (used by ResultsPanel title builder)
  const lastRequest = ref<ReportRequest | null>(null)

  async function runReport(payload: ReportRequest) {
    isLoading.value = true
    error.value = null
    lastRequest.value = payload
    try {
      const res = await fetchReport(payload)
      // Prepend new group so it appears at the top
      groups.value.unshift({ id: nextId++, request: payload, variants: res.variants })
    } catch (e: any) {
      error.value = e.response?.data?.error ?? 'Unexpected error contacting the API.'
    } finally {
      isLoading.value = false
    }
  }

  function clearAll() {
    groups.value = []
    error.value = null
  }

  function removeGroup(id: number) {
    groups.value = groups.value.filter(g => g.id !== id)
  }


  return { groups, isLoading, error, lastRequest, runReport, clearAll, removeGroup }
})
