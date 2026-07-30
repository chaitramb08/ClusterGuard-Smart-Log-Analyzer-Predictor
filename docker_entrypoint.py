"""
docker_entrypoint.py
Container startup: builds the database/features/model on first run
(if they don't already exist), then launches the server.

Deliberately written in Python rather than a .sh script — avoids the
classic Windows line-ending (CRLF) issue that breaks shell scripts
inside Linux containers, since Python parses both line-ending styles fine.
"""

import os
import subprocess
import sys


def run(cmd):
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


if not os.path.exists("database/logs.db"):
    print("No database found — running ETL...")
    run([sys.executable, "etl/etl.py"])

if not os.path.exists("data_analysis/window_features.csv"):
    print("Building Phase 2 features...")
    run([sys.executable, "data_analysis/analyze_logs.py"])

if not os.path.exists("model/failure_model.pkl"):
    print("Training Phase 3 model...")
    run([sys.executable, "model/train_model.py"])

print("Starting server...")
os.execvp(sys.executable, [sys.executable, "main.py"])