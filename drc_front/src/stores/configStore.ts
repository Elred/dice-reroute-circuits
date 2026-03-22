import { defineStore } from 'pinia'
import { reactive, ref, computed, watch } from 'vue'
import type { DicePool, Operation } from '../types/api'
import { useMetaStore } from './metaStore'

export const useConfigStore = defineStore('config', () => {
  const pool = reactive<DicePool>({ red: 0, blue: 0, black: 0, type: 'ship' })
  const pipeline = ref<Operation[]>([])
  const strategies = ref<string[]>(['max_damage'])

  const isPoolEmpty = computed(() => pool.red + pool.blue + pool.black === 0)

  function addOperation(op: Operation) {
    pipeline.value.push(op)
  }

  function removeOperation(index: number) {
    pipeline.value.splice(index, 1)
  }

  function moveOperation(from: number, to: number) {
    if (to < 0 || to >= pipeline.value.length) return
    const [op] = pipeline.value.splice(from, 1)
    pipeline.value.splice(to, 0, op)
  }

  function toggleStrategy(name: string) {
    const idx = strategies.value.indexOf(name)
    if (idx === -1) strategies.value.push(name)
    else strategies.value.splice(idx, 1)
  }

  // When type changes, drop strategies not valid for the new type
  watch(() => pool.type, (newType) => {
    const meta = useMetaStore()
    const valid = meta.strategiesForType(newType)
    strategies.value = strategies.value.filter(s => valid.includes(s))
  })

  return { pool, pipeline, strategies, isPoolEmpty, addOperation, removeOperation, moveOperation, toggleStrategy }
})
