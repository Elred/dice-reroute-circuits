/**
 * reportCardEncoder.ts
 *
 * Encodes a ReportCard to a compact URL-safe string using a positional
 * descriptor format (no JSON field names in the payload), then compresses
 * with deflate-raw and base64url-encodes the result.
 *
 * No Vue or Pinia dependencies.
 *
 * ==========================================================================
 * DESCRIPTOR FORMAT  (schema version 2)
 * ==========================================================================
 *
 * The descriptor is a pipe-delimited string:
 *
 *   v2|<pool>|<bomber>|<strategies>|<precision>|<pipeline>|<defense_pipeline>|<label>
 *
 * Fields:
 *   v2                — literal schema version prefix
 *   <pool>            — dice pool: "r<R>b<B>k<K><T>"
 *                         R = red count, B = blue count, K = black count
 *                         T = "s" (ship) or "q" (squad)
 *                         e.g. "r3b1k0s"
 *   <bomber>          — "1" (true) or "0" (false)
 *   <strategies>      — comma-separated strategy tokens (see STRATEGY TOKENS)
 *   <precision>       — "h" (high) or "n" (normal)
 *   <pipeline>        — comma-separated attack effect tokens (see ATTACK EFFECT TOKENS)
 *                         empty string if no effects
 *   <defense_pipeline>— comma-separated defense effect tokens (see DEFENSE EFFECT TOKENS)
 *                         empty string if no effects
 *   <label>           — pool_label string, or empty string if absent
 *
 * Example (3R 1B ship, reroll any blank, max_damage, high, no defense, no label):
 *   v2|r3b1k0s|0|md|h|rr:*:Rb||
 *
 * ==========================================================================
 * TOKEN TABLES
 * ==========================================================================
 *
 * STRATEGY TOKENS
 * ---------------
 *   max_damage    → md
 *   max_accuracy  → ma
 *   max_crits     → mc
 *   max_doubles   → mx
 *
 * PRECISION TOKENS
 * ----------------
 *   high          → h
 *   normal        → n
 *
 * DICE TYPE TOKENS
 * ----------------
 *   ship          → s
 *   squad         → q
 *
 * ATTACK EFFECT TYPE TOKENS
 * -------------------------
 *   reroll        → rr
 *   cancel        → cn
 *   add_dice      → ad
 *   change_die    → cd
 *   add_set_die   → sd
 *   reroll_all    → ra
 *
 * DEFENSE EFFECT TYPE TOKENS
 * --------------------------
 *   defense_reroll  → dr
 *   defense_cancel  → dc
 *   reduce_damage   → rd
 *   divide_damage   → dd
 *
 * DIE FACE TOKENS  (color prefix + face suffix)
 * -----------------------------------------------
 * Color prefixes:
 *   Red   → R
 *   Blue  → U
 *   Black → B
 *
 * Face suffixes:
 *   hit       → h
 *   crit      → c
 *   acc       → a
 *   blank     → b
 *   hit+hit   → hh
 *   hit+crit  → hc
 *
 * Combined examples:
 *   R_hit       → Rh
 *   R_crit      → Rc
 *   R_acc       → Ra
 *   R_blank     → Rb
 *   R_hit+hit   → Rhh
 *   R_hit+crit  → Rhc
 *   U_hit       → Uh
 *   U_crit      → Uc
 *   U_acc       → Ua
 *   U_blank     → Ub
 *   U_hit+hit   → Uhh
 *   U_hit+crit  → Uhc
 *   B_hit       → Bh
 *   B_crit      → Bc
 *   B_acc       → Ba
 *   B_blank     → Bb
 *   B_hit+hit   → Bhh
 *   B_hit+crit  → Bhc
 *
 * Color-agnostic faces (used in change_die target_result):
 *   hit         → h
 *   crit        → c
 *   acc         → a
 *
 * CONDITION ATTRIBUTE TOKENS
 * --------------------------
 *   damage      → dmg
 *   crit        → crt
 *   acc         → acc
 *   blank       → blk
 *
 * CONDITION OPERATOR TOKENS
 * -------------------------
 *   lte         → lte
 *   lt          → lt
 *   gte         → gte
 *   gt          → gt
 *   eq          → eq
 *   neq         → neq
 *
 * DEFENSE REROLL MODE TOKENS
 * --------------------------
 *   safe        → s
 *   gamble      → g
 *
 * ==========================================================================
 * ATTACK EFFECT SERIALIZATION
 * ==========================================================================
 *
 * Each attack effect is serialized as a colon-delimited token string.
 * Only present fields are included; optional fields are omitted when absent.
 *
 *   reroll / cancel:
 *     <type>:<count>:<results>[:<face_condition>]
 *     count: integer or "*" (any)
 *     results: comma-separated face tokens joined with "+"
 *     face_condition: face token, omitted if null/absent
 *     e.g. "rr:*:Rb+Ub+Bb"  (reroll any blank of any color)
 *          "cn:2:Rb"          (cancel up to 2 red blanks)
 *
 *   add_dice (fixed counts):
 *     ad:r<R>b<B>k<K>[:<face_condition>]
 *     e.g. "ad:r1b0k0"
 *
 *   add_dice (color_in_pool):
 *     ad:pool<N>:<priority>[:<face_condition>]
 *     N = count (integer >= 1; "pool" alone means count=1 for backward compat)
 *     priority: color tokens joined with "+" in priority order
 *     e.g. "ad:pool1:black+blue+red"   (add 1 die from pool)
 *          "ad:pool2:black+blue+red"   (add 2 dice from pool)
 *
 *   change_die:
 *     cd:<results>:<target>
 *     results: face tokens joined with "+"
 *     target: face token
 *     e.g. "cd:Rb+Ub:h"
 *
 *   add_set_die:
 *     sd:<target>[:<face_condition>]
 *     e.g. "sd:Rc"
 *
 *   reroll_all:
 *     ra:<attr>:<op>:<threshold>
 *     e.g. "ra:dmg:lte:3"
 *
 * ==========================================================================
 * DEFENSE EFFECT SERIALIZATION
 * ==========================================================================
 *
 *   defense_reroll:
 *     dr:<count>:<mode>[:<results>]
 *     results: face tokens joined with "+", omitted if absent
 *     e.g. "dr:2:s"  (defense reroll 2, safe mode, all results)
 *          "dr:1:g:Rh+Rc"
 *
 *   defense_cancel:
 *     dc:<count>[:<results>]
 *     e.g. "dc:1"
 *
 *   reduce_damage:
 *     rd:<amount>
 *     e.g. "rd:2"
 *
 *   divide_damage:
 *     dd
 *
 * ==========================================================================
 * UNKNOWN / PASS-THROUGH STRATEGIES
 * ==========================================================================
 *
 * Strategies not in the known token table are passed through as-is (the raw
 * strategy name string). This preserves forward-compatibility with new
 * strategies added to the backend without requiring an encoder version bump.
 *
 */

import type { ReportRequest, AttackEffect, DefenseEffect, Condition } from '../types/api'

// ---------------------------------------------------------------------------
// Public constants & types
// ---------------------------------------------------------------------------

/** Schema version embedded in every payload. Increment when the shape changes. */
export const CURRENT_VERSION = 2

/**
 * A ReportCard is the full shareable unit: the ReportRequest plus the bomber flag.
 */
export interface ReportCard {
  request: ReportRequest
  bomber: boolean
}

/** Discriminated union result for encode (exported for consumers) */
export type EncodeResult = { ok: true; value: string }

/** Discriminated union result for decode — never throws, always returns ok/error */
export type DecodeResult = { ok: true; value: ReportCard } | { ok: false; error: string }

// ---------------------------------------------------------------------------
// Token tables
// ---------------------------------------------------------------------------

const STRATEGY_TO_TOKEN: Record<string, string> = {
  max_damage: 'md',
  max_accuracy: 'ma',
  max_crits: 'mc',
  max_doubles: 'mx',
}
const TOKEN_TO_STRATEGY: Record<string, string> = Object.fromEntries(
  Object.entries(STRATEGY_TO_TOKEN).map(([k, v]) => [v, k]),
)

const ATTACK_TYPE_TO_TOKEN: Record<string, string> = {
  reroll: 'rr',
  cancel: 'cn',
  add_dice: 'ad',
  change_die: 'cd',
  add_set_die: 'sd',
  reroll_all: 'ra',
}
const TOKEN_TO_ATTACK_TYPE: Record<string, string> = Object.fromEntries(
  Object.entries(ATTACK_TYPE_TO_TOKEN).map(([k, v]) => [v, k]),
)

const DEFENSE_TYPE_TO_TOKEN: Record<string, string> = {
  defense_reroll: 'dr',
  defense_cancel: 'dc',
  reduce_damage: 'rd',
  divide_damage: 'dd',
}
const TOKEN_TO_DEFENSE_TYPE: Record<string, string> = Object.fromEntries(
  Object.entries(DEFENSE_TYPE_TO_TOKEN).map(([k, v]) => [v, k]),
)

// Die face full name → compact token
const FACE_TO_TOKEN: Record<string, string> = {
  R_hit: 'Rh', R_crit: 'Rc', R_acc: 'Ra', R_blank: 'Rb',
  'R_hit+hit': 'Rhh', 'R_hit+crit': 'Rhc',
  U_hit: 'Uh', U_crit: 'Uc', U_acc: 'Ua', U_blank: 'Ub',
  'U_hit+hit': 'Uhh', 'U_hit+crit': 'Uhc',
  B_hit: 'Bh', B_crit: 'Bc', B_acc: 'Ba', B_blank: 'Bb',
  'B_hit+hit': 'Bhh', 'B_hit+crit': 'Bhc',
  // Color-agnostic faces (used in change_die target_result)
  hit: 'h', crit: 'c', acc: 'a',
}
const TOKEN_TO_FACE: Record<string, string> = Object.fromEntries(
  Object.entries(FACE_TO_TOKEN).map(([k, v]) => [v, k]),
)

const COND_ATTR_TO_TOKEN: Record<string, string> = {
  damage: 'dmg', crit: 'crt', acc: 'acc', blank: 'blk',
}
const TOKEN_TO_COND_ATTR: Record<string, string> = Object.fromEntries(
  Object.entries(COND_ATTR_TO_TOKEN).map(([k, v]) => [v, k]),
)

// Condition operators are kept as-is (already short)
const KNOWN_OPERATORS = new Set(['lte', 'lt', 'gte', 'gt', 'eq', 'neq'])

// ---------------------------------------------------------------------------
// Internal helpers — stream compression
// ---------------------------------------------------------------------------

async function collectStream(stream: ReadableStream<Uint8Array>): Promise<Uint8Array> {
  const reader = stream.getReader()
  const chunks: Uint8Array[] = []
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    chunks.push(value)
  }
  const totalLength = chunks.reduce((sum, c) => sum + c.length, 0)
  const result = new Uint8Array(totalLength)
  let offset = 0
  for (const chunk of chunks) {
    result.set(chunk, offset)
    offset += chunk.length
  }
  return result
}

function bytesToBase64url(bytes: Uint8Array): string {
  let binary = ''
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

function base64urlToBytes(encoded: string): Uint8Array {
  const base64 = encoded.replace(/-/g, '+').replace(/_/g, '/')
  const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4)
  const binary = atob(padded)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes
}

// ---------------------------------------------------------------------------
// Descriptor serialization helpers
// ---------------------------------------------------------------------------

function encodeFace(face: string): string {
  const tok = FACE_TO_TOKEN[face]
  if (!tok) throw new Error(`Unknown die face: '${face}'`)
  return tok
}

function encodeFaces(faces: string[]): string {
  return faces.map(encodeFace).join('+')
}

function encodeAttackEffect(e: AttackEffect): string {
  const t = ATTACK_TYPE_TO_TOKEN[e.type]
  if (!t) throw new Error(`Unknown attack effect type: '${e.type}'`)

  if (e.type === 'reroll' || e.type === 'cancel') {
    const count = e.count === 'any' || e.count === undefined ? '*' : String(e.count)
    const results = encodeFaces(e.applicable_results ?? [])
    const parts = [t, count, results]
    if (e.face_condition) parts.push(encodeFace(e.face_condition))
    return parts.join(':')
  }

  if (e.type === 'add_dice') {
    if (e.color_in_pool) {
      const count = e.count && e.count !== 'any' && (e.count as number) > 1 ? String(e.count) : '1'
      const priority = (e.color_priority ?? ['black', 'blue', 'red']).join('+')
      const parts = [t, `pool${count}`, priority]
      if (e.face_condition) parts.push(encodeFace(e.face_condition))
      return parts.join(':')
    } else {
      const d = e.dice_to_add ?? { red: 0, blue: 0, black: 0 }
      const diceStr = `r${d.red}b${d.blue}k${d.black}`
      const parts = [t, diceStr]
      if (e.face_condition) parts.push(encodeFace(e.face_condition))
      return parts.join(':')
    }
  }

  if (e.type === 'change_die') {
    const results = encodeFaces(e.applicable_results ?? [])
    const target = encodeFace(e.target_result ?? '')
    return [t, results, target].join(':')
  }

  if (e.type === 'add_set_die') {
    const target = encodeFace(e.target_result ?? '')
    const parts = [t, target]
    if (e.face_condition) parts.push(encodeFace(e.face_condition))
    return parts.join(':')
  }

  if (e.type === 'reroll_all') {
    const cond = e.condition
    if (!cond) throw new Error('reroll_all requires a condition')
    const attr = COND_ATTR_TO_TOKEN[cond.attribute]
    if (!attr) throw new Error(`Unknown condition attribute: '${cond.attribute}'`)
    return [t, attr, cond.operator, String(cond.threshold)].join(':')
  }

  throw new Error(`Unhandled attack effect type: '${e.type}'`)
}

function encodeDefenseEffect(e: DefenseEffect): string {
  const t = DEFENSE_TYPE_TO_TOKEN[e.type]
  if (!t) throw new Error(`Unknown defense effect type: '${e.type}'`)

  if (e.type === 'defense_reroll') {
    const mode = e.mode === 'gamble' ? 'g' : 's'
    const parts = [t, String(e.count ?? 1), mode]
    if (e.applicable_results && e.applicable_results.length > 0) {
      parts.push(encodeFaces(e.applicable_results))
    }
    return parts.join(':')
  }

  if (e.type === 'defense_cancel') {
    const parts = [t, String(e.count ?? 1)]
    if (e.applicable_results && e.applicable_results.length > 0) {
      parts.push(encodeFaces(e.applicable_results))
    }
    return parts.join(':')
  }

  if (e.type === 'reduce_damage') {
    return [t, String(e.amount ?? 1)].join(':')
  }

  if (e.type === 'divide_damage') {
    return t
  }

  throw new Error(`Unhandled defense effect type: '${e.type}'`)
}

function buildDescriptor(card: ReportCard): string {
  const { request, bomber } = card
  const dp = request.dice_pool
  const pool = `r${dp.red}b${dp.blue}k${dp.black}${dp.type === 'ship' ? 's' : 'q'}`
  const bomberToken = bomber ? '1' : '0'
  const strategies = request.strategies
    .map((s) => STRATEGY_TO_TOKEN[s] ?? s)
    .join(',')
  const precision = (request.precision ?? 'high') === 'high' ? 'h' : 'n'
  const pipeline = (request.pipeline ?? []).map(encodeAttackEffect).join(',')
  const defensePipeline = (request.defense_pipeline ?? []).map(encodeDefenseEffect).join(',')
  const label = request.pool_label ?? ''

  return `v2|${pool}|${bomberToken}|${strategies}|${precision}|${pipeline}|${defensePipeline}|${label}`
}

// ---------------------------------------------------------------------------
// Descriptor deserialization helpers
// ---------------------------------------------------------------------------

function decodeFace(tok: string): string {
  const face = TOKEN_TO_FACE[tok]
  if (!face) throw new Error(`Unknown face token: '${tok}'`)
  return face
}

function decodeFaces(joined: string): string[] {
  if (!joined) return []
  return joined.split('+').map(decodeFace)
}

function decodeAttackEffect(token: string): AttackEffect {
  const parts = token.split(':')
  const typeTok = parts[0]
  const fullType = TOKEN_TO_ATTACK_TYPE[typeTok]
  if (!fullType) throw new Error(`Unknown attack effect token: '${typeTok}'`)

  if (fullType === 'reroll' || fullType === 'cancel') {
    const count: number | 'any' = parts[1] === '*' ? 'any' : parseInt(parts[1], 10)
    const applicable_results = decodeFaces(parts[2] ?? '')
    const effect: AttackEffect = { type: fullType as 'reroll' | 'cancel', count, applicable_results }
    if (parts[3]) effect.face_condition = decodeFace(parts[3])
    return effect
  }

  if (fullType === 'add_dice') {
    if (parts[1].startsWith('pool')) {
      const countStr = parts[1].slice(4) // everything after "pool"
      const count = countStr ? parseInt(countStr, 10) : 1
      const priority = (parts[2] ?? 'black+blue+red').split('+') as [string, string, string]
      const effect: AttackEffect = {
        type: 'add_dice',
        count: count > 1 ? count : undefined,
        dice_to_add: { red: 0, blue: 0, black: 0 },
        color_in_pool: true,
        color_priority: priority,
      }
      if (parts[3]) effect.face_condition = decodeFace(parts[3])
      return effect
    } else {
      const m = (parts[1] ?? '').match(/^r(\d+)b(\d+)k(\d+)$/)
      if (!m) throw new Error(`Invalid add_dice dice string: '${parts[1]}'`)
      const effect: AttackEffect = {
        type: 'add_dice',
        dice_to_add: { red: parseInt(m[1], 10), blue: parseInt(m[2], 10), black: parseInt(m[3], 10) },
      }
      if (parts[2]) effect.face_condition = decodeFace(parts[2])
      return effect
    }
  }

  if (fullType === 'change_die') {
    const applicable_results = decodeFaces(parts[1] ?? '')
    const target_result = decodeFace(parts[2] ?? '')
    return { type: 'change_die', applicable_results, target_result }
  }

  if (fullType === 'add_set_die') {
    const target_result = decodeFace(parts[1] ?? '')
    const effect: AttackEffect = { type: 'add_set_die', target_result }
    if (parts[2]) effect.face_condition = decodeFace(parts[2])
    return effect
  }

  if (fullType === 'reroll_all') {
    const attr = TOKEN_TO_COND_ATTR[parts[1]]
    if (!attr) throw new Error(`Unknown condition attribute token: '${parts[1]}'`)
    const op = parts[2]
    if (!KNOWN_OPERATORS.has(op)) throw new Error(`Unknown condition operator: '${op}'`)
    const threshold = parseInt(parts[3], 10)
    if (isNaN(threshold)) throw new Error(`Invalid condition threshold: '${parts[3]}'`)
    const condition: Condition = {
      attribute: attr as Condition['attribute'],
      operator: op as Condition['operator'],
      threshold,
    }
    return { type: 'reroll_all', condition }
  }

  throw new Error(`Unhandled attack effect token: '${typeTok}'`)
}

function decodeDefenseEffect(token: string): DefenseEffect {
  const parts = token.split(':')
  const typeTok = parts[0]
  const fullType = TOKEN_TO_DEFENSE_TYPE[typeTok]
  if (!fullType) throw new Error(`Unknown defense effect token: '${typeTok}'`)

  if (fullType === 'defense_reroll') {
    const count = parseInt(parts[1], 10)
    if (isNaN(count) || count < 1) throw new Error(`Invalid defense_reroll count: '${parts[1]}'`)
    const mode: 'safe' | 'gamble' = parts[2] === 'g' ? 'gamble' : 'safe'
    const effect: DefenseEffect = { type: 'defense_reroll', count, mode }
    if (parts[3]) effect.applicable_results = decodeFaces(parts[3])
    return effect
  }

  if (fullType === 'defense_cancel') {
    const count = parseInt(parts[1], 10)
    if (isNaN(count) || count < 1) throw new Error(`Invalid defense_cancel count: '${parts[1]}'`)
    const effect: DefenseEffect = { type: 'defense_cancel', count }
    if (parts[2]) effect.applicable_results = decodeFaces(parts[2])
    return effect
  }

  if (fullType === 'reduce_damage') {
    const amount = parseInt(parts[1], 10)
    if (isNaN(amount) || amount < 1) throw new Error(`Invalid reduce_damage amount: '${parts[1]}'`)
    return { type: 'reduce_damage', amount }
  }

  if (fullType === 'divide_damage') {
    return { type: 'divide_damage' }
  }

  throw new Error(`Unhandled defense effect token: '${typeTok}'`)
}

function parseDescriptor(descriptor: string): ReportCard {
  // Split on | but allow label (last field) to contain | characters
  const firstPipe = descriptor.indexOf('|')
  if (firstPipe === -1) throw new Error('Invalid descriptor: missing fields')

  const version = descriptor.slice(0, firstPipe)
  if (version !== 'v2') throw new Error(`Unsupported descriptor version: '${version}'`)

  // Split remaining into exactly 7 fields (pool|bomber|strategies|precision|pipeline|defense|label)
  const rest = descriptor.slice(firstPipe + 1)
  const parts = rest.split('|')
  if (parts.length < 7) throw new Error(`Invalid descriptor: expected 7 fields after version, got ${parts.length}`)

  // Rejoin any extra pipes back into the label (last field)
  const [poolStr, bomberStr, strategiesStr, precisionStr, pipelineStr, defenseStr, ...labelParts] = parts
  const labelStr = labelParts.join('|')

  // Parse pool: r<R>b<B>k<K><T>
  const poolMatch = poolStr.match(/^r(\d+)b(\d+)k(\d+)([sq])$/)
  if (!poolMatch) throw new Error(`Invalid pool descriptor: '${poolStr}'`)
  const dice_pool = {
    red: parseInt(poolMatch[1], 10),
    blue: parseInt(poolMatch[2], 10),
    black: parseInt(poolMatch[3], 10),
    type: poolMatch[4] === 's' ? 'ship' as const : 'squad' as const,
  }
  if (dice_pool.red < 0 || dice_pool.blue < 0 || dice_pool.black < 0) {
    throw new Error('Invalid pool: dice counts must be >= 0')
  }

  // Parse bomber
  if (bomberStr !== '0' && bomberStr !== '1') throw new Error(`Invalid bomber token: '${bomberStr}'`)
  const bomber = bomberStr === '1'

  // Parse strategies
  if (!strategiesStr) throw new Error('Invalid descriptor: strategies field is empty')
  const strategies = strategiesStr.split(',').map((tok) => TOKEN_TO_STRATEGY[tok] ?? tok)

  // Parse precision
  if (precisionStr !== 'h' && precisionStr !== 'n') throw new Error(`Invalid precision token: '${precisionStr}'`)
  const precision: 'normal' | 'high' = precisionStr === 'h' ? 'high' : 'normal'

  // Parse attack pipeline
  const pipeline: AttackEffect[] = pipelineStr
    ? pipelineStr.split(',').map(decodeAttackEffect)
    : []

  // Parse defense pipeline
  const defense_pipeline: DefenseEffect[] = defenseStr
    ? defenseStr.split(',').map(decodeDefenseEffect)
    : []

  const request: ReportRequest = { dice_pool, pipeline, strategies, precision }
  if (defense_pipeline.length > 0) request.defense_pipeline = defense_pipeline
  if (labelStr) request.pool_label = labelStr

  return { request, bomber }
}

// ---------------------------------------------------------------------------
// encode
// ---------------------------------------------------------------------------

/**
 * Encode a ReportCard to a URL-safe base64url string.
 *
 * Builds a compact positional descriptor string (no JSON field names),
 * compresses it with deflate-raw, and base64url-encodes the result.
 *
 * Throws on encoding failure (programming error, not a user error).
 */
export async function encode(card: ReportCard): Promise<string> {
  const descriptor = buildDescriptor(card)

  const inputBytes = new TextEncoder().encode(descriptor)
  const cs = new CompressionStream('deflate-raw')
  const writer = cs.writable.getWriter()
  writer.write(inputBytes)
  writer.close()

  const compressed = await collectStream(cs.readable)
  return bytesToBase64url(compressed)
}

// ---------------------------------------------------------------------------
// decode
// ---------------------------------------------------------------------------

/**
 * Decode a base64url string back to a ReportCard.
 *
 * Never throws — always returns a DecodeResult discriminated union.
 */
export async function decode(encoded: string): Promise<DecodeResult> {
  // 1. base64url → bytes
  let compressed: Uint8Array
  try {
    compressed = base64urlToBytes(encoded)
  } catch (e) {
    return { ok: false, error: `Failed to decode base64url: ${e instanceof Error ? e.message : String(e)}` }
  }

  // 2. Decompress
  let descriptor: string
  try {
    const ds = new DecompressionStream('deflate-raw')
    const writer = ds.writable.getWriter()
    const writePromise = writer.write(compressed).then(() => writer.close())
    writePromise.catch(() => { /* error surfaces via readable */ })
    const decompressed = await collectStream(ds.readable)
    descriptor = new TextDecoder().decode(decompressed)
  } catch (e) {
    return { ok: false, error: `Failed to decompress: ${e instanceof Error ? e.message : String(e)}` }
  }

  // 3. Check version prefix before full parse
  if (!descriptor.startsWith('v')) {
    return { ok: false, error: 'Missing version field' }
  }
  const versionEnd = descriptor.indexOf('|')
  const versionStr = versionEnd === -1 ? descriptor : descriptor.slice(0, versionEnd)
  const versionNum = parseInt(versionStr.slice(1), 10)
  if (isNaN(versionNum)) {
    return { ok: false, error: 'Missing version field' }
  }
  if (versionNum > CURRENT_VERSION) {
    return { ok: false, error: 'This link was created with a newer version of DRC and cannot be decoded.' }
  }

  // 4. Parse descriptor
  try {
    const card = parseDescriptor(descriptor)
    return { ok: true, value: card }
  } catch (e) {
    return { ok: false, error: `Invalid descriptor: ${e instanceof Error ? e.message : String(e)}` }
  }
}
