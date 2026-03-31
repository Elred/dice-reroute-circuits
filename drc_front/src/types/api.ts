// --- Request types ---

export interface DicePool {
  red: number
  blue: number
  black: number
  type: 'ship' | 'squad'
}

export interface AttackEffect {
  type: 'reroll' | 'cancel' | 'add_dice' | 'change_die'
  count?: number | 'any'
  applicable_results?: string[]
  dice_to_add?: { red: number; blue: number; black: number }
  target_result?: string
}

export interface ReportRequest {
  dice_pool: DicePool
  pipeline: AttackEffect[]
  strategies: string[]
  precision?: 'normal' | 'high'
}

// --- Response types ---

export interface VariantResult {
  label: string
  avg_damage: number
  crit: number
  damage_zero: number
  acc_zero: number
  damage: [number, number][]
  accuracy: [number, number][]
  engine_type?: string
}

export interface ReportResponse {
  variants: VariantResult[]
}

// --- Metadata types ---

export interface StrategyPriorityList {
  reroll: string[]
  cancel: string[]
  change_die: Record<string, string[]>
}

export interface MetaResponse {
  dice_types: string[]
  strategies: Record<string, string[]>
  attack_effect_types: string[]
  result_values: Record<string, Record<string, string[]>>
  strategy_priority_lists: Record<string, Record<string, StrategyPriorityList>>
}
