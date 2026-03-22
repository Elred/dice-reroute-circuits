# Tech Stack — drc_front

## Framework & Language

- **Vue.js 3** — progressive JavaScript framework using the Composition API
- **TypeScript** — all `.vue` and `.ts` files use TypeScript for type safety
- **Vite** — build tool and dev server (fast HMR, minimal config)

## Key Libraries

- **Vue Router** — client-side routing (single route for the SPA, but structured for extensibility)
- **Pinia** — state management store (replaces Vuex in Vue 3)
- **Axios** — HTTP client for API calls to the Flask backend
- **Chart.js + vue-chartjs** — probability distribution charts
- **Tailwind CSS** — utility-first CSS framework for styling

## Project Structure

```
drc_front/
├── public/                  # Static assets
├── src/
│   ├── assets/              # Images, fonts, global CSS
│   ├── components/          # Reusable UI components
│   │   ├── DicePoolConfig.vue
│   │   ├── OperationPipeline.vue
│   │   ├── StrategySelector.vue
│   │   └── ResultsPanel.vue
│   ├── composables/         # Reusable logic (Vue 3 Composition API hooks)
│   │   └── useReport.ts
│   ├── stores/              # Pinia stores
│   │   └── reportStore.ts
│   ├── types/               # TypeScript interfaces matching the API contract
│   │   └── api.ts
│   ├── api/                 # Axios API client
│   │   └── client.ts
│   ├── App.vue              # Root component
│   └── main.ts              # Entry point
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

## Vue 3 Concepts Used

- **Composition API** (`setup()`, `ref`, `computed`, `watch`) — preferred over Options API
- **`<script setup>`** syntax — concise single-file component syntax
- **Reactive state** via `ref()` and `reactive()`
- **Computed properties** for derived UI state
- **Watchers** to trigger API calls when inputs change

## Styling Conventions

- Dark gaming theme: deep navy/charcoal backgrounds, gold/amber accents, crisp white text
- Tailwind utility classes in templates; no scoped CSS unless necessary
- Dice color coding: Red → `#e53e3e`, Blue → `#4299e1`, Black → `#718096`

## Dev Server

```bash
cd drc_front
npm install
npm run dev        # starts Vite dev server on http://localhost:5173
```

The Flask API is expected at `http://localhost:5000` during development.
Vite proxy config forwards `/api/*` requests to avoid CORS issues in dev.

## Build

```bash
npm run build      # outputs to drc_front/dist/
```
