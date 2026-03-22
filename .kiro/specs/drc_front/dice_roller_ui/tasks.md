# Tasks — Dice Roller UI

## Task List

- [ ] 1. Project scaffolding
  - [ ] 1.1 Scaffold Vue 3 + TypeScript + Vite project in `drc_front/` using `npm create vue@latest`
  - [ ] 1.2 Install dependencies: `pinia`, `vue-router`, `axios`, `chart.js`, `vue-chartjs`, `tailwindcss`
  - [ ] 1.3 Configure Tailwind CSS with the custom color palette from the design doc
  - [ ] 1.4 Configure Vite proxy: `/api` → `http://localhost:5000`
  - [ ] 1.5 Set up Pinia in `main.ts`

- [ ] 2. TypeScript types and API client
  - [ ] 2.1 Create `src/types/api.ts` with `DicePool`, `Operation`, `ReportRequest`, `VariantResult`, `ReportResponse`, `MetaResponse` interfaces
  - [ ] 2.2 Create `src/api/client.ts` with Axios instance and `fetchMeta()` / `fetchReport()` functions

- [ ] 3. Pinia stores
  - [ ] 3.1 Create `src/stores/metaStore.ts` — `loadMeta()`, `strategiesForType()`, `faceValuesForType()`
  - [ ] 3.2 Create `src/stores/configStore.ts` — pool, pipeline, strategies, `isPoolEmpty`, `addOperation`, `removeOperation`, `moveOperation`, `toggleStrategy`, type-change watcher
  - [ ] 3.3 Create `src/stores/reportStore.ts` — `variants`, `isLoading`, `error`, `runReport()`

- [ ] 4. Composable
  - [ ] 4.1 Create `src/composables/useReport.ts` — `buildRequest()` and `calculate()`

- [ ] 5. DicePoolConfig component
  - [ ] 5.1 Create `src/components/DicePoolConfig.vue`
  - [ ] 5.2 Implement Ship/Squad toggle bound to `configStore.pool.type`
  - [ ] 5.3 Implement +/- controls for Red, Blue, Black counts with minimum 0 guard
  - [ ] 5.4 Display pool summary string (e.g. "3R 2U 1B — Ship")
  - [ ] 5.5 Apply dice color coding (red/blue/grey) to each row

- [ ] 6. Operation pipeline components
  - [ ] 6.1 Create `src/components/OperationCard.vue` — display a single operation's type and parameters
  - [ ] 6.2 Create `src/components/AddOperationForm.vue` — operation type selector, conditional fields for reroll/cancel/add_dice, face value checklist from metaStore
  - [ ] 6.3 Create `src/components/OperationPipeline.vue` — renders pipeline list with OperationCard, remove buttons, up/down reorder buttons, and AddOperationForm trigger

- [ ] 7. StrategySelector component
  - [ ] 7.1 Create `src/components/StrategySelector.vue`
  - [ ] 7.2 Render strategy toggle buttons populated from `metaStore.strategiesForType(pool.type)`
  - [ ] 7.3 Apply active styling to selected strategies
  - [ ] 7.4 Display human-readable label and description for each strategy

- [ ] 8. ResultsPanel component
  - [ ] 8.1 Create `src/components/ResultsPanel.vue`
  - [ ] 8.2 Implement empty/placeholder state
  - [ ] 8.3 Implement loading spinner state
  - [ ] 8.4 Implement error message state
  - [ ] 8.5 Implement variant result rendering: strategy label, avg damage, crit %
  - [ ] 8.6 Implement cumulative damage Bar chart using vue-chartjs
  - [ ] 8.7 Implement cumulative accuracy Bar chart using vue-chartjs
  - [ ] 8.8 Apply gold/amber chart color scheme

- [ ] 9. App.vue root layout
  - [ ] 9.1 Implement two-panel layout (config left, results right)
  - [ ] 9.2 Add responsive stacking for narrow viewports (< 768px)
  - [ ] 9.3 Call `metaStore.loadMeta()` on mount
  - [ ] 9.4 Show connection error banner if metadata fails to load
  - [ ] 9.5 Wire up "Calculate" button: disabled when pool empty or no strategy selected, calls `useReport().calculate()`

- [ ] 10. Global styling
  - [ ] 10.1 Apply dark theme base styles in `src/assets/main.css`
  - [ ] 10.2 Style scrollbars, focus rings, and button states to match the gaming theme
