import { useConfigStore } from '../stores/configStore'
import { useReportStore } from '../stores/reportStore'
import type { ReportRequest } from '../types/api'

export function useReport() {
  const config = useConfigStore()
  const report = useReportStore()

  function buildRequest(): ReportRequest {
    const req: ReportRequest = JSON.parse(JSON.stringify({
      dice_pool: { ...config.pool, type: config.effectiveType },
      pipeline: config.pipeline,
      strategies: config.strategies,
      precision: config.precision,
    }))
    req.pool_label = config.poolLabel
    if (config.defensePipeline.length > 0) {
      req.defense_pipeline = JSON.parse(JSON.stringify(config.defensePipeline))
    }
    return req
  }

  function calculate() {
    if (config.isPoolEmpty || config.strategies.length === 0) return
    report.runReport(buildRequest())
  }

  return { calculate }
}
