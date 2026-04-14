// --- Request types ---

export interface DicePool {
  red: number
  blue: number
  black: number
  type: 'ship' | 'squad'
}

export interface AttackEffect {
  type: 'reroll' | 'cancel' | 'add_dice' | 'change_die' | 'add_set_die'
  count?: number | 'any'
  applicable_results?: string[]
  dice_to_add?: { red: number; blue: number; black: number }
  target_result?: string
  face_condition?: string | null
  color_in_pool?: boolean
  color_priority?: [string, string, string] | null
}

export interface DefenseEffect {
  type: 'defense_reroll' | 'defense_cancel' | 'reduce_damage' | 'divide_damage'
  count?: number
  mode?: 'safe' | 'could_be_blank'
  amount?: number
  applicable_results?: string[]
}

export interface ReportRequest {
  dice_pool: DicePool
  pipeline: AttackEffect[]
  strategies: string[]
  precision?: 'normal' | 'high'
  defense_pipeline?: DefenseEffect[]
  pool_label?: string  // Display label: "Ship", "Squadron", or "Bomber"
}

// --- Response types ---

export interface VariantStats {
  avg_damage: number
  crit: number
  damage_zero: number
  acc_zero: number
  damage: [number, number][]
  accuracy: [number, number][]
}

export interface VariantResult {
  label: string
  avg_damage: number
  crit: number
  damage_zero: number
  acc_zero: number
  damage: [number, number][]
  accuracy: [number, number][]
  engine_type?: string
  pre_defense?: VariantStats
  post_defense?: VariantStats
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
