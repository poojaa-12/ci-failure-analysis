import re
from enum import Enum


class FailureType(str, Enum):
    FLAKY_TEST = "flaky_test"
    DEP_INSTALL = "dependency_install_error"
    DEP_RUNTIME = "dependency_runtime_error"
    ENV_CONFIG = "env_config_error"
    ASSERTION = "assertion_error"
    UNKNOWN = "unknown"


PATTERNS_BY_TYPE: dict[FailureType, list[str]] = {
    FailureType.FLAKY_TEST: [
        r"assert random\.random\(\)",
        r"AssertionError.*random",
        r"test.*flaky",
        r"timeout.*exceeded",
    ],
    FailureType.DEP_INSTALL: [
        r"ERROR: pip.*install",
        r"Could not find a version",
        r"No matching distribution",
        r"ModuleNotFoundError",
        r"incompatible.*version",
    ],
    FailureType.DEP_RUNTIME: [
        r"ImportError",
        r"cannot import name",
        r"pydantic.*validation",
        r"AttributeError.*module",
    ],
    FailureType.ENV_CONFIG: [
        r"KeyError.*environ",
        r"Environment variable.*not set",
        r"MISSING_VAR",
        r"os\.environ\[",
        r"APP_SECRET_KEY",
    ],
    FailureType.ASSERTION: [
        r"AssertionError",
        r"assert.*==.*False",
        r"FAILED tests/",
    ],
}

# Explicit evaluation order (flaky first, then install, runtime, env, assertion).
ORDERED_TYPES: list[FailureType] = [
    FailureType.FLAKY_TEST,
    FailureType.DEP_INSTALL,
    FailureType.DEP_RUNTIME,
    FailureType.ENV_CONFIG,
    FailureType.ASSERTION,
]


def classify(log_text: str) -> FailureType:
    for failure_type in ORDERED_TYPES:
        for pattern in PATTERNS_BY_TYPE[failure_type]:
            if re.search(pattern, log_text, re.IGNORECASE | re.DOTALL):
                return failure_type
    return FailureType.UNKNOWN
