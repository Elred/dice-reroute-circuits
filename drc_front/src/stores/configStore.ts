import { defineStore } from 'pinia'
import { reactive, ref, computed, watch } from 'vue'
import type { DicePool, AttackEffect, DefenseEffect } from '../types/api'
import { useMetaStore } from './metaStore'

export const useConfigStore = defineStore('config', () => {
  const pool = reactive<DicePool>({ red: 0, blue: 0, black: 0, type: 'ship' })
  const pipeline = ref<AttackEffect[]>([])
  const strategies = ref<string[]>(['max_damage'])
  const precision = ref<'normal' | 'high'>('high')
  const defensePipeline = ref<DefenseEffect[]>([])
  const bomber = ref(false)

  const isPoolEmpty = computed(() => pool.red + pool.blue + pool.black === 0)

  // The dice type sent to the backend: bomber squads use ship dice
  const effectiveType = computed(() => {
    if (pool.type === 'squad' && bomber.value) return 'ship'
    return pool.type
  })

  // Human-readable label for the pool type
  const poolLabel = computed(() => {
    if (pool.type === 'ship') return 'Ship'
    if (bomber.value) return 'Bomber'
    return 'Squadron'
  })

  const totalDiceCount = computed(() => {
    const base = pool.red + pool.blue + pool.black
    const added = pipeline.value
      .filter(op => op.type === 'add_dice' && op.dice_to_add && !op.color_in_pool)
      .reduce((sum, op) => sum + (op.dice_to_add!.red + op.dice_to_add!.blue + op.dice_to_add!.black), 0)
    const colorInPoolCount = pipeline.value
      .filter(op => op.type === 'add_dice' && op.color_in_pool)
      .reduce((sum, op) => sum + (op.count && op.count !== 'any' ? (op.count as number) : 1), 0)
    const setDice = pipeline.value
      .filter(op => op.type === 'add_set_die')
      .length
    return base + added + colorInPoolCount + setDice
  })

  function addAttackEffect(op: AttackEffect) {
    pipeline.value.push(op)
  }

  function removeAttackEffect(index: number) {
    pipeline.value.splice(index, 1)
  }

  function moveAttackEffect(from: number, to: number) {
    if (to < 0 || to >= pipeline.value.length) return
    const [op] = pipeline.value.splice(from, 1)
    pipeline.value.splice(to, 0, op)
  }

  function toggleStrategy(name: string) {
    strategies.value = strategies.value[0] === name ? [] : [name]
  }

  function addDefenseEffect(op: DefenseEffect) {
    defensePipeline.value.push(op)
  }

  function removeDefenseEffect(index: number) {
    defensePipeline.value.splice(index, 1)
  }

  function moveDefenseEffect(from: number, to: number) {
    if (to < 0 || to >= defensePipeline.value.length) return
    const [op] = defensePipeline.value.splice(from, 1)
    defensePipeline.value.splice(to, 0, op)
  }

  let _isLoadingFromRequest = false

  // When type or bomber changes, drop strategies not valid for the effective type
  watch([() => pool.type, bomber], () => {
    if (_isLoadingFromRequest) return
    const meta = useMetaStore()
    const valid = meta.strategiesForType(effectiveType.value)
    strategies.value = strategies.value.filter(s => valid.includes(s))
    if (pool.type === 'ship') bomber.value = false
  })

  /**
   * Load a ReportRequest into the config panel (dice pool, pipeline, strategies, defense).
   */
  function loadFromRequest(req: import('../types/api').ReportRequest) {
    _isLoadingFromRequest = true

    // Determine bomber state from pool_label
    const isBomber = req.pool_label === 'Bomber'

    // For bombers, the request stores type='ship' (effectiveType), but actual pool type is 'squad'
    pool.type = isBomber ? 'squad' : req.dice_pool.type
    bomber.value = isBomber

    pool.red = req.dice_pool.red
    pool.blue = req.dice_pool.blue
    pool.black = req.dice_pool.black

    pipeline.value = JSON.parse(JSON.stringify(req.pipeline))
    strategies.value = [...req.strategies]
    precision.value = req.precision ?? 'high'
    defensePipeline.value = req.defense_pipeline ? JSON.parse(JSON.stringify(req.defense_pipeline)) : []

    _isLoadingFromRequest = false
  }

  return { pool, pipeline, strategies, precision, defensePipeline, bomber, effectiveType, poolLabel, isPoolEmpty, totalDiceCount, addAttackEffect, removeAttackEffect, moveAttackEffect, toggleStrategy, addDefenseEffect, removeDefenseEffect, moveDefenseEffect, loadFromRequest }
})
