"""
tools/generate_logs.py
Continuously generates random (but realistic-looking) Android-style log
entries and POSTs them to the running dashboard's API, so you can watch
the dashboard's status/score/pulse update live.

Normal traffic is generated most of the time. Periodically, an anomalous
burst is injected, chosen from three types that map onto the three ways
the IsolationForest model can flag a 10s window (data_analysis/analyze_logs.py
features: total_logs, error_count, warn_count, distinct_events,
distinct_components, error_warn_ratio):

    error   - spike in error/warn ratio (crashes, timeouts, ANRs)
    volume  - spike in raw traffic volume (flood of logs in a short window)
    diversity - spike in distinct_events / distinct_components (a sudden
                burst of many different event types across many different
                components, as if lots of unrelated subsystems misbehaved
                at once)

Requires the app to already be running (python main.py -> port 8000).

Usage:
    pip install requests   # if not already installed
    python tools/generate_logs.py
    python tools/generate_logs.py --rate 5 --url http://127.0.0.1:8000
    python tools/generate_logs.py --burst-every 20 --burst-size 15
    python tools/generate_logs.py --anomaly-types error,volume
    python tools/generate_logs.py --anomaly-types diversity --burst-size 25
"""

import argparse
import random
import time
import requests

COMPONENTS = [
    "ActivityManager", "WindowManager", "PackageManager", "InputDispatcher",
    "PowerManagerService", "Zygote", "SurfaceFlinger", "AudioFlinger",
    "WifiService", "BluetoothAdapter", "NotificationService", "LocationManager",
    "TelephonyManager", "MediaServer", "CameraService", "SensorService",
    "AlarmManager", "JobScheduler", "UsageStatsService", "DisplayManager",
]

# Weighted so most traffic looks "normal" (mirrors the real dataset's ~9%
# combined error/warn rate under everyday conditions)
NORMAL_LEVELS = ["V"] * 3 + ["D"] * 4 + ["I"] * 4 + ["W"] * 1

# A small, stable set of "everyday" event ids — normal traffic mostly
# repeats these, keeping distinct_events low per window (as in real logs).
NORMAL_EVENT_IDS = [f"E{i}" for i in range(1, 9)]

NORMAL_MESSAGES = [
    "Activity resumed successfully",
    "Service bound to client",
    "Surface layout updated",
    "Received broadcast intent",
    "Connection established",
    "Cache refreshed",
    "Sensor reading updated",
    "Scheduled task executed",
]

ERROR_LEVELS = ["E"] * 5 + ["W"] * 4 + ["I"] * 1
ERROR_MESSAGES = [
    "Connection timed out after retries",
    "Out of memory while allocating buffer",
    "Unexpected null reference in handler",
    "Service crashed and was restarted",
    "Failed to acquire wake lock",
    "ANR: input dispatch not responding",
    "Disk I/O error writing cache",
    "Watchdog detected unresponsive thread",
]
ERROR_EVENT_IDS = [f"ERR{i}" for i in range(1, 5)]  # few distinct ids, but lots of E/W

DIVERSITY_MESSAGES = [
    "Unrecognized state transition",
    "Fallback path triggered",
    "Subsystem reinitialized unexpectedly",
    "Config mismatch detected",
    "Unusual event sequence observed",
    "Cross-service handshake retried",
    "Deprecated API path invoked",
    "Unexpected component wakeup",
]


def make_normal_log():
    level = random.choice(NORMAL_LEVELS)
    return {
        "level": level,
        "component": random.choice(COMPONENTS[:12]),  # normal traffic sticks to a smaller set
        "content": random.choice(NORMAL_MESSAGES),
        "event_id": random.choice(NORMAL_EVENT_IDS),
    }


def make_error_burst_log():
    level = random.choice(ERROR_LEVELS)
    message_pool = ERROR_MESSAGES if level in ("E", "W") else NORMAL_MESSAGES
    return {
        "level": level,
        "component": random.choice(COMPONENTS[:12]),
        "content": random.choice(message_pool),
        "event_id": random.choice(ERROR_EVENT_IDS),
    }


def make_volume_burst_log():
    # Same *kind* of traffic as normal, just fired in much larger quantity
    # per burst (see --burst-size) -> spikes total_logs without changing
    # the error/warn ratio or diversity much.
    return make_normal_log()


_diversity_counter = {"n": 0}


def make_diversity_burst_log():
    # Force a unique event_id and cycle through the full component list so
    # distinct_events / distinct_components spike sharply within the window.
    _diversity_counter["n"] += 1
    level = random.choice(["I", "D", "W"])
    return {
        "level": level,
        "component": random.choice(COMPONENTS),  # full pool, incl. rarely-used ones
        "content": random.choice(DIVERSITY_MESSAGES),
        "event_id": f"NOVEL{_diversity_counter['n']}",  # unique every time
    }


ANOMALY_BUILDERS = {
    "error": make_error_burst_log,
    "volume": make_volume_burst_log,
    "diversity": make_diversity_burst_log,
}


def main():
    parser = argparse.ArgumentParser(description="Feed random log entries into the dashboard API")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="base URL of the running app")
    parser.add_argument("--rate", type=float, default=2.0, help="logs per second (avg) during normal traffic")
    parser.add_argument("--burst-every", type=int, default=30,
                         help="roughly every N seconds, inject an anomalous burst")
    parser.add_argument("--burst-size", type=int, default=15,
                         help="how many log lines to fire rapidly during a burst")
    parser.add_argument("--anomaly-types", default="error,volume,diversity",
                         help="comma-separated list to choose from each burst: error,volume,diversity")
    parser.add_argument("--count", type=int, default=0,
                         help="stop after this many logs (0 = run forever)")
    args = parser.parse_args()

    endpoint = f"{args.url}/api/logs"
    delay = 1.0 / args.rate if args.rate > 0 else 1.0

    enabled_types = [t.strip() for t in args.anomaly_types.split(",") if t.strip() in ANOMALY_BUILDERS]
    if not enabled_types:
        raise SystemExit(f"--anomaly-types must be a subset of {list(ANOMALY_BUILDERS)}")

    sent = 0
    next_burst = time.time() + args.burst_every

    print(f"Posting to {endpoint} (~{args.rate}/s normal). "
          f"Bursts every ~{args.burst_every}s from {enabled_types}. Ctrl+C to stop.")
    try:
        while True:
            now = time.time()
            in_burst = now >= next_burst
            burst_type = random.choice(enabled_types) if in_burst else None
            n = args.burst_size if in_burst else 1

            for _ in range(n):
                payload = make_normal_log() if not in_burst else ANOMALY_BUILDERS[burst_type]()
                try:
                    resp = requests.post(endpoint, json=payload, timeout=3)
                    resp.raise_for_status()
                    tag = f"BURST:{burst_type:<9}" if in_burst else " " * 15
                    print(f"[{tag}] {payload['level']} {payload['component']:<20} {payload['content']}")
                except requests.RequestException as e:
                    print(f"  !! failed to post log: {e}")
                sent += 1
                if args.count and sent >= args.count:
                    print(f"Sent {sent} logs, stopping.")
                    return

            if in_burst:
                next_burst = now + args.burst_every  # schedule the next burst
            time.sleep(delay)
    except KeyboardInterrupt:
        print(f"\nStopped after sending {sent} logs.")


if __name__ == "__main__":
    main()
