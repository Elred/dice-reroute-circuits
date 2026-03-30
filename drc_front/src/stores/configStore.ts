import { defineStore } from 'pinia'
import { reactive, ref, computed, watch } from 'vue'
import type { DicePool, AttackEffect } from '../types/api'
import { useMetaStore } from './metaStore'

export const useConfigStore = defineStore('config', () => {
  const pool = reactive<DicePool>({ red: 0, blue: 0, black: 0, type: 'ship' })
  const pipeline = ref<AttackEffect[]>([])
  const strategies = ref<string[]>(['max_damage'])
  const precision = ref<'normal' | 'high'>('high')

  const isPoolEmpty = computed(() => pool.red + pool.blue + pool.black === 0)

  const totalDiceCount = computed(() => {
    const base = pool.red + pool.blue + pool.black
    const added = pipeline.value
      .filter(op => op.type === 'add_dice' && op.dice_to_add)
      .reduce((sum, op) => sum + (op.dice_to_add!.red + op.dice_to_add!.blue + op.dice_to_add!.black), 0)
    return base + added
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

  // When type changes, drop strategies not valid for the new type
  watch(() => pool.type, (newType) => {
    const meta = useMetaStore()
    const valid = meta.strategiesForType(newType)
    strategies.value = strategies.value.filter(s => valid.includes(s))
  })

  return { pool, pipeline, strategies, precision, isPoolEmpty, totalDiceCount, addAttackEffect, removeAttackEffect, moveAttackEffect, toggleStrategy }
})
