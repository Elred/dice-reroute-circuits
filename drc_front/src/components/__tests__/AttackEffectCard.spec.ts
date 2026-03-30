/**
 * Exploratory test — confirms the bug in opSummary for set_die ops.
 *
 * Validates: Requirements 1.1, 1.2
 *
 * This test MUST FAIL on unfixed code because opSummary uses a binary ternary
 * `op.type === 'reroll' ? 'Reroll' : 'Cancel'` with no branch for `set_die`,
 * so it returns "Cancel ..." instead of "Set Die ...".
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia, defineStore } from 'pinia'
import AttackEffectCard from '../AttackEffectCard.vue'

// Minimal mock for metaStore — describeResults just returns the result strings joined
const useMetaStore = defineStore('meta', () => ({
  describeResults: (results: string[], _poolType: string) =>
    results.length > 0 ? results.join(', ') : 'any',
}))

// Minimal mock for configStore — pool.type is 'ship'
const useConfigStore = defineStore('config', () => ({
  pool: { type: 'ship' as const },
}))

function mountCard(op: object) {
  return mount(AttackEffectCard, {
    props: { op, index: 0, total: 1 },
    global: {
      plugins: [createPinia()],
    },
  })
}

describe('AttackEffectCard — opSummary bug condition (set_die)', () => {
  it('displays "Set Die" label for a set_die op with R_blank face', () => {
    setActivePinia(createPinia())
    // Seed the stores so the component picks them up
    useMetaStore()
    useConfigStore()

    const wrapper = mountCard({ type: 'set_die', count: 1, applicable_results: ['R_blank'] })
    const text = wrapper.find('span').text()

    // This assertion FAILS on unfixed code (returns "Cancel 1× [...]" instead)
    expect(text).toMatch(/^Set Die/)
  })
})

/**
 * Preservation tests — existing labels are unchanged after the set_die fix.
 *
 * Validates: Requirements 3.1, 3.2, 3.3
 */
describe('AttackEffectCard — opSummary label preservation', () => {
  it('reroll op starts with "Reroll"', () => {
    setActivePinia(createPinia())
    useMetaStore()
    useConfigStore()

    const wrapper = mountCard({ type: 'reroll', count: 1, applicable_results: ['R_blank'] })
    expect(wrapper.find('span').text()).toMatch(/^Reroll/)
  })

  it('cancel op starts with "Cancel"', () => {
    setActivePinia(createPinia())
    useMetaStore()
    useConfigStore()

    const wrapper = mountCard({ type: 'cancel', count: 1, applicable_results: ['R_blank'] })
    expect(wrapper.find('span').text()).toMatch(/^Cancel/)
  })

  it('add_dice op starts with "Add Dice"', () => {
    setActivePinia(createPinia())
    useMetaStore()
    useConfigStore()

    const wrapper = mountCard({ type: 'add_dice', dice_to_add: { red: 1, blue: 0, black: 0 } })
    expect(wrapper.find('span').text()).toMatch(/^Add Dice/)
  })
})
