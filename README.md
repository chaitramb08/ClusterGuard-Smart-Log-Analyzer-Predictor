# ClusterGuard-Smart-Log-Analyzer-Predictor
A full-stack MLOps pipeline that ingests Android system logs via ETL, detects anomalies with an IsolationForest model, and forecasts near-term failure risk. Serves a live monitoring dashboard through a FastAPI + CRUD backend, containerized with Docker and deployed across dev/qa/prod environments on Kubernetes with CI/CD via GitHub Actions.
