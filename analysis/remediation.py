from analysis.classifier import FailureType

REMEDIATION_MAP: dict[FailureType, str] = {
    FailureType.FLAKY_TEST: (
        "Retry the test run automatically. "
        "If it fails 3+ times, add pytest-retry and mark the test @pytest.mark.flaky. "
        "Consider adding a fixed random seed."
    ),
    FailureType.DEP_INSTALL: (
        "Pin all dependency versions in requirements.txt. "
        "Run pip-compile to generate a locked requirements.txt. "
        "Check for pydantic v1 vs v2 conflicts if using FastAPI >= 0.100."
    ),
    FailureType.DEP_RUNTIME: (
        "Check import paths and installed package versions. "
        "Run pip show <package> to confirm installed version. "
        "Look for pydantic migration issues if using FastAPI."
    ),
    FailureType.ENV_CONFIG: (
        "Add missing environment variable to GitHub Actions secrets. "
        "Reference it in ci.yml under env: block. "
        "Use python-dotenv locally with a .env.example file."
    ),
    FailureType.ASSERTION: (
        "Review the test logic — the assertion is failing deterministically. "
        "Check if the function under test changed recently. "
        "Run pytest -v locally to reproduce."
    ),
    FailureType.UNKNOWN: (
        "Could not classify automatically. "
        "Open the full log and search for the first ERROR or FAILED line."
    ),
}


def suggest_remediation(failure_type: FailureType) -> str:
    return REMEDIATION_MAP.get(failure_type, REMEDIATION_MAP[FailureType.UNKNOWN])
