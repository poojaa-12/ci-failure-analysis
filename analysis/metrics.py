from __future__ import annotations

import logging
import os
import threading

from prometheus_client import Counter, Histogram, start_http_server

from analysis.classifier import FailureType

logger = logging.getLogger(__name__)

failure_counter = Counter(
    "ci_failures_total",
    "Total CI failures by type",
    ["failure_type"],
)

triage_duration = Histogram(
    "ci_triage_duration_seconds",
    "Time to classify and triage a CI failure",
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120, 300, 600],
)

cluster_assignment = Counter(
    "ci_failure_cluster_assignments_total",
    "Batch clustering assignments per cluster id",
    ["cluster_id"],
)

_metrics_lock = threading.Lock()
_metrics_started = False


def track_failure(failure_type: FailureType, duration_seconds: float) -> None:
    failure_counter.labels(failure_type=failure_type.value).inc()
    triage_duration.observe(duration_seconds)


def record_cluster_assignments(labels: list[int]) -> None:
    for lbl in labels:
        cluster_assignment.labels(cluster_id=str(int(lbl))).inc()


def start_metrics_server(port: int = 8001, addr: str = "0.0.0.0") -> None:
    """Start Prometheus metrics HTTP server once (idempotent)."""
    if os.environ.get("DISABLE_METRICS_SERVER"):
        return
    global _metrics_started
    with _metrics_lock:
        if _metrics_started:
            return
        start_http_server(port, addr=addr)
        _metrics_started = True
        logger.info("Prometheus metrics listening on %s:%s", addr, port)
