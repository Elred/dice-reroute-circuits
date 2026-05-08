// Feature: joint-cumulative-display
import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import { extractJointData, buildAnchorLabel } from '../../composables/useJointView'
import type { JointCumulativePayload } from '../../types/api'

// ---------------------------------------------------------------------------
// Shared generator: valid JointCumulativePayload with monotonically
// non-increasing matrix along both axes.
//
// Strategy: generate random decrements to enforce the constraint.
// Start at 1.0 for matrix[0][0], then each cell is ≤ the cell above it
// and ≤ the cell to its left.
// ---------------------------------------------------------------------------

/**
 * Generate a JointCumulativePayload with:
 * - damage_thresholds: [0, 1, ..., D] where D is random 1–8
 * - accuracy_thresholds: [0, 1, ..., A] where A is random 1–6
 * - matrix: (D+1) × (A+1) values in [0, 1], monotonically non-increasing
 *   along both axes, with matrix[0][0] = 1.0
 */
const jointPayloadArb: fc.Arbitrary<JointCumulativePayload> = fc
  .record({
    D: fc.integer({ min: 1, max: 8 }),
    A: fc.integer({ min: 1, max: 6 }),
  })
  .chain(({ D, A }) => {
    const rows = D + 1
    const cols = A + 1
    // Generate rows * cols floats in [0, 1] used as decay factors
    return fc.array(fc.double({ min: 0, max: 1, noNaN: true }), {
      minLength: rows * cols,
      maxLength: rows * cols,
    }).map((factors) => {
      // Build matrix with monotonically non-increasing constraint
      const matrix: number[][] = []
      for (let i = 0; i < rows; i++) {
        matrix.push(new Array(cols).fill(0))
      }
      // matrix[0][0] = 1.0
      matrix[0][0] = 1.0
      // Fill first row: each cell ≤ cell to its left
      for (let j = 1; j < cols; j++) {
        matrix[0][j] = matrix[0][j - 1] * factors[j]
      }
      // Fill remaining rows
      for (let i = 1; i < rows; i++) {
        // First column: ≤ cell above
        matrix[i][0] = matrix[i - 1][0] * factors[i * cols]
        for (let j = 1; j < cols; j++) {
          // Must be ≤ cell above AND ≤ cell to the left
          const upperBound = Math.min(matrix[i - 1][j], matrix[i][j - 1])
          matrix[i][j] = upperBound * factors[i * cols + j]
        }
      }

      const damage_thresholds = Array.from({ length: rows }, (_, i) => i)
      const accuracy_thresholds = Array.from({ length: cols }, (_, j) => j)

      return { damage_thresholds, accuracy_thresholds, matrix }
    })
  })

// ---------------------------------------------------------------------------
// Property 1: Damage row extraction
// ---------------------------------------------------------------------------

describe('Property 1: Damage row extraction', () => {
  // Feature: joint-cumulative-display, Property 1: Damage row extraction
  it('for any threshold index X (1 ≤ X < damage_thresholds.length), joint data equals matrix[X][j] * 100 for each j', () => {
    // **Validates: Requirements 1.1, 5.1, 5.5**
    fc.assert(
      fc.property(
        jointPayloadArb.chain((payload) => {
          // Pick a random bar index X from 1 to damage_thresholds.length - 1
          const maxIndex = payload.damage_thresholds.length - 1
          return fc.record({
            payload: fc.constant(payload),
            barIndex: fc.integer({ min: 1, max: maxIndex }),
          })
        }),
        ({ payload, barIndex }) => {
          const result = extractJointData(payload, 'damage', barIndex)
          expect(result).not.toBeNull()
          if (!result) return

          const { jointData } = result
          const expectedRow = payload.matrix[barIndex]

          // jointData length should match accuracy_thresholds length
          expect(jointData.length).toBe(payload.accuracy_thresholds.length)

          // Index 0 is now P(=0): matrix[X][0]*100 - matrix[X][1]*100 (if ≥2 thresholds)
          // Index j≥1: matrix[X][j] * 100
          for (let j = 0; j < expectedRow.length; j++) {
            if (j === 0 && expectedRow.length >= 2) {
              const expected = Math.max(0, expectedRow[0] * 100 - expectedRow[1] * 100)
              expect(jointData[j]).toBeCloseTo(expected, 10)
            } else {
              expect(jointData[j]).toBeCloseTo(expectedRow[j] * 100, 10)
            }
          }
        },
      ),
      { numRuns: 100 },
    )
  })
})


// ---------------------------------------------------------------------------
// Property 2: Accuracy column extraction
// ---------------------------------------------------------------------------

describe('Property 2: Accuracy column extraction', () => {
  // Feature: joint-cumulative-display, Property 2: Accuracy column extraction
  it('for any threshold index Y (1 ≤ Y < accuracy_thresholds.length), joint data equals matrix[i][Y] * 100 for each i', () => {
    // **Validates: Requirements 1.2, 5.2, 5.5**
    fc.assert(
      fc.property(
        jointPayloadArb.chain((payload) => {
          // Pick a random bar index Y from 1 to accuracy_thresholds.length - 1
          const maxIndex = payload.accuracy_thresholds.length - 1
          return fc.record({
            payload: fc.constant(payload),
            barIndex: fc.integer({ min: 1, max: maxIndex }),
          })
        }),
        ({ payload, barIndex }) => {
          const result = extractJointData(payload, 'accuracy', barIndex)
          expect(result).not.toBeNull()
          if (!result) return

          const { jointData } = result

          // jointData length should match damage_thresholds length
          expect(jointData.length).toBe(payload.damage_thresholds.length)

          // Index 0 is now P(=0): matrix[0][Y]*100 - matrix[1][Y]*100 (if ≥2 thresholds)
          // Index i≥1: matrix[i][Y] * 100
          for (let i = 0; i < payload.matrix.length; i++) {
            if (i === 0 && payload.matrix.length >= 2) {
              const expected = Math.max(0, payload.matrix[0][barIndex] * 100 - payload.matrix[1][barIndex] * 100)
              expect(jointData[i]).toBeCloseTo(expected, 10)
            } else {
              expect(jointData[i]).toBeCloseTo(payload.matrix[i][barIndex] * 100, 10)
            }
          }
        },
      ),
      { numRuns: 100 },
    )
  })
})


// ---------------------------------------------------------------------------
// Property 3: Zero-damage joint computation
// ---------------------------------------------------------------------------

describe('Property 3: Zero-damage joint computation', () => {
  // Feature: joint-cumulative-display, Property 3: Zero-damage joint computation
  it('for any valid payload with ≥2 damage thresholds, =0 damage joint data equals Math.max(0, (matrix[0][j] - matrix[1][j]) * 100) for each j', () => {
    // **Validates: Requirements 1.3, 5.3**
    fc.assert(
      fc.property(
        jointPayloadArb,
        (payload) => {
          const result = extractJointData(payload, 'damage', 0)
          expect(result).not.toBeNull()
          if (!result) return

          const { jointData } = result

          // jointData length should match accuracy_thresholds length
          expect(jointData.length).toBe(payload.accuracy_thresholds.length)

          // Each value: for j=0, P(dmg=0 AND acc=0) = rawData[0] - rawData[1]
          // where rawData[j] = Math.max(0, (matrix[0][j] - matrix[1][j]) * 100)
          // For j≥1: Math.max(0, (matrix[0][j] - matrix[1][j]) * 100)
          for (let j = 0; j < payload.accuracy_thresholds.length; j++) {
            const raw_j = Math.max(0, (payload.matrix[0][j] - payload.matrix[1][j]) * 100)
            if (j === 0 && payload.accuracy_thresholds.length >= 2) {
              const raw_1 = Math.max(0, (payload.matrix[0][1] - payload.matrix[1][1]) * 100)
              const expected = Math.max(0, raw_j - raw_1)
              expect(jointData[j]).toBeCloseTo(expected, 10)
            } else {
              expect(jointData[j]).toBeCloseTo(raw_j, 10)
            }
          }
        },
      ),
      { numRuns: 100 },
    )
  })
})


// ---------------------------------------------------------------------------
// Property 4: Zero-accuracy joint computation
// ---------------------------------------------------------------------------

describe('Property 4: Zero-accuracy joint computation', () => {
  // Feature: joint-cumulative-display, Property 4: Zero-accuracy joint computation
  it('for any valid payload with ≥2 accuracy thresholds, =0 accuracy joint data equals Math.max(0, (matrix[i][0] - matrix[i][1]) * 100) for each i', () => {
    // **Validates: Requirements 1.4, 5.4**
    fc.assert(
      fc.property(
        jointPayloadArb,
        (payload) => {
          const result = extractJointData(payload, 'accuracy', 0)
          expect(result).not.toBeNull()
          if (!result) return

          const { jointData } = result

          // jointData length should match damage_thresholds length
          expect(jointData.length).toBe(payload.damage_thresholds.length)

          // Each value: for i=0, P(acc=0 AND dmg=0) = rawData[0] - rawData[1]
          // where rawData[i] = Math.max(0, (matrix[i][0] - matrix[i][1]) * 100)
          // For i≥1: Math.max(0, (matrix[i][0] - matrix[i][1]) * 100)
          for (let i = 0; i < payload.damage_thresholds.length; i++) {
            const raw_i = Math.max(0, (payload.matrix[i][0] - payload.matrix[i][1]) * 100)
            if (i === 0 && payload.damage_thresholds.length >= 2) {
              const raw_1 = Math.max(0, (payload.matrix[1][0] - payload.matrix[1][1]) * 100)
              const expected = Math.max(0, raw_i - raw_1)
              expect(jointData[i]).toBeCloseTo(expected, 10)
            } else {
              expect(jointData[i]).toBeCloseTo(raw_i, 10)
            }
          }
        },
      ),
      { numRuns: 100 },
    )
  })
})


// ---------------------------------------------------------------------------
// Property 5: Joint values non-negativity
// ---------------------------------------------------------------------------

describe('Property 5: Joint values non-negativity', () => {
  // Feature: joint-cumulative-display, Property 5: Joint values non-negativity
  it('for any valid monotonically non-increasing payload, all computed joint values (row, column, =0 damage, =0 accuracy) shall be ≥ 0', () => {
    // **Validates: Requirements 5.3, 5.4, 5.5**
    fc.assert(
      fc.property(
        jointPayloadArb,
        (payload) => {
          // Test row extraction: damage bars (barIndex 1 to damage_thresholds.length - 1)
          for (let x = 1; x < payload.damage_thresholds.length; x++) {
            const result = extractJointData(payload, 'damage', x)
            expect(result).not.toBeNull()
            if (result) {
              for (const val of result.jointData) {
                expect(val).toBeGreaterThanOrEqual(0)
              }
            }
          }

          // Test column extraction: accuracy bars (barIndex 1 to accuracy_thresholds.length - 1)
          for (let y = 1; y < payload.accuracy_thresholds.length; y++) {
            const result = extractJointData(payload, 'accuracy', y)
            expect(result).not.toBeNull()
            if (result) {
              for (const val of result.jointData) {
                expect(val).toBeGreaterThanOrEqual(0)
              }
            }
          }

          // Test =0 damage computation
          const zeroDamageResult = extractJointData(payload, 'damage', 0)
          expect(zeroDamageResult).not.toBeNull()
          if (zeroDamageResult) {
            for (const val of zeroDamageResult.jointData) {
              expect(val).toBeGreaterThanOrEqual(0)
            }
          }

          // Test =0 accuracy computation
          const zeroAccResult = extractJointData(payload, 'accuracy', 0)
          expect(zeroAccResult).not.toBeNull()
          if (zeroAccResult) {
            for (const val of zeroAccResult.jointData) {
              expect(val).toBeGreaterThanOrEqual(0)
            }
          }
        },
      ),
      { numRuns: 100 },
    )
  })
})


// ---------------------------------------------------------------------------
// Property 6: Label generation correctness
// ---------------------------------------------------------------------------

describe('Property 6: Label generation correctness', () => {
  // Feature: joint-cumulative-display, Property 6: Label generation correctness
  // **Validates: Requirements 3.1, 3.2, 3.4**

  it('for damage chart with barIndex ≥ 1, jointLabels are accuracy thresholds formatted as "≥{t}" and anchor label is "damage ≥ {T}"', () => {
    fc.assert(
      fc.property(
        jointPayloadArb.chain((payload) => {
          const maxIndex = payload.damage_thresholds.length - 1
          return fc.record({
            payload: fc.constant(payload),
            barIndex: fc.integer({ min: 1, max: maxIndex }),
          })
        }),
        ({ payload, barIndex }) => {
          const result = extractJointData(payload, 'damage', barIndex)
          expect(result).not.toBeNull()
          if (!result) return

          const { jointLabels, anchorThreshold, anchorIsZeroBar } = result

          // Cross-dimension labels should be accuracy thresholds formatted as "≥{t}"
          expect(jointLabels.length).toBe(payload.accuracy_thresholds.length)
          for (let j = 0; j < payload.accuracy_thresholds.length; j++) {
            expect(jointLabels[j]).toBe(`≥${payload.accuracy_thresholds[j]}`)
          }

          // anchorIsZeroBar should be false for barIndex ≥ 1
          expect(anchorIsZeroBar).toBe(false)

          // Anchor label should be "damage ≥ {T}"
          const anchorLabel = buildAnchorLabel('damage', anchorThreshold, anchorIsZeroBar)
          expect(anchorLabel).toBe(`damage ≥ ${anchorThreshold}`)
        },
      ),
      { numRuns: 100 },
    )
  })

  it('for accuracy chart with barIndex ≥ 1, jointLabels are damage thresholds formatted as "≥{t}" and anchor label is "acc ≥ {T}"', () => {
    fc.assert(
      fc.property(
        jointPayloadArb.chain((payload) => {
          const maxIndex = payload.accuracy_thresholds.length - 1
          return fc.record({
            payload: fc.constant(payload),
            barIndex: fc.integer({ min: 1, max: maxIndex }),
          })
        }),
        ({ payload, barIndex }) => {
          const result = extractJointData(payload, 'accuracy', barIndex)
          expect(result).not.toBeNull()
          if (!result) return

          const { jointLabels, anchorThreshold, anchorIsZeroBar } = result

          // Cross-dimension labels should be damage thresholds formatted as "≥{t}"
          expect(jointLabels.length).toBe(payload.damage_thresholds.length)
          for (let i = 0; i < payload.damage_thresholds.length; i++) {
            expect(jointLabels[i]).toBe(`≥${payload.damage_thresholds[i]}`)
          }

          // anchorIsZeroBar should be false for barIndex ≥ 1
          expect(anchorIsZeroBar).toBe(false)

          // Anchor label should be "acc ≥ {T}"
          const anchorLabel = buildAnchorLabel('accuracy', anchorThreshold, anchorIsZeroBar)
          expect(anchorLabel).toBe(`acc ≥ ${anchorThreshold}`)
        },
      ),
      { numRuns: 100 },
    )
  })

  it('for damage chart with barIndex 0, anchor label is "damage = 0"', () => {
    fc.assert(
      fc.property(
        jointPayloadArb,
        (payload) => {
          const result = extractJointData(payload, 'damage', 0)
          expect(result).not.toBeNull()
          if (!result) return

          const { anchorThreshold, anchorIsZeroBar } = result

          // anchorIsZeroBar should be true for barIndex 0
          expect(anchorIsZeroBar).toBe(true)
          expect(anchorThreshold).toBe(0)

          // Anchor label should be "damage = 0"
          const anchorLabel = buildAnchorLabel('damage', anchorThreshold, anchorIsZeroBar)
          expect(anchorLabel).toBe('damage = 0')
        },
      ),
      { numRuns: 100 },
    )
  })

  it('for accuracy chart with barIndex 0, anchor label is "acc = 0"', () => {
    fc.assert(
      fc.property(
        jointPayloadArb,
        (payload) => {
          const result = extractJointData(payload, 'accuracy', 0)
          expect(result).not.toBeNull()
          if (!result) return

          const { anchorThreshold, anchorIsZeroBar } = result

          // anchorIsZeroBar should be true for barIndex 0
          expect(anchorIsZeroBar).toBe(true)
          expect(anchorThreshold).toBe(0)

          // Anchor label should be "acc = 0"
          const anchorLabel = buildAnchorLabel('accuracy', anchorThreshold, anchorIsZeroBar)
          expect(anchorLabel).toBe('acc = 0')
        },
      ),
      { numRuns: 100 },
    )
  })
})
