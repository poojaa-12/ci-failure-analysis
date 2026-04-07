import os

# Avoid binding Prometheus port during pytest.
os.environ.setdefault("DISABLE_METRICS_SERVER", "1")
