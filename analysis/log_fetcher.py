"""
Fetch failed GitHub Actions workflow logs via the REST API.

Requires a token with `repo` and `actions:read` (classic PAT) or fine-grained
equivalent for the repository.
"""

from __future__ import annotations

import io
import os
import zipfile
from typing import Any

import httpx


def _parse_repo(repo_name: str) -> tuple[str, str]:
    parts = repo_name.strip().split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("GITHUB_REPO must be 'owner/repo'")
    return parts[0], parts[1]


def _github_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _extract_zip_log_text(data: bytes) -> str:
    buf = io.BytesIO(data)
    with zipfile.ZipFile(buf) as zf:
        chunks: list[str] = []
        for name in sorted(zf.namelist()):
            if name.endswith("/"):
                continue
            with zf.open(name) as f:
                chunks.append(f.read().decode("utf-8", errors="replace"))
    return "\n".join(chunks)


def download_workflow_run_logs(owner: str, repo: str, run_id: int, token: str) -> str:
    """
    GET /repos/{owner}/{repo}/actions/runs/{run_id}/logs
    Follows redirect to the zip artifact and returns concatenated text from all files.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/logs"
    headers = _github_headers(token)
    with httpx.Client(follow_redirects=True, timeout=120.0) as client:
        resp = client.get(url, headers=headers)
    resp.raise_for_status()
    return _extract_zip_log_text(resp.content)


def fetch_failed_run_logs(repo_name: str, limit: int = 100) -> list[dict[str, Any]]:
    """
    List failed workflow runs and download logs for each (up to `limit` runs).
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set")

    owner, repo = _parse_repo(repo_name)
    headers = _github_headers(token)
    base = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"

    failed_runs: list[dict[str, Any]] = []
    page = 1
    per_page = min(30, max(1, limit))

    with httpx.Client(timeout=60.0) as client:
        while len(failed_runs) < limit:
            params = {"status": "failure", "per_page": per_page, "page": page}
            r = client.get(base, headers=headers, params=params)
            r.raise_for_status()
            payload = r.json()
            runs: list[dict[str, Any]] = payload.get("workflow_runs") or []
            if not runs:
                break
            for run in runs:
                if len(failed_runs) >= limit:
                    break
                run_id = int(run["id"])
                created_at = str(run.get("created_at", ""))
                try:
                    log_text = download_workflow_run_logs(owner, repo, run_id, token)
                except httpx.HTTPError:
                    log_text = ""
                failed_runs.append(
                    {
                        "run_id": run_id,
                        "created_at": created_at,
                        "log_text": log_text,
                        "html_url": run.get("html_url", ""),
                    }
                )
            if len(runs) < per_page:
                break
            page += 1

    return failed_runs
