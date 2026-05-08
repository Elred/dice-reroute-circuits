import { ref, type Ref } from 'vue'
import type { VariantResult, JointCumulativePayload } from '../types/api'

export interface JointViewState {
  mode: 'normal' | 'animating-in' | 'joint' | 'animating-out'
  chartType: 'damage' | 'accuracy' | null
  anchorIndex: number
  anchorThreshold: number
  anchorIsZeroBar: boolean
  anchorValue: number
  jointData: number[]
  jointLabels: string[]
  anchorLabel: string
  anchorValuePost: number | null
  jointDataPost: number[] | null
}

function defaultState(): JointViewState {
  return {
    mode: 'normal',
    chartType: null,
    anchorIndex: 0,
    anchorThreshold: 0,
    anchorIsZeroBar: false,
    anchorValue: 0,
    jointData: [],
    jointLabels: [],
    anchorLabel: '',
    anchorValuePost: null,
    jointDataPost: null,
  }
}

/**
 * Checks whether a variant has joint_cumulative data available.
 * Works for both regular variants and defense variants.
 */
export function isClickable(variant: VariantResult): boolean {
  if (variant.joint_cumulative) return true
  if (variant.pre_defense?.joint_cumulative) return true
  if (variant.post_defense?.joint_cumulative) return true
  return false
}

/**
 * Extract joint data from a JointCumulativePayload for a given chart type and bar index.
 * Returns { jointData, jointLabels, anchorThreshold, anchorIsZeroBar } or null if not clickable.
 */
export function extractJointData(
  payload: JointCumulativePayload,
  chartType: 'damage' | 'accuracy',
  barIndex: number,
): { jointData: number[]; jointLabels: string[]; anchorThreshold: number; anchorIsZeroBar: boolean } | null {
  const { damage_thresholds, accuracy_thresholds, matrix } = payload

  if (chartType === 'damage') {
    if (barIndex === 0) {
      // =0 damage bar: need at least 2 damage thresholds to compute
      if (damage_thresholds.length < 2) return null
      // P(damage = 0 AND accuracy ≥ y) = matrix[0][j] - matrix[1][j] for each j
      const rawData = accuracy_thresholds.map((_, j) =>
        Math.max(0, (matrix[0][j] - matrix[1][j]) * 100)
      )
      // Transform first element from P(dmg=0 AND acc≥0) to P(dmg=0 AND acc=0)
      const jointData = rawData.map((v, j) => {
        if (j === 0 && rawData.length >= 2) return Math.max(0, v - rawData[1])
        return v
      })
      const jointLabels = accuracy_thresholds.map(t => `≥${t}`)
      return { jointData, jointLabels, anchorThreshold: 0, anchorIsZeroBar: true }
    } else {
      // ≥X damage bar: row X from matrix
      const rowIndex = barIndex // barIndex 1 = ≥1, which is matrix row index 1
      if (rowIndex >= matrix.length) return null
      const rawRow = matrix[rowIndex].map(v => Math.max(0, v * 100))
      // Transform first element from P(≥0) to P(=0): P(acc=0) = P(acc≥0) - P(acc≥1)
      const jointData = rawRow.map((v, j) => {
        if (j === 0 && rawRow.length >= 2) return Math.max(0, v - rawRow[1])
        return v
      })
      const jointLabels = accuracy_thresholds.map(t => `≥${t}`)
      return { jointData, jointLabels, anchorThreshold: damage_thresholds[rowIndex], anchorIsZeroBar: false }
    }
  } else {
    // accuracy chart
    if (barIndex === 0) {
      // =0 accuracy bar: need at least 2 accuracy thresholds to compute
      if (accuracy_thresholds.length < 2) return null
      // P(accuracy = 0 AND damage ≥ x) = matrix[i][0] - matrix[i][1] for each i
      const rawData = damage_thresholds.map((_, i) =>
        Math.max(0, (matrix[i][0] - matrix[i][1]) * 100)
      )
      // Transform first element from P(acc=0 AND dmg≥0) to P(acc=0 AND dmg=0)
      const jointData = rawData.map((v, i) => {
        if (i === 0 && rawData.length >= 2) return Math.max(0, v - rawData[1])
        return v
      })
      const jointLabels = damage_thresholds.map(t => `≥${t}`)
      return { jointData, jointLabels, anchorThreshold: 0, anchorIsZeroBar: true }
    } else {
      // ≥Y accuracy bar: column Y from matrix
      const colIndex = barIndex
      if (colIndex >= (matrix[0]?.length ?? 0)) return null
      const rawCol = matrix.map(row => Math.max(0, row[colIndex] * 100))
      // Transform first element from P(≥0) to P(=0): P(dmg=0) = P(dmg≥0) - P(dmg≥1)
      const jointData = rawCol.map((v, i) => {
        if (i === 0 && rawCol.length >= 2) return Math.max(0, v - rawCol[1])
        return v
      })
      const jointLabels = damage_thresholds.map(t => `≥${t}`)
      return { jointData, jointLabels, anchorThreshold: accuracy_thresholds[colIndex], anchorIsZeroBar: false }
    }
  }
}

/**
 * Get the anchor bar's probability value (0-100 scale) from the variant's chart data.
 */
function getAnchorValue(
  variant: VariantResult,
  chartType: 'damage' | 'accuracy',
  barIndex: number,
  isPreDefense: boolean,
): number {
  // For defense variants, data lives in pre_defense/post_defense, not at top level
  const src = isPreDefense
    ? variant.pre_defense!
    : (variant.post_defense ?? variant)
  if (chartType === 'damage') {
    if (barIndex === 0) return (src.damage_zero ?? 0) * 100
    const entry = src.damage?.[barIndex]
    return entry ? entry[1] * 100 : 0
  } else {
    if (barIndex === 0) return (src.acc_zero ?? 0) * 100
    const entry = src.accuracy?.[barIndex]
    return entry ? entry[1] * 100 : 0
  }
}

/**
 * Generate the anchor label string.
 */
export function buildAnchorLabel(chartType: 'damage' | 'accuracy', anchorThreshold: number, anchorIsZeroBar: boolean): string {
  if (chartType === 'damage') {
    return anchorIsZeroBar ? 'damage = 0' : `damage ≥ ${anchorThreshold}`
  } else {
    return anchorIsZeroBar ? 'acc = 0' : `acc ≥ ${anchorThreshold}`
  }
}

export function useJointView(variant: Ref<VariantResult>) {
  const state = ref<JointViewState>(defaultState())

  function enterJointView(chartType: 'damage' | 'accuracy', barIndex: number): void {
    const v = variant.value
    if (!isClickable(v)) return

    const hasDefense = !!(v.pre_defense && v.post_defense)

    // Find the joint_cumulative payload — check pre_defense first, then top-level
    let prePayload: JointCumulativePayload | undefined
    let postPayload: JointCumulativePayload | undefined

    if (hasDefense) {
      prePayload = v.pre_defense!.joint_cumulative ?? v.joint_cumulative
      postPayload = v.post_defense!.joint_cumulative
    } else {
      prePayload = v.joint_cumulative
      postPayload = undefined
    }

    if (!prePayload) return

    const result = extractJointData(prePayload, chartType, barIndex)
    if (!result) return

    // Get anchor value from the chart data
    const anchorValue = getAnchorValue(v, chartType, barIndex, hasDefense)

    // Post-defense data (if available)
    let anchorValuePost: number | null = null
    let jointDataPost: number[] | null = null
    if (postPayload) {
      const postResult = extractJointData(postPayload, chartType, barIndex)
      if (postResult) {
        jointDataPost = postResult.jointData
        // Get post-defense anchor value from post_defense stats
        if (v.post_defense) {
          if (chartType === 'damage') {
            anchorValuePost = barIndex === 0
              ? (v.post_defense.damage_zero ?? 0) * 100
              : (v.post_defense.damage?.[barIndex]?.[1] ?? 0) * 100
          } else {
            anchorValuePost = barIndex === 0
              ? (v.post_defense.acc_zero ?? 0) * 100
              : (v.post_defense.accuracy?.[barIndex]?.[1] ?? 0) * 100
          }
        }
      }
    }

    const anchorLabel = buildAnchorLabel(chartType, result.anchorThreshold, result.anchorIsZeroBar)

    state.value = {
      mode: 'animating-in',
      chartType,
      anchorIndex: barIndex,
      anchorThreshold: result.anchorThreshold,
      anchorIsZeroBar: result.anchorIsZeroBar,
      anchorValue,
      jointData: result.jointData,
      jointLabels: result.jointLabels,
      anchorLabel,
      anchorValuePost,
      jointDataPost,
    }
  }

  function exitJointView(): void {
    if (state.value.mode === 'joint') {
      state.value = { ...state.value, mode: 'animating-out' }
    }
  }

  return { state, enterJointView, exitJointView, isClickable }
}
