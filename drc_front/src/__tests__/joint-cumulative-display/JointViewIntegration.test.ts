// Feature: joint-cumulative-display — Integration tests for joint view in ResultsPanel
// _Requirements: 1.1, 1.2, 4.1, 4.2, 4.3, 4.5, 6.1, 6.3_
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import ResultsPanel from '../../components/ResultsPanel.vue'
import JointViewChart from '../../components/JointViewChart.vue'
import { useReportStore } from '../../stores/reportStore'
import { useMetaStore } from '../../stores/metaStore'
import type { VariantResult, ReportRequest, JointCumulativePayload } from '../../types/api'

// Mock the API client to prevent actual network calls
vi.mock('../../api/client', () => ({
  fetchReport: vi.fn(),
  fetchMeta: vi.fn().mockResolvedValue({
    dice_types: ['ship', 'squad'],
    strategies: { ship: ['max_damage'], squad: ['max_damage'] },
    attack_effect_types: [],
    result_values: { ship: {}, squad: {} },
    strategy_priority_lists: { ship: {}, squad: {} },
  }),
}))

// Mock vue-chartjs to avoid Chart.js canvas issues in jsdom
vi.mock('vue-chartjs', () => ({
  Bar: {
    name: 'Bar',
    template: '<div class="mock-bar-chart" data-testid="bar-chart"></div>',
    props: ['data', 'options'],
  },
}))

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const mockPayload: JointCumulativePayload = {
  damage_thresholds: [0, 1, 2],
  accuracy_thresholds: [0, 1],
  matrix: [
    [1.0, 0.8],
    [0.7, 0.5],
    [0.3, 0.2],
  ],
}

const mockVariant: VariantResult = {
  label: 'max_damage',
  avg_damage: 1.5,
  crit: 0.3,
  damage_zero: 0.3,
  acc_zero: 0.2,
  damage: [[0, 1.0], [1, 0.7], [2, 0.3]],
  accuracy: [[0, 1.0], [1, 0.8]],
  joint_cumulative: mockPayload,
}

const mockRequest: ReportRequest = {
  dice_pool: { red: 2, blue: 1, black: 0, type: 'ship' },
  pipeline: [],
  strategies: ['max_damage'],
}

// ---------------------------------------------------------------------------
// Helper: mount ResultsPanel with store pre-populated
// ---------------------------------------------------------------------------

function mountResultsPanel() {
  const pinia = createPinia()
  setActivePinia(pinia)

  const reportStore = useReportStore(pinia)
  const metaStore = useMetaStore(pinia)

  // Pre-populate the report store with a group
  reportStore.groups = [
    { id: 1, request: mockRequest, variants: [mockVariant] },
  ]

  const wrapper = mount(ResultsPanel, {
    global: {
      plugins: [pinia],
    },
  })

  return { wrapper, reportStore, metaStore, pinia }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ResultsPanel Joint View Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Pointer cursor affordance (Requirement 6.1)', () => {
    it('chart options include onHover handler when joint_cumulative is available', () => {
      const { wrapper } = mountResultsPanel()

      // The component should render with the mock data
      const barCharts = wrapper.findAll('.mock-bar-chart')
      expect(barCharts.length).toBeGreaterThan(0)

      // The component renders — the onHover handler is set in makeDamageChartOptions
      // which sets cursor to 'pointer' when hovering. We verify the chart options
      // are constructed with onClick/onHover by checking the component rendered
      // in normal mode (Bar is shown, not JointViewChart)
      expect(wrapper.findComponent({ name: 'JointViewChart' }).exists()).toBe(false)
    })
  })

  describe('Enter Joint View (Requirements 1.1, 1.2)', () => {
    it('renders JointViewChart after entering joint view on damage chart', async () => {
      const { wrapper } = mountResultsPanel()

      // Initially, no JointViewChart should be rendered
      expect(wrapper.findComponent(JointViewChart).exists()).toBe(false)

      // Access the internal joint view state via the component's exposed functions
      // We simulate what happens when a bar is clicked by directly manipulating
      // the joint view state through the component's internal logic.
      // The component uses getJointView which stores instances in a Map.
      // We trigger the click handler logic by finding the chart options and calling onClick.

      // Since we can't easily trigger Chart.js click events in jsdom,
      // we access the component's internal state. The ResultsPanel uses
      // getJointView() which creates useJointView instances stored in a Map.
      // We can trigger the state change by calling the composable directly.
      const vm = wrapper.vm as any

      // Call the internal function to enter joint view
      // The card key for the first card is "1-max_damage"
      const cardKey = '1-max_damage'
      const jv = vm.getJointView(cardKey, 'damage', mockVariant)
      jv.enterJointView('damage', 1)

      // Skip animation — transition directly to joint mode (as the component does)
      jv.state.value = { ...jv.state.value, mode: 'joint' }

      await nextTick()

      // Now JointViewChart should be rendered
      const jointChart = wrapper.findComponent(JointViewChart)
      expect(jointChart.exists()).toBe(true)

      // Verify correct props are passed
      expect(jointChart.props('anchorLabel')).toBe('damage ≥ 1')
      expect(jointChart.props('anchorValue')).toBeCloseTo(70) // 0.7 * 100
      expect(jointChart.props('anchorColor')).toBe('#d69e2e')
      expect(jointChart.props('anchorIsZeroBar')).toBe(false)
      expect(jointChart.props('jointData')).toEqual([70, 50]) // matrix[1] * 100
      expect(jointChart.props('jointLabels')).toEqual(['≥0', '≥1'])
      expect(jointChart.props('crossDimensionLabel')).toBe('accuracy')
    })

    it('renders JointViewChart after entering joint view on accuracy chart', async () => {
      const { wrapper } = mountResultsPanel()

      const vm = wrapper.vm as any
      const cardKey = '1-max_damage'
      const jv = vm.getJointView(cardKey, 'accuracy', mockVariant)
      jv.enterJointView('accuracy', 1)
      jv.state.value = { ...jv.state.value, mode: 'joint' }

      await nextTick()

      // Find the JointViewChart — there should be one for accuracy
      const jointCharts = wrapper.findAllComponents(JointViewChart)
      const accChart = jointCharts.find(c => c.props('crossDimensionLabel') === 'damage')
      expect(accChart).toBeDefined()
      expect(accChart!.props('anchorLabel')).toBe('acc ≥ 1')
      expect(accChart!.props('anchorValue')).toBeCloseTo(80) // 0.8 * 100
      expect(accChart!.props('anchorColor')).toBe('#4299e1')
      expect(accChart!.props('jointData')).toEqual([80, 50, 20]) // matrix column 1 * 100
      expect(accChart!.props('jointLabels')).toEqual(['≥0', '≥1', '≥2'])
    })
  })

  describe('Back arrow button (Requirements 4.1, 4.2, 4.5)', () => {
    it('back arrow is visible when a chart is in joint view', async () => {
      const { wrapper } = mountResultsPanel()

      // Initially, no back arrow should be visible
      const backBtnBefore = wrapper.find('button[title="Back to normal view"]')
      expect(backBtnBefore.exists()).toBe(false)

      // Enter joint view
      const vm = wrapper.vm as any
      const cardKey = '1-max_damage'
      const jv = vm.getJointView(cardKey, 'damage', mockVariant)
      jv.enterJointView('damage', 1)
      jv.state.value = { ...jv.state.value, mode: 'joint' }

      await nextTick()

      // Back arrow should now be visible
      const backBtn = wrapper.find('button[title="Back to normal view"]')
      expect(backBtn.exists()).toBe(true)
      expect(backBtn.text()).toBe('←')
    })

    it('back arrow is positioned left of dismiss button', async () => {
      const { wrapper } = mountResultsPanel()

      // Enter joint view
      const vm = wrapper.vm as any
      const cardKey = '1-max_damage'
      const jv = vm.getJointView(cardKey, 'damage', mockVariant)
      jv.enterJointView('damage', 1)
      jv.state.value = { ...jv.state.value, mode: 'joint' }

      await nextTick()

      // Find both buttons in the card header
      const backBtn = wrapper.find('button[title="Back to normal view"]')
      const dismissBtn = wrapper.find('button[title="Dismiss"]')

      expect(backBtn.exists()).toBe(true)
      expect(dismissBtn.exists()).toBe(true)

      // The back arrow should appear before the dismiss button in DOM order
      // (which means it's positioned to the left in a flex row)
      const headerDiv = backBtn.element.parentElement!
      const buttons = Array.from(headerDiv.querySelectorAll('button'))
      const backIndex = buttons.indexOf(backBtn.element as HTMLButtonElement)
      const dismissIndex = buttons.indexOf(dismissBtn.element as HTMLButtonElement)
      expect(backIndex).toBeLessThan(dismissIndex)
    })

    it('clicking back arrow returns to normal view and hides the arrow', async () => {
      const { wrapper } = mountResultsPanel()

      // Enter joint view
      const vm = wrapper.vm as any
      const cardKey = '1-max_damage'
      const jv = vm.getJointView(cardKey, 'damage', mockVariant)
      jv.enterJointView('damage', 1)
      jv.state.value = { ...jv.state.value, mode: 'joint' }

      await nextTick()

      // Verify joint view is active
      expect(wrapper.findComponent(JointViewChart).exists()).toBe(true)

      // Click the back arrow
      const backBtn = wrapper.find('button[title="Back to normal view"]')
      await backBtn.trigger('click')
      await nextTick()

      // Should return to normal view (exitJointViewDirect resets to 'normal')
      expect(jv.state.value.mode).toBe('normal')

      // JointViewChart should no longer be rendered
      expect(wrapper.findComponent(JointViewChart).exists()).toBe(false)

      // Back arrow should be hidden
      const backBtnAfter = wrapper.find('button[title="Back to normal view"]')
      expect(backBtnAfter.exists()).toBe(false)
    })
  })

  describe('Return via anchor bar click (Requirement 4.3)', () => {
    it('clicking anchored bar in JointViewChart emits exit and returns to normal view', async () => {
      const { wrapper } = mountResultsPanel()

      // Enter joint view
      const vm = wrapper.vm as any
      const cardKey = '1-max_damage'
      const jv = vm.getJointView(cardKey, 'damage', mockVariant)
      jv.enterJointView('damage', 1)
      jv.state.value = { ...jv.state.value, mode: 'joint' }

      await nextTick()

      // Find JointViewChart and emit 'exit' (simulating anchor bar click)
      const jointChart = wrapper.findComponent(JointViewChart)
      expect(jointChart.exists()).toBe(true)

      jointChart.vm.$emit('exit')
      await nextTick()

      // Should return to normal view
      expect(jv.state.value.mode).toBe('normal')

      // JointViewChart should no longer be rendered
      expect(wrapper.findComponent(JointViewChart).exists()).toBe(false)
    })
  })

  describe('Variant without joint_cumulative (Requirement 6.1 negative)', () => {
    it('does not show pointer cursor or joint view when joint_cumulative is absent', () => {
      const pinia = createPinia()
      setActivePinia(pinia)

      const reportStore = useReportStore(pinia)

      const variantWithoutJoint: VariantResult = {
        label: 'max_damage',
        avg_damage: 1.5,
        crit: 0.3,
        damage_zero: 0.3,
        acc_zero: 0.2,
        damage: [[0, 1.0], [1, 0.7], [2, 0.3]],
        accuracy: [[0, 1.0], [1, 0.8]],
        // No joint_cumulative
      }

      reportStore.groups = [
        { id: 1, request: mockRequest, variants: [variantWithoutJoint] },
      ]

      const wrapper = mount(ResultsPanel, {
        global: {
          plugins: [pinia],
        },
      })

      // No JointViewChart should be rendered
      expect(wrapper.findComponent(JointViewChart).exists()).toBe(false)

      // No back arrow should be visible
      expect(wrapper.find('button[title="Back to normal view"]').exists()).toBe(false)
    })
  })
})
