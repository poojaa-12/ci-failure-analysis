from __future__ import annotations

import numpy as np
from scipy.sparse import issparse
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score


def find_optimal_k(X, k_range: range | None = None) -> int:
    """
    Tune k using silhouette score. For small samples, k may be 2 only.
    """
    n_samples = X.shape[0]
    if n_samples < 2:
        return 1
    if n_samples == 2:
        return 2

    if k_range is None:
        low = 2 if n_samples < 5 else 3
        high = min(9, n_samples)
        k_range = range(low, high)

    best_k = min(next(iter(k_range), 2), n_samples - 1)
    best_score = -1.0

    for k in k_range:
        if k < 2 or k >= n_samples:
            continue
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X)
        if len(set(labels)) < 2:
            continue
        try:
            score = silhouette_score(X, labels)
        except ValueError:
            continue
        if score > best_score:
            best_score = score
            best_k = k

    if best_score < 0:
        return min(6, max(2, n_samples // 2))
    return best_k


def cluster_failures(
    failure_logs: list[str],
    n_clusters: int | None = None,
) -> tuple[np.ndarray, list[str]]:
    """
    TF-IDF + KMeans. Returns labels and one representative log per cluster.
    """
    if not failure_logs:
        return np.array([], dtype=int), []

    n_samples = len(failure_logs)
    vectorizer = TfidfVectorizer(
        max_features=2000,
        ngram_range=(1, 2),
        stop_words="english",
    )
    X = vectorizer.fit_transform(failure_logs)

    if n_samples == 1:
        return np.zeros(1, dtype=int), [failure_logs[0]]

    if n_clusters is None:
        n_clusters = find_optimal_k(X)

    n_clusters = max(1, min(int(n_clusters), n_samples))

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)

    X_dense = X.toarray() if issparse(X) else np.asarray(X)
    centers = kmeans.cluster_centers_
    representatives: list[str] = []

    for i in range(n_clusters):
        cluster_indices = np.where(labels == i)[0]
        if cluster_indices.size == 0:
            representatives.append("")
            continue
        centroid = centers[i]
        diffs = X_dense[cluster_indices] - centroid
        distances = np.linalg.norm(diffs, axis=1)
        rep_local = int(np.argmin(distances))
        rep_idx = cluster_indices[rep_local]
        representatives.append(failure_logs[rep_idx])

    return labels, representatives
