import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import { encode, decode, CURRENT_VERSION } from '../../utils/reportCardEncoder'
import type { ReportCard } from '../../utils/reportCardEncoder'

// ---------------------------------------------------------------------------
// Shared arbitraries
//
// NOTE: All effect types and strategy names must be from the known token
// tables, since the compact descriptor encoder throws on unknown values.
// ---------------------------------------------------------------------------

const attackEffectTypeArb = fc.constantFrom(
  'reroll' as const,
  'cancel' as const,
  'add_dice' as const,
  'change_die' as const,
  'add_set_die' as const,
  'reroll_all' as const,
)

// Minimal attack effect arbitraries — only the type field is needed for
// round-trip tests; the encoder handles missing optional fields gracefully.
// For effects that require specific fields (change_die, add_set_die,
// reroll_all), we use dedicated arbitraries.
const knownFaceArb = fc.constantFrom(
  'R_hit', 'R_crit', 'R_acc', 'R_blank', 'R_hit+hit', 'R_hit+crit',
  'U_hit', 'U_crit', 'U_acc', 'U_blank', 'U_hit+hit', 'U_hit+crit',
  'B_hit', 'B_crit', 'B_acc', 'B_blank', 'B_hit+hit', 'B_hit+crit',
)
const colorAgnosticFaceArb = fc.constantFrom('hit', 'crit', 'acc')
const condAttrArb = fc.constantFrom('damage' as const, 'crit' as const, 'acc' as const, 'blank' as const)
const condOpArb = fc.constantFrom('lte' as const, 'lt' as const, 'gte' as const, 'gt' as const, 'eq' as const, 'neq' as const)

const simpleAttackEffectArb = fc.oneof(
  // reroll / cancel
  fc.record({
    type: fc.constantFrom('reroll' as const, 'cancel' as const),
    count: fc.oneof(fc.constant('any' as const), fc.nat({ max: 5 })),
    applicable_results: fc.array(knownFaceArb, { maxLength: 4 }),
  }),
  // add_dice (fixed)
  fc.record({
    type: fc.constant('add_dice' as const),
    dice_to_add: fc.record({
      red: fc.nat({ max: 3 }),
      blue: fc.nat({ max: 3 }),
      black: fc.nat({ max: 3 }),
    }),
  }),
  // change_die
  fc.record({
    type: fc.constant('change_die' as const),
    applicable_results: fc.array(knownFaceArb, { minLength: 1, maxLength: 3 }),
    target_result: colorAgnosticFaceArb,
  }),
  // add_set_die
  fc.record({
    type: fc.constant('add_set_die' as const),
    target_result: knownFaceArb,
  }),
  // reroll_all
  fc.record({
    type: fc.constant('reroll_all' as const),
    condition: fc.record({
      attribute: condAttrArb,
      operator: condOpArb,
      threshold: fc.nat({ max: 10 }),
    }),
  }),
)

const defenseEffectTypeArb = fc.constantFrom(
  'defense_reroll' as const,
  'defense_cancel' as const,
  'reduce_damage' as const,
  'divide_damage' as const,
)

const simpleDefenseEffectArb = fc.oneof(
  fc.record({
    type: fc.constant('defense_reroll' as const),
    count: fc.integer({ min: 1, max: 5 }),
    mode: fc.constantFrom('safe' as const, 'gamble' as const),
  }),
  fc.record({
    type: fc.constant('defense_cancel' as const),
    count: fc.integer({ min: 1, max: 5 }),
  }),
  fc.record({
    type: fc.constant('reduce_damage' as const),
    amount: fc.integer({ min: 1, max: 5 }),
  }),
  fc.record({
    type: fc.constant('divide_damage' as const),
  }),
)

const knownStrategyArb = fc.constantFrom('max_damage', 'max_accuracy', 'max_crits', 'max_doubles')

const dicePoolArb = fc.record({
  red: fc.nat({ max: 5 }),
  blue: fc.nat({ max: 5 }),
  black: fc.nat({ max: 5 }),
  type: fc.constantFrom('ship', 'squad') as fc.Arbitrary<'ship' | 'squad'>,
})

const reportCardArb: fc.Arbitrary<ReportCard> = fc.record({
  request: fc.record({
    dice_pool: dicePoolArb,
    pipeline: fc.array(simpleAttackEffectArb, { maxLength: 4 }),
    strategies: fc.array(knownStrategyArb, { minLength: 1, maxLength: 3 }),
    precision: fc.constantFrom('normal', 'high') as fc.Arbitrary<'normal' | 'high'>,
  }),
  bomber: fc.boolean(),
})

// Typical config arbitrary for Property 2
const typicalDicePoolArb = fc
  .record({
    red: fc.nat({ max: 3 }),
    blue: fc.nat({ max: 3 }),
    black: fc.nat({ max: 3 }),
    type: fc.constantFrom('ship', 'squad') as fc.Arbitrary<'ship' | 'squad'>,
  })
  .filter((dp) => dp.red + dp.blue + dp.black >= 3 && dp.red + dp.blue + dp.black <= 5)

const typicalReportCardArb: fc.Arbitrary<ReportCard> = fc.record({
  request: fc.record({
    dice_pool: typicalDicePoolArb,
    pipeline: fc.array(simpleAttackEffectArb, { minLength: 2, maxLength: 4 }),
    strategies: fc.constant(['max_damage']),
    precision: fc.constant('high' as const),
    defense_pipeline: fc.array(simpleDefenseEffectArb, { minLength: 1, maxLength: 2 }),
  }),
  bomber: fc.boolean(),
})

// ---------------------------------------------------------------------------
// Helper: build a descriptor string, compress it, and base64url-encode it.
// Used by tests that need to craft specific payloads (e.g. future versions,
// invalid fields) without going through the public encode() API.
// ---------------------------------------------------------------------------

async function compressDescriptor(descriptor: string): Promise<string> {
  const inputBytes = new TextEncoder().encode(descriptor)
  const cs = new CompressionStream('deflate-raw')
  const writer = cs.writable.getWriter()
  const writePromise = writer.write(inputBytes).then(() => writer.close())
  writePromise.catch(() => { /* error surfaces via readable */ })

  const reader = cs.readable.getReader()
  const chunks: Uint8Array[] = []
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    chunks.push(value)
  }
  const totalLength = chunks.reduce((sum, c) => sum + c.length, 0)
  const compressed = new Uint8Array(totalLength)
  let offset = 0
  for (const chunk of chunks) {
    compressed.set(chunk, offset)
    offset += chunk.length
  }

  let binary = ''
  for (let i = 0; i < compressed.length; i++) {
    binary += String.fromCharCode(compressed[i])
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

// ---------------------------------------------------------------------------
// Helper: decompress a base64url string and return the raw descriptor string.
// Used by Property 4 to verify the version prefix is present.
// ---------------------------------------------------------------------------

async function decompressToString(encoded: string): Promise<string> {
  const base64 = encoded.replace(/-/g, '+').replace(/_/g, '/')
  const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4)
  const binary = atob(padded)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }

  const ds = new DecompressionStream('deflate-raw')
  const writer = ds.writable.getWriter()
  writer.write(bytes)
  writer.close()

  const reader = ds.readable.getReader()
  const chunks: Uint8Array[] = []
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    chunks.push(value)
  }
  const totalLength = chunks.reduce((sum, c) => sum + c.length, 0)
  const decompressed = new Uint8Array(totalLength)
  let offset = 0
  for (const chunk of chunks) {
    decompressed.set(chunk, offset)
    offset += chunk.length
  }

  return new TextDecoder().decode(decompressed)
}

// ---------------------------------------------------------------------------
// Known fixture
// ---------------------------------------------------------------------------

const knownCard: ReportCard = {
  request: {
    dice_pool: { red: 3, blue: 1, black: 0, type: 'ship' },
    pipeline: [
      { type: 'reroll', count: 'any', applicable_results: ['R_blank', 'U_blank', 'B_blank'] },
      { type: 'cancel', count: 2, applicable_results: ['R_blank'] },
    ],
    strategies: ['max_damage'],
    precision: 'high',
  },
  bomber: false,
}

// ---------------------------------------------------------------------------
// 2.1 Unit tests
// ---------------------------------------------------------------------------

describe('reportCardEncoder — unit tests', () => {
  it('encodes a known ReportCard to a non-empty URL-safe string', async () => {
    const result = await encode(knownCard)
    expect(result).toBeTruthy()
    expect(result).toMatch(/^[A-Za-z0-9_-]+$/)
  })

  it('decodes the known encoded string back to the original ReportCard', async () => {
    const encoded = await encode(knownCard)
    const result = await decode(encoded)
    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.value).toEqual(knownCard)
    }
  })

  it('returns { ok: false } when decoding an empty string', async () => {
    const result = await decode('')
    expect(result.ok).toBe(false)
  })

  it('returns { ok: false } when decoding a valid base64url string that is not valid compressed data', async () => {
    // "hello" base64url-encoded — valid base64 but not deflate-raw compressed data
    const notCompressed = btoa('hello world not compressed').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
    const result = await decode(notCompressed)
    expect(result.ok).toBe(false)
  })

  it('returns { ok: false } with "newer version" in the error when version > CURRENT_VERSION', async () => {
    // Build a future-version descriptor: v<CURRENT_VERSION+1>|...
    const futureVersion = CURRENT_VERSION + 1
    const descriptor = `v${futureVersion}|r1b0k0s|0|md|h|||`
    const encoded = await compressDescriptor(descriptor)
    const result = await decode(encoded)
    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.error.toLowerCase()).toContain('newer version')
    }
  })

  it('returns { ok: false } with a validation error when dice pool has negative counts', async () => {
    // The pool regex r(\d+)b(\d+)k(\d+) only matches digits, so negative
    // counts produce a parse error. Use a descriptor with an invalid pool token.
    const descriptor = `v${CURRENT_VERSION}|r-1b0k0s|0|md|h|||`
    const encoded = await compressDescriptor(descriptor)
    const result = await decode(encoded)
    expect(result.ok).toBe(false)
    if (!result.ok) {
      // Error should mention the pool or descriptor being invalid
      expect(result.error.length).toBeGreaterThan(0)
    }
  })
})

// ---------------------------------------------------------------------------
// 2.2 Property 1: Encoding produces URL-safe output
// ---------------------------------------------------------------------------

describe('Property 1: Encoding produces URL-safe output', () => {
  // Feature: shareable-report-url, Property 1: Encoding produces URL-safe output
  it('encoded string matches /^[A-Za-z0-9_-]+$/ for all valid ReportCards', async () => {
    // Validates: Requirements 1.1
    await fc.assert(
      fc.asyncProperty(reportCardArb, async (card) => {
        const encoded = await encode(card)
        expect(encoded).toMatch(/^[A-Za-z0-9_-]+$/)
      }),
      { numRuns: 25 },
    )
  })
})

// ---------------------------------------------------------------------------
// 2.3 Property 2: Typical config stays under 400 characters
// ---------------------------------------------------------------------------

describe('Property 2: Typical config stays under 400 characters', () => {
  // Feature: shareable-report-url, Property 2: Typical config stays under 400 characters
  it('encoded length <= 400 for typical configs', async () => {
    // Validates: Requirements 1.2
    await fc.assert(
      fc.asyncProperty(typicalReportCardArb, async (card) => {
        const encoded = await encode(card)
        expect(encoded.length).toBeLessThanOrEqual(400)
      }),
      { numRuns: 25 },
    )
  })
})

// ---------------------------------------------------------------------------
// 2.4 Property 3: Round-trip encoding preserves all fields
// ---------------------------------------------------------------------------

describe('Property 3: Round-trip encoding preserves all fields', () => {
  // Feature: shareable-report-url, Property 3: Round-trip encoding preserves all fields
  it('decode(encode(card)) deeply equals the original card', async () => {
    // Validates: Requirements 1.3, 1.4, 1.5, 2.1, 5.2
    await fc.assert(
      fc.asyncProperty(reportCardArb, async (card) => {
        const encoded = await encode(card)
        const result = await decode(encoded)
        expect(result.ok).toBe(true)
        if (result.ok) {
          expect(result.value).toEqual(card)
        }
      }),
      { numRuns: 25 },
    )
  })
})

// ---------------------------------------------------------------------------
// 2.5 Property 4: Version field is always present in encoded payload
// ---------------------------------------------------------------------------

describe('Property 4: Version field is always present in encoded payload', () => {
  // Feature: shareable-report-url, Property 4: Version field is always present in encoded payload
  it('raw decompressed descriptor always starts with a version prefix "vN|"', async () => {
    // Validates: Requirements 1.4, 5.1
    await fc.assert(
      fc.asyncProperty(reportCardArb, async (card) => {
        const encoded = await encode(card)
        const descriptor = await decompressToString(encoded)
        // Descriptor must start with "v<number>|"
        expect(descriptor).toMatch(/^v\d+\|/)
        // Extract the version number and verify it is numeric
        const versionStr = descriptor.slice(1, descriptor.indexOf('|'))
        const versionNum = parseInt(versionStr, 10)
        expect(isNaN(versionNum)).toBe(false)
      }),
      { numRuns: 25 },
    )
  })
})

// ---------------------------------------------------------------------------
// 2.6 Property 5: Malformed inputs return errors, never throw
// ---------------------------------------------------------------------------

describe('Property 5: Malformed inputs return errors, never throw', () => {
  // Feature: shareable-report-url, Property 5: Malformed inputs return errors, never throw
  it('decode(s) always returns { ok: false, error: string } for arbitrary strings', async () => {
    // Validates: Requirements 2.2
    await fc.assert(
      fc.asyncProperty(fc.string(), async (s) => {
        const result = await decode(s)
        expect(result.ok).toBe(false)
        if (!result.ok) {
          expect(typeof result.error).toBe('string')
          expect(result.error.length).toBeGreaterThan(0)
        }
      }),
      { numRuns: 25 },
    )
  })
})

// ---------------------------------------------------------------------------
// 2.7 Property 6: Schema-invalid payloads return validation errors
// ---------------------------------------------------------------------------

describe('Property 6: Schema-invalid payloads return validation errors', () => {
  // Feature: shareable-report-url, Property 6: Schema-invalid payloads return validation errors
  it('decode returns { ok: false, error } for descriptors with invalid field values', async () => {
    // Validates: Requirements 2.3
    // Generate invalid descriptors: bad pool token or unknown effect token
    const invalidPoolArb = fc.record({
      red: fc.integer({ min: -100, max: -1 }),
      blue: fc.nat({ max: 5 }),
      black: fc.nat({ max: 5 }),
    }).map((dp) =>
      // Negative counts break the pool regex — use a clearly invalid pool string
      `v${CURRENT_VERSION}|rXb${dp.blue}k${dp.black}s|0|md|h|||`,
    )

    const unknownEffectTokenArb = fc
      .string({ minLength: 2, maxLength: 4 })
      .filter((s) => /^[a-z]+$/.test(s) && !['rr', 'cn', 'ad', 'cd', 'sd', 'ra'].includes(s))
      .map((tok) =>
        `v${CURRENT_VERSION}|r1b0k0s|0|md|h|${tok}||`,
      )

    const invalidDescriptorArb = fc.oneof(invalidPoolArb, unknownEffectTokenArb)

    await fc.assert(
      fc.asyncProperty(invalidDescriptorArb, async (descriptor) => {
        const encoded = await compressDescriptor(descriptor)
        const result = await decode(encoded)
        expect(result.ok).toBe(false)
        if (!result.ok) {
          expect(typeof result.error).toBe('string')
          expect(result.error.length).toBeGreaterThan(0)
        }
      }),
      { numRuns: 25 },
    )
  })
})

// ---------------------------------------------------------------------------
// 2.8 Property 11: Future-version payloads return a descriptive error
// ---------------------------------------------------------------------------

describe('Property 11: Future-version payloads return a descriptive error', () => {
  // Feature: shareable-report-url, Property 11: Future-version payloads return a descriptive error
  it('decode returns { ok: false } with a "newer version" error for v > CURRENT_VERSION', async () => {
    // Validates: Requirements 5.3
    await fc.assert(
      fc.asyncProperty(
        reportCardArb,
        fc.integer({ min: 1, max: 100 }),
        async (card, versionOffset) => {
          const futureVersion = CURRENT_VERSION + versionOffset
          // Build a descriptor with the future version prefix
          const encoded = await encode(card)
          const originalDescriptor = await decompressToString(encoded)
          // Replace the version prefix (e.g. "v2|" → "v999|")
          const futureDescriptor = originalDescriptor.replace(/^v\d+\|/, `v${futureVersion}|`)
          const futureEncoded = await compressDescriptor(futureDescriptor)
          const result = await decode(futureEncoded)
          expect(result.ok).toBe(false)
          if (!result.ok) {
            expect(result.error.toLowerCase()).toContain('newer version')
          }
        },
      ),
      { numRuns: 25 },
    )
  })
})
