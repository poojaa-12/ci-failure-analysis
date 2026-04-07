from analysis.clustering import cluster_failures


def test_cluster_smoke():
    logs = [
        "ModuleNotFoundError: no module named foo",
        "ModuleNotFoundError: no module named bar",
        "AssertionError: expected 1 == 2",
    ]
    labels, reps = cluster_failures(logs)
    assert len(labels) == 3
    assert len(reps) >= 1


def test_cluster_empty():
    labels, reps = cluster_failures([])
    assert list(labels) == []
    assert reps == []
