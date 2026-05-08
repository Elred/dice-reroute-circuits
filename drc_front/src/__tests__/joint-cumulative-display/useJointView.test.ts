// Feature: joint-cumulative-display — Unit tests for useJointView composable
import { describe, it, expect } from 'vitest'
import { ref } from 'vue'
import { useJointView, isClickable, extractJointData } from '../../composables/useJointView'
import type { VariantResult, JointCumulativePayload } from '../../types/api'

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const mockPayload: JointCumulativePayload = {
  damage_thresholds: [0, 1, 2],
  accuracy_thresholds: [0, 1],
  matrix: [
    [1.0, 0.8],   // row 0: P(dmg≥0 AND acc≥y)
    [0.7, 0.5],   // row 1: P(dmg≥1 AND acc≥y)
    [0.3, 0.2],   // row 2: P(dmg≥2 AND acc≥y)
  ],
}

const mockVariant: VariantResult = {
  label: 'max_damage',
  avg_damage: 1.5,
  crit: 0.3,
  damage_zero: 0.3,
  acc_zero: 0.2,
  damage: [[0, 1.0], [1, 0.7], [2, 0.3]],
  accuracy: [[0, 1.0], [1, 0.8]],
  joint_cumulative: mockPayload,
}

// ---------------------------------------------------------------------------
// isClickable tests
// ---------------------------------------------------------------------------

describe('isClickable', () => {
  // _Requirements: 1.5_
  it('returns true when variant has joint_cumulative', () => {
    expect(isClickable(mockVariant)).toBe(true)
  })

  it('returns true when variant has pre_defense.joint_cumulative', () => {
    const variant: VariantResult = {
      label: 'max_damage',
      avg_damage: 1.0,
      crit: 0.2,
      damage_zero: 0.4,
      acc_zero: 0.3,
      damage: [[0, 1.0], [1, 0.6]],
      accuracy: [[0, 1.0], [1, 0.7]],
      pre_defense: {
        avg_damage: 1.5,
        crit: 0.3,
        damage_zero: 0.3,
        acc_zero: 0.2,
        damage: [[0, 1.0], [1, 0.7], [2, 0.3]],
        accuracy: [[0, 1.0], [1, 0.8]],
        joint_cumulative: mockPayload,
      },
      post_defense: {
        avg_damage: 1.0,
        crit: 0.2,
        damage_zero: 0.4,
        acc_zero: 0.3,
        damage: [[0, 1.0], [1, 0.6]],
        accuracy: [[0, 1.0], [1, 0.7]],
      },
    }
    expect(isClickable(variant)).toBe(true)
  })

  it('returns false when no joint_cumulative anywhere', () => {
    const variant: VariantResult = {
      label: 'max_damage',
      avg_damage: 1.0,
      crit: 0.2,
      damage_zero: 0.4,
      acc_zero: 0.3,
      damage: [[0, 1.0], [1, 0.6]],
      accuracy: [[0, 1.0], [1, 0.7]],
    }
    expect(isClickable(variant)).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// State transition tests
// ---------------------------------------------------------------------------

describe('useJointView state transitions', () => {
  // _Requirements: 1.1, 1.2_
  it('enterJointView transitions state from normal to animating-in', () => {
    const variantRef = ref<VariantResult>(mockVariant)
    const { state, enterJointView } = useJointView(variantRef)

    expect(state.value.mode).toBe('normal')
    enterJointView('damage', 1)
    expect(state.value.mode).toBe('animating-in')
  })

  it('exitJointView transitions state from joint to animating-out', () => {
    const variantRef = ref<VariantResult>(mockVariant)
    const { state, enterJointView, exitJointView } = useJointView(variantRef)

    // Enter joint view first, then manually set to 'joint' (simulating animation complete)
    enterJointView('damage', 1)
    state.value = { ...state.value, mode: 'joint' }
    expect(state.value.mode).toBe('joint')

    exitJointView()
    expect(state.value.mode).toBe('animating-out')
  })

  it('exitJointView does nothing when state is normal', () => {
    const variantRef = ref<VariantResult>(mockVariant)
    const { state, exitJointView } = useJointView(variantRef)

    expect(state.value.mode).toBe('normal')
    exitJointView()
    expect(state.value.mode).toBe('normal')
  })
})

// ---------------------------------------------------------------------------
// Defense variant extraction tests
// ---------------------------------------------------------------------------

describe('useJointView defense variant extraction', () => {
  // _Requirements: 7.3, 7.4_
  it('extracts both pre and post datasets for a defense variant', () => {
    const defenseVariant: VariantResult = {
      label: 'max_damage',
      avg_damage: 1.5,
      crit: 0.3,
      damage_zero: 0.3,
      acc_zero: 0.2,
      damage: [[0, 1.0], [1, 0.7], [2, 0.3]],
      accuracy: [[0, 1.0], [1, 0.8]],
      pre_defense: {
        avg_damage: 1.5,
        crit: 0.3,
        damage_zero: 0.3,
        acc_zero: 0.2,
        damage: [[0, 1.0], [1, 0.7], [2, 0.3]],
        accuracy: [[0, 1.0], [1, 0.8]],
        joint_cumulative: mockPayload,
      },
      post_defense: {
        avg_damage: 1.0,
        crit: 0.2,
        damage_zero: 0.4,
        acc_zero: 0.3,
        damage: [[0, 1.0], [1, 0.6], [2, 0.2]],
        accuracy: [[0, 1.0], [1, 0.7]],
        joint_cumulative: {
          damage_thresholds: [0, 1, 2],
          accuracy_thresholds: [0, 1],
          matrix: [
            [1.0, 0.7],
            [0.6, 0.4],
            [0.2, 0.1],
          ],
        },
      },
    }

    const variantRef = ref<VariantResult>(defenseVariant)
    const { state, enterJointView } = useJointView(variantRef)

    enterJointView('damage', 1)

    // Pre-defense joint data: row 1 = [0.7, 0.5]
    // jointData[0] = P(acc=0) = 0.7*100 - 0.5*100 = 20
    // jointData[1] = P(acc≥1) = 0.5*100 = 50
    expect(state.value.jointData).toEqual([20, 50])

    // Post-defense joint data: row 1 = [0.6, 0.4]
    // jointDataPost[0] = P(acc=0) = 0.6*100 - 0.4*100 = 20
    // jointDataPost[1] = P(acc≥1) = 0.4*100 = 40
    expect(state.value.jointDataPost).toEqual([20, 40])

    // Anchor value post should be populated
    expect(state.value.anchorValuePost).not.toBeNull()
  })
})

// ---------------------------------------------------------------------------
// Edge case: =0 bar not clickable with single threshold
// ---------------------------------------------------------------------------

describe('extractJointData edge cases', () => {
  // _Requirements: 5.3, 5.4_
  it('=0 damage bar returns null when only one damage threshold exists', () => {
    const singleDamagePayload: JointCumulativePayload = {
      damage_thresholds: [0],
      accuracy_thresholds: [0, 1],
      matrix: [
        [1.0, 0.8],
      ],
    }
    const result = extractJointData(singleDamagePayload, 'damage', 0)
    expect(result).toBeNull()
  })

  it('=0 accuracy bar returns null when only one accuracy threshold exists', () => {
    const singleAccPayload: JointCumulativePayload = {
      damage_thresholds: [0, 1, 2],
      accuracy_thresholds: [0],
      matrix: [
        [1.0],
        [0.7],
        [0.3],
      ],
    }
    const result = extractJointData(singleAccPayload, 'accuracy', 0)
    expect(result).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// Anchor value matches original chart data probability
// ---------------------------------------------------------------------------

describe('useJointView anchor value', () => {
  // _Requirements: 5.1, 5.2_
  it('anchor value matches the probability from the variant damage chart data', () => {
    const variantRef = ref<VariantResult>(mockVariant)
    const { state, enterJointView } = useJointView(variantRef)

    // Click ≥2 damage bar (barIndex 2)
    enterJointView('damage', 2)

    // The anchor value should match damage[2][1] * 100 = 0.3 * 100 = 30
    expect(state.value.anchorValue).toBeCloseTo(mockVariant.damage[2][1] * 100, 10)
  })

  it('anchor value matches the probability from the variant accuracy chart data', () => {
    const variantRef = ref<VariantResult>(mockVariant)
    const { state, enterJointView } = useJointView(variantRef)

    // Click ≥1 accuracy bar (barIndex 1)
    enterJointView('accuracy', 1)

    // The anchor value should match accuracy[1][1] * 100 = 0.8 * 100 = 80
    expect(state.value.anchorValue).toBeCloseTo(mockVariant.accuracy[1][1] * 100, 10)
  })

  it('anchor value for =0 damage bar matches damage_zero * 100', () => {
    const variantRef = ref<VariantResult>(mockVariant)
    const { state, enterJointView } = useJointView(variantRef)

    // Click =0 damage bar (barIndex 0)
    enterJointView('damage', 0)

    // The anchor value should match damage_zero * 100 = 0.3 * 100 = 30
    expect(state.value.anchorValue).toBeCloseTo(mockVariant.damage_zero * 100, 10)
  })
})
