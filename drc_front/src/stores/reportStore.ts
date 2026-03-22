import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchReport } from '../api/client'
import type { ReportRequest, VariantResult } from '../types/api'

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
      error.value = e.response?.data?.error ?? 'Unexpected error contacting the API.'
    } finally {
      isLoading.value = false
    }
  }

  return { variants, isLoading, error, runReport }
})
