from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import Body, FastAPI, HTTPException
from pydantic import BaseModel, Field

from analysis.classifier import FailureType, classify
from analysis.log_fetcher import fetch_failed_run_logs
from analysis.clustering import cluster_failures
from analysis.llm_summarizer import summarize_log
from analysis.metrics import record_cluster_assignments, start_metrics_server, track_failure
from analysis.remediation import suggest_remediation


@asynccontextmanager
async def lifespan(app: FastAPI):
    metrics_port = int(os.environ.get("METRICS_PORT", "8001"))
    start_metrics_server(port=metrics_port)
    yield


app = FastAPI(title="CI Failure Analysis", lifespan=lifespan)


class LogRequest(BaseModel):
    run_id: str
    log_text: str
    timestamp: float | None = None
    include_llm_summary: bool = False


class AnalysisResult(BaseModel):
    run_id: str
    failure_type: FailureType
    cluster_id: int = Field(
        default=0,
        description="Batch clustering assigns ids; single-request analyze uses 0 as placeholder.",
    )
    remediation: str
    triage_time_seconds: float
    llm_summary: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalysisResult)
def analyze(request: LogRequest) -> AnalysisResult:
    start = time.perf_counter()

    failure_type = classify(request.log_text)
    remediation = suggest_remediation(failure_type)
    llm_summary = None
    if request.include_llm_summary:
        llm_summary = summarize_log(request.log_text)

    elapsed = time.perf_counter() - start
    track_failure(failure_type, elapsed)

    return AnalysisResult(
        run_id=request.run_id,
        failure_type=failure_type,
        cluster_id=0,
        remediation=remediation,
        triage_time_seconds=elapsed,
        llm_summary=llm_summary,
    )


class ClusterResponse(BaseModel):
    n_clusters: int
    labels: list[int]
    representatives: list[str]


@app.post("/cluster", response_model=ClusterResponse)
def cluster(logs: list[str] = Body(...)) -> ClusterResponse:
    labels_arr, representatives = cluster_failures(logs)
    labels_list = [int(x) for x in labels_arr.tolist()]
    record_cluster_assignments(labels_list)
    n_clusters = len(set(labels_list)) if labels_list else 0
    return ClusterResponse(
        n_clusters=n_clusters,
        labels=labels_list,
        representatives=representatives,
    )


@app.get("/failed-runs")
def failed_runs(limit: int = 20) -> list[dict]:
    """
    List recent failed workflow runs and downloaded log text (requires GITHUB_TOKEN + GITHUB_REPO).
    """
    repo = os.environ.get("GITHUB_REPO")
    if not repo:
        raise HTTPException(status_code=503, detail="GITHUB_REPO is not set")
    try:
        return fetch_failed_run_logs(repo, limit=min(limit, 100))
    except (RuntimeError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
