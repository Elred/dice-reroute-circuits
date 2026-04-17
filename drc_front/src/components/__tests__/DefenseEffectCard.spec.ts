import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import DefenseEffectCard from '../DefenseEffectCard.vue'
import type { DefenseEffect } from '../../types/api'

function mountCard(op: DefenseEffect, index = 0, total = 1) {
  return mount(DefenseEffectCard, {
    props: { op, index, total },
    global: { plugins: [createPinia()] },
  })
}

describe('DefenseEffectCard — summary display', () => {
  it('defense_reroll shows "Reroll {count}× [{mode}]"', () => {
    setActivePinia(createPinia())
    const wrapper = mountCard({ type: 'defense_reroll', count: 2, mode: 'safe' })
    expect(wrapper.find('span').text()).toBe('Reroll 2× [safe]')
  })

  it('defense_reroll gamble mode', () => {
    setActivePinia(createPinia())
    const wrapper = mountCard({ type: 'defense_reroll', count: 1, mode: 'gamble' })
    expect(wrapper.find('span').text()).toBe('Reroll 1× [gamble]')
  })

  it('defense_reroll with applicable_results shows them in braces', () => {
    setActivePinia(createPinia())
    const wrapper = mountCard({
      type: 'defense_reroll', count: 1, mode: 'safe',
      applicable_results: ['R_hit', 'U_crit'],
    })
    expect(wrapper.find('span').text()).toBe('Reroll 1× [safe] {R_hit, U_crit}')
  })

  it('defense_cancel shows "Cancel {count}×"', () => {
    setActivePinia(createPinia())
    const wrapper = mountCard({ type: 'defense_cancel', count: 3 })
    expect(wrapper.find('span').text()).toBe('Cancel 3×')
  })

  it('defense_cancel with applicable_results shows them in braces', () => {
    setActivePinia(createPinia())
    const wrapper = mountCard({
      type: 'defense_cancel', count: 1,
      applicable_results: ['B_hit+crit'],
    })
    expect(wrapper.find('span').text()).toBe('Cancel 1× {B_hit+crit}')
  })

  it('reduce_damage shows "Reduce Damage by {amount}"', () => {
    setActivePinia(createPinia())
    const wrapper = mountCard({ type: 'reduce_damage', amount: 2 })
    expect(wrapper.find('span').text()).toBe('Reduce Damage by 2')
  })

  it('divide_damage shows "Halve Damage"', () => {
    setActivePinia(createPinia())
    const wrapper = mountCard({ type: 'divide_damage' })
    expect(wrapper.find('span').text()).toBe('Halve Damage')
  })
})

describe('DefenseEffectCard — button interactions', () => {
  it('emits remove with index when remove button clicked', async () => {
    setActivePinia(createPinia())
    const wrapper = mountCard({ type: 'divide_damage' }, 1, 3)
    await wrapper.findAll('button')[2].trigger('click')
    expect(wrapper.emitted('remove')).toEqual([[1]])
  })

  it('emits moveUp with index when up button clicked', async () => {
    setActivePinia(createPinia())
    const wrapper = mountCard({ type: 'divide_damage' }, 1, 3)
    await wrapper.findAll('button')[0].trigger('click')
    expect(wrapper.emitted('moveUp')).toEqual([[1]])
  })

  it('emits moveDown with index when down button clicked', async () => {
    setActivePinia(createPinia())
    const wrapper = mountCard({ type: 'divide_damage' }, 1, 3)
    await wrapper.findAll('button')[1].trigger('click')
    expect(wrapper.emitted('moveDown')).toEqual([[1]])
  })

  it('disables moveUp when index is 0', () => {
    setActivePinia(createPinia())
    const wrapper = mountCard({ type: 'divide_damage' }, 0, 3)
    const upBtn = wrapper.findAll('button')[0]
    expect(upBtn.attributes('disabled')).toBeDefined()
  })

  it('disables moveDown when index is total - 1', () => {
    setActivePinia(createPinia())
    const wrapper = mountCard({ type: 'divide_damage' }, 2, 3)
    const downBtn = wrapper.findAll('button')[1]
    expect(downBtn.attributes('disabled')).toBeDefined()
  })
})

describe('DefenseEffectCard — green accent styling', () => {
  it('up/down buttons use green hover color (#276749) instead of gold', () => {
    setActivePinia(createPinia())
    const wrapper = mountCard({ type: 'divide_damage' }, 1, 3)
    const upBtn = wrapper.findAll('button')[0]
    const downBtn = wrapper.findAll('button')[1]
    expect(upBtn.classes()).toContain('hover:text-[#276749]')
    expect(downBtn.classes()).toContain('hover:text-[#276749]')
  })
})
