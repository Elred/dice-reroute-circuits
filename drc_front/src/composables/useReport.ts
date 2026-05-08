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

    // Expand color_in_pool effects with count > 1 into N single-die effects.
    // The backend processes each add_dice effect as a single die addition,
    // so we repeat the effect to achieve the desired count.
    req.pipeline = req.pipeline.flatMap((op) => {
      if (op.type === 'add_dice' && op.color_in_pool && typeof op.count === 'number' && op.count > 1) {
        const { count: _count, ...singleDieOp } = op
        return Array.from({ length: _count }, () => ({ ...singleDieOp }))
      }
      return [op]
    })

    return req
  }

  function calculate() {
    if (config.isPoolEmpty || config.strategies.length === 0) return
    report.runReport(buildRequest())
  }

  return { calculate }
}
