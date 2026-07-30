# Smart Log Analyzer & Failure Prediction

Automatically processes application logs, flags abnormal system behavior,
predicts potential failures, and surfaces it all in a live web dashboard.

**Dataset**: [loghub Android_2k.log_structured.csv](https://github.com/logpai/loghub/blob/master/Android/Android_2k.log_structured.csv)
(included in `logs/`). `Level` is one of `V/D/I/W/E` — Error/Warn are rare
(~9% combined), so failure prediction is framed as **unsupervised anomaly
detection** over 10-second log-traffic windows rather than per-row classification.

## Folder Structure

```
smart-log-analyzer/
├── app.py                    # Flask API (original Phase 1/4 entrypoint)
├── main.py                   # FastAPI API + web dashboard (recommended entrypoint)
├── requirements.txt
├── logs/
│   └── Android_2k.csv        # raw dataset
├── etl/                       # ETL pipeline + one-click automation
│   ├── etl.py                  # extract (CSV) -> transform (clean/dedupe) -> load (SQLite)
│   └── run.bat                 # sets up venv, installs deps, runs the full pipeline, launches dashboard
├── crud/                      # CRUD, one operation per file
│   ├── create.py
│   ├── read.py                  # also has dashboard helpers: count_by_level, top_components
│   ├── update.py
│   ├── delete.py
│   ├── __init__.py              # re-exports all four for convenient imports
│   └── import_csv.py            # legacy single-file bulk import (etl/etl.py supersedes this)
├── database/
│   ├── db_connection.py       # SQLite connection + schema
│   └── logs.db                 # created at runtime
├── data_analysis/             # pandas exploration, feature engineering, charts
│   ├── analyze_logs.py
│   ├── visualize_logs.py        # generates PNG charts into data_analysis/charts/
│   └── window_features.csv      # created at runtime
├── model/                      # ML model
│   ├── train_model.py
│   ├── predict.py
│   ├── failure_model.pkl        # created after training
│   └── scaler.pkl
├── templates/
│   └── dashboard.html          # web dashboard (served by main.py)
├── static/
│   ├── style.css                 # dashboard styling
│   └── dashboard.js              # dashboard data fetching + charts
├── tests/
└── docs/                       # final report goes here
```

## Getting Started

### Option A — one command (Windows)

```cmd
etl\run.bat
```
This creates/activates a venv, installs everything, runs the ETL, builds features
and charts, trains the model, and launches the dashboard at `http://127.0.0.1:8000`.

### Option B — step by step

```bash
pip install -r requirements.txt

# ETL: extract the CSV, clean it, load it into SQLite (safe to re-run — de-dupes)
python etl/etl.py

# Data analysis: build time-window features
python data_analysis/analyze_logs.py

# Generate charts (PNG files in data_analysis/charts/)
python data_analysis/visualize_logs.py

# Train the anomaly detection model
python model/train_model.py

# Launch the dashboard (FastAPI)
python main.py
# then open http://127.0.0.1:8000
```

The original Flask API (`python app.py`, port 5000) still works too, if you need
it for comparison — it exposes the same CRUD endpoints without the dashboard.

## Dashboard

`main.py` serves a live dashboard at `/`:
- **Status readout** — NORMAL / AT RISK based on the latest time window's anomaly score
- **Pulse strip** — error/warn ratio over time, with anomalous windows marked
- **Stat tiles** — total logs, info/warning/error counts, anomalous window count
- **Level distribution & top components** charts
- **Recent logs table**, filterable by level

It auto-refreshes every 30 seconds. All data comes from the JSON API under `/api/*`
(see `main.py` for the full route list), which you can also hit directly or explore
via FastAPI's built-in docs at `/docs`.

## CRUD API (same routes on both `app.py` and `main.py`, `main.py` prefixes with `/api`)

| Operation | Flask (`app.py`)     | FastAPI (`main.py`)      |
|-----------|-----------------------|---------------------------|
| Create    | `POST /logs`           | `POST /api/logs`           |
| List      | `GET /logs`             | `GET /api/logs`             |
| Read one  | `GET /logs/<id>`        | `GET /api/logs/{id}`        |
| Update    | `PUT /logs/<id>`        | `PUT /api/logs/{id}`        |
| Delete    | `DELETE /logs/<id>`     | `DELETE /api/logs/{id}`     |

## Notes / tuning knobs

- `WINDOW` in `data_analysis/analyze_logs.py` (default `10s`) controls how logs are
  bucketed for feature engineering.
- `contamination` in `model/train_model.py` (default `0.1`) controls how sensitive
  the anomaly detector is.
- `etl/etl.py` de-duplicates by `line_id`, so running it again (or via `run.bat`)
  after adding new rows to `logs/Android_2k.csv` only loads what's new.
