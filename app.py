"""
app.py
Main entrypoint — Flask REST API wrapping the CRUD layer and the
Phase 3 prediction model. Run this for Phase 1 (CRUD) and Phase 4
(local deployment).

    python app.py

Endpoints:
    POST   /logs             create a log entry
    GET    /logs              list logs (?limit=&offset=&level=&component=)
    GET    /logs/<id>         get one log entry
    PUT    /logs/<id>         update a log entry
    DELETE /logs/<id>         delete a log entry
    GET    /predict/latest    (Phase 3) score the most recent time window for failure risk
"""

from flask import Flask, request, jsonify
from database.db_connection import init_db
from crud.create import create_log as crud_create_log
from crud.read import get_log, get_all_logs
from crud.update import update_log as crud_update_log
from crud.delete import delete_log as crud_delete_log

app = Flask(__name__)


@app.route("/logs", methods=["POST"])
def create_log():
    data = request.get_json()
    new_id = crud_create_log(
        line_id=data.get("line_id"),
        log_date=data.get("log_date"),
        log_time=data.get("log_time"),
        pid=data.get("pid"),
        tid=data.get("tid"),
        level=data.get("level"),
        component=data.get("component"),
        content=data.get("content"),
        event_id=data.get("event_id"),
        event_template=data.get("event_template"),
    )
    return jsonify({"id": new_id}), 201


@app.route("/logs", methods=["GET"])
def list_logs():
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))
    level = request.args.get("level")
    component = request.args.get("component")
    return jsonify(get_all_logs(limit, offset, level, component))


@app.route("/logs/<int:log_id>", methods=["GET"])
def read_log(log_id):
    log = get_log(log_id)
    if not log:
        return jsonify({"error": "not found"}), 404
    return jsonify(log)


@app.route("/logs/<int:log_id>", methods=["PUT"])
def update_log(log_id):
    data = request.get_json()
    crud_update_log(log_id, **data)
    return jsonify({"updated": log_id})


@app.route("/logs/<int:log_id>", methods=["DELETE"])
def delete_log(log_id):
    crud_delete_log(log_id)
    return jsonify({"deleted": log_id})


@app.route("/predict/latest", methods=["GET"])
def predict_latest():
    from model.predict import predict_latest_window
    try:
        return jsonify(predict_latest_window())
    except FileNotFoundError:
        return jsonify({"error": "model not trained yet — run model/train_model.py first"}), 503


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
