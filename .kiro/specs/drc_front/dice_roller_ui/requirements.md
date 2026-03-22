# Requirements — Dice Roller UI

## Overview

A Vue.js 3 single-page application that lets a Star Wars Armada player configure a dice pool, build an operation pipeline, select strategies, and instantly see probability statistics — all on one screen. The interface is dark, gaming-themed, and elegant.

---

## Functional Requirements

### 1. Dice Pool Configuration

**REQ-1.1** The user MUST be able to set the count of Red, Blue, and Black dice independently using increment/decrement controls (spinner or +/- buttons). Minimum value is 0 for each color.

**REQ-1.2** The user MUST be able to toggle between "Ship" and "Squad" dice types. The toggle MUST be visually prominent.

**REQ-1.3** The UI MUST display a visual summary of the current pool (e.g. "3R 2U 1B — Ship").

**REQ-1.4** The UI MUST prevent submitting an empty pool (all counts zero) and display an inline validation message.

---

### 2. Operation Pipeline

**REQ-2.1** The user MUST be able to add operations to a pipeline in any order. Supported operation types: `reroll`, `cancel`, `add_dice`.

**REQ-2.2** Each operation in the pipeline MUST be displayed as a card showing its type and parameters.

**REQ-2.3** The user MUST be able to remove any operation from the pipeline.

**REQ-2.4** The user MUST be able to reorder operations in the pipeline via drag-and-drop or up/down buttons.

**REQ-2.5** For `reroll` and `cancel` operations, the user MUST be able to:
- Set the count (how many dice to affect), minimum 1
- Select which face values are eligible (`applicable_results`) from a checklist. The available faces MUST be populated from the `/api/v1/meta` response and filtered to faces relevant to the current pool's dice type.

**REQ-2.6** For `add_dice` operations, the user MUST be able to set the Red, Blue, and Black counts to add (each ≥ 0, total > 0).

**REQ-2.7** An empty pipeline (no operations) MUST be valid — it represents a raw roll with no modifications.

---

### 3. Strategy Selection

**REQ-3.1** The user MUST be able to select one or more strategies from the available list. Available strategies MUST be populated from the `/api/v1/meta` response, filtered to the current dice type.

**REQ-3.2** At least one strategy MUST be selected before a report can be requested. The UI MUST enforce this with an inline message.

**REQ-3.3** Each strategy MUST be displayed with a human-readable label and a short description of what it optimizes.

**REQ-3.4** The selected strategies MUST be visually distinguished from unselected ones (e.g. highlighted border, filled background).

---

### 4. Results Panel

**REQ-4.1** The results panel MUST display one section per selected strategy variant.

**REQ-4.2** Each variant section MUST show:
- Strategy label
- Average damage (numeric)
- Crit probability (percentage)
- Cumulative damage chart: a bar or line chart of P(damage ≥ x) for each threshold x
- Cumulative accuracy chart: a bar or line chart of P(acc ≥ x) for each threshold x

**REQ-4.3** Charts MUST use Chart.js via `vue-chartjs`. The x-axis is the threshold value; the y-axis is probability (0–100%).

**REQ-4.4** When multiple strategies are selected, their charts MUST be displayed side-by-side or in clearly labeled separate sections so the user can compare them.

**REQ-4.5** While a report request is in flight, the results panel MUST show a loading indicator.

**REQ-4.6** If the API returns an error, the results panel MUST display the error message clearly (not a blank screen or silent failure).

**REQ-4.7** The results panel MUST be empty (or show a placeholder) on initial load before any report has been requested.

---

### 5. Report Triggering

**REQ-5.1** The report MUST be triggered by a "Calculate" button. The button MUST be disabled when the pool is empty or no strategy is selected.

**REQ-5.2** The report MAY also be triggered automatically when any input changes, after a short debounce delay (300–500 ms). This is an optional enhancement.

---

### 6. Metadata Loading

**REQ-6.1** On application startup, the UI MUST call `GET /api/v1/meta` to fetch valid face values, strategies, and operation types.

**REQ-6.2** If the metadata call fails, the UI MUST display a connection error message and disable the form until metadata is available.

**REQ-6.3** Face value checklists and strategy selectors MUST be populated from the metadata response — never hardcoded in the front-end.

---

### 7. Visual Design

**REQ-7.1** The application MUST use a dark gaming theme: deep navy/charcoal backgrounds, gold/amber accents, crisp white text.

**REQ-7.2** Dice colors MUST be visually coded: Red dice → red tones, Blue dice → blue tones, Black dice → grey/dark tones.

**REQ-7.3** The layout MUST be a single page with a left/top configuration panel and a right/bottom results panel. On narrow screens, the panels MUST stack vertically.

**REQ-7.4** The UI MUST be responsive down to a minimum viewport width of 375px (mobile).

---

### 8. Non-Functional Requirements

**REQ-8.1** The application MUST be a Vue.js 3 SPA using the Composition API with `<script setup>` syntax.

**REQ-8.2** All component state MUST be managed via Pinia stores.

**REQ-8.3** All API calls MUST go through the `src/api/client.ts` Axios client — no `fetch()` calls in components.

**REQ-8.4** TypeScript interfaces in `src/types/api.ts` MUST match the API contract exactly.

**REQ-8.5** The application MUST start with `npm run dev` from the `drc_front/` directory.

---

## Correctness Properties

**PROP-1** (Metadata consistency) The face values shown in operation checklists MUST be a subset of the face values returned by `/api/v1/meta` for the current dice type. No face value may appear in the UI that is not in the metadata.

**PROP-2** (Request fidelity) The JSON body sent to `POST /api/v1/report` MUST exactly match the TypeScript `ReportRequest` interface — no extra fields, no missing required fields.

**PROP-3** (Strategy filter) When the dice type changes from "ship" to "squad" (or vice versa), any previously selected strategies that are not valid for the new type MUST be automatically deselected.

**PROP-4** (Empty pool guard) The "Calculate" button MUST be disabled whenever `red + blue + black === 0`, regardless of other state.

**PROP-5** (Loading state exclusivity) The results panel MUST NOT display stale results while a new request is in flight — it MUST show the loading indicator until the new response arrives.

**PROP-6** (Chart data integrity) For each variant, the number of data points in the damage chart MUST equal the length of the `damage` array in the API response. No data points may be dropped or added.
