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
      .length
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

  // When type or bomber changes, drop strategies not valid for the effective type
  watch([() => pool.type, bomber], () => {
    const meta = useMetaStore()
    const valid = meta.strategiesForType(effectiveType.value)
    strategies.value = strategies.value.filter(s => valid.includes(s))
    if (pool.type === 'ship') bomber.value = false
  })

  return { pool, pipeline, strategies, precision, defensePipeline, bomber, effectiveType, poolLabel, isPoolEmpty, totalDiceCount, addAttackEffect, removeAttackEffect, moveAttackEffect, toggleStrategy, addDefenseEffect, removeDefenseEffect, moveDefenseEffect }
})
