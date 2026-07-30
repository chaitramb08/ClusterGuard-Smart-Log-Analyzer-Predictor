"""
main.py
FastAPI application — serves the same CRUD + prediction functionality
as app.py (Flask), plus a web dashboard for visualizing logs and
failure predictions.

Run:
    uvicorn main:app --reload
    (or just: python main.py)

Routes:
    GET  /                      dashboard (HTML)
    GET  /api/logs               list logs
    GET  /api/logs/{id}          get one log
    POST /api/logs               create a log
    PUT  /api/logs/{id}          update a log
    DELETE /api/logs/{id}        delete a log
    GET  /api/summary            dashboard summary stats + latest prediction
    GET  /api/window-features    time-window features with anomaly flags
    GET  /api/predict/latest     score the most recent time window
"""

import os
import sys
sys.path.append(os.path.dirname(__file__))

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from database.db_connection import init_db
from crud.create import create_log as crud_create_log
from crud.read import get_log, get_all_logs, count_logs, count_by_level, top_components, next_line_id
from crud.update import update_log as crud_update_log
from crud.delete import delete_log as crud_delete_log

VALID_LEVELS = {"V", "D", "I", "W", "E"}

BASE_DIR = os.path.dirname(__file__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Smart Log Analyzer & Failure Prediction", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


class LogCreate(BaseModel):
    level: str
    component: str
    content: str
    event_id: Optional[str] = None
    event_template: Optional[str] = None
    # advanced/optional — auto-filled if omitted, so a dashboard user
    # only ever has to think about level/component/content
    line_id: Optional[int] = None
    log_date: Optional[str] = None
    log_time: Optional[str] = None
    pid: Optional[int] = None
    tid: Optional[int] = None


class LogUpdate(BaseModel):
    level: Optional[str] = None
    component: Optional[str] = None
    content: Optional[str] = None
    is_anomaly: Optional[int] = None


# ---------- Dashboard ----------

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", {})


# ---------- CRUD API ----------

@app.post("/api/logs", status_code=201)
def api_create_log(log: LogCreate):
    if log.level.upper() not in VALID_LEVELS:
        raise HTTPException(status_code=400, detail=f"level must be one of {sorted(VALID_LEVELS)}")

    now = datetime.now()
    payload = log.model_dump()
    payload["level"] = log.level.upper()
    payload["line_id"] = payload["line_id"] or next_line_id()
    payload["log_date"] = payload["log_date"] or now.strftime("%m-%d")
    payload["log_time"] = payload["log_time"] or now.strftime("%H:%M:%S.%f")[:-3]
    payload["pid"] = payload["pid"] if payload["pid"] is not None else 0
    payload["tid"] = payload["tid"] if payload["tid"] is not None else 0

    new_id = crud_create_log(**payload)
    return {"id": new_id}


@app.get("/api/logs")
def api_list_logs(limit: int = 100, offset: int = 0,
                   level: Optional[str] = None, component: Optional[str] = None):
    return get_all_logs(limit=limit, offset=offset, level=level, component=component)


@app.get("/api/logs/{log_id}")
def api_read_log(log_id: int):
    log = get_log(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="not found")
    return log


@app.put("/api/logs/{log_id}")
def api_update_log(log_id: int, log: LogUpdate):
    if not get_log(log_id):
        raise HTTPException(status_code=404, detail="not found")
    fields = {k: v for k, v in log.model_dump().items() if v is not None}
    if "level" in fields:
        if fields["level"].upper() not in VALID_LEVELS:
            raise HTTPException(status_code=400, detail=f"level must be one of {sorted(VALID_LEVELS)}")
        fields["level"] = fields["level"].upper()
    if not fields:
        raise HTTPException(status_code=400, detail="no fields to update")
    crud_update_log(log_id, **fields)
    return {"updated": log_id}


@app.delete("/api/logs/{log_id}")
def api_delete_log(log_id: int):
    if not get_log(log_id):
        raise HTTPException(status_code=404, detail="not found")
    crud_delete_log(log_id)
    return {"deleted": log_id}


# ---------- Analytics / prediction API (powers the dashboard) ----------

@app.get("/api/summary")
def api_summary():
    from model.predict import predict_latest_window

    try:
        prediction = predict_latest_window()
    except FileNotFoundError:
        prediction = {"error": "model not trained yet"}

    return {
        "total_logs": count_logs(),
        "by_level": count_by_level(),
        "top_components": top_components(8),
        "prediction": prediction,
    }


@app.get("/api/window-features")
def api_window_features():
    import pandas as pd
    from database.db_connection import get_connection
    from data_analysis.analyze_logs import build_timestamp, build_window_features
    from model.predict import predict_window

    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM logs", conn)
    conn.close()

    if df.empty:
        return []

    df = build_timestamp(df)
    features = build_window_features(df)

    results = []
    for _, row in features.iterrows():
        entry = {
            "timestamp": str(row["timestamp"]),
            "total_logs": int(row["total_logs"]),
            "error_count": int(row["error_count"]),
            "warn_count": int(row["warn_count"]),
            "distinct_events": int(row["distinct_events"]),
            "distinct_components": int(row["distinct_components"]),
            "error_warn_ratio": float(row["error_warn_ratio"]),
        }
        try:
            pred = predict_window(
                row["total_logs"], row["error_count"], row["warn_count"],
                row["distinct_events"], row["distinct_components"]
            )
            entry["is_anomaly"] = pred["is_anomaly"]
        except FileNotFoundError:
            entry["is_anomaly"] = False
        results.append(entry)

    return results


@app.get("/api/predict/latest")
def api_predict_latest():
    from model.predict import predict_latest_window
    try:
        return predict_latest_window()
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="model not trained yet — run model/train_model.py first")

@app.get("/api/predict/trend")
def api_predict_trend():
    from model.predict import predict_trend
    try:
        return predict_trend()
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="model not trained yet — run model/train_model.py first")
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)