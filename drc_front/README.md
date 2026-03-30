# DRC Front — Dice Probability Calculator

Vue 3 + TypeScript SPA for the `drc_stat_engine` probability analysis tool.

---

## Prerequisites

- Node.js (via nvm recommended) — `nvm install --lts`
- Python 3 virtualenv at `~/.virtualenvs/drc` with the stat engine installed

---

## Running the app

You need two terminals running simultaneously.

### Terminal 1 — Flask API (port 5000)

```bash
source ~/.virtualenvs/drc/bin/activate
cd drc_stat_engine/api
python app.py
```

The API will be available at `http://localhost:5000`.

### Terminal 2 — Vue dev server (port 5173)

```bash
cd drc_front
npm install       # first time only
npm run dev
```

Open `http://localhost:5173` in your browser. The Vite dev server proxies all `/api/*` requests to the Flask API automatically — no CORS issues.

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/meta` | Returns dice types, strategies, operation types, and face values |
| `POST` | `/api/v1/report` | Runs a probability report for a given dice pool, pipeline, and strategies |

### POST /api/v1/report — request body

```json
{
  "dice_pool": { "red": 3, "blue": 2, "black": 0, "type": "ship" },
  "pipeline": [
    { "type": "reroll", "count": 2, "applicable_results": ["R_blank", "R_hit"] }
  ],
  "strategies": ["max_damage", "max_accuracy"]
}
```

### POST /api/v1/report — response

```json
{
  "variants": [
    {
      "label": "Max Damage",
      "avg_damage": 4.21,
      "crit": 0.63,
      "damage": [[0, 1.0], [1, 0.94], [2, 0.81]],
      "accuracy": [[0, 1.0], [1, 0.45]]
    }
  ]
}
```

---

## Build for production

```bash
cd drc_front
npm run build
# output in drc_front/dist/
```

## Type checking

```bash
cd drc_front
npm run typecheck
```
