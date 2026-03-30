import { useConfigStore } from '../stores/configStore'
import { useReportStore } from '../stores/reportStore'
import type { ReportRequest, AttackEffect } from '../types/api'

export function useReport() {
  const config = useConfigStore()
  const report = useReportStore()

  function buildRequest(): ReportRequest {
    return JSON.parse(JSON.stringify({
      dice_pool: config.pool,
      pipeline: config.pipeline,
      strategies: config.strategies,
      precision: config.precision,
    }))
  }

  function calculate() {
    if (config.isPoolEmpty || config.strategies.length === 0) return
    report.runReport(buildRequest())
  }

  return { calculate }
}
