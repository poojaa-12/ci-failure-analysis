from analysis.classifier import FailureType, classify


def test_classify_flaky_first():
    text = "assert random.random() failed AssertionError"
    assert classify(text) == FailureType.FLAKY_TEST


def test_classify_dep_install():
    text = "ERROR: pip install failed: No matching distribution found for xyz"
    assert classify(text) == FailureType.DEP_INSTALL


def test_classify_env():
    text = "KeyError: 'MISSING_VAR' when reading os.environ['MISSING_VAR']"
    assert classify(text) == FailureType.ENV_CONFIG


def test_classify_assertion_not_before_env():
    text = "AssertionError: 1 == 2"
    assert classify(text) == FailureType.ASSERTION


def test_unknown():
    assert classify("nothing recognizable here") == FailureType.UNKNOWN
