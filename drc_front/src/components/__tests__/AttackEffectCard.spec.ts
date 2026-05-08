/**
 * Exploratory test — confirms the current behavior of opSummary for
 * unrecognized op types (they fall through to the reroll/cancel ternary).
 *
 * NOTE: This test documents the CURRENT behavior. The set-die-cross-color
 * bugfix spec (which would add a 'set_die' branch) has not been implemented.
 * When that spec is implemented, this test should be updated to expect
 * "Set Die" instead of "Cancel".
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

describe('AttackEffectCard — opSummary for unrecognized type (set_die)', () => {
  it('falls through to Cancel label for unrecognized set_die type (unfixed)', () => {
    setActivePinia(createPinia())
    // Seed the stores so the component picks them up
    useMetaStore()
    useConfigStore()

    const wrapper = mountCard({ type: 'set_die', count: 1, applicable_results: ['R_blank'] })
    const text = wrapper.find('span').text()

    // Current behavior: unrecognized types fall through to the Cancel branch
    // When the set-die-cross-color bugfix is implemented, update this to expect /^Set Die/
    expect(text).toMatch(/^Cancel/)
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
