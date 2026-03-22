import { useConfigStore } from '../stores/configStore'
import { useReportStore } from '../stores/reportStore'
import type { ReportRequest } from '../types/api'

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
