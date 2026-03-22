// --- Request types ---

export interface DicePool {
  red: number
  blue: number
  black: number
  type: 'ship' | 'squad'
}

export interface Operation {
  type: 'reroll' | 'cancel' | 'add_dice'
  count?: number
  applicable_results?: string[]
  dice_to_add?: { red: number; blue: number; black: number }
}

export interface ReportRequest {
  dice_pool: DicePool
  pipeline: Operation[]
  strategies: string[]
}

// --- Response types ---

export interface VariantResult {
  label: string
  avg_damage: number
  crit: number
  damage: [number, number][]   // [threshold, probability] pairs
  accuracy: [number, number][]
}

export interface ReportResponse {
  variants: VariantResult[]
}

// --- Metadata types ---

export interface MetaResponse {
  dice_types: string[]
  strategies: Record<string, string[]>
  operation_types: string[]
  face_values: Record<string, Record<string, string[]>>
}
